# JKanban — Visión general

## Índice

- [Descripción](#descripción)
- [Stack](#stack)
- [Estructura de carpetas](#estructura-de-carpetas)
- [Arranque en desarrollo](#arranque-en-desarrollo)
- [Variables de entorno](#variables-de-entorno)
- [Documentación técnica](#documentación-técnica)

---

## Descripción

JKanban es una aplicación web de gestión de tareas tipo Kanban multiusuario. Organiza el trabajo en **proyectos → grupos (columnas) → tareas**, con soporte para subtareas, etiquetas, prioridades, asignación de responsables y roles por proyecto.

**Versión:** 7.0.0 · **Idioma UI:** Español · **Tipo:** SPA + REST API

---

## Stack

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3 + FastAPI 0.115 |
| Base de datos | SQLite por defecto (`tasks.db`) — configurable via `DB_ENGINE`; sin ORM, queries SQL manuales |
| Autenticación | JWT HS256 · 7 días de expiración (PyJWT) |
| Passwords | PBKDF2-SHA256 · 100 000 iteraciones |
| Frontend | Vanilla JS + TailwindCSS · sin frameworks |
| Iconos | Material Symbols Outlined (Google Fonts CDN) |
| Tests | Pytest + httpx TestClient |
| Servidor dev | Uvicorn `--reload` |

---

## Estructura de carpetas

```
JKanban/
├── app/                        # Backend
│   ├── domain/                 # Entidades, ABCs repositorios, excepciones
│   ├── application/            # Casos de uso (lógica de negocio)
│   ├── infrastructure/         # SQLite, JWT, repos concretos
│   └── interfaces/             # Routers FastAPI, schemas Pydantic, DI
│       └── static/             # Archivos servidos (apunta a frontend/)
├── frontend/                   # Fuente del frontend
│   ├── index.html              # HTML + CSS embebido (TailwindCSS)
│   └── js/
│       ├── state.js            # Estado global S
│       ├── utils.js, api.js, auth.js, router.js, render.js
│       ├── views/              # dashboard, board, team, tags, priorities
│       ├── modals/             # base, project, group, task, tag, priority, user, subtask
│       └── dnd.js, delete.js
├── tests/                      # Pytest (un archivo por recurso)
├── scripts/start-dev.ps1       # Script arranque Windows
├── docs/                       # Esta documentación técnica
└── backend/requirements.txt
```

---

## Arranque en desarrollo

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
# o en Windows:
.\scripts\start-dev.ps1
```

- App: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`

## Variables de entorno

| Variable | Default (dev) | Producción |
|----------|--------------|------------|
| `JWT_SECRET` | `dev-secret-key-change-in-production-32b` | Cadena aleatoria ≥32 chars |
| `DB_ENGINE` | `sqlite` | `sqlite` (PostgreSQL: pendiente de adapter) |
| `SQLITE_PATH` | `<repo>/tasks.db` | Ruta absoluta al archivo SQLite |

---

## Documentación técnica

Este documento es el punto de entrada. Los documentos siguientes cubren cada área en detalle:

| Documento | Contenido |
|-----------|-----------|
| [Arquitectura del backend](architecture.md) | Clean Architecture: responsabilidades de cada capa, flujo de request, inyección de dependencias, patrones. Incluye anexo de migración SQLite → PostgreSQL. |
| [Modelo de datos](data-model.md) | Entidades con todos sus campos, tablas de unión, relaciones FK y comportamiento de cascadas. |
| [API REST](api.md) | Referencia completa de endpoints: parámetros, body, formato de respuesta y errores posibles por endpoint. |
| [Autenticación y permisos](auth-permissions.md) | JWT, hashing de contraseñas, sistema de roles (owner/leader/member/admin), tabla de permisos y flujos de login/logout. |
| [Frontend](frontend.md) | Arquitectura SPA: estado global, router hash-based, pipeline de render, sistema de modales, módulos JS y seguridad. |
| [Reglas de negocio](business-rules.md) | 21 excepciones de dominio con su código HTTP, restricciones por recurso y comportamiento SET NULL vs CASCADE. |
| [Tests](testing.md) | Setup de fixtures, archivos de test, patrón de test típico y comandos de ejecución. |
| [Añadir un motor de BD](adding-a-db-engine.md) | Guía paso a paso para conectar un engine nuevo (PostgreSQL, MySQL…): checklist, código de cada módulo del adapter y tabla de diferencias SQL. |
