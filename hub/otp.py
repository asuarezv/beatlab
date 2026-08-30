import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils import timezone

from .emails import send_register_otp
from .models import SignupChallenge
from .validation import (
    COMPANY_NAME_ERROR,
    USERNAME_ERROR,
    is_valid_company_name,
    is_valid_username,
)

logger = logging.getLogger(__name__)

OTP_LENGTH = 6


def hash_otp(otp: str) -> str:
    raw = f"{settings.SECRET_KEY}:register-otp:{otp.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _ttl() -> int:
    return int(getattr(settings, "REGISTER_OTP_TTL_SECONDS", 600))


def _max_attempts() -> int:
    return int(getattr(settings, "REGISTER_OTP_MAX_ATTEMPTS", 5))


def validate_signup_fields(*, company_name, username, email, password, password2):
    company_name = (company_name or "").strip()
    username = username or ""
    email = (email or "").strip().lower()
    password = (password or "").strip()
    password2 = (password2 or "").strip()
    if not company_name or not username or not email or not password:
        raise ValueError("Empresa, usuario, correo y contraseña son obligatorios.")
    if not is_valid_company_name(company_name):
        raise ValueError(COMPANY_NAME_ERROR)
    if not is_valid_username(username):
        raise ValueError(USERNAME_ERROR)
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValueError("El correo no es válido.") from None
    if password != password2:
        raise ValueError("Las contraseñas no coinciden.")
    try:
        validate_password(password)
    except DjangoValidationError as exc:
        raise ValueError(" ".join(exc.messages)) from exc
    return company_name, username, email, password


def issue_signup_otp(*, company_name, username, email, password) -> dict:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    if User.objects.filter(username__iexact=username).exists():
        raise ValueError("Ese usuario ya está en uso.")
    if User.objects.filter(email__iexact=email).exists():
        raise ValueError("Ese correo ya está en uso.")

    otp = "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))
    ttl = _ttl()
    SignupChallenge.objects.filter(email=email).delete()
    SignupChallenge.objects.create(
        email=email,
        username=username,
        company_name=company_name,
        password_hash=make_password(password),
        code_hash=hash_otp(otp),
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )
    try:
        send_register_otp(email, username, otp, ttl)
    except Exception:
        SignupChallenge.objects.filter(email=email).delete()
        logger.exception("No se pudo enviar el OTP a %s", email)
        raise ValueError("No se pudo enviar el código. Inténtalo de nuevo.") from None
    return {
        "email": email,
        "expires_in": ttl,
        "detail": "Te enviamos un código de verificación a tu correo.",
    }


def consume_signup_otp(*, email, otp):
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    challenge = SignupChallenge.objects.filter(email=email).first()
    if not challenge:
        raise ValueError("Solicita un código nuevo.")
    if timezone.now() >= challenge.expires_at:
        challenge.delete()
        raise ValueError("El código caducó. Solicita uno nuevo.")
    if challenge.attempts >= _max_attempts():
        challenge.delete()
        raise ValueError("Demasiados intentos. Solicita un código nuevo.")
    if not secrets.compare_digest(challenge.code_hash, hash_otp(otp)):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        raise ValueError("El código no es válido.")
    return challenge
