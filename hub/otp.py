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

from .emails import (
    send_email_change_otp,
    send_monitor_otp,
    send_operator_invite_otp,
    send_register_otp,
)
from .models import (
    EmailChangeChallenge,
    Operator,
    OperatorInviteChallenge,
    OperatorOtpChallenge,
    SignupChallenge,
)
from .validation import (
    COMPANY_NAME_ERROR,
    EMAIL_CHANGE_SENT,
    HUB_ACCOUNT_ON_MONITOR,
    MONITOR_CREDENTIALS_ERROR,
    MONITOR_LOGIN_REQUIRED,
    OPERATOR_EMAIL_TAKEN,
    PERSON_NAME_ERROR,
    USERNAME_ERROR,
    assert_email_available,
    email_already_used,
    is_valid_company_name,
    is_valid_username,
    normalize_person_name,
)

logger = logging.getLogger(__name__)

OTP_LENGTH = 6


def hash_otp(otp: str, purpose: str = "register-otp") -> str:
    raw = f"{settings.SECRET_KEY}:{purpose}:{otp.strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _new_otp() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(OTP_LENGTH))


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
    if email_already_used(email):
        raise ValueError("Ese correo ya está en uso.")

    otp = _new_otp()
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


def _monitor_generic(email: str, ttl: int) -> dict:
    return {
        "email": email,
        "expires_in": ttl,
        "detail": "Si el correo está dado de alta, te enviamos un código.",
    }


def _hub_admin_for_email(email: str):
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    return (
        get_user_model()
        .objects.filter(email__iexact=email, is_active=True)
        .filter(Q(is_staff=True) | Q(is_superuser=True))
        .first()
    )


def issue_monitor_otp(*, email) -> dict:
    email = (email or "").strip().lower()
    ttl = _ttl()
    if not email:
        raise ValueError("El correo es obligatorio.")
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValueError("El correo no es válido.") from None

    operator = (
        Operator.objects.filter(email__iexact=email)
        .select_related("user")
        .first()
    )
    if not operator or not operator.user.is_active:
        if _hub_admin_for_email(email):
            raise ValueError(HUB_ACCOUNT_ON_MONITOR)
        return _monitor_generic(email, ttl)

    otp = _new_otp()
    OperatorOtpChallenge.objects.filter(email=email).delete()
    OperatorOtpChallenge.objects.create(
        email=email,
        code_hash=hash_otp(otp, "monitor-otp"),
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )
    try:
        send_monitor_otp(email, operator.display_name(), otp, ttl)
    except Exception:
        OperatorOtpChallenge.objects.filter(email=email).delete()
        logger.exception("No se pudo enviar el OTP de Monitor a %s", email)
        raise ValueError("No se pudo enviar el código. Inténtalo de nuevo.") from None
    return _monitor_generic(email, ttl)


def issue_operator_invite_otp(*, company, first_name, last_name, email) -> dict:
    first_name = normalize_person_name(first_name)
    last_name = normalize_person_name(last_name)
    email = (email or "").strip().lower()
    if not first_name or not last_name:
        raise ValueError(PERSON_NAME_ERROR)
    if not email:
        raise ValueError("El correo es obligatorio.")
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValueError("El correo no es válido.") from None
    if Operator.objects.filter(email__iexact=email).exists():
        raise ValueError(OPERATOR_EMAIL_TAKEN)
    if email_already_used(email):
        raise ValueError("Ese correo ya está en uso.")

    otp = _new_otp()
    ttl = _ttl()
    OperatorInviteChallenge.objects.filter(email=email).delete()
    OperatorInviteChallenge.objects.create(
        company=company,
        first_name=first_name,
        last_name=last_name,
        email=email,
        code_hash=hash_otp(otp, "operator-invite-otp"),
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )
    try:
        send_operator_invite_otp(email, first_name, otp, ttl)
    except Exception:
        OperatorInviteChallenge.objects.filter(email=email).delete()
        logger.exception("No se pudo enviar el OTP de alta de Operator a %s", email)
        raise ValueError("No se pudo enviar el código. Inténtalo de nuevo.") from None
    return {
        "email": email,
        "expires_in": ttl,
        "detail": "Enviamos un código de verificación a ese correo.",
    }


def consume_operator_invite_otp(*, email, otp) -> OperatorInviteChallenge:
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    challenge = OperatorInviteChallenge.objects.filter(email=email).first()
    if not challenge:
        raise ValueError("Solicita un código nuevo.")
    if timezone.now() >= challenge.expires_at:
        challenge.delete()
        raise ValueError("El código caducó. Solicita uno nuevo.")
    if challenge.attempts >= _max_attempts():
        challenge.delete()
        raise ValueError("Demasiados intentos. Solicita un código nuevo.")
    if not secrets.compare_digest(
        challenge.code_hash,
        hash_otp(otp, "operator-invite-otp"),
    ):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        raise ValueError("El código no es válido.")
    return challenge


def consume_monitor_otp(*, email, otp) -> Operator:
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    if _hub_admin_for_email(email) and not Operator.objects.filter(
        email__iexact=email
    ).exists():
        raise ValueError(HUB_ACCOUNT_ON_MONITOR)
    challenge = OperatorOtpChallenge.objects.filter(email=email).first()
    if not challenge:
        raise ValueError("Solicita un código nuevo.")
    if timezone.now() >= challenge.expires_at:
        challenge.delete()
        raise ValueError("El código caducó. Solicita uno nuevo.")
    if challenge.attempts >= _max_attempts():
        challenge.delete()
        raise ValueError("Demasiados intentos. Solicita un código nuevo.")
    if not secrets.compare_digest(challenge.code_hash, hash_otp(otp, "monitor-otp")):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        raise ValueError("El código no es válido.")
    operator = (
        Operator.objects.filter(email__iexact=email)
        .select_related("user", "company")
        .first()
    )
    challenge.delete()
    if not operator or not operator.user.is_active:
        raise ValueError("Solicita un código nuevo.")
    return operator


def issue_email_change_otp(*, email, name, user=None, operator=None) -> dict:
    email = (email or "").strip().lower()
    name = (name or "").strip() or email
    if user is None and operator is None:
        raise ValueError("Solicita un código nuevo.")
    if user is not None:
        assert_email_available(email, exclude_user_id=user.pk)
        EmailChangeChallenge.objects.filter(user=user).delete()
    if operator is not None:
        assert_email_available(email, exclude_operator_id=operator.pk)
        EmailChangeChallenge.objects.filter(operator=operator).delete()
    EmailChangeChallenge.objects.filter(email=email).delete()

    otp = _new_otp()
    ttl = _ttl()
    EmailChangeChallenge.objects.create(
        user=user,
        operator=operator,
        email=email,
        code_hash=hash_otp(otp, "email-change-otp"),
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )
    try:
        send_email_change_otp(email, name, otp, ttl)
    except Exception:
        EmailChangeChallenge.objects.filter(email=email).delete()
        logger.exception("No se pudo enviar el OTP de cambio de correo a %s", email)
        raise ValueError("No se pudo enviar el código. Inténtalo de nuevo.") from None
    return {
        "pending_email": email,
        "email": email,
        "expires_in": ttl,
        "detail": EMAIL_CHANGE_SENT,
    }


def consume_email_change_otp(*, email, otp, user=None, operator=None) -> EmailChangeChallenge:
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    qs = EmailChangeChallenge.objects.filter(email=email)
    if user is not None:
        qs = qs.filter(user=user, operator__isnull=True)
    elif operator is not None:
        qs = qs.filter(operator=operator)
    else:
        raise ValueError("Solicita un código nuevo.")
    challenge = qs.first()
    if not challenge:
        raise ValueError("Solicita un código nuevo.")
    if timezone.now() >= challenge.expires_at:
        challenge.delete()
        raise ValueError("El código caducó. Solicita uno nuevo.")
    if challenge.attempts >= _max_attempts():
        challenge.delete()
        raise ValueError("Demasiados intentos. Solicita un código nuevo.")
    if not secrets.compare_digest(
        challenge.code_hash,
        hash_otp(otp, "email-change-otp"),
    ):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        raise ValueError("El código no es válido.")
    return challenge


def consume_monitor_password(*, email, password) -> Operator:
    email = (email or "").strip().lower()
    password = (password or "").strip()
    if not email or not password:
        raise ValueError(MONITOR_LOGIN_REQUIRED)
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValueError("El correo no es válido.") from None
    operator = (
        Operator.objects.filter(email__iexact=email)
        .select_related("user", "company")
        .first()
    )
    if not operator or not operator.user.is_active:
        if _hub_admin_for_email(email):
            raise ValueError(HUB_ACCOUNT_ON_MONITOR)
        raise ValueError(MONITOR_CREDENTIALS_ERROR)
    if not operator.check_password(password):
        raise ValueError(MONITOR_CREDENTIALS_ERROR)
    return operator
