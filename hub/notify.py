import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .assignment import operators_for_beat
from .models import Beat

logger = logging.getLogger(__name__)


def beat_payload(beat: Beat) -> dict:
    beat_type = beat.beat_type
    return {
        "id": beat.id,
        "system": beat.system_id,
        "beat_type": beat_type.id,
        "system_name": beat.system.name,
        "beat_type_name": beat_type.name,
        "beat_type_slug": beat_type.slug,
        "severity": beat_type.severity,
        "severity_label": beat_type.get_severity_display(),
        "beat_type_icon": beat_type.resolved_icon(),
        "title": beat.title,
        "payload": beat.payload or {},
        "created_at": beat.created_at.isoformat(),
    }


def company_admin_group(company_id: int) -> str:
    return f"company_{company_id}_admin"


def operator_group(operator_id: int) -> str:
    return f"operator_{operator_id}"


def notify_company_beat(beat: Beat) -> None:
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        payload = {"type": "beat.created", "beat": beat_payload(beat)}
        async_to_sync(layer.group_send)(
            company_admin_group(beat.company_id),
            payload,
        )
        for operator_id in operators_for_beat(beat).values_list("id", flat=True):
            async_to_sync(layer.group_send)(operator_group(operator_id), payload)
    except Exception:
        logger.exception("No se pudo notificar el Beat %s", beat.pk)
