# BeatLab Monitor

App del Operator: panel de Beats en vivo. Pensada para **Expo Go**.

## Arranque

```bash
cd monitor
npm install
npx expo start
```

Escanea el QR con Expo Go. En Windows, `npx expo start --tunnel` ayuda si el teléfono no ve la LAN.

## Hub

Monitor apunta siempre a `https://hub.nynusoft.com` (`expo.extra.hubUrl` en `app.json`). Login, lista de Beats y WebSocket (`wss://hub.nynusoft.com/ws/monitor/`) usan esa base.

## Auth y vivo

1. Da de alta un Operator en el Hub.
2. En Monitor: usuario + contraseña de ese Operator.
3. Los Beats que lleguen al API (`POST /api/ingest/beats/` con el JWT del System) aparecen en la lista y por WebSocket (`/ws/monitor/?token=...`).

No guardes secretos ni JWTs de Systems en esta app.
