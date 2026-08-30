from django.conf import settings
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
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("company", "user")
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
