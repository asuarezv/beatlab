# Dominio

**BeatLab** es el SaaS. El dominio gira en torno a quién compra, quién observa, quién emite, cómo se clasifica el mensaje y el mensaje en sí.

## Empresa y Hub

La **empresa** es la cliente. Se le vende un **Hub**: su centro para controlar la salud de sus Systems.

Ese Hub comercial es un espacio aislado. Técnicamente no hay un Hub por empresa: **un solo Hub** (API Django + administración React) administra todos los Hubs.

Desde el Hub de una empresa se dan de alta sus Operators, sus Systems (con JWT) y sus tipos de Beat. También se validan, persisten y enrutan los Beats de esa empresa.

Hub no es el panel de cada Operator en Monitor. Ese panel es la vista personal de Beats y notificaciones, siempre dentro de su empresa.

No hay un nombre oficial extra para la empresa ni para quien administra el Hub. Operator es quien usa Monitor.

## Operator

Persona de una empresa con acceso a **Monitor** y a **su** panel: ve los Beats que le corresponden (de los Systems de su empresa) y recibe notificaciones.

Los Operators se dan de alta desde el Hub de su empresa, no desde Monitor.

## System

Cualquier aplicación de una empresa autorizada a mandar Beats a Hub. Cada System se registra en el Hub de esa empresa y obtiene credenciales para autenticarse con JWT.

Un System no es un Operator: es un cliente técnico (un producto, un servicio, un job) que publica su salud como Beats.

## Tipo de Beat

Etiqueta con la que se clasifica un Beat. El Hub de la empresa define los tipos disponibles. Un Beat siempre pertenece a un tipo; no hay mensajes “sin categoría”.

Ejemplos posibles (ilustrativos, no cerrados): alerta, aviso, confirmación, error, estado.

## Beat

Un mensaje emitido por un System, autenticado con JWT y clasificado por tipo de Beat. Es una señal de salud de ese System.

Un Beat es el hecho que el Operator ve en su panel y, cuando aplica, el origen de una notificación en Monitor.

## Monitor

App nativa en React Native. Es la superficie del Operator: panel personal de Beats y notificaciones, acotado a su empresa.

## Relaciones

```
BeatLab (SaaS)
        │
        └── un Hub técnico administra → Hub de cada empresa
                │
                ├── da de alta → Operator ───► panel en Monitor + notificaciones
                ├── da de alta → System ─────► emite Beats (JWT)
                └── da de alta → Tipo de Beat

System ──JWT──► Hub ──► Beat (tipo de Beat, empresa) ──► Operator(s) de esa empresa
```
