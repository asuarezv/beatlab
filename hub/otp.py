import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.utils import timezone

from .emails import (
    operator_invite_url,
    operator_recover_url,
    send_email_change_otp,
    send_monitor_otp,
    send_operator_invite,
    send_operator_recover,
    send_register_otp,
)
from .models import (
    EmailChangeChallenge,
    Operator,
    OperatorInviteChallenge,
    OperatorOtpChallenge,
    SignupChallenge,
)
from .tokens import MonitorActor
from .validation import (
    COMPANY_NAME_ERROR,
    EMAIL_CHANGE_SENT,
    EMAIL_INVALID,
    HUB_ACCOUNT_ON_MONITOR,
    MONITOR_CREDENTIALS_ERROR,
    MONITOR_LOGIN_REQUIRED,
    OPERATOR_ACTIVATE_OK,
    OPERATOR_EMAIL_TAKEN,
    OPERATOR_GRANT_REQUIRED,
    OPERATOR_INVITE_INVALID,
    OPERATOR_INVITE_SENT,
    OPERATOR_RECOVER_SENT,
    PERSON_NAME_ERROR,
    USERNAME_ERROR,
    assert_email_available,
    email_already_used,
    is_valid_company_name,
    is_valid_username,
    normalize_person_name,
    validate_new_password,
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
    if email_already_used(email, include_invites=True):
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


def _company_for_hub_admin(user):
    from .models import Membership

    membership = (
        Membership.objects.filter(user=user)
        .select_related("company")
        .order_by("id")
        .first()
    )
    return membership.company if membership else None


def _hub_admin_display_name(user) -> str:
    full = f"{user.first_name} {user.last_name}".strip()
    return full or user.username


def _hub_admin_monitor_actor(*, email=None) -> MonitorActor | None:
    from django.contrib.auth import get_user_model
    from django.db.models import Q

    if not email:
        return None
    user = (
        get_user_model()
        .objects.filter(is_active=True)
        .filter(Q(is_staff=True) | Q(is_superuser=True))
        .filter(email__iexact=email)
        .first()
    )
    if not user:
        return None
    company = _company_for_hub_admin(user)
    if not company:
        return None
    return MonitorActor.from_admin(user, company)


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
    admin = None
    recipient_name = ""
    if operator and operator.user.is_active:
        recipient_name = operator.display_name()
    else:
        admin = _hub_admin_monitor_actor(email=email)
        if not admin:
            return _monitor_generic(email, ttl)
        recipient_name = _hub_admin_display_name(admin.user)

    otp = _new_otp()
    OperatorOtpChallenge.objects.filter(email=email).delete()
    OperatorOtpChallenge.objects.create(
        email=email,
        code_hash=hash_otp(otp, "monitor-otp"),
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )
    try:
        send_monitor_otp(email, recipient_name, otp, ttl)
    except Exception:
        OperatorOtpChallenge.objects.filter(email=email).delete()
        logger.exception("No se pudo enviar el OTP de Monitor a %s", email)
        raise ValueError("No se pudo enviar el código. Inténtalo de nuevo.") from None
    return _monitor_generic(email, ttl)


ACTIVATE_SALT = "operator-activate"
INVITE_OTP_PURPOSE = "operator-invite-otp"
RECOVER_OTP_PURPOSE = "operator-recover-otp"


def _new_invite_token() -> str:
    for _ in range(8):
        token = secrets.token_urlsafe(16)
        if not OperatorInviteChallenge.objects.filter(token=token).exists():
            return token
    raise RuntimeError("No se pudo generar el vínculo.")


def _assert_live_otp(challenge, otp, purpose: str):
    otp = (otp or "").strip()
    if timezone.now() >= challenge.expires_at:
        challenge.delete()
        raise ValueError("El código caducó. Solicita uno nuevo.")
    if challenge.attempts >= _max_attempts():
        challenge.delete()
        raise ValueError("Demasiados intentos. Solicita un código nuevo.")
    if not secrets.compare_digest(challenge.code_hash, hash_otp(otp, purpose)):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        raise ValueError("El código no es válido.")
    return challenge


def issue_activate_grant(*, kind, email, challenge_id) -> str:
    return TimestampSigner(salt=ACTIVATE_SALT).sign_object(
        {"k": kind, "e": email, "c": challenge_id}
    )


def read_activate_grant(grant: str) -> dict:
    grant = (grant or "").strip()
    if not grant:
        raise ValueError(OPERATOR_GRANT_REQUIRED)
    try:
        data = TimestampSigner(salt=ACTIVATE_SALT).unsign_object(
            grant, max_age=_ttl()
        )
    except SignatureExpired:
        raise ValueError("El código caducó. Solicita uno nuevo.") from None
    except BadSignature:
        raise ValueError(OPERATOR_GRANT_REQUIRED) from None
    if not isinstance(data, dict) or data.get("k") not in {"invite", "recover"}:
        raise ValueError(OPERATOR_GRANT_REQUIRED)
    return data


def issue_operator_invite_otp(
    *, company, first_name, last_name, email, inviter_name=""
) -> dict:
    first_name = normalize_person_name(first_name)
    last_name = normalize_person_name(last_name)
    email = (email or "").strip().lower()
    inviter_name = (inviter_name or "").strip()
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
    token = _new_invite_token()
    OperatorInviteChallenge.objects.filter(email=email).delete()
    challenge = OperatorInviteChallenge.objects.create(
        company=company,
        first_name=first_name,
        last_name=last_name,
        email=email,
        inviter_name=inviter_name,
        token=token,
        code_hash=hash_otp(otp, INVITE_OTP_PURPOSE),
        expires_at=timezone.now() + timedelta(seconds=ttl),
    )
    invite_url = operator_invite_url(challenge.token)
    try:
        send_operator_invite(
            email,
            name=first_name,
            inviter_name=inviter_name or company.name,
            company_name=company.name,
            otp=otp,
            ttl_seconds=ttl,
            invite_url=invite_url,
        )
    except Exception:
        OperatorInviteChallenge.objects.filter(email=email).delete()
        logger.exception("No se pudo enviar la invitación de Operator a %s", email)
        raise ValueError("No se pudo enviar la invitación. Inténtalo de nuevo.") from None
    return {
        "email": email,
        "expires_in": ttl,
        "detail": OPERATOR_INVITE_SENT,
    }


def lookup_operator_invite(*, token=None, email=None) -> OperatorInviteChallenge:
    token = (token or "").strip()
    email = (email or "").strip().lower()
    if token:
        challenge = OperatorInviteChallenge.objects.filter(token=token).select_related(
            "company"
        ).first()
        if not challenge:
            raise ValueError(OPERATOR_INVITE_INVALID)
        return challenge
    if email:
        challenge = OperatorInviteChallenge.objects.filter(email=email).select_related(
            "company"
        ).first()
        if challenge:
            return challenge
    raise ValueError(OPERATOR_INVITE_INVALID)


def invite_info_payload(challenge: OperatorInviteChallenge) -> dict:
    expired = timezone.now() >= challenge.expires_at
    return {
        "email": challenge.email,
        "first_name": challenge.first_name,
        "company_name": challenge.company.name,
        "token": challenge.token,
        "expired": expired,
    }


def check_operator_invite_otp(*, token=None, email=None, otp) -> OperatorInviteChallenge:
    challenge = lookup_operator_invite(token=token, email=email)
    if timezone.now() >= challenge.expires_at:
        raise ValueError("El código caducó. Solicita uno nuevo.")
    if challenge.attempts >= _max_attempts():
        raise ValueError("Demasiados intentos. Solicita un código nuevo.")
    otp = (otp or "").strip()
    if not secrets.compare_digest(
        challenge.code_hash,
        hash_otp(otp, INVITE_OTP_PURPOSE),
    ):
        challenge.attempts += 1
        challenge.save(update_fields=["attempts"])
        raise ValueError("El código no es válido.")
    return challenge


def check_operator_recover_otp(*, email, otp) -> Operator:
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
    if _hub_admin_for_email(email) and not Operator.objects.filter(
        email__iexact=email
    ).exists():
        raise ValueError(HUB_ACCOUNT_ON_MONITOR)
    challenge = OperatorOtpChallenge.objects.filter(email=email).first()
    if not challenge:
        raise ValueError("Solicita un código nuevo.")
    _assert_live_otp(challenge, otp, RECOVER_OTP_PURPOSE)
    operator = (
        Operator.objects.filter(email__iexact=email)
        .select_related("user", "company")
        .first()
    )
    if not operator or not operator.user.is_active:
        raise ValueError("Solicita un código nuevo.")
    return operator


def verify_operator_access_otp(*, token=None, email=None, otp) -> dict:
    token = (token or "").strip()
    email = (email or "").strip().lower()
    if not token and not email:
        raise ValueError("El correo es obligatorio.")
    if token or OperatorInviteChallenge.objects.filter(email=email).exists():
        challenge = check_operator_invite_otp(token=token, email=email, otp=otp)
        return {
            "grant": issue_activate_grant(
                kind="invite",
                email=challenge.email,
                challenge_id=challenge.pk,
            ),
            "email": challenge.email,
            "first_name": challenge.first_name,
            "detail": "Elige la contraseña que vas a usar en Monitor.",
        }
    operator = check_operator_recover_otp(email=email, otp=otp)
    recover = OperatorOtpChallenge.objects.filter(email=operator.email).first()
    return {
        "grant": issue_activate_grant(
            kind="recover",
            email=operator.email,
            challenge_id=recover.pk if recover else operator.pk,
        ),
        "email": operator.email,
        "first_name": operator.first_name,
        "detail": "Elige la contraseña que vas a usar en Monitor.",
    }


def _create_operator_from_invite(challenge, password: str) -> Operator:
    import uuid

    from django.contrib.auth import get_user_model

    User = get_user_model()
    user = User(
        username=f"op{uuid.uuid4().hex[:20]}",
        email=challenge.email,
        first_name=challenge.first_name,
        last_name=challenge.last_name,
    )
    user.set_unusable_password()
    user.save()
    operator = Operator.objects.create(
        company=challenge.company,
        user=user,
        first_name=challenge.first_name,
        last_name=challenge.last_name,
        email=challenge.email,
    )
    operator.set_password(password)
    operator.save(update_fields=["password_hash"])
    return operator


def activate_operator_password(*, grant, password, password2) -> dict:
    data = read_activate_grant(grant)
    password = validate_new_password(password, password2)
    if data["k"] == "invite":
        challenge = (
            OperatorInviteChallenge.objects.filter(pk=data["c"], email=data["e"])
            .select_related("company")
            .first()
        )
        if not challenge:
            raise ValueError("Solicita un código nuevo.")
        if timezone.now() >= challenge.expires_at:
            raise ValueError("El código caducó. Solicita uno nuevo.")
        try:
            with transaction.atomic():
                operator = _create_operator_from_invite(challenge, password)
                challenge.delete()
        except IntegrityError:
            raise ValueError(OPERATOR_EMAIL_TAKEN) from None
        return {
            "email": operator.email,
            "detail": OPERATOR_ACTIVATE_OK,
            "created": True,
        }
    operator = (
        Operator.objects.filter(email__iexact=data["e"])
        .select_related("user")
        .first()
    )
    if not operator or not operator.user.is_active:
        raise ValueError("Solicita un código nuevo.")
    operator.set_password(password)
    operator.save(update_fields=["password_hash"])
    OperatorOtpChallenge.objects.filter(email__iexact=operator.email).delete()
    return {
        "email": operator.email,
        "detail": OPERATOR_ACTIVATE_OK,
        "created": False,
    }


def _refresh_invite_otp(challenge: OperatorInviteChallenge) -> tuple[str, int]:
    otp = _new_otp()
    ttl = _ttl()
    challenge.code_hash = hash_otp(otp, INVITE_OTP_PURPOSE)
    challenge.expires_at = timezone.now() + timedelta(seconds=ttl)
    challenge.attempts = 0
    challenge.save(update_fields=["code_hash", "expires_at", "attempts"])
    return otp, ttl


def issue_operator_recover_otp(*, email) -> dict:
    email = (email or "").strip().lower()
    ttl = _ttl()
    if not email:
        raise ValueError("El correo es obligatorio.")
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValueError("El correo no es válido.") from None
    if _hub_admin_for_email(email) and not Operator.objects.filter(
        email__iexact=email
    ).exists():
        raise ValueError(HUB_ACCOUNT_ON_MONITOR)

    operator = (
        Operator.objects.filter(email__iexact=email)
        .select_related("user")
        .first()
    )
    invite = (
        OperatorInviteChallenge.objects.filter(email=email)
        .select_related("company")
        .first()
    )
    if operator and operator.user.is_active:
        otp = _new_otp()
        OperatorOtpChallenge.objects.filter(email=email).delete()
        OperatorOtpChallenge.objects.create(
            email=email,
            code_hash=hash_otp(otp, RECOVER_OTP_PURPOSE),
            expires_at=timezone.now() + timedelta(seconds=ttl),
        )
        try:
            send_operator_recover(
                email,
                name=operator.display_name(),
                otp=otp,
                ttl_seconds=ttl,
                recover_url=operator_recover_url(email),
            )
        except Exception:
            OperatorOtpChallenge.objects.filter(email=email).delete()
            logger.exception("No se pudo enviar el OTP de recuperación a %s", email)
            raise ValueError("No se pudo enviar el código. Inténtalo de nuevo.") from None
        return {
            "email": email,
            "expires_in": ttl,
            "detail": OPERATOR_RECOVER_SENT,
        }
    if invite:
        otp, ttl = _refresh_invite_otp(invite)
        try:
            send_operator_recover(
                email,
                name=invite.first_name,
                otp=otp,
                ttl_seconds=ttl,
                recover_url=operator_invite_url(invite.token),
            )
        except Exception:
            logger.exception("No se pudo enviar el OTP de recuperación a %s", email)
            raise ValueError("No se pudo enviar el código. Inténtalo de nuevo.") from None
        return {
            "email": email,
            "expires_in": ttl,
            "detail": OPERATOR_RECOVER_SENT,
        }
    return {
        "email": email,
        "expires_in": ttl,
        "detail": OPERATOR_RECOVER_SENT,
    }


def consume_monitor_otp(*, email, otp) -> MonitorActor:
    email = (email or "").strip().lower()
    otp = (otp or "").strip()
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
    if operator and operator.user.is_active:
        challenge.delete()
        return MonitorActor.from_operator(operator)
    admin = _hub_admin_monitor_actor(email=email)
    challenge.delete()
    if admin:
        return admin
    raise ValueError("Solicita un código nuevo.")


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


def consume_monitor_password(*, email, password) -> MonitorActor:
    email = (email or "").strip()
    password = (password or "").strip()
    if not email or not password:
        raise ValueError(MONITOR_LOGIN_REQUIRED)
    email = email.lower()
    try:
        validate_email(email)
    except DjangoValidationError:
        raise ValueError(EMAIL_INVALID) from None
    operator = (
        Operator.objects.filter(email__iexact=email)
        .select_related("user", "company")
        .first()
    )
    if operator:
        if not operator.user.is_active or not operator.check_password(password):
            raise ValueError(MONITOR_CREDENTIALS_ERROR)
        return MonitorActor.from_operator(operator)
    admin = _hub_admin_monitor_actor(email=email)
    if admin and admin.check_password(password):
        return admin
    raise ValueError(MONITOR_CREDENTIALS_ERROR)
