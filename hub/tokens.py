import hashlib
import uuid
from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

from django.contrib.auth import get_user_model

from .models import Membership, Operator, System

SYSTEM_AUD = "beatlab-system"
MONITOR_AUD = "beatlab-monitor"
ISSUER = "beatlab"
OPERATOR_TTL = timedelta(days=30)
MONITOR_ROLE_OPERATOR = "operator"
MONITOR_ROLE_ADMIN = "admin"


class MonitorActor:
    def __init__(self, *, role, user, company, operator=None):
        self.role = role
        self.user = user
        self.company = company
        self.operator = operator

    @classmethod
    def from_operator(cls, operator: Operator):
        return cls(
            role=MONITOR_ROLE_OPERATOR,
            user=operator.user,
            company=operator.company,
            operator=operator,
        )

    @classmethod
    def from_admin(cls, user, company):
        return cls(role=MONITOR_ROLE_ADMIN, user=user, company=company)

    @property
    def company_id(self) -> int:
        return self.company.id

    @property
    def id(self) -> int:
        if self.operator is not None:
            return self.operator.id
        return self.user.id

    @property
    def first_name(self) -> str:
        if self.operator is not None:
            return self.operator.first_name
        return self.user.first_name

    @property
    def last_name(self) -> str:
        if self.operator is not None:
            return self.operator.last_name
        return self.user.last_name

    @property
    def email(self) -> str:
        if self.operator is not None:
            return self.operator.email
        return self.user.email or ""

    def display_name(self) -> str:
        if self.operator is not None:
            return self.operator.display_name()
        full = f"{self.user.first_name} {self.user.last_name}".strip()
        return full or self.user.username

    def has_password(self) -> bool:
        if self.operator is not None:
            return self.operator.has_password()
        return self.user.has_usable_password()

    def check_password(self, raw: str) -> bool:
        if self.operator is not None:
            return self.operator.check_password(raw)
        return self.user.check_password(raw)

    def set_password(self, raw: str) -> None:
        if self.operator is not None:
            self.operator.set_password(raw)
            return
        self.user.set_password(raw)

    def save_password(self) -> None:
        if self.operator is not None:
            self.operator.save(update_fields=["password_hash"])
            return
        self.user.save(update_fields=["password"])


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def issue_system_jwt(system: System) -> str:
    now = timezone.now()
    payload = {
        "iss": ISSUER,
        "aud": SYSTEM_AUD,
        "sub": str(system.id),
        "cid": system.company_id,
        "slug": system.slug,
        "jti": uuid.uuid4().hex,
        "iat": int(now.timestamp()),
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
    system.jwt_hash = _hash_token(token)
    system.jwt_issued_at = now
    system.save(update_fields=["jwt_hash", "jwt_issued_at"])
    return token


def verify_system_jwt(token: str) -> System | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            audience=SYSTEM_AUD,
            issuer=ISSUER,
        )
        system = System.objects.select_related("company").get(pk=int(payload["sub"]))
    except (jwt.InvalidTokenError, System.DoesNotExist, ValueError, TypeError, KeyError):
        return None
    if not system.jwt_hash or system.jwt_hash != _hash_token(token):
        return None
    return system


def issue_operator_jwt(operator: Operator) -> str:
    return issue_monitor_jwt(MonitorActor.from_operator(operator))


def issue_monitor_jwt(actor: MonitorActor) -> str:
    now = timezone.now()
    if actor.operator is not None:
        subject = actor.operator.id
    else:
        subject = actor.user.id
    payload = {
        "iss": ISSUER,
        "aud": MONITOR_AUD,
        "sub": str(subject),
        "uid": actor.user.id,
        "cid": actor.company_id,
        "role": actor.role,
        "iat": int(now.timestamp()),
        "exp": int((now + OPERATOR_TTL).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def _admin_actor_from_payload(payload: dict) -> MonitorActor | None:
    User = get_user_model()
    try:
        user = User.objects.get(pk=int(payload.get("uid") or payload["sub"]))
        company = Membership.objects.select_related("company").get(
            user=user,
            company_id=int(payload["cid"]),
        ).company
    except (
        User.DoesNotExist,
        Membership.DoesNotExist,
        ValueError,
        TypeError,
        KeyError,
    ):
        return None
    if not user.is_active or not (user.is_staff or user.is_superuser):
        return None
    return MonitorActor.from_admin(user, company)


def verify_monitor_token(token: str) -> MonitorActor | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
            audience=MONITOR_AUD,
            issuer=ISSUER,
        )
    except jwt.InvalidTokenError:
        return None
    role = payload.get("role") or MONITOR_ROLE_OPERATOR
    if role == MONITOR_ROLE_ADMIN:
        return _admin_actor_from_payload(payload)
    try:
        operator = Operator.objects.select_related("user", "company").get(
            pk=int(payload["sub"])
        )
    except (Operator.DoesNotExist, ValueError, TypeError, KeyError):
        return None
    if not operator.user.is_active:
        return None
    return MonitorActor.from_operator(operator)


def verify_operator_token(token: str) -> Operator | None:
    actor = verify_monitor_token(token)
    if actor is None or actor.operator is None:
        return None
    return actor.operator
