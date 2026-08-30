# BeatLab Monitor

App del Operator: panel de Beats en vivo. Pensada para **Expo Go**.

## Arranque

```bash
cd monitor
npm install
npx expo start
```

Escanea el QR con Expo Go. En Windows, `npx expo start --tunnel` ayuda si el teléfono no ve la LAN.

## Apuntar al Hub

Por defecto Monitor usa `https://hub.nynusoft.com`. En la pantalla de entrada puedes cambiar la URL del Hub (por ejemplo `http://192.168.1.20:8000` si corres el API en tu máquina).

El Hub local debe escucharse en la IP de la LAN, no solo en `127.0.0.1`:

```bash
# desde la raíz del repo, con las dependencias de Python instaladas
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

`python manage.py runserver 0.0.0.0:8000` también sirve HTTP y WebSocket si Daphne está instalado.

## Auth y vivo

1. Da de alta un Operator en el Hub.
2. En Monitor: usuario + contraseña de ese Operator.
3. Los Beats que lleguen al API (`POST /api/ingest/beats/` con el JWT del System) aparecen en la lista y por WebSocket (`/ws/monitor/?token=...`).

No guardes secretos ni JWTs de Systems en esta app.
