from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Company(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(unique=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def beats_included(self) -> int:
        return self.packages.aggregate(total=Sum("beats"))["total"] or 0

    def beats_used(self) -> int:
        return self.beats.count()

    def beats_remaining(self) -> int:
        return max(0, self.beats_included() - self.beats_used())

    def trial_active(self) -> bool:
        return bool(self.trial_ends_at and timezone.now() < self.trial_ends_at)

    def has_paid_package(self) -> bool:
        return self.packages.filter(kind=BeatPackage.Kind.PURCHASE).exists()

    def is_writable(self) -> bool:
        return self.trial_active() or self.has_paid_package()


class BeatPackage(models.Model):
    class Kind(models.TextChoices):
        DEMO = "demo", "Demo"
        PURCHASE = "purchase", "Compra"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="packages",
    )
    beats = models.PositiveIntegerField()
    kind = models.CharField(max_length=16, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class SignupChallenge(models.Model):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150)
    company_name = models.CharField(max_length=160)
    password_hash = models.CharField(max_length=256)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class Membership(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "company")


class Operator(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="operators",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="operator_profiles",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=256, blank=True, null=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "user")
        ordering = ["last_name", "first_name", "email"]

    def display_name(self) -> str:
        full = f"{self.first_name} {self.last_name}".strip()
        return full or self.email

    def has_password(self) -> bool:
        return bool(self.password_hash)

    def set_password(self, raw: str) -> None:
        self.password_hash = make_password(raw)

    def check_password(self, raw: str) -> bool:
        if not self.password_hash:
            return False
        return check_password(raw, self.password_hash)


class OperatorOtpChallenge(models.Model):
    email = models.EmailField(unique=True)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class OperatorInviteChallenge(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="operator_invite_challenges",
    )
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class EmailChangeChallenge(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_change_challenges",
        null=True,
        blank=True,
    )
    operator = models.ForeignKey(
        Operator,
        on_delete=models.CASCADE,
        related_name="email_change_challenges",
        null=True,
        blank=True,
    )
    email = models.EmailField(unique=True)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class BeatType(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="beat_types",
    )
    name = models.CharField(max_length=80)
    slug = models.SlugField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "slug")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class System(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="systems",
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField()
    is_active = models.BooleanField(default=True)
    jwt_hash = models.CharField(max_length=64, blank=True, default="")
    jwt_issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "slug")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Beat(models.Model):
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        related_name="beats",
    )
    system = models.ForeignKey(
        System,
        on_delete=models.CASCADE,
        related_name="beats",
    )
    beat_type = models.ForeignKey(
        BeatType,
        on_delete=models.PROTECT,
        related_name="beats",
    )
    title = models.CharField(max_length=200)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
