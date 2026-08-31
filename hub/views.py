import json

from django.contrib.auth import (
    get_user_model,
    login,
    logout,
    update_session_auth_hash,
)
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.exceptions import MethodNotAllowed, PermissionDenied, ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .authentication import (
    IsOperatorToken,
    IsSystemJWT,
    OperatorTokenAuthentication,
    SystemJWTAuthentication,
)
from .models import (
    Beat,
    BeatType,
    Company,
    EmailChangeChallenge,
    Operator,
    OperatorInviteChallenge,
    OperatorOtpChallenge,
    System,
)
from .assignment import (
    AssignmentError,
    apply_assignment,
    assignment_payload,
    beats_visible_to_actor,
    parse_receive_all,
    resolve_company_beat_types,
    types_visible_to_actor,
)
from .stats import beat_stats_payload
from .notify import beat_payload, notify_company_beat
from .tokens import (
    MONITOR_ROLE_ADMIN,
    MONITOR_ROLE_OPERATOR,
    MonitorActor,
    issue_monitor_jwt,
    issue_system_jwt,
)
from .otp import (
    activate_operator_password,
    consume_email_change_otp,
    consume_monitor_otp,
    consume_monitor_password,
    consume_signup_otp,
    invite_info_payload,
    issue_email_change_otp,
    issue_monitor_otp,
    issue_operator_invite_otp,
    issue_operator_recover_otp,
    issue_signup_otp,
    lookup_operator_invite,
    validate_signup_fields,
    verify_operator_access_otp,
)
from .validation import (
    CURRENT_PASSWORD_ERROR,
    HUB_EMAIL_TAKEN,
    OPERATOR_EMAIL_TAKEN,
    PASSWORD_CHANGE_REQUIRED,
    PASSWORD_CREATED,
    PASSWORD_UPDATED,
    PERSON_NAME_ERROR,
    PROFILE_UPDATED,
    assert_email_available,
    normalize_person_name,
    validate_new_password,
    validate_profile_fields,
)
from .quota import (
    assert_can_consume_beat,
    assert_company_writable,
    company_payload,
    grant_demo,
    usage_payload,
)
from .serializers import (
    BeatSerializer,
    BeatTypeSerializer,
    CompanySerializer,
    IngestBeatSerializer,
    OperatorSerializer,
    SystemSerializer,
)
from .tenant import companies_for, current_company, ensure_membership

User = get_user_model()


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
        "first_name": user.first_name or "",
        "last_name": user.last_name or "",
        "email": user.email or "",
        "display_name": user.get_full_name().strip() or user.username,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
    }


def _staff_ok(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)


def hub_role(request):
    stored = request.session.get("hub_role")
    if stored in {MONITOR_ROLE_ADMIN, MONITOR_ROLE_OPERATOR}:
        return stored
    if _staff_ok(request.user):
        return MONITOR_ROLE_ADMIN
    return None


def current_operator(request):
    if hub_role(request) != MONITOR_ROLE_OPERATOR:
        return None
    if not request.user.is_authenticated:
        return None
    operator_id = request.session.get("operator_id")
    if not operator_id:
        return None
    return (
        Operator.objects.filter(pk=operator_id, user=request.user)
        .select_related("company", "user")
        .first()
    )


def is_hub_admin(request):
    return hub_role(request) == MONITOR_ROLE_ADMIN and _staff_ok(request.user)


def operator_user_payload(operator):
    return {
        "username": "",
        "first_name": operator.first_name or "",
        "last_name": operator.last_name or "",
        "email": operator.email or "",
        "display_name": operator.display_name(),
        "is_staff": False,
        "is_superuser": False,
    }


def session_payload(request, user):
    operator = current_operator(request)
    if operator:
        company = operator.company
        return {
            "role": MONITOR_ROLE_OPERATOR,
            "user": operator_user_payload(operator),
            "companies": [
                {"id": company.id, "name": company.name, "slug": company.slug}
            ],
            "current_company": company_payload(company),
        }
    company = current_company(request)
    return {
        "role": MONITOR_ROLE_ADMIN,
        "user": user_payload(user),
        "companies": list(companies_for(user).values("id", "name", "slug")),
        "current_company": company_payload(company),
    }


def _login_actor(request, actor):
    login(
        request,
        actor.user,
        backend="django.contrib.auth.backends.ModelBackend",
    )
    if actor.operator is not None:
        request.session["hub_role"] = MONITOR_ROLE_OPERATOR
        request.session["operator_id"] = actor.operator.id
        request.session["company_id"] = actor.company_id
    else:
        request.session["hub_role"] = MONITOR_ROLE_ADMIN
        request.session.pop("operator_id", None)
    _mark_monitor_login(actor)


def _unique_company_slug(name: str) -> str:
    base = slugify(name) or "empresa"
    slug = base
    index = 2
    while Company.objects.filter(slug=slug).exists():
        slug = f"{base}-{index}"
        index += 1
    return slug


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
    if is_hub_admin(request) or current_operator(request):
        return JsonResponse(session_payload(request, request.user))
    return JsonResponse(
        {"user": None, "companies": [], "current_company": None, "role": None}
    )


@require_POST
def login_view(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    try:
        actor = consume_monitor_password(
            email=data.get("email"),
            password=data.get("password"),
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    _login_actor(request, actor)
    return JsonResponse(session_payload(request, actor.user))


@require_POST
def register_start(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    try:
        company_name, username, email, password = validate_signup_fields(
            company_name=data.get("company_name"),
            username=data.get("username"),
            email=data.get("email"),
            password=data.get("password"),
            password2=data.get("password2"),
        )
        result = issue_signup_otp(
            company_name=company_name,
            username=username,
            email=email,
            password=password,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    return JsonResponse(result)


@require_POST
def register_verify(request):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    try:
        challenge = consume_signup_otp(
            email=data.get("email"),
            otp=data.get("otp"),
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)

    with transaction.atomic():
        if User.objects.filter(username__iexact=challenge.username).exists():
            challenge.delete()
            return JsonResponse({"detail": "Ese usuario ya está en uso."}, status=400)
        if User.objects.filter(email__iexact=challenge.email).exists():
            challenge.delete()
            return JsonResponse({"detail": "Ese correo ya está en uso."}, status=400)
        company = Company.objects.create(
            name=challenge.company_name,
            slug=_unique_company_slug(challenge.company_name),
        )
        grant_demo(company)
        user = User(
            username=challenge.username,
            email=challenge.email,
            is_staff=True,
        )
        user.password = challenge.password_hash
        user.save()
        ensure_membership(user, company)
        challenge.delete()

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["company_id"] = company.id
    return JsonResponse(session_payload(request, user), status=201)


@require_POST
def logout_view(request):
    logout(request)
    return JsonResponse({"ok": True})


@require_POST
def change_password(request):
    operator = current_operator(request)
    if not operator and not is_hub_admin(request):
        return JsonResponse({"detail": "No autorizado"}, status=401)
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    current = (data.get("current_password") or "").strip()
    if not current:
        return JsonResponse({"detail": PASSWORD_CHANGE_REQUIRED}, status=400)
    if operator:
        if not operator.check_password(current):
            return JsonResponse({"detail": CURRENT_PASSWORD_ERROR}, status=400)
        try:
            new_password = validate_new_password(
                data.get("password"),
                data.get("password2"),
                user=operator.user,
            )
        except ValueError as exc:
            return JsonResponse({"detail": str(exc)}, status=400)
        operator.set_password(new_password)
        operator.save(update_fields=["password_hash"])
        return JsonResponse({"ok": True, "detail": PASSWORD_UPDATED})
    if not request.user.check_password(current):
        return JsonResponse({"detail": CURRENT_PASSWORD_ERROR}, status=400)
    try:
        new_password = validate_new_password(
            data.get("password"),
            data.get("password2"),
            user=request.user,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    request.user.set_password(new_password)
    request.user.save(update_fields=["password"])
    update_session_auth_hash(request, request.user)
    return JsonResponse({"ok": True, "detail": PASSWORD_UPDATED})


def _update_operator_hub_profile(request, operator):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    try:
        first_name, last_name, email = validate_profile_fields(
            first_name=data.get("first_name", operator.first_name),
            last_name=data.get("last_name", operator.last_name),
            email=data.get("email", operator.email),
            exclude_operator_id=operator.pk,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    email_changed = (operator.email or "").strip().lower() != email
    operator.first_name = first_name
    operator.last_name = last_name
    try:
        operator.save(update_fields=["first_name", "last_name"])
    except IntegrityError:
        return JsonResponse({"detail": OPERATOR_EMAIL_TAKEN}, status=400)
    user = operator.user
    if user:
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=["first_name", "last_name"])
    if not email_changed:
        EmailChangeChallenge.objects.filter(operator=operator).delete()
        payload = session_payload(request, request.user)
        payload["detail"] = PROFILE_UPDATED
        return JsonResponse(payload)
    try:
        result = issue_email_change_otp(
            email=email,
            name=first_name or operator.display_name(),
            operator=operator,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    payload = session_payload(request, request.user)
    payload.update(result)
    return JsonResponse(payload)


def _verify_operator_hub_email(request, operator):
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    try:
        challenge = consume_email_change_otp(
            email=data.get("email"),
            otp=data.get("otp"),
            operator=operator,
        )
        assert_email_available(challenge.email, exclude_operator_id=operator.pk)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    operator.email = challenge.email
    try:
        with transaction.atomic():
            operator.save(update_fields=["email"])
            user = operator.user
            if user:
                user.email = challenge.email
                user.save(update_fields=["email"])
            challenge.delete()
    except IntegrityError:
        return JsonResponse({"detail": OPERATOR_EMAIL_TAKEN}, status=400)
    payload = session_payload(request, request.user)
    payload["detail"] = PROFILE_UPDATED
    return JsonResponse(payload)


@require_http_methods(["PATCH"])
def update_profile(request):
    operator = current_operator(request)
    if operator:
        return _update_operator_hub_profile(request, operator)
    if not is_hub_admin(request):
        return JsonResponse({"detail": "No autorizado"}, status=401)
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    try:
        first_name, last_name, email = validate_profile_fields(
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            email=data.get("email"),
            exclude_user_id=request.user.pk,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    user = request.user
    email_changed = (user.email or "").strip().lower() != email
    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=["first_name", "last_name"])
    if not email_changed:
        EmailChangeChallenge.objects.filter(user=user, operator__isnull=True).delete()
        payload = session_payload(request, user)
        payload["detail"] = PROFILE_UPDATED
        return JsonResponse(payload)
    try:
        result = issue_email_change_otp(
            email=email,
            name=first_name or user.username,
            user=user,
        )
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    payload = session_payload(request, user)
    payload.update(result)
    return JsonResponse(payload)


@require_POST
def verify_profile_email(request):
    operator = current_operator(request)
    if operator:
        return _verify_operator_hub_email(request, operator)
    if not is_hub_admin(request):
        return JsonResponse({"detail": "No autorizado"}, status=401)
    data = _json_body(request)
    if data is None:
        return JsonResponse({"detail": "JSON inválido"}, status=400)
    try:
        challenge = consume_email_change_otp(
            email=data.get("email"),
            otp=data.get("otp"),
            user=request.user,
        )
        assert_email_available(challenge.email, exclude_user_id=request.user.pk)
    except ValueError as exc:
        return JsonResponse({"detail": str(exc)}, status=400)
    user = request.user
    user.email = challenge.email
    try:
        with transaction.atomic():
            user.save(update_fields=["email"])
            challenge.delete()
    except IntegrityError:
        return JsonResponse({"detail": HUB_EMAIL_TAKEN}, status=400)
    payload = session_payload(request, user)
    payload["detail"] = PROFILE_UPDATED
    return JsonResponse(payload)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def select_company(request):
    if not is_hub_admin(request):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
    company_id = request.data.get("company_id")
    company = companies_for(request.user).filter(pk=company_id).first()
    if not company:
        return Response({"detail": "Empresa no encontrada"}, status=status.HTTP_404_NOT_FOUND)
    request.session["company_id"] = company.id
    return Response(company_payload(company))


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def salud(request):
    if not is_hub_admin(request):
        return Response({"detail": "No autorizado"}, status=status.HTTP_403_FORBIDDEN)
    company = current_company(request)
    if not company:
        return Response({"detail": "No hay empresa activa."}, status=status.HTTP_404_NOT_FOUND)
    return Response(usage_payload(company))


class TenantViewSet(viewsets.ModelViewSet):
    http_method_names = ["get", "post", "head", "options"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_hub_admin(request):
            self.permission_denied(request, message="No autorizado")
        self.company = current_company(request)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["company"] = getattr(self, "company", None)
        return context

    def perform_create(self, serializer):
        assert_company_writable(self.company)
        serializer.save()


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    http_method_names = ["get", "post", "head", "options"]

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if not is_hub_admin(request):
            self.permission_denied(request, message="No autorizado")

    def get_queryset(self):
        return companies_for(self.request.user)

    def perform_create(self, serializer):
        if not self.request.user.is_superuser:
            self.permission_denied(self.request, message="Solo un superusuario crea empresas.")
        company = serializer.save()
        grant_demo(company)
        ensure_membership(self.request.user, company)
        self.request.session["company_id"] = company.id


class OperatorViewSet(TenantViewSet):
    serializer_class = OperatorSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        if not self.company:
            return Operator.objects.none()
        return (
            Operator.objects.filter(company=self.company)
            .select_related("user")
            .prefetch_related("assigned_beat_types")
        )

    def create(self, request, *args, **kwargs):
        raise MethodNotAllowed("POST")

    def perform_destroy(self, instance):
        email = instance.email
        user = instance.user
        instance.delete()
        OperatorOtpChallenge.objects.filter(email__iexact=email).delete()
        OperatorInviteChallenge.objects.filter(email__iexact=email).delete()
        EmailChangeChallenge.objects.filter(email__iexact=email).delete()
        if user and not user.is_staff and not user.is_superuser:
            user.delete()

    @action(detail=False, methods=["post"], url_path="invite")
    def invite(self, request):
        if not self.company:
            return Response(
                {"detail": "No hay empresa activa."},
                status=status.HTTP_404_NOT_FOUND,
            )
        assert_company_writable(self.company)
        inviter = request.user
        inviter_name = (
            f"{inviter.first_name} {inviter.last_name}".strip() or inviter.username
        )
        try:
            beat_types = resolve_company_beat_types(
                self.company, request.data.get("beat_type_ids")
            )
            result = issue_operator_invite_otp(
                company=self.company,
                first_name=request.data.get("first_name"),
                last_name=request.data.get("last_name"),
                email=request.data.get("email"),
                inviter_name=inviter_name,
                receive_all_beat_types=parse_receive_all(
                    request.data.get("receive_all_beat_types")
                ),
                beat_types=beat_types,
            )
        except (AssignmentError, ValueError) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        if not self.company:
            return Response(
                {"detail": "No hay empresa activa."},
                status=status.HTTP_404_NOT_FOUND,
            )
        rows = (
            OperatorInviteChallenge.objects.filter(company=self.company)
            .prefetch_related("assigned_beat_types")
            .order_by("-created_at")
        )
        return Response(
            [
                {
                    "id": item.id,
                    "email": item.email,
                    "first_name": item.first_name,
                    "last_name": item.last_name,
                    "created_at": item.created_at,
                    "expires_at": item.expires_at,
                    **assignment_payload(item),
                }
                for item in rows
            ]
        )

    @action(
        detail=False,
        methods=["patch"],
        url_path=r"pending/(?P<invite_id>[0-9]+)",
    )
    def update_pending(self, request, invite_id=None):
        if not self.company:
            return Response(
                {"detail": "No hay empresa activa."},
                status=status.HTTP_404_NOT_FOUND,
            )
        challenge = (
            OperatorInviteChallenge.objects.filter(
                pk=invite_id, company=self.company
            )
            .prefetch_related("assigned_beat_types")
            .first()
        )
        if not challenge:
            return Response(
                {"detail": "Invitación no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )
        first_name = request.data.get("first_name", challenge.first_name)
        last_name = request.data.get("last_name", challenge.last_name)
        first_name = normalize_person_name(first_name)
        last_name = normalize_person_name(last_name)
        if not first_name or not last_name:
            return Response(
                {"detail": PERSON_NAME_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            if "beat_type_ids" in request.data or "receive_all_beat_types" in request.data:
                beat_types = (
                    resolve_company_beat_types(
                        self.company, request.data.get("beat_type_ids")
                    )
                    if "beat_type_ids" in request.data
                    else list(challenge.assigned_beat_types.all())
                )
                receive_all = (
                    parse_receive_all(request.data.get("receive_all_beat_types"))
                    if "receive_all_beat_types" in request.data
                    else challenge.receive_all_beat_types
                )
                apply_assignment(
                    challenge, receive_all=receive_all, beat_types=beat_types
                )
        except AssignmentError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        challenge.first_name = first_name
        challenge.last_name = last_name
        challenge.save(update_fields=["first_name", "last_name"])
        challenge.refresh_from_db()
        return Response(
            {
                "id": challenge.id,
                "email": challenge.email,
                "first_name": challenge.first_name,
                "last_name": challenge.last_name,
                "created_at": challenge.created_at,
                "expires_at": challenge.expires_at,
                **assignment_payload(challenge),
            }
        )


class BeatTypeViewSet(TenantViewSet):
    serializer_class = BeatTypeSerializer
    http_method_names = ["get", "post", "put", "patch", "head", "options"]

    def get_queryset(self):
        if not self.company:
            return BeatType.objects.none()
        return BeatType.objects.filter(company=self.company)

    def perform_update(self, serializer):
        assert_company_writable(self.company)
        serializer.save()


class SystemViewSet(TenantViewSet):
    serializer_class = SystemSerializer

    def get_queryset(self):
        if not self.company:
            return System.objects.none()
        return System.objects.filter(company=self.company)

    @action(detail=True, methods=["post"], url_path="jwt")
    def issue_jwt(self, request, pk=None):
        system = self.get_object()
        rotated = bool(system.jwt_hash)
        token = issue_system_jwt(system)
        return Response(
            {
                "token": token,
                "issued_at": system.jwt_issued_at,
                "rotated": rotated,
            },
            status=status.HTTP_201_CREATED,
        )


class BeatViewSet(TenantViewSet):
    serializer_class = BeatSerializer
    http_method_names = ["get", "head", "options"]

    def initial(self, request, *args, **kwargs):
        super(TenantViewSet, self).initial(request, *args, **kwargs)
        if is_hub_admin(request):
            self.company = current_company(request)
            self.hub_operator = None
            return
        operator = current_operator(request)
        if operator:
            self.company = operator.company
            self.hub_operator = operator
            return
        self.permission_denied(request, message="No autorizado")

    def get_queryset(self):
        if not self.company:
            return Beat.objects.none()
        if self.hub_operator:
            actor = MonitorActor.from_operator(self.hub_operator)
            return beats_visible_to_actor(actor)
        return Beat.objects.filter(company=self.company).select_related(
            "system", "beat_type"
        )

    @action(detail=False, methods=["get"], url_path="stats")
    def stats(self, request):
        if not self.company:
            return Response(
                {"detail": "No hay empresa activa."},
                status=status.HTTP_404_NOT_FOUND,
            )
        if self.hub_operator:
            actor = MonitorActor.from_operator(self.hub_operator)
            types = types_visible_to_actor(actor)
            beats = beats_visible_to_actor(actor)
        else:
            types = BeatType.objects.filter(company=self.company)
            beats = Beat.objects.filter(company=self.company)
        return Response(beat_stats_payload(beats=beats, types=types))


@api_view(["POST"])
@authentication_classes([SystemJWTAuthentication])
@permission_classes([IsSystemJWT])
def ingest_beat(request):
    system = request.auth
    if not system.is_active:
        return Response(
            {"detail": "El System está inactivo."},
            status=status.HTTP_403_FORBIDDEN,
        )
    serializer = IngestBeatSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    beat_type = BeatType.objects.filter(
        company=system.company,
        slug=data["type"],
    ).first()
    if not beat_type:
        return Response(
            {"detail": "Tipo de Beat desconocido."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with transaction.atomic():
            company = Company.objects.select_for_update().get(pk=system.company_id)
            assert_can_consume_beat(company)
            beat = Beat.objects.create(
                company=company,
                system=system,
                beat_type=beat_type,
                title=data["title"],
                payload=data.get("payload") or {},
            )
    except PermissionDenied as exc:
        return Response({"detail": str(exc.detail)}, status=status.HTTP_403_FORBIDDEN)
    except ValidationError as exc:
        detail = exc.detail
        if isinstance(detail, (list, dict)):
            detail = (
                detail[0]
                if isinstance(detail, list)
                else next(iter(detail.values()), "No quedan Beats en el paquete.")
            )
            if isinstance(detail, list):
                detail = detail[0]
        return Response({"detail": str(detail)}, status=status.HTTP_409_CONFLICT)

    notify_company_beat(beat)
    return Response(beat_payload(beat), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def monitor_request_otp(request):
    try:
        result = issue_monitor_otp(email=request.data.get("email"))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


def monitor_session_payload(actor, *, with_token=True):
    data = {
        "role": actor.role,
        "operator": {
            "id": actor.id,
            "display_name": actor.display_name(),
            "first_name": actor.first_name,
            "last_name": actor.last_name,
            "email": actor.email,
            "has_password": actor.has_password(),
        },
        "company": {
            "id": actor.company_id,
            "name": actor.company.name,
        },
    }
    if with_token:
        data["token"] = issue_monitor_jwt(actor)
    return data


def _mark_monitor_login(actor):
    if actor.operator is not None:
        actor.operator.last_login_at = timezone.now()
        actor.operator.save(update_fields=["last_login_at"])
        return
    actor.user.last_login = timezone.now()
    actor.user.save(update_fields=["last_login"])


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def monitor_verify_otp(request):
    try:
        actor = consume_monitor_otp(
            email=request.data.get("email"),
            otp=request.data.get("otp"),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    _mark_monitor_login(actor)
    return Response(monitor_session_payload(actor))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def monitor_login(request):
    try:
        actor = consume_monitor_password(
            email=request.data.get("email"),
            password=request.data.get("password"),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    _mark_monitor_login(actor)
    return Response(monitor_session_payload(actor))


@api_view(["GET", "PATCH"])
@authentication_classes([OperatorTokenAuthentication])
@permission_classes([IsOperatorToken])
def monitor_me(request):
    actor = request.auth
    if request.method != "PATCH":
        return Response(monitor_session_payload(actor, with_token=False))
    operator = actor.operator
    if operator is not None:
        try:
            first_name, last_name, email = validate_profile_fields(
                first_name=request.data.get("first_name", operator.first_name),
                last_name=request.data.get("last_name", operator.last_name),
                email=request.data.get("email", operator.email),
                exclude_operator_id=operator.pk,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        email_changed = (operator.email or "").strip().lower() != email
        operator.first_name = first_name
        operator.last_name = last_name
        try:
            operator.save(update_fields=["first_name", "last_name"])
        except IntegrityError:
            return Response(
                {"detail": OPERATOR_EMAIL_TAKEN},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = operator.user
        if user:
            user.first_name = first_name
            user.last_name = last_name
            user.save(update_fields=["first_name", "last_name"])
        if not email_changed:
            EmailChangeChallenge.objects.filter(operator=operator).delete()
            payload = monitor_session_payload(actor, with_token=False)
            payload["detail"] = PROFILE_UPDATED
            return Response(payload)
        try:
            result = issue_email_change_otp(
                email=email,
                name=first_name or operator.display_name(),
                operator=operator,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        payload = monitor_session_payload(actor, with_token=False)
        payload.update(result)
        return Response(payload)

    user = actor.user
    try:
        first_name, last_name, email = validate_profile_fields(
            first_name=request.data.get("first_name", user.first_name),
            last_name=request.data.get("last_name", user.last_name),
            email=request.data.get("email", user.email),
            exclude_user_id=user.pk,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    email_changed = (user.email or "").strip().lower() != email
    user.first_name = first_name
    user.last_name = last_name
    user.save(update_fields=["first_name", "last_name"])
    if not email_changed:
        EmailChangeChallenge.objects.filter(user=user, operator__isnull=True).delete()
        payload = monitor_session_payload(actor, with_token=False)
        payload["detail"] = PROFILE_UPDATED
        return Response(payload)
    try:
        result = issue_email_change_otp(
            email=email,
            name=first_name or actor.display_name(),
            user=user,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    payload = monitor_session_payload(actor, with_token=False)
    payload.update(result)
    return Response(payload)


@api_view(["POST"])
@authentication_classes([OperatorTokenAuthentication])
@permission_classes([IsOperatorToken])
def monitor_verify_email(request):
    actor = request.auth
    operator = actor.operator
    if operator is not None:
        try:
            challenge = consume_email_change_otp(
                email=request.data.get("email"),
                otp=request.data.get("otp"),
                operator=operator,
            )
            assert_email_available(challenge.email, exclude_operator_id=operator.pk)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        operator.email = challenge.email
        try:
            with transaction.atomic():
                operator.save(update_fields=["email"])
                user = operator.user
                if user:
                    user.email = challenge.email
                    user.save(update_fields=["email"])
                challenge.delete()
        except IntegrityError:
            return Response(
                {"detail": OPERATOR_EMAIL_TAKEN},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = monitor_session_payload(actor, with_token=False)
        payload["detail"] = PROFILE_UPDATED
        return Response(payload)

    user = actor.user
    try:
        challenge = consume_email_change_otp(
            email=request.data.get("email"),
            otp=request.data.get("otp"),
            user=user,
        )
        assert_email_available(challenge.email, exclude_user_id=user.pk)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    user.email = challenge.email
    try:
        with transaction.atomic():
            user.save(update_fields=["email"])
            challenge.delete()
    except IntegrityError:
        return Response(
            {"detail": HUB_EMAIL_TAKEN},
            status=status.HTTP_400_BAD_REQUEST,
        )
    payload = monitor_session_payload(actor, with_token=False)
    payload["detail"] = PROFILE_UPDATED
    return Response(payload)


@api_view(["POST"])
@authentication_classes([OperatorTokenAuthentication])
@permission_classes([IsOperatorToken])
def monitor_password(request):
    actor = request.auth
    had_password = actor.has_password()
    if had_password:
        current = (request.data.get("current_password") or "").strip()
        if not current:
            return Response(
                {"detail": PASSWORD_CHANGE_REQUIRED},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not actor.check_password(current):
            return Response(
                {"detail": CURRENT_PASSWORD_ERROR},
                status=status.HTTP_400_BAD_REQUEST,
            )
    try:
        new_password = validate_new_password(
            request.data.get("password"),
            request.data.get("password2"),
            user=actor.user,
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    actor.set_password(new_password)
    actor.save_password()
    return Response(
        {
            "ok": True,
            "has_password": True,
            "detail": PASSWORD_UPDATED if had_password else PASSWORD_CREATED,
        }
    )


@api_view(["GET"])
@authentication_classes([OperatorTokenAuthentication])
@permission_classes([IsOperatorToken])
def monitor_beats(request):
    actor = request.auth
    beats = beats_visible_to_actor(actor)[:100]
    return Response([beat_payload(beat) for beat in beats])


@api_view(["GET"])
@authentication_classes([OperatorTokenAuthentication])
@permission_classes([IsOperatorToken])
def monitor_stats(request):
    actor = request.auth
    return Response(
        beat_stats_payload(
            beats=beats_visible_to_actor(actor),
            types=types_visible_to_actor(actor),
        )
    )


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_operator_invite_info(request):
    try:
        challenge = lookup_operator_invite(token=request.query_params.get("token"))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_404_NOT_FOUND)
    return Response(invite_info_payload(challenge))


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_operator_verify(request):
    try:
        result = verify_operator_access_otp(
            token=request.data.get("token"),
            email=request.data.get("email"),
            otp=request.data.get("otp"),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_operator_password(request):
    try:
        result = activate_operator_password(
            grant=request.data.get("grant"),
            password=request.data.get("password"),
            password2=request.data.get("password2"),
        )
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    created = result.pop("created", False)
    return Response(
        result,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def public_operator_recover(request):
    try:
        result = issue_operator_recover_otp(email=request.data.get("email"))
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
    return Response(result)
