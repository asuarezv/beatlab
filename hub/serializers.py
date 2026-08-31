import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.utils.text import slugify
from rest_framework import serializers

from .assignment import AssignmentError, apply_assignment, resolve_company_beat_types
from .models import Beat, BeatType, Company, Operator, System
from .validation import (
    COMPANY_NAME_ERROR,
    OPERATOR_EMAIL_TAKEN,
    PERSON_NAME_ERROR,
    email_already_used,
    is_valid_company_name,
    normalize_person_name,
)

User = get_user_model()


class CompanySerializer(serializers.ModelSerializer):
    class Meta:
        model = Company
        fields = ("id", "name", "slug", "created_at")
        read_only_fields = ("id", "slug", "created_at")

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("El nombre de la empresa es obligatorio.")
        if not is_valid_company_name(name):
            raise serializers.ValidationError(COMPANY_NAME_ERROR)
        return name

    def create(self, validated_data):
        name = validated_data["name"]
        base = slugify(name) or "empresa"
        slug = base
        index = 2
        while Company.objects.filter(slug=slug).exists():
            slug = f"{base}-{index}"
            index += 1
        return Company.objects.create(name=name, slug=slug)


class OperatorSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    beat_type_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
    )

    class Meta:
        model = Operator
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "display_name",
            "last_login_at",
            "receive_all_beat_types",
            "beat_type_ids",
            "created_at",
        )
        read_only_fields = ("id", "display_name", "last_login_at", "created_at")

    def get_display_name(self, obj):
        return obj.display_name()

    def validate_first_name(self, value):
        name = normalize_person_name(value)
        if not name:
            raise serializers.ValidationError(PERSON_NAME_ERROR)
        return name

    def validate_last_name(self, value):
        name = normalize_person_name(value)
        if not name:
            raise serializers.ValidationError(PERSON_NAME_ERROR)
        return name

    def validate_email(self, value):
        email = (value or "").strip().lower()
        if not email:
            raise serializers.ValidationError("El correo es obligatorio.")
        try:
            validate_email(email)
        except DjangoValidationError:
            raise serializers.ValidationError("El correo no es válido.") from None
        exclude_id = self.instance.pk if self.instance else None
        operators = Operator.objects.filter(email__iexact=email)
        if exclude_id:
            operators = operators.exclude(pk=exclude_id)
        if operators.exists():
            raise serializers.ValidationError(OPERATOR_EMAIL_TAKEN)
        if email_already_used(email, exclude_operator_id=exclude_id):
            raise serializers.ValidationError("Ese correo ya está en uso.")
        return email

    def validate(self, attrs):
        company = self.context["company"]
        if "beat_type_ids" in attrs:
            try:
                attrs["_beat_types"] = resolve_company_beat_types(
                    company, attrs.pop("beat_type_ids")
                )
            except AssignmentError as exc:
                raise serializers.ValidationError({"beat_type_ids": str(exc)}) from None
        return attrs

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["beat_type_ids"] = list(
            instance.assigned_beat_types.values_list("id", flat=True)
        )
        return data

    def create(self, validated_data):
        beat_types = validated_data.pop("_beat_types", None)
        receive_all = validated_data.pop("receive_all_beat_types", False)
        company = self.context["company"]
        user = User(
            username=f"op{uuid.uuid4().hex[:20]}",
            email=validated_data["email"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )
        user.set_unusable_password()
        user.save()
        operator = Operator.objects.create(company=company, user=user, **validated_data)
        if beat_types is not None or receive_all:
            apply_assignment(
                operator, receive_all=receive_all, beat_types=beat_types or []
            )
        return operator

    def update(self, instance, validated_data):
        beat_types = validated_data.pop("_beat_types", None)
        receive_all = validated_data.pop("receive_all_beat_types", None)
        instance.first_name = validated_data.get("first_name", instance.first_name)
        instance.last_name = validated_data.get("last_name", instance.last_name)
        instance.email = validated_data.get("email", instance.email)
        instance.save(update_fields=["first_name", "last_name", "email"])
        if receive_all is not None or beat_types is not None:
            apply_assignment(
                instance,
                receive_all=(
                    receive_all
                    if receive_all is not None
                    else instance.receive_all_beat_types
                ),
                beat_types=(
                    beat_types
                    if beat_types is not None
                    else list(instance.assigned_beat_types.all())
                ),
            )
        user = instance.user
        user.first_name = instance.first_name
        user.last_name = instance.last_name
        user.email = instance.email
        user.save(update_fields=["first_name", "last_name", "email"])
        return instance


class BeatTypeSerializer(serializers.ModelSerializer):
    icon = serializers.CharField(required=False, allow_blank=True, default="")
    resolved_icon = serializers.SerializerMethodField()
    severity_label = serializers.SerializerMethodField()

    class Meta:
        model = BeatType
        fields = (
            "id",
            "name",
            "slug",
            "severity",
            "severity_label",
            "icon",
            "resolved_icon",
            "created_at",
        )
        read_only_fields = ("id", "slug", "severity_label", "resolved_icon", "created_at")

    def get_resolved_icon(self, obj):
        return obj.resolved_icon()

    def get_severity_label(self, obj):
        return obj.get_severity_display()

    def validate_name(self, value):
        name = (value or "").strip()
        if not name:
            raise serializers.ValidationError("El nombre del tipo es obligatorio.")
        return name

    def validate_icon(self, value):
        icon = (value or "").strip()
        if not icon:
            return ""
        if icon not in BeatType.ICONS:
            raise serializers.ValidationError("El icono no es válido.")
        return icon

    def create(self, validated_data):
        company = self.context["company"]
        name = validated_data["name"]
        base = slugify(name) or "tipo"
        slug = base
        index = 2
        while BeatType.objects.filter(company=company, slug=slug).exists():
            slug = f"{base}-{index}"
            index += 1
        return BeatType.objects.create(
            company=company,
            name=name,
            slug=slug,
            severity=validated_data.get("severity", BeatType.Severity.AVISO),
            icon=validated_data.get("icon", ""),
        )


class SystemSerializer(serializers.ModelSerializer):
    has_jwt = serializers.SerializerMethodField()

    class Meta:
        model = System
        fields = (
            "id",
            "name",
            "slug",
            "is_active",
            "has_jwt",
            "jwt_issued_at",
            "created_at",
        )
        read_only_fields = ("id", "slug", "has_jwt", "jwt_issued_at", "created_at")

    def get_has_jwt(self, obj):
        return bool(obj.jwt_hash)

    def create(self, validated_data):
        company = self.context["company"]
        name = validated_data["name"]
        base = slugify(name) or "system"
        slug = base
        index = 2
        while System.objects.filter(company=company, slug=slug).exists():
            slug = f"{base}-{index}"
            index += 1
        return System.objects.create(
            company=company,
            name=name,
            slug=slug,
            is_active=validated_data.get("is_active", True),
        )


class BeatSerializer(serializers.ModelSerializer):
    system_name = serializers.CharField(source="system.name", read_only=True)
    beat_type_name = serializers.CharField(source="beat_type.name", read_only=True)
    beat_type_slug = serializers.CharField(source="beat_type.slug", read_only=True)
    severity = serializers.CharField(source="beat_type.severity", read_only=True)
    severity_label = serializers.CharField(
        source="beat_type.get_severity_display", read_only=True
    )
    beat_type_icon = serializers.SerializerMethodField()

    class Meta:
        model = Beat
        fields = (
            "id",
            "system",
            "beat_type",
            "system_name",
            "beat_type_name",
            "beat_type_slug",
            "severity",
            "severity_label",
            "beat_type_icon",
            "title",
            "payload",
            "created_at",
        )
        read_only_fields = (
            "id",
            "system_name",
            "beat_type_name",
            "beat_type_slug",
            "severity",
            "severity_label",
            "beat_type_icon",
            "created_at",
        )

    def get_beat_type_icon(self, obj):
        return obj.beat_type.resolved_icon()

    def validate(self, attrs):
        company = self.context["company"]
        system = attrs["system"]
        beat_type = attrs["beat_type"]
        if system.company_id != company.id:
            raise serializers.ValidationError({"system": "El System no es de esta empresa."})
        if beat_type.company_id != company.id:
            raise serializers.ValidationError({"beat_type": "El tipo no es de esta empresa."})
        return attrs

    def create(self, validated_data):
        return Beat.objects.create(company=self.context["company"], **validated_data)


class IngestBeatSerializer(serializers.Serializer):
    type = serializers.SlugField(max_length=80)
    title = serializers.CharField(max_length=200)
    payload = serializers.JSONField(required=False, default=dict)

    def validate_payload(self, value):
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise serializers.ValidationError("El payload debe ser un objeto.")
        return value
