import hashlib
import uuid
from datetime import timedelta

import jwt
from django.conf import settings
from django.utils import timezone

from .models import Operator, System

SYSTEM_AUD = "beatlab-system"
MONITOR_AUD = "beatlab-monitor"
ISSUER = "beatlab"
OPERATOR_TTL = timedelta(days=30)


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
    now = timezone.now()
    payload = {
        "iss": ISSUER,
        "aud": MONITOR_AUD,
        "sub": str(operator.id),
        "uid": operator.user_id,
        "cid": operator.company_id,
        "iat": int(now.timestamp()),
        "exp": int((now + OPERATOR_TTL).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def verify_operator_token(token: str) -> Operator | None:
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
        operator = Operator.objects.select_related("user", "company").get(
            pk=int(payload["sub"])
        )
    except (jwt.InvalidTokenError, Operator.DoesNotExist, ValueError, TypeError, KeyError):
        return None
    if not operator.user.is_active:
        return None
    return operator
