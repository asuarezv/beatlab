from django.contrib.auth.models import AnonymousUser
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission

from .models import System
from .tokens import MonitorActor, verify_monitor_token, verify_system_jwt


def _bearer(request) -> str:
    header = request.META.get("HTTP_AUTHORIZATION") or ""
    if not header.startswith("Bearer "):
        return ""
    return header[7:].strip()


class SystemJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = _bearer(request)
        if not token:
            raise AuthenticationFailed("Falta el JWT del System.")
        system = verify_system_jwt(token)
        if system is None:
            raise AuthenticationFailed("JWT inválido o revocado.")
        return (AnonymousUser(), system)

    def authenticate_header(self, request):
        return "Bearer"


class OperatorTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = _bearer(request)
        if not token:
            return None
        actor = verify_monitor_token(token)
        if actor is None:
            raise AuthenticationFailed("Token inválido o vencido.")
        return (actor.user, actor)

    def authenticate_header(self, request):
        return "Bearer"


class HubMonitorSessionAuthentication(BaseAuthentication):
    def authenticate(self, request):
        from .views import current_operator

        operator = current_operator(getattr(request, "_request", request))
        if operator is None:
            return None
        return (operator.user, MonitorActor.from_operator(operator))


class IsSystemJWT(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, System)


class IsOperatorToken(BasePermission):
    def has_permission(self, request, view):
        return isinstance(request.auth, MonitorActor)
