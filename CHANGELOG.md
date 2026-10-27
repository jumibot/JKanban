# Cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/).
Versionado semántico: el primer número sube cuando algo deja de ser compatible
(API REST, herramientas del MCP o datos); el segundo, al añadir funciones; el tercero, en correcciones.

## [Sin publicar]

### Cambiado
- Guías en `docs/guias/`: instalación desde cero (`instalacion.md`, antes `docs/installation.md`, ahora con el MCP) y actualización (`actualizacion.md`, nueva), como pide la Software Factory.

## [1.0.0] — 2026-10-27

Primera versión estable: la que instala la Software Factory.

### Añadido
- **Flujos de estados**: estados (uno inicial), transiciones e historial de cambios con nota. Se asignan a etiquetas; cada etiqueta asignada a una tarea o grupo lleva su estado. Ver `docs/flows.md`.
- **Etiquetas y flujos globales**, gestionados por el admin y compartidos por todos los proyectos.
- **Servidor MCP** (`jkanban_mcp/`, 44 herramientas) para que Claude Code use el tablero. Ver `docs/mcp.md`.
- **Arranque vacío**: `JKANBAN_DEMO_DATA=0` y `python -m backend.create_admin`.
- La base de datos puede vivir fuera del código (`SQLITE_PATH`).
- Guía de instalación pensada para que la ejecute Claude Code (`docs/installation.md`).

### Cambiado
- Backend en `backend/` y frontend separado en `frontend/` (21 módulos JS). En `v0.0.0` todo estaba en `app/`.
- Persistencia detrás de un factory (`DB_ENGINE`) con SQL portable; solo hay motor SQLite.
- La API se presenta como «JKanban API» 1.0.0 (antes «Tasks API» 7.0.0).

### Corregido
- XSS en manejadores `onclick` (helper `jsq()`).
- Reordenar y prioridades limitados a su propio proyecto.
- Las migraciones ya no borran datos en cascada al recrear tablas.

### Retirado
- `backend/infrastructure/database.py`, el alias de la conexión antigua: usar `backend.infrastructure.persistence.factory`.

## [0.0.0] — 2026-04-13

Versión inicial: FastAPI + SPA en JavaScript, en `app/`.
