from django.db.models import Q

from .models import Beat, BeatType, Operator


class AssignmentError(ValueError):
    pass


def parse_receive_all(value) -> bool:
    if isinstance(value, bool):
        return value
    if value in (None, ""):
        return False
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def resolve_company_beat_types(company, type_ids):
    if type_ids is None:
        return []
    if not isinstance(type_ids, (list, tuple)):
        raise AssignmentError("Los tipos de Beat deben enviarse como lista.")
    ids = []
    for raw in type_ids:
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            raise AssignmentError("Hay un tipo de Beat que no es válido.") from None
    unique = list(dict.fromkeys(ids))
    if not unique:
        return []
    found = list(BeatType.objects.filter(company=company, pk__in=unique))
    if len(found) != len(unique):
        raise AssignmentError("Hay tipos de Beat que no son de esta empresa.")
    by_id = {item.id: item for item in found}
    return [by_id[item_id] for item_id in unique]


def assignment_payload(obj) -> dict:
    return {
        "receive_all_beat_types": bool(obj.receive_all_beat_types),
        "beat_type_ids": list(obj.assigned_beat_types.values_list("id", flat=True)),
    }


def apply_assignment(target, *, receive_all, beat_types):
    target.receive_all_beat_types = bool(receive_all)
    target.save(update_fields=["receive_all_beat_types"])
    if target.receive_all_beat_types:
        target.assigned_beat_types.clear()
    else:
        target.assigned_beat_types.set(beat_types)


def operators_for_beat(beat: Beat):
    return (
        Operator.objects.filter(company_id=beat.company_id)
        .filter(
            Q(receive_all_beat_types=True) | Q(assigned_beat_types=beat.beat_type_id)
        )
        .distinct()
    )


def types_visible_to_actor(actor):
    types = BeatType.objects.filter(company=actor.company)
    if actor.operator is None:
        return types
    operator = actor.operator
    if operator.receive_all_beat_types:
        return types
    type_ids = list(operator.assigned_beat_types.values_list("id", flat=True))
    if not type_ids:
        return types.none()
    return types.filter(pk__in=type_ids)


def beats_visible_to_actor(actor):
    beats = Beat.objects.filter(company=actor.company).select_related(
        "system", "beat_type"
    )
    if actor.operator is None:
        return beats
    operator = actor.operator
    if operator.receive_all_beat_types:
        return beats
    type_ids = list(operator.assigned_beat_types.values_list("id", flat=True))
    if not type_ids:
        return beats.none()
    return beats.filter(beat_type_id__in=type_ids)
