import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email

COMPANY_NAME_ERROR = (
    "El nombre de la empresa solo puede incluir letras, números, espacios "
    "y los símbolos & y -."
)
USERNAME_ERROR = (
    "El usuario solo puede incluir letras y números, sin espacios ni símbolos."
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")
PERSON_NAME_ERROR = "El nombre y los apellidos son obligatorios."
EMAIL_REQUIRED = "El correo es obligatorio."
EMAIL_INVALID = "El correo no es válido."
OPERATOR_EMAIL_TAKEN = "Ese correo ya está dado de alta."
HUB_EMAIL_TAKEN = "Ese correo ya pertenece a una cuenta del Hub."
PROFILE_UPDATED = "Datos actualizados."
EMAIL_CHANGE_SENT = "Enviamos un código de verificación a ese correo."
PASSWORD_MISMATCH_ERROR = "Las contraseñas no coinciden."
CURRENT_PASSWORD_ERROR = "La contraseña actual no es correcta."
PASSWORD_CHANGE_REQUIRED = "La contraseña actual y la nueva son obligatorias."
HUB_ACCOUNT_ON_MONITOR = "Esta cuenta es del Hub. Entra en hub.nynusoft.com."
OPERATOR_ACCOUNT_ON_HUB = "Esta cuenta es de Operator. Entra en Monitor."
HUB_CREDENTIALS_ERROR = "Correo o contraseña no válidos."
HUB_LOGIN_REQUIRED = "El correo y la contraseña son obligatorios."
MONITOR_CREDENTIALS_ERROR = "Correo o contraseña no válidos."
MONITOR_LOGIN_REQUIRED = "El correo y la contraseña son obligatorios."
PASSWORD_CREATED = "Contraseña creada."
PASSWORD_UPDATED = "Contraseña actualizada."
OPERATOR_INVITE_SENT = "Enviamos la invitación a ese correo."
OPERATOR_ACTIVATE_OK = "Ya puedes entrar a Monitor con tu correo y contraseña."
OPERATOR_RECOVER_SENT = "Si el correo está dado de alta, te enviamos un código."
OPERATOR_INVITE_INVALID = "Este vínculo no es válido."
OPERATOR_GRANT_REQUIRED = "Confirma el código antes de elegir la contraseña."


def is_valid_company_name(name: str) -> bool:
    return bool(name) and all(ch.isalnum() or ch in " &-" for ch in name)


def is_valid_username(username: str) -> bool:
    return bool(username) and USERNAME_RE.fullmatch(username) is not None


def normalize_person_name(value: str) -> str:
    return (value or "").strip()


def validate_new_password(password, password2, user=None) -> str:
    password = (password or "").strip()
    password2 = (password2 or "").strip()
    if not password:
        raise ValueError(PASSWORD_CHANGE_REQUIRED)
    if password != password2:
        raise ValueError(PASSWORD_MISMATCH_ERROR)
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValueError(" ".join(exc.messages)) from exc
    return password


def email_already_used(
    email: str, *, exclude_operator_id=None, include_invites=False
) -> bool:
    from django.contrib.auth import get_user_model

    from .models import Operator, OperatorInviteChallenge

    email = (email or "").strip().lower()
    if not email:
        return False
    operators = Operator.objects.filter(email__iexact=email)
    if exclude_operator_id:
        operators = operators.exclude(pk=exclude_operator_id)
    if operators.exists():
        return True
    if include_invites and OperatorInviteChallenge.objects.filter(
        email__iexact=email
    ).exists():
        return True
    users = get_user_model().objects.filter(email__iexact=email)
    if exclude_operator_id:
        users = users.exclude(operator_profiles__pk=exclude_operator_id)
    return users.exists()


def assert_email_available(
    email: str, *, exclude_operator_id=None, exclude_user_id=None
) -> None:
    from django.contrib.auth import get_user_model

    from .models import Operator, OperatorInviteChallenge

    email = (email or "").strip().lower()
    if not email:
        return
    operators = Operator.objects.filter(email__iexact=email)
    if exclude_operator_id:
        operators = operators.exclude(pk=exclude_operator_id)
    if operators.exists():
        raise ValueError(OPERATOR_EMAIL_TAKEN)
    if OperatorInviteChallenge.objects.filter(email__iexact=email).exists():
        raise ValueError(OPERATOR_EMAIL_TAKEN)
    users = get_user_model().objects.filter(email__iexact=email)
    if exclude_operator_id:
        users = users.exclude(operator_profiles__pk=exclude_operator_id)
    if exclude_user_id:
        users = users.exclude(pk=exclude_user_id)
    if users.exists():
        raise ValueError(HUB_EMAIL_TAKEN)


def validate_profile_fields(
    *, first_name, last_name, email, exclude_operator_id=None, exclude_user_id=None
):
    first_name = normalize_person_name(first_name)
    last_name = normalize_person_name(last_name)
    email = (email or "").strip().lower()
    if not first_name or not last_name:
        raise ValueError(PERSON_NAME_ERROR)
    if not email:
        raise ValueError(EMAIL_REQUIRED)
    try:
        validate_email(email)
    except DjangoValidationError as exc:
        raise ValueError(EMAIL_INVALID) from exc
    assert_email_available(
        email,
        exclude_operator_id=exclude_operator_id,
        exclude_user_id=exclude_user_id,
    )
    return first_name, last_name, email
