import json

from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Beat, BeatType, Operator, System
from .serializers import (
    BeatSerializer,
    BeatTypeSerializer,
    CompanySerializer,
    OperatorSerializer,
    SystemSerializer,
)
from .tenant import companies_for, current_company, ensure_membership


def _json_body(request):
    if not request.body:
        return {}
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def user_payload(user):
    return {
        "username": user.username,
        "display_name": user.get_full_name().strip() or user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def _staff_ok(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


@require_GET
def health(_request):
    return JsonResponse({"ok": True, "service": "beatlab-hub"})


@ensure_csrf_cookie
@require_GET
def csrf(request):
    get_token(request)
    return JsonResponse({"ok": True})


@ensure_csrf_cookie
@require_GET
def me(request):
    get_token(request)
    if not _staff_ok(request.user):
        return JsonResponse({"user": None, "companies": [], "current_company": None})
    company = current_company(request)
    return JsonResponse(
        {
            "user": user_payload(request.user),
            "companies": list(companies_for(request.user).values("id", "name", "slug")),
            "current_company": (
                {"id": company.id, "name": company.name, "slug": company.slug}
                if company
                else None
            ),
        }
    )


@require_POST
def login_view(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    user = authenticate(request, username=username, password=password)
    if user is None or not user.is_active or not _staff_ok(user):
        return JsonResponse({"detail": "Usuario o contraseña no válidos"}, status=400)
    login(request, user)
    company = current_company(request)
    return JsonResponse(
        {
            "user": user_payload(user),
            "companies": list(companies_for(user).values("id", "name", "slug")),
            "current_company": (
                {"id": company.id, "name": company.name, "slug": company.slug}
                if company
                else None
            ),
        }
    )


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def select_company(request):
    if not _staff_ok(request.user):
        return Response({"detail": "No autorizado"}, status=status.HTTP_401_UNAUTHORIZED)
    company_id = request.data.get("company_id")
    company = companies_for(request.user).filter(pk=company_id).first()
    if not company:
        return Response({"detail": "Empresa no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    request.session["company_id"] = company.id
    return Response({"id": company.id, "name": company.name, "slug": company.slug})


class TenantViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not _staff_ok(request.user):
            self.permission_denied(request, message="No autorizado")
        self.company = current_company(request)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = getattr(self, "company", None)
        return context


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    http_method_names = ["get", "post", "head", "options"]

    def get_queryset(self):
        return companies_for(self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            self.permission_denied(self.request, message="Solo un superusuario crea empresas.")
        company = serializer.save()
        ensure_membership(self.request.user, company)
        self.request.session["company_id"] = company.id


class OperatorViewSet(TenantViewSet):
    serializer_class = OperatorSerializer

    def get_queryset(self):
        if not self.company:
            return Operator.objects.none()
        return Operator.objects.filter(company=self.company).select_related("user")


class BeatTypeViewSet(TenantViewSet):
    serializer_class = BeatTypeSerializer

    def get_queryset(self):
        if not self.company:
            return BeatType.objects.none()
        return BeatType.objects.filter(company=self.company)


class SystemViewSet(TenantViewSet):
    serializer_class = SystemSerializer

    def get_queryset(self):
        if not self.company:
            return System.objects.none()
        return System.objects.filter(company=self.company)


class BeatViewSet(TenantViewSet):
    serializer_class = BeatSerializer

    def get_queryset(self):
        if not self.company:
            return Beat.objects.none()
        return Beat.objects.filter(company=self.company).select_related("system", "beat_type")
