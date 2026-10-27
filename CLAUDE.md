# JKanban — Guía de sesión

## Software Factory

Este proyecto se desarrolla con la Software Factory (SF), que llega como el plugin `sf` de Claude Code, instalado desde el catálogo publicado en GitHub.

- Método: la skill `sf:metodologia`, que dice qué parte del método leer en cada momento. JKanban es anterior a la SF: su documentación aún no sigue la estructura común (sección 6 del método).
- Decisiones: en `docs/decisiones.md`, con su porqué (sección 6 del método). Aún no existe.
- Estado en la SF: carpeta `.sf/` (metodología, 6). `.sf/proyecto.json`, versionado, identifica el proyecto; `.sf/estado.json`, fuera de git, guarda la fase, la devslice en curso, las fases hechas y los pendientes. Actualizarlo al cambiar de fase o de devslice. Lo muestra el plugin `sf` de la SF (línea de estado y `/sf`), instalado desde el catálogo publicado en GitHub.
- Mejora continua: las mejoras de la SF que se detecten aquí se registran en el proyecto **SoftwareFactory** del kanban (tarea «Mejorar la Software Factory»), indicando que el origen es JKanban y el contexto. Pedir aprobación antes de aplicarlas a la SF.

## Documentación técnica

El punto de entrada a toda la documentación está en [`docs/overview.md`](docs/overview.md).
Cárgala cuando necesites contexto sobre arquitectura, API, modelo de datos, permisos o frontend.

---

## Ramas y estructura de carpetas

| Rama | Uso |
|------|-----|
| `develop` | Rama habitual de trabajo. Las features salen en `feature/*` y vuelven por PR. |
| `release/vX.Y.Z` | Se abre desde `develop` para preparar una versión; PR a `main`. |
| `main` | Solo versiones publicadas; cada una con su tag `vX.Y.Z` (ver `CHANGELOG.md`). |

Backend en `backend/`, frontend en `frontend/` (21 módulos JS). Solo el tag antiguo `v0.0.0` usa `app/`.

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
- Timestamps con `utcnow()` al escribir y `row_dt()` al leer (acepta `str` o `datetime`); nada de `%` literal en el SQL (pasar patrones `LIKE` como parámetro)
- Booleanos: escribir `bool(...)`, nunca `int(...)`; sumar con `SUM(CASE WHEN col THEN 1 ELSE 0 END)`
- Columnas por nombre: `SELECT COUNT(*) AS n` → `row["n"]`, nunca `row[0]`
- Solo los repositorios (`Sql*Repository`) ejecutan SQL: routers, casos de uso y tests nunca usan `get_connection`
- Usar siempre `with get_connection() as conn:` — al salir hace commit/rollback **y cierra** la conexión

Específico de SQLite (dentro de `persistence/sqlite/`): `PRAGMA foreign_keys = ON` por conexión, migraciones no destructivas en `migrations.py`. Para añadir un engine: `docs/adding-a-db-engine.md`.

---

## Tests

```bash
pytest          # todos
pytest -v       # con detalle
pytest tests/test_projects.py  # un módulo
```

- BD SQLite en fichero temporal (`conftest.py` fija `SQLITE_PATH`), independiente de `tasks.db`
- Fixture `auth` → usuario normal; `admin_auth` → usuario admin
- `clean_db` (autouse) vacía tablas y reinicia IDs antes de cada test (`factory.reset_tables()`)
- Los tests no ejecutan SQL: preparan datos vía API o casos de uso
- `tests/test_persistence_portability.py` vigila las reglas de la sección *Base de datos*

---

## Arranque

```bash
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
# o en Windows:
.\scripts\start-dev.ps1
```

Swagger UI: `http://127.0.0.1:8000/docs`
