import math
from datetime import timedelta

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import Beat, BeatPackage, BeatType, Company, Operator, System
from .stats import beat_stats_payload

DEMO_DAYS = 15
DEMO_BEATS = 10_000


def grant_demo(company: Company) -> Company:
    if not company.trial_ends_at:
        company.trial_ends_at = timezone.now() + timedelta(days=DEMO_DAYS)
        company.save(update_fields=["trial_ends_at"])
    if not company.packages.filter(kind=BeatPackage.Kind.DEMO).exists():
        BeatPackage.objects.create(
            company=company,
            beats=DEMO_BEATS,
            kind=BeatPackage.Kind.DEMO,
        )
    return company


def trial_days_left(company: Company) -> int:
    if not company.trial_ends_at:
        return 0
    seconds = (company.trial_ends_at - timezone.now()).total_seconds()
    if seconds <= 0:
        return 0
    return max(1, math.ceil(seconds / 86400))


def company_identity_payload(company: Company | None) -> dict | None:
    if not company:
        return None
    return {
        "id": company.id,
        "name": company.name,
        "slug": company.slug,
    }


def company_payload(company: Company | None) -> dict | None:
    identity = company_identity_payload(company)
    if not identity:
        return None
    used = company.beats_used()
    included = company.beats_included()
    identity.update(
        {
            "trial_ends_at": company.trial_ends_at.isoformat() if company.trial_ends_at else None,
            "trial_active": company.trial_active(),
            "trial_days_left": trial_days_left(company),
            "beats_included": included,
            "beats_used": used,
            "beats_remaining": max(0, included - used),
        }
    )
    return identity


def usage_payload(company: Company) -> dict:
    payload = company_payload(company)
    stats = beat_stats_payload(
        beats=Beat.objects.filter(company=company),
        types=BeatType.objects.filter(company=company),
    )
    payload.update(
        {
            "systems": System.objects.filter(company=company).count(),
            "operators": Operator.objects.filter(company=company).count(),
            "types": BeatType.objects.filter(company=company).count(),
            **stats,
        }
    )
    return payload


def assert_company_writable(company: Company | None) -> None:
    if not company:
        raise PermissionDenied("No hay empresa activa.")
    if not company.is_writable():
        raise PermissionDenied(
            "El demo de 15 días terminó. Contrata un paquete de Beats para seguir."
        )


def assert_can_consume_beat(company: Company | None) -> None:
    assert_company_writable(company)
    if company.beats_remaining() < 1:
        raise ValidationError("No quedan Beats en el paquete.")
