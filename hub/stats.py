from datetime import timedelta

from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import BeatType

STATS_DAYS = 14

SEVERITY_LABELS = {
    BeatType.Severity.INFO: "Info",
    BeatType.Severity.AVISO: "Aviso",
    BeatType.Severity.ALERTA: "Alerta",
    BeatType.Severity.CRITICA: "Crítica",
}


def type_public(beat_type: BeatType) -> dict:
    return {
        "id": beat_type.id,
        "name": beat_type.name,
        "slug": beat_type.slug,
        "severity": beat_type.severity,
        "severity_label": SEVERITY_LABELS.get(beat_type.severity, beat_type.severity),
        "icon": beat_type.resolved_icon(),
    }


def beat_stats_payload(*, beats, types) -> dict:
    type_list = list(types.order_by("name"))
    counts = dict(
        beats.values("beat_type_id").annotate(n=Count("id")).values_list("beat_type_id", "n")
    )
    by_type = []
    for item in type_list:
        row = type_public(item)
        row["consumed"] = counts.get(item.id, 0)
        by_type.append(row)

    severity_counts = {key: 0 for key in BeatType.Severity.values}
    for row in by_type:
        severity_counts[row["severity"]] = (
            severity_counts.get(row["severity"], 0) + row["consumed"]
        )
    by_severity = [
        {
            "severity": key,
            "label": SEVERITY_LABELS.get(key, key),
            "consumed": severity_counts.get(key, 0),
        }
        for key in BeatType.Severity.values
    ]

    today = timezone.localdate()
    start = today - timedelta(days=STATS_DAYS - 1)
    daily_rows = (
        beats.filter(created_at__date__gte=start)
        .annotate(day=TruncDate("created_at"))
        .values("day", "beat_type_id")
        .annotate(n=Count("id"))
    )
    daily_map = {}
    for row in daily_rows:
        day = row["day"]
        if day is None:
            continue
        key = day.isoformat()
        bucket = daily_map.setdefault(key, {})
        bucket[row["beat_type_id"]] = row["n"]

    by_day = []
    cursor = start
    while cursor <= today:
        key = cursor.isoformat()
        bucket = daily_map.get(key, {})
        by_type_day = [
            {
                "id": item.id,
                "slug": item.slug,
                "name": item.name,
                "count": bucket.get(item.id, 0),
            }
            for item in type_list
        ]
        by_day.append(
            {
                "date": key,
                "total": sum(point["count"] for point in by_type_day),
                "by_type": by_type_day,
            }
        )
        cursor += timedelta(days=1)

    return {
        "beats_total": beats.count(),
        "days": STATS_DAYS,
        "by_type": by_type,
        "by_severity": by_severity,
        "by_day": by_day,
    }
