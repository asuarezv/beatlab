import re

COMPANY_NAME_ERROR = (
    "El nombre de la empresa solo puede incluir letras, números, espacios "
    "y los símbolos & y -."
)
USERNAME_ERROR = (
    "El usuario solo puede incluir letras y números, sin espacios ni símbolos."
)

USERNAME_RE = re.compile(r"^[A-Za-z0-9]+$")


def is_valid_company_name(name: str) -> bool:
    return bool(name) and all(ch.isalnum() or ch in " &-" for ch in name)


def is_valid_username(username: str) -> bool:
    return bool(username) and USERNAME_RE.fullmatch(username) is not None
