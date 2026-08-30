# Arquitectura

**BeatLab** es un SaaS. Comercialmente se venden Hubs (uno por empresa). Técnicamente hay **un solo Hub** multi-tenant que administra todos, más **Monitor** (app del Operator).

## Stack

| Pieza | Tecnología | Rol |
|-------|------------|-----|
| Monitor | React Native | Notificaciones y panel de Beats por Operator (dentro de su empresa) |
| Hub (admin) | React | Alta de Operators, Systems (JWT) y tipos de Beat por empresa |
| Hub (API) | Django | Única puerta de negocio; sin interfaz Django |
| Push | FCM | Canal de notificaciones nativas (Android e iOS vía Firebase) |
| Base de datos | PostgreSQL | Persistencia multi-tenant |

Django no se usa como sitio ni como Django Admin. El API de Hub es el contrato; la administración de Hub y Monitor son las únicas UIs.

## Piezas

```
┌─────────────────────┐     JWT      ┌─────────────────────┐     ┌────────────┐
│  Systems (empresa)  │─────────────►│         Hub         │────►│ PostgreSQL │
└─────────────────────┘              │  un solo Hub SaaS   │     │ (tenants)  │
                                     │  API Django + admin │     └────────────┘
                                     └──────────┬──────────┘
                                                │
                                                │ FCM
                                                ▼
                                       ┌─────────────────┐
                                       │     Monitor     │
                                       │      (RN)       │
                                       └─────────────────┘
```

- **Systems:** publican Beats contra Hub con JWT. Pertenecen a una empresa.
- **Hub:** una instancia. Valida el token, resuelve la empresa, clasifica el Beat por tipo, lo persiste en ese tenant y, si aplica, dispara el push por FCM. La administración de Hub es el Hub de cada empresa.
- **Monitor:** consumo: panel por Operator, acotado a su empresa, y notificaciones (token FCM del dispositivo).

## Flujo de un Beat

1. Un System, ya dado de alta en el Hub de su empresa, firma la petición con JWT.
2. Hub autentica al System, resuelve la empresa, valida el tipo de Beat y guarda el Beat en ese tenant.
3. Hub determina qué Operators de esa empresa deben verlo.
4. Esos Operators lo reciben en Monitor y, si aplica, como notificación push vía FCM.

## Superficies de uso

| Superficie | Quién | Qué hace |
|------------|-------|----------|
| Hub (admin) | Administración del Hub de la empresa | Alta de Operators, Systems (JWT) y tipos de Beat |
| Monitor | Operator | Ve su panel, consulta Beats de su empresa y recibe notificaciones |
| Hub (API) | Systems y UIs | Autenticación JWT, persistencia y reglas de negocio |

## Decisiones cerradas

- **Modelo comercial:** SaaS. Se vende un Hub por empresa.
- **Modelo técnico:** un solo Hub multi-tenant administra todos los Hubs.
- **Propósito del Hub de una empresa:** controlar la salud de sus Systems.
- **Push:** FCM. Un solo canal para Android e iOS (iOS pasa por APNs debajo de Firebase). Monitor registra el token del dispositivo; Hub envía el push.

## Decisiones abiertas

- Cómo se aísla el tenant (columna de empresa, schema por empresa, u otro).
- Cómo se asocia un Beat a uno o varios Operators (todos los de la empresa, por System, por tipo, por suscripción).
- Si el JWT de Systems y el de Operators/administración de Hub es el mismo esquema o dos audiencias distintas.
- Facturación, planes y límites por Hub/empresa.
