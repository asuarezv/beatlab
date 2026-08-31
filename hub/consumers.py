from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from .notify import company_admin_group, operator_group
from .tokens import MONITOR_ROLE_ADMIN, verify_monitor_token


class MonitorConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        qs = parse_qs((self.scope.get("query_string") or b"").decode())
        token = (qs.get("token") or [""])[0]
        actor = await database_sync_to_async(verify_monitor_token)(token)
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
