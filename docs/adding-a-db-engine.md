# Añadir un nuevo motor de base de datos

Esta guía explica cómo conectar un engine de base de datos nuevo (p.ej. PostgreSQL, MySQL) a JKanban sin modificar el dominio, los casos de uso, los routers ni los repositorios existentes.

## Índice

- [Cómo funciona el sistema actual](#cómo-funciona-el-sistema-actual)
- [Checklist de implementación](#checklist-de-implementación)
- [Paso 1 — Crear la carpeta del adapter](#paso-1--crear-la-carpeta-del-adapter)
- [Paso 2 — connection.py](#paso-2--connectionpy)
- [Paso 3 — adapter.py](#paso-3--adapterpy)
- [Paso 4 — schema.py](#paso-4--schemapy)
- [Paso 5 — migrations.py](#paso-5--migrationspy)
- [Paso 6 — seed.py](#paso-6--seedpy)
- [Paso 7 — Registrar en factory.py](#paso-7--registrar-en-factorypy)
- [Paso 8 — Activar y verificar](#paso-8--activar-y-verificar)
- [Referencia: diferencias SQLite vs PostgreSQL](#referencia-diferencias-sqlite-vs-postgresql)

---

## Cómo funciona el sistema actual

```
database.py  (alias público, 2 líneas)
    └── persistence/factory.py   ← punto de despacho por DB_ENGINE
            ├── sqlite/
            │     ├── connection.py   ← wrapper de sqlite3
            │     ├── adapter.py      ← insert_returning_id, idempotent_insert, map_integrity_error
            │     ├── schema.py       ← CREATE TABLE
            │     ├── migrations.py   ← migraciones ad-hoc
            │     └── seed.py         ← datos demo
            └── <nuevo-engine>/       ← lo que hay que crear
```

Todos los repositorios importan **solo desde `persistence.factory`**: `get_connection()` y los helpers de dialecto (`insert_returning_id`, `idempotent_insert`, `map_integrity_error`; `reset_tables` lo usan solo los tests). El factory lee la variable de entorno `DB_ENGINE` y delega en los módulos `connection.py` / `adapter.py` del engine activo. **Añadir un engine es completamente aditivo**: no se modifica ningún repositorio ni ninguna capa superior.

### Reglas para el SQL de repositorios y routers

- Placeholders siempre `%s` (el wrapper SQLite los traduce a `?`). Para `IN (...)` usar `ph(n)` de `persistence/common/utils.py`.
- Nunca `cursor.lastrowid`, `INSERT OR IGNORE`, `import sqlite3` ni imports desde `persistence.sqlite`: usar los helpers del factory.
- No escribir un `%` literal en el SQL (p.ej. `LIKE '%texto'`): pasar el patrón como parámetro (`LIKE %s`, `("%texto",)`).
- Timestamps generados en Python con `utcnow()`, nunca `datetime('now')` / `NOW()` en el SQL. Leerlos con `row_dt()`, nunca `datetime.fromisoformat()`.
- Booleanos: escribir `bool(...)`, nunca `int(...)`. Sumar con `SUM(CASE WHEN col THEN 1 ELSE 0 END)`.
- Leer columnas por nombre (`SELECT COUNT(*) AS n` → `row["n"]`), nunca por posición (`row[0]`).
- Solo los repositorios hablan con la BD: ni routers, ni casos de uso, ni dominio importan `persistence` o `get_connection`.

`tests/test_persistence_portability.py` verifica estas reglas automáticamente en `repositories/`, `domain/`, `application/` e `interfaces/`.

---

## Checklist de implementación

```
[ ] 1. Crear backend/infrastructure/persistence/<engine>/
[ ] 2. connection.py  — clase wrapper + get_connection()
[ ] 3. adapter.py     — insert_returning_id, idempotent_insert, map_integrity_error, reset_tables
[ ] 4. schema.py      — create_schema(conn)
[ ] 5. migrations.py  — migrate(conn)
[ ] 6. seed.py        — seed_db()
[ ] 7. factory.py     — añadir el engine a _ENGINE_PACKAGES y una rama en init_engine()
[ ] 8. Añadir driver a requirements.txt
[ ] 9. pytest con DB_ENGINE=<engine> — 334 passed (mismo resultado que con SQLite)
```

---

## Paso 1 — Crear la carpeta del adapter

```
backend/infrastructure/persistence/
└── postgres/           ← nombre del engine (minúsculas, sin guiones)
    ├── __init__.py
    ├── connection.py
    ├── adapter.py
    ├── schema.py
    ├── migrations.py
    └── seed.py
```

---

## Paso 2 — `connection.py`

El objeto devuelto por `get_connection()` debe cumplir el mismo contrato que `SQLiteConnection`:

- `conn.execute(sql, params)` → devuelve un cursor con `.fetchone()`, `.fetchall()`
- `conn.executemany(sql, seq)`
- `with conn:` → commit en éxito, rollback en excepción y **cierre de la conexión** en ambos casos (o devolverla al pool)
- Las filas son accesibles por nombre de columna: `row["id"]`

**Problema con psycopg2:** las conexiones de psycopg2 no tienen `.execute()` — solo los cursors lo tienen. Devolver la conexión raw haría que `conn.execute(...)` fallara en runtime. La solución es un wrapper, igual que `SQLiteConnection`.

### Ejemplo PostgreSQL

```python
"""PostgreSQL connection adapter."""
import os
import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor


class PostgreSQLConnection:
    """Thin wrapper around psycopg2 connection.

    Exposes the same execute/executemany surface that SQLiteConnection
    provides, so schema, migration and seed modules work identically
    regardless of the underlying driver.

    A single RealDictCursor is kept for the lifetime of the connection;
    rows are accessible by column name (row["id"]).
    """

    def __init__(self, raw: psycopg2.extensions.connection) -> None:
        self._conn = raw
        self._cur = raw.cursor(cursor_factory=RealDictCursor)

    def execute(self, sql: str, params=()) -> psycopg2.extensions.cursor:
        self._cur.execute(sql, params)
        return self._cur

    def executemany(self, sql: str, seq) -> psycopg2.extensions.cursor:
        self._cur.executemany(sql, seq)
        return self._cur

    def commit(self) -> None:
        self._conn.commit()

    def __enter__(self) -> "PostgreSQLConnection":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._conn.rollback()
        else:
            self._conn.commit()
        self._cur.close()
        self._conn.close()

    def __getattr__(self, name: str):
        return getattr(self._conn, name)


def get_connection() -> PostgreSQLConnection:
    """Open and return a wrapped PostgreSQL connection.

    DATABASE_URL format: postgresql://user:password@host:5432/jkanban
    """
    raw = psycopg2.connect(os.environ["DATABASE_URL"])
    return PostgreSQLConnection(raw)
```

> `DATABASE_URL` sigue el formato estándar:  
> `postgresql://user:password@host:5432/jkanban`

**Consideración de producción:** para alta concurrencia usa un pool. El wrapper sigue siendo el mismo; solo cambia cómo se obtiene la conexión raw:

```python
from contextlib import contextmanager
from psycopg2 import pool as pg_pool

_pool: pg_pool.ThreadedConnectionPool | None = None

def _get_pool() -> pg_pool.ThreadedConnectionPool:
    global _pool
    if _pool is None:
        _pool = pg_pool.ThreadedConnectionPool(2, 10, os.environ["DATABASE_URL"])
    return _pool

@contextmanager
def get_connection() -> PostgreSQLConnection:
    raw = _get_pool().getconn()
    try:
        yield PostgreSQLConnection(raw)
    finally:
        _get_pool().putconn(raw)
```

---

## Paso 3 — `adapter.py`

Este módulo aísla los puntos de especificidad del driver que de otro modo se filtrarían a los repositorios. Debe ofrecer las mismas cuatro funciones que `sqlite/adapter.py` (`reset_tables` solo la usan los tests):

| Función | Qué hace | SQLite | PostgreSQL |
|---------|---------|--------|-----------|
| `insert_returning_id(conn, sql, params)` | INSERT y devuelve el ID generado | `cursor.lastrowid` | `RETURNING id` |
| `idempotent_insert(conn, sql, params)` | INSERT que ignora duplicados | `INSERT OR IGNORE INTO` | `INSERT … ON CONFLICT DO NOTHING` |
| `map_integrity_error(exc_factory)` | Context manager que traduce errores de integridad a excepciones de dominio | `sqlite3.IntegrityError` | `psycopg2.errors.UniqueViolation` |
| `reset_tables(conn, tables)` | Vacía tablas y reinicia contadores de ID (tests) | `DELETE` + `sqlite_sequence` | `TRUNCATE … RESTART IDENTITY CASCADE` |

### Ejemplo PostgreSQL

```python
"""PostgreSQL-specific persistence helpers."""
import psycopg2.errors
from contextlib import contextmanager
from typing import Callable


def insert_returning_id(conn, sql: str, params) -> int:
    sql_returning = sql.rstrip().rstrip(";") + " RETURNING id"
    row = conn.execute(sql_returning, params).fetchone()
    return row["id"]


def idempotent_insert(conn, sql: str, params) -> None:
    adapted = sql.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    conn.execute(adapted, params)


@contextmanager
def map_integrity_error(exc_factory: Callable):
    try:
        yield
    except psycopg2.errors.UniqueViolation as e:
        raise exc_factory() from e


def reset_tables(conn, tables: list[str]) -> None:
    conn.execute(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE")
```

---

## Paso 4 — `schema.py`

Define `create_schema(conn)` con los `CREATE TABLE IF NOT EXISTS` adaptados al nuevo engine.

### Diferencias clave respecto a SQLite

| SQLite | PostgreSQL |
|--------|-----------|
| `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| `TEXT NOT NULL DEFAULT (datetime('now'))` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` |
| `TEXT` para fechas | `TIMESTAMPTZ` |
| `INTEGER NOT NULL DEFAULT 0 CHECK(is_admin IN (0,1))` | `BOOLEAN NOT NULL DEFAULT FALSE` |
| `CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#')` | `CHECK(color ~ '^#[0-9A-Fa-f]{6}$')` |
| `INSERT OR IGNORE INTO` | `INSERT INTO … ON CONFLICT DO NOTHING` |

### FK circular entre `projects` y `priorities`

SQLite acepta la FK circular sin validarla. PostgreSQL la rechaza en la creación. La solución es crear `projects` sin `priority_id`, luego añadirlo con `ALTER TABLE`:

```python
def create_schema(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id          SERIAL PRIMARY KEY,
            name        TEXT    NOT NULL,
            ...
            -- Sin priority_id aquí; se añade después de crear priorities
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS priorities (
            id          SERIAL PRIMARY KEY,
            project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
            ...
        )
    """)
    # Añadir la FK circular ahora que priorities ya existe
    conn.execute("""
        ALTER TABLE projects
        ADD COLUMN IF NOT EXISTS priority_id INTEGER REFERENCES priorities(id) ON DELETE SET NULL
    """)
    ...
```

---

## Paso 5 — `migrations.py`

Define `migrate(conn)`. Para engines distintos de SQLite se recomienda usar **migraciones versionadas** en lugar del patrón de introspección de SQLite (que depende de `sqlite_master` y `PRAGMA`, ambos SQLite-específicos).

Opción recomendada: **Alembic** o archivos SQL numerados.

```python
"""PostgreSQL migrations — versioned approach."""


def migrate(conn) -> None:
    """Apply all pending migrations."""
    _ensure_migrations_table(conn)
    _run_pending(conn)


def _ensure_migrations_table(conn) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _migrations (
            id         SERIAL PRIMARY KEY,
            name       TEXT NOT NULL UNIQUE,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)


def _run_pending(conn) -> None:
    applied = {r["name"] for r in conn.execute("SELECT name FROM _migrations").fetchall()}
    for name, sql in _MIGRATIONS:
        if name not in applied:
            conn.execute(sql)
            conn.execute("INSERT INTO _migrations (name) VALUES (%s)", (name,))


# Lista de migraciones en orden; añadir al final, nunca modificar las existentes
_MIGRATIONS: list[tuple[str, str]] = [
    # ("0001_ejemplo", "ALTER TABLE users ADD COLUMN IF NOT EXISTS nueva_col TEXT"),
]
```

---

## Paso 6 — `seed.py`

Igual que `sqlite/seed.py` pero usando los helpers del nuevo adapter. Asegúrate de importar `get_connection` y `insert_returning_id` del módulo del propio engine:

```python
"""PostgreSQL seed data."""
from backend.infrastructure.persistence.postgres.connection import get_connection
from backend.infrastructure.persistence.postgres.adapter import insert_returning_id


def seed_db() -> None:
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) AS n FROM users").fetchone()["n"] > 0:
            return
        u_alice = insert_returning_id(
            conn,
            "INSERT INTO users (name, email, password_hash, is_admin) VALUES (%s,%s,%s,%s)",
            ("Alice Martín", "alice@example.com", "pbkdf2$seed$placeholder", True),
        )
        # … resto del seed igual que sqlite/seed.py
        conn.commit()
```

---

## Paso 7 — Registrar en `factory.py`

Dos cambios. **No modificar las entradas existentes**:

1. Registrar el paquete en `_ENGINE_PACKAGES`. Con eso, `get_connection()` y los helpers de dialecto ya despachan al nuevo engine:

```python
_ENGINE_PACKAGES = {
    "sqlite": "backend.infrastructure.persistence.sqlite",
    "postgres": "backend.infrastructure.persistence.postgres",       # ← añadir
}
```

2. Añadir la rama de inicialización en `init_engine()`:

```python
def init_engine() -> None:
    engine = db_settings.engine
    if engine == "sqlite":
        # … (sin cambios)
        return
    if engine == "postgres":                                          # ← añadir
        from backend.infrastructure.persistence.postgres.migrations import migrate
        from backend.infrastructure.persistence.postgres.schema import create_schema
        from backend.infrastructure.persistence.postgres.seed import seed_db
        with get_connection() as conn:
            create_schema(conn)
            migrate(conn)
            conn.commit()
        seed_db()
        return
    raise _unsupported(engine)
```

---

## Paso 8 — Activar y verificar

```bash
# Añadir el driver
echo "psycopg2-binary>=2.9" >> backend/requirements.txt
pip install psycopg2-binary

# Arrancar con el nuevo engine
DB_ENGINE=postgres DATABASE_URL=postgresql://user:pass@localhost:5432/jkanban \
    python -m uvicorn backend.main:app --reload

# Pasar los tests contra el nuevo engine
DB_ENGINE=postgres DATABASE_URL=postgresql://user:pass@localhost:5432/jkanban_test \
    pytest -v
```

La suite de tests no requiere modificaciones: `tests/conftest.py` solo crea el fichero temporal cuando `DB_ENGINE=sqlite` y limpia las tablas con `factory.reset_tables()`, que delega en el `adapter.py` del engine. Con otro engine, la BD de pruebas se indica por entorno (`DATABASE_URL` apuntando a una BD **desechable**: los tests la vacían).

### Qué ya está resuelto en el código común

| Diferencia entre engines | Cómo lo absorbe el código actual |
|--------------------------|----------------------------------|
| Fechas: SQLite devuelve `str`, PostgreSQL `datetime` (con zona si es `TIMESTAMPTZ`) | `row_dt()` / `to_datetime()` aceptan ambos y normalizan a `datetime` UTC sin zona |
| Booleanos: SQLite `INTEGER` 0/1, PostgreSQL `BOOLEAN` | Se escribe siempre `bool(...)` (sqlite3 lo guarda como 1/0); las sumas usan `SUM(CASE WHEN completed THEN 1 ELSE 0 END)` |
| Filas: `sqlite3.Row` admite `row[0]`, `RealDictCursor` no | Todo acceso por nombre: `SELECT COUNT(*) AS n … row["n"]` |
| SQL fuera de infraestructura | Recuentos y borrados en cascada movidos a `ProjectRepository.count_contents()` / `get_owned_by()` y `UserRepository.delete_with_owned_projects()` |

`tests/test_persistence_portability.py` impide que estas diferencias vuelvan a colarse.

> **Recomendación de esquema:** declarar las fechas como `TIMESTAMP` (sin zona) y guardar UTC, igual que hace hoy `utcnow()`. `TIMESTAMPTZ` también funciona gracias a `to_datetime()`, pero entonces la zona horaria del servidor deja de ser irrelevante.

---

## Referencia: diferencias SQLite vs PostgreSQL

| Aspecto | SQLite | PostgreSQL |
|---------|--------|-----------|
| Driver Python | `sqlite3` (stdlib) | `psycopg2-binary` |
| Placeholder | `?` (o `%s` via wrapper) | `%s` |
| ID insertado | `cursor.lastrowid` | `RETURNING id` |
| Booleanos | `INTEGER` 0/1 | `BOOLEAN` nativo |
| Timestamps | `TEXT` ISO-8601 | `TIMESTAMPTZ` |
| Auto-ID | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| DEFAULT fecha | `datetime('now')` | `NOW()` |
| CHECK color | `SUBSTR(color,1,1)='#'` | `color ~ '^#[0-9A-Fa-f]{6}$'` |
| Upsert silencioso | `INSERT OR IGNORE INTO` | `INSERT … ON CONFLICT DO NOTHING` |
| FK enforcement | `PRAGMA foreign_keys = ON` por conexión | Activo por defecto |
| Error duplicado | `sqlite3.IntegrityError` | `psycopg2.errors.UniqueViolation` |
| Introspección schema | `sqlite_master`, `PRAGMA table_info` | `information_schema`, `pg_catalog` |
| Migraciones | Introspección ad-hoc | Versionadas (Alembic recomendado) |
