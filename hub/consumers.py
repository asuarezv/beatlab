from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .models import Operator
from .notify import company_admin_group, operator_group
from .tokens import MONITOR_ROLE_ADMIN, MONITOR_ROLE_OPERATOR, MonitorActor, verify_monitor_token


def _actor_from_scope(scope):
    qs = parse_qs((scope.get("query_string") or b"").decode())
    token = (qs.get("token") or [""])[0]
    if token:
        return verify_monitor_token(token)
    session = scope.get("session")
    user = scope.get("user")
    if session is None or user is None or not getattr(user, "is_authenticated", False):
        return None
    if session.get("hub_role") != MONITOR_ROLE_OPERATOR:
        return None
    operator_id = session.get("operator_id")
    if not operator_id:
        return None
    operator = (
        Operator.objects.filter(pk=operator_id, user_id=user.pk)
        .select_related("user", "company")
        .first()
    )
    if operator is None:
        return None
    return MonitorActor.from_operator(operator)


class MonitorConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        actor = await database_sync_to_async(_actor_from_scope)(self.scope)
        if actor is None:
            await self.close(code=4401)
            return
        if actor.role == MONITOR_ROLE_ADMIN or actor.operator is None:
            self.group_name = company_admin_group(actor.company_id)
        else:
            self.group_name = operator_group(actor.operator.id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"type": "ready"})

    async def disconnect(self, code):
        group = getattr(self, "group_name", None)
        if group:
            await self.channel_layer.group_discard(group, self.channel_name)

    async def beat_created(self, event):
        await self.send_json({"type": "beat", "beat": event["beat"]})
