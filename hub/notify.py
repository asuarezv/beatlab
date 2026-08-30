import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Beat

logger = logging.getLogger(__name__)


def beat_payload(beat: Beat) -> dict:
    return {
        "id": beat.id,
        "system": beat.system_id,
        "beat_type": beat.beat_type_id,
        "system_name": beat.system.name,
        "beat_type_name": beat.beat_type.name,
        "title": beat.title,
        "payload": beat.payload or {},
        "created_at": beat.created_at.isoformat(),
    }


def company_group(company_id: int) -> str:
    return f"company_{company_id}"


def notify_company_beat(beat: Beat) -> None:
    try:
        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            company_group(beat.company_id),
            {"type": "beat.created", "beat": beat_payload(beat)},
        )
    except Exception:
        logger.exception("No se pudo notificar el Beat %s", beat.pk)
