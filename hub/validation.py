import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError

COMPANY_NAME_ERROR = (
    "El nombre de la empresa solo puede incluir letras, números, espacios "
    "y los símbolos & y -."
)
USERNAME_ERROR = (
    "El usuario solo puede incluir letras y números, sin espacios ni símbolos."
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")
PERSON_NAME_ERROR = "El nombre y los apellidos son obligatorios."
PASSWORD_MISMATCH_ERROR = "Las contraseñas no coinciden."
CURRENT_PASSWORD_ERROR = "La contraseña actual no es correcta."
PASSWORD_CHANGE_REQUIRED = "La contraseña actual y la nueva son obligatorias."


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


def email_already_used(email: str, *, exclude_operator_id=None) -> bool:
    from django.contrib.auth import get_user_model

    from .models import Operator

    email = (email or "").strip().lower()
    if not email:
        return False
    operators = Operator.objects.filter(email__iexact=email)
    if exclude_operator_id:
        operators = operators.exclude(pk=exclude_operator_id)
    if operators.exists():
        return True
    users = get_user_model().objects.filter(email__iexact=email)
    if exclude_operator_id:
        users = users.exclude(operator_profiles__pk=exclude_operator_id)
    return users.exists()
