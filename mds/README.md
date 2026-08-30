# Documentación

Los archivos Markdown de este proyecto viven aquí.

| Documento | Contenido |
|-----------|-----------|
| [vision.md](./vision.md) | Qué es el producto, para quién es y qué problemas resuelve |
| [dominio.md](./dominio.md) | Conceptos: empresa/Hub, Operators, Systems, tipos de Beat y Beats |
| [arquitectura.md](./arquitectura.md) | Stack, multi-tenant, piezas del sistema y flujo de un Beat |

Nombres oficiales:

- **BeatLab** — el SaaS
- **Hub** — comercialmente, lo que se vende a cada empresa (su centro de salud de Systems). Técnicamente, un solo Hub multi-tenant que los administra todos
- **Monitor** — app nativa (React Native)
- **System** — aplicación de una empresa que emite Beats
- **Beat** — el evento de salud clasificado por tipo
- **Operator** — quien usa Monitor, dentro de una empresa
