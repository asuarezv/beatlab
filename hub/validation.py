import re

COMPANY_NAME_ERROR = (
    "El nombre de la empresa solo puede incluir letras, números, espacios "
    "y los símbolos & y -."
)
USERNAME_ERROR = (
    "El usuario solo puede incluir letras y números, sin espacios ni símbolos."
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")
PERSON_NAME_ERROR = "El nombre y los apellidos son obligatorios."


def is_valid_company_name(name: str) -> bool:
    return bool(name) and all(ch.isalnum() or ch in " &-" for ch in name)


def is_valid_username(username: str) -> bool:
    return bool(username) and USERNAME_RE.fullmatch(username) is not None


def normalize_person_name(value: str) -> str:
    return (value or "").strip()


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
