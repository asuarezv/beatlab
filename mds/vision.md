# Visión de producto

**BeatLab** es un SaaS. A cada empresa se le vende un **Hub**: su centro para controlar la salud de sus sistemas. Otras aplicaciones de esa empresa envían eventos; cada evento se llama **Beat**.

Comercialmente hay muchos Hubs (uno por empresa). Técnicamente hay **un solo Hub** que administra todos.

## Para quién

Empresas que necesitan ver la salud de sus sistemas. En el dominio, la empresa es la cliente; las personas que observan en el celular son **Operators**; cada sistema que reporta es un **System**.

## Qué construimos

- **Monitor**, la app nativa en React Native. Cada Operator ve los Beats de su empresa y recibe notificaciones.
- **Hub**, el centro del SaaS. Una sola instancia multi-tenant. Incluye:
  - un **API** en Django + PostgreSQL. Django solo expone el API; no usamos su interfaz de administración.
  - una **administración** en React. Desde el Hub de cada empresa se dan de alta:
    - los **Operators** (quienes usan Monitor)
    - los **Systems** (cualquier aplicación de la empresa que pueda mandar un Beat autenticado con JWT)
    - los **tipos de Beat** con los que se clasifican esos mensajes

## Principios

- **SaaS multi-tenant.** Un Hub técnico; aislamiento por empresa. Lo que se vende es el Hub de esa empresa.
- **Salud de sistemas.** El Hub de una empresa existe para controlar el estado de sus Systems, no como un buzón genérico.
- **Multiusuario.** Cada Operator tiene su propio panel en Monitor, acotado a su empresa.
- **Clasificación por tipo.** Un Beat no es un mensaje genérico: siempre llega asociado a un tipo de Beat.
- **Emisión autenticada.** Los Systems firman sus envíos con JWT. Hub no acepta Beats anónimos.
- **Administración en Hub.** El backoffice es la UI de Hub (React), no Django Admin, para controlar la experiencia de alta y operación.

## Fuera de alcance (por ahora)

- Usar Django Admin o plantillas de Django como interfaz.
- Definir aún el modelo de permisos fino; eso se documentará cuando se diseñe cada módulo. Las notificaciones push van por FCM.
- Un quinto nombre oficial para quien administra Hub. Operator es quien usa Monitor, no quien da de alta Systems, Operators y tipos de Beat.
- Un nombre oficial distinto para la empresa cliente. Comercialmente se le vende un Hub; no hay un séptimo nombre de producto para el tenant.
