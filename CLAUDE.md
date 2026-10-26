# JKanban — Guía de sesión

## Documentación técnica

El punto de entrada a toda la documentación está en [`docs/overview.md`](docs/overview.md).
Cárgala cuando necesites contexto sobre arquitectura, API, modelo de datos, permisos o frontend.

---

## Ramas y estructura de carpetas

> La estructura del backend **cambia según la rama**. Verificar siempre con `git branch`.

| Rama | Backend en | Frontend en |
|------|-----------|-------------|
| `develop` | `backend/` | `frontend/` (21 módulos JS) |
| `main` / `release/*` | `app/` | `app/interfaces/static/` |

**Rama habitual de trabajo: `develop`**

---

## Arquitectura (resumen)

Clean Architecture en 4 capas con dependencias unidireccionales hacia dentro:

```
interfaces/ → application/ → domain/
infrastructure/  (implementa contratos de domain/)
```

- **`domain/`** — entidades puras, ABCs de repositorios, 21 excepciones tipadas. Sin imports externos.
- **`application/`** — casos de uso. Solo importa `domain/`. Nunca lanza `HTTPException`.
- **`infrastructure/`** — SQLite, JWT, repositorios concretos. Único sitio donde vive SQL.
- **`interfaces/`** — routers FastAPI, schemas Pydantic, DI con `Depends()`. Convierte excepciones de dominio → HTTP 4xx.

Para añadir una nueva entidad: entity → repository ABC → use case → SQLite repo → schema Pydantic → router.

---

## Frontend

SPA Vanilla JS sin bundler. Módulos cargados como `<script src>` en orden en `index.html`.

- Estado global en objeto `S` (`js/state.js`) — mutación directa + `render()` al final de cada operación.
- Routing hash-based (`#/`, `#/board/{pid}`, `#/team`) en `js/router.js`.
- Render completo en cada ciclo: `render()` → `renderSidebar()` + `renderHeader()` + `renderContent()`.

---

## Convenciones de seguridad (frontend)

| Función | Cuándo usarla |
|---------|--------------|
| `esc(s)` | Siempre que se inserte user content en `innerHTML` |
| `jsq(s)` | Para strings dentro de atributos `onclick` (literales JS) |
| ID numérico directo | En onclick es seguro sin escapar — pasar IDs, no nombres |

`confirmDel(type, id)` recibe solo el ID y busca el nombre en `S` internamente. No pasar el nombre como argumento.

---

## Base de datos

Motor seleccionado con `DB_ENGINE` (default y **único implementado hoy: `sqlite`**). Sin ORM, queries SQL manuales en `infrastructure/repositories/`.

SQL portable en repositorios y routers (lo verifica `tests/test_persistence_portability.py`):

- Importar solo desde `persistence.factory`: `get_connection`, `insert_returning_id`, `idempotent_insert`, `map_integrity_error`. Nunca desde `persistence.sqlite` ni `import sqlite3`.
- `%s` como placeholder (el wrapper SQLite lo traduce a `?`); `ph(n)` de `persistence/common/utils.py` para `IN (...)`
- `insert_returning_id(conn, sql, params)` para obtener el ID insertado (no `cursor.lastrowid`)
- `idempotent_insert(...)` en vez de `INSERT OR IGNORE`; `with map_integrity_error(lambda: DomainExc(...)):` en vez de capturar `sqlite3.IntegrityError`
- Timestamps con `utcnow()` de `common/utils.py`; nada de `%` literal en el SQL (pasar patrones `LIKE` como parámetro)
- Usar siempre `with get_connection() as conn:` — al salir hace commit/rollback **y cierra** la conexión

Específico de SQLite (dentro de `persistence/sqlite/`): `PRAGMA foreign_keys = ON` por conexión, migraciones no destructivas en `migrations.py`. Para añadir un engine: `docs/adding-a-db-engine.md`.

---

## Tests

```bash
pytest          # todos
pytest -v       # con detalle
pytest tests/test_projects.py  # un módulo
```

- BD en memoria (`:memory:`), independiente de `tasks.db`
- Fixture `auth` → usuario normal; `admin_auth` → usuario admin
- `clean_db` (autouse) trunca tablas antes de cada test

---

## Arranque

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# o en Windows:
.\scripts\start-dev.ps1
```

Swagger UI: `http://127.0.0.1:8000/docs`
