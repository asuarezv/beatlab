from django.contrib.auth import get_user_model
from django.utils.text import slugify
from rest_framework import serializers

from .models import Beat, BeatType, Company, Operator, System
from .validation import (
    COMPANY_NAME_ERROR,
    USERNAME_ERROR,
    is_valid_company_name,
    is_valid_username,
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
    username = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, min_length=8)
    display_name = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Operator
        fields = ("id", "username", "password", "display_name", "created_at")
        read_only_fields = ("id", "display_name", "created_at")

    def validate_username(self, value):
        username = (value or "").strip()
        if not username:
            raise serializers.ValidationError("El usuario es obligatorio.")
        if not is_valid_username(username):
            raise serializers.ValidationError(USERNAME_ERROR)
        return username

    def create(self, validated_data):
        username = validated_data.pop("username").strip()
        password = validated_data.pop("password")
        company = self.context["company"]
        if User.objects.filter(username__iexact=username).exists():
            raise serializers.ValidationError({"username": "Ese usuario ya existe."})
        user = User.objects.create_user(username=username, password=password)
        return Operator.objects.create(company=company, user=user)


class BeatTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = BeatType
        fields = ("id", "name", "slug", "created_at")
        read_only_fields = ("id", "slug", "created_at")

    def create(self, validated_data):
        company = self.context["company"]
        name = validated_data["name"]
        base = slugify(name) or "tipo"
        slug = base
        index = 2
        while BeatType.objects.filter(company=company, slug=slug).exists():
            slug = f"{base}-{index}"
            index += 1
        return BeatType.objects.create(company=company, name=name, slug=slug)


class SystemSerializer(serializers.ModelSerializer):
    class Meta:
        model = System
        fields = ("id", "name", "slug", "is_active", "created_at")
        read_only_fields = ("id", "slug", "created_at")

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

    class Meta:
        model = Beat
        fields = (
            "id",
            "system",
            "beat_type",
            "system_name",
            "beat_type_name",
            "title",
            "payload",
            "created_at",
        )
        read_only_fields = ("id", "system_name", "beat_type_name", "created_at")

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
