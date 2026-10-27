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

Estructura de la rama `develop` (en `main` / `release/*` el backend está en `app/`).

```
JKanban/
├── backend/                    # Backend
│   ├── main.py                 # App FastAPI: registra routers y sirve frontend/
│   ├── config.py               # Settings por variables de entorno (DB_ENGINE, SQLITE_PATH, JKANBAN_DEMO_DATA)
│   ├── create_admin.py         # Comando: crear o promover un administrador
│   ├── domain/                 # Entidades, ABCs repositorios, excepciones
│   ├── application/            # Casos de uso (lógica de negocio)
│   ├── infrastructure/
│   │   ├── persistence/        # factory (dispatch por engine), common/, sqlite/
│   │   ├── repositories/       # Sql*Repository: único sitio con SQL
│   │   └── jwt_handler.py
│   └── interfaces/             # Routers FastAPI, schemas Pydantic, DI
├── frontend/                   # SPA servida como estáticos
│   ├── index.html              # HTML + CSS embebido (TailwindCSS)
│   └── js/
│       ├── state.js            # Estado global S
│       ├── utils.js, api.js, auth.js, router.js, render.js
│       ├── views/              # dashboard, board, team, tags, priorities
│       ├── modals/             # base, project, group, task, tag, priority, user, subtask
│       └── dnd.js, delete.js
├── tests/                      # Pytest: un archivo por recurso + guardas de portabilidad
├── scripts/start-dev.ps1       # Script arranque Windows
├── docs/                       # Esta documentación técnica
└── backend/requirements.txt
```

---

## Arranque en desarrollo

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
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
| `JKANBAN_DEMO_DATA` | `1` (carga datos demo en una BD sin usuarios) | `0`: arranca vacío |
| `JKANBAN_ADMIN_PASSWORD` | — | Contraseña para `python -m backend.create_admin` |

El primer administrador se crea con `python -m backend.create_admin` (ver
[Instalación](installation.md#4-base-de-datos-y-administrador)).

---

## Documentación técnica

Este documento es el punto de entrada. Los documentos siguientes cubren cada área en detalle:

| Documento | Contenido |
|-----------|-----------|
| [Instalación](installation.md) | Instalar JKanban en una carpeta nueva paso a paso (pensado para que lo ejecute Claude Code): clonado, venv, contraseña del admin, variables de entorno y verificación. |
| [Flujos y etiquetas globales](flows.md) | **Especificación pendiente de implementar.** Flujos con estados y transiciones asignables a etiquetas; flujos y etiquetas globales o de proyecto. |
| [Servidor MCP](mcp.md) | `jkanban_mcp`: tools MCP para que el proyecto SF guarde planes y actividades (plan = grupo, actividad = tarea, paso = subtarea) a través de la API REST. Instalación y registro en Claude Code. |
| [Arquitectura del backend](architecture.md) | Clean Architecture: responsabilidades de cada capa, flujo de request, inyección de dependencias, patrones. Incluye anexo sobre cómo añadir un engine de BD. |
| [Modelo de datos](data-model.md) | Entidades con todos sus campos, tablas de unión, relaciones FK y comportamiento de cascadas. |
| [API REST](api.md) | Referencia completa de endpoints: parámetros, body, formato de respuesta y errores posibles por endpoint. |
| [Autenticación y permisos](auth-permissions.md) | JWT, hashing de contraseñas, sistema de roles (owner/leader/member/admin), tabla de permisos y flujos de login/logout. |
| [Frontend](frontend.md) | Arquitectura SPA: estado global, router hash-based, pipeline de render, sistema de modales, módulos JS y seguridad. |
| [Reglas de negocio](business-rules.md) | 21 excepciones de dominio con su código HTTP, restricciones por recurso y comportamiento SET NULL vs CASCADE. |
| [Tests](testing.md) | Setup de fixtures, archivos de test, patrón de test típico y comandos de ejecución. |
| [Aislamiento de BD en tests](testing-db.md) | Cómo `conftest.py` redirige la BD a un fichero temporal, ciclo de vida de `clean_db`, variables de entorno y qué no hacer. |
| [Añadir un motor de BD](adding-a-db-engine.md) | Reglas de SQL portable, guía paso a paso para conectar un engine nuevo (PostgreSQL, MySQL…): checklist, código de cada módulo del adapter y tabla de diferencias SQL. |
