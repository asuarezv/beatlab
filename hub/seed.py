from datetime import timedelta

from django.utils import timezone
from django.utils.text import slugify

from .models import Beat, BeatPackage, BeatType, Company, System
from .quota import grant_demo

SEED_TYPES = [
    ("heartbeat", "Heartbeat", BeatType.Severity.INFO, "pulse"),
    ("alerta", "Alerta", BeatType.Severity.ALERTA, "alert"),
    ("recuperacion", "Recuperación", BeatType.Severity.INFO, "check"),
    ("error", "Error", BeatType.Severity.CRITICA, "error"),
    ("umbral", "Umbral", BeatType.Severity.AVISO, "activity"),
    ("job", "Job", BeatType.Severity.AVISO, "sync"),
    ("api", "API", BeatType.Severity.ALERTA, "cloud"),
    ("backup", "Backup", BeatType.Severity.AVISO, "shield"),
    ("disco", "Disco", BeatType.Severity.CRITICA, "server"),
    ("latencia", "Latencia", BeatType.Severity.ALERTA, "bell"),
]

TITLES = {
    "heartbeat": "Pulso del System",
    "alerta": "Alerta del System",
    "recuperacion": "System recuperado",
    "error": "Error en el System",
    "umbral": "Umbral del System",
    "job": "Job del System",
    "api": "API del System",
    "backup": "Backup del System",
    "disco": "Disco del System",
    "latencia": "Latencia del System",
}

TARGET_TYPES = 10
TARGET_BEATS = 100
REMAINING_BUFFER = 100


def companies_for_seed(slug=None):
    qs = Company.objects.all().order_by("id")
    if slug:
        qs = qs.filter(slug=slug)
    return [company for company in qs if company.systems.exists()]


def complete_types(company) -> list[BeatType]:
    existing = {item.slug: item for item in company.beat_types.all()}
    created = []
    for slug, name, severity, icon in SEED_TYPES:
        if len(existing) >= TARGET_TYPES:
            break
        if slug in existing:
            continue
        base = slugify(slug) or "tipo"
        unique = base
        index = 2
        while BeatType.objects.filter(company=company, slug=unique).exists():
            unique = f"{base}-{index}"
            index += 1
        item = BeatType.objects.create(
            company=company,
            name=name,
            slug=unique,
            severity=severity,
            icon=icon,
        )
        existing[item.slug] = item
        created.append(item)
    return list(company.beat_types.order_by("name"))


def _title_for(beat_type: BeatType, index: int) -> str:
    base = TITLES.get(beat_type.slug, f"Beat {beat_type.name}")
    return f"{base} · {index + 1}"


def ensure_quota(company, created_count: int) -> None:
    grant_demo(company)
    if created_count <= 0:
        return
    package = company.packages.order_by("id").first()
    package.beats += created_count + REMAINING_BUFFER
    package.save(update_fields=["beats"])


def seed_beats(company, types, *, target=TARGET_BEATS) -> int:
    system = company.systems.order_by("id").first()
    if not system or not types:
        return 0
    existing = company.beats.count()
    needed = max(0, target - existing)
    if needed == 0:
        return 0
    now = timezone.now()
    created_ids = []
    for index in range(needed):
        beat_type = types[index % len(types)]
        day = index % 14
        hour = (index * 3) % 20 + 1
        minute = (index * 11) % 60
        when = now - timedelta(days=13 - day, hours=20 - hour, minutes=minute)
        beat = Beat.objects.create(
            company=company,
            system=system,
            beat_type=beat_type,
            title=_title_for(beat_type, existing + index),
            payload={"seed": True},
        )
        Beat.objects.filter(pk=beat.pk).update(created_at=when)
        created_ids.append(beat.pk)
    ensure_quota(company, len(created_ids))
    return len(created_ids)


def seed_company(company, *, target_beats=TARGET_BEATS) -> dict:
    types = complete_types(company)
    created_beats = seed_beats(company, types, target=target_beats)
    return {
        "company": company.name,
        "slug": company.slug,
        "types": len(types),
        "beats_created": created_beats,
        "beats_total": company.beats.count(),
        "beats_remaining": company.beats_remaining(),
        "system": company.systems.order_by("id").first().name,
    }
