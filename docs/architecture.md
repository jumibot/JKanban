# Arquitectura del backend

## Índice

- [Introducción a Clean Architecture](#introducción-a-clean-architecture)
- [Responsabilidades de cada capa](#responsabilidades-de-cada-capa)
  - [Domain](#domain-backenddomain)
  - [Application](#application-backendapplication)
  - [Infrastructure](#infrastructure-backendinfrastructure)
  - [Interfaces](#interfaces-backendinterfaces)
- [Flujo completo de una request](#flujo-completo-de-una-request)
- [Inyección de dependencias](#inyección-de-dependencias-dependenciespy)
- [Patrones notables](#patrones-notables)
- [Anexo: migrar de SQLite a PostgreSQL](#anexo-migrar-de-sqlite-a-postgresql)
  - [1. Dependencia](#1-dependencia)
  - [2. infrastructure/database.py](#2-infrastructuredatabasepy)
  - [3. Repositorios — diferencias SQL](#3-infrastructurerepositories---diferencias-sql)
  - [4. Schema DDL](#4-schema-ddl-infrastructuredatabasepy---init_db)
  - [5. Ajuste de booleanos](#5-_to_entity---ajuste-de-booleanos)
  - [Resumen del alcance](#resumen-del-alcance-del-cambio)

---

## Introducción a Clean Architecture

El backend sigue los principios de **Clean Architecture** (también conocida como arquitectura hexagonal o de puertos y adaptadores). La idea central es una sola regla: **las dependencias solo apuntan hacia dentro**. El núcleo del sistema (dominio y lógica de negocio) no sabe nada de frameworks, bases de datos ni HTTP; son las capas externas las que dependen del núcleo, nunca al revés.

```
           ┌─────────────────────────────────┐
           │         interfaces/             │  ← FastAPI, HTTP, JSON
           │  ┌───────────────────────────┐  │
           │  │      application/         │  │  ← casos de uso
           │  │  ┌─────────────────────┐  │  │
           │  │  │      domain/        │  │  │  ← entidades, contratos
           │  │  └─────────────────────┘  │  │
           │  └───────────────────────────┘  │
           └─────────────────────────────────┘
                infrastructure/  ←─────────────── implementa contratos de domain
```

**Por qué importa:** si el dominio y los casos de uso no dependen de SQLite ni de FastAPI, se pueden sustituir ambos sin tocar la lógica de negocio. Los tests unitarios de use cases no necesitan una base de datos real.

---

## Responsabilidades de cada capa

### Domain (`backend/domain/`)

**Es el núcleo. No importa nada externo — ni FastAPI, ni sqlite3, ni Pydantic.**

| Archivo | Responsabilidad |
|---------|----------------|
| `entities.py` | Dataclasses Python puras que representan los conceptos del negocio: `User`, `Project`, `Group`, `Task`, `Priority`, `Tag`, `TodoItem`. Sin lógica de persistencia ni validación HTTP. |
| `repositories.py` | ABCs (clases abstractas) que declaran los contratos de acceso a datos. Definen *qué* operaciones existen (`get_by_id`, `create`, `update`, `delete`…) sin decir *cómo* se implementan. |
| `exceptions.py` | 21 excepciones tipadas que representan violaciones de reglas de negocio (`ProjectLeaderRequired`, `TagNameAlreadyExists`, etc.). Son el único mecanismo de señalización de errores entre capas internas. |

**Regla:** nada en `domain/` tiene un `import` de fuera del propio paquete.

---

### Application (`backend/application/`)

**Orquesta la lógica de negocio. Depende de `domain/`, nada más.**

Contiene los *casos de uso*: cada módulo agrupa las operaciones de un recurso. Un caso de uso recibe repositorios por inyección de dependencias, invoca sus métodos y lanza excepciones de dominio si se viola alguna regla.

```python
# Ejemplo: lo que un use case puede y no puede hacer
class ProjectUseCases:
    def create(self, name, owner_id, leader_id, ...):
        # ✓ Consulta repositorios
        owner = self.user_repo.get_by_id(owner_id)
        # ✓ Lanza excepciones de dominio
        if owner is None:
            raise UserNotFound(owner_id)
        # ✓ Crea y persiste entidades
        project = Project(name=name, owner_id=owner_id, ...)
        return self.project_repo.create(project)
        # ✗ No importa sqlite3, FastAPI ni Pydantic
        # ✗ No lanza HTTPException
        # ✗ No conoce request/response bodies
```

| Módulo | Responsabilidad |
|--------|----------------|
| `user_use_cases.py` | Registro, login, CRUD usuarios, hashing PBKDF2 |
| `project_use_cases.py` | CRUD proyectos, gestión de miembros, cálculo de roles |
| `group_use_cases.py` | CRUD grupos kanban, reordenación de columnas |
| `task_use_cases.py` | CRUD tareas, asignación, reordenación dentro de grupo |
| `todo_use_cases.py` | CRUD subtareas (checklist de tarea) |
| `tag_use_cases.py` | CRUD etiquetas scoped al proyecto, asignación a tareas y grupos |
| `priority_use_cases.py` | CRUD prioridades scoped al proyecto |

---

### Infrastructure (`backend/infrastructure/`)

**Implementa los contratos de `domain/` con tecnología concreta. Es la única capa que conoce SQLite, JWT y detalles de I/O.**

| Archivo / carpeta | Responsabilidad |
|-------------------|----------------|
| `database.py` | Alias público de dos líneas: re-exporta `get_connection` e `init_db` desde el factory. Los imports existentes no necesitan cambiar. |
| `persistence/factory.py` | Despacha por engine (`DB_ENGINE`): da la conexión y los helpers de dialecto (`insert_returning_id`, `idempotent_insert`, `map_integrity_error`) del engine activo, y orquesta schema + migraciones + seed. Único punto de import para el resto del código. Añadir un engine solo requiere extender este archivo (y crear su carpeta). |
| `persistence/sqlite/` | Implementación SQLite completa: `connection.py` (wrapper con traducción `%s`→`?`), `schema.py` (DDL), `migrations.py` (migraciones ad-hoc no destructivas), `seed.py` (datos demo), `adapter.py` (helpers `insert_returning_id`, etc.). |
| `persistence/common/` | Utilidades agnósticas de engine: `utcnow()`, `ph(n)` para placeholders portables, helpers de datetime. |
| `jwt_handler.py` | Codifica y decodifica tokens JWT HS256 con `PyJWT`. Expone `create_access_token(user_id)` y `decode_token(token) → user_id`. |
| `repositories/` | Una clase por entidad (`SQLiteUserRepository`, `SQLiteProjectRepository`, etc.) que implementa el ABC correspondiente de `domain/repositories.py`. Importan conexión y helpers solo desde el factory; SQL con placeholders `%s`, sin nada específico de SQLite (lo verifica `tests/test_persistence_portability.py`). El prefijo `SQLite` del nombre de clase es histórico. |

**Regla:** esta capa puede importar `domain/` y librerías externas (sqlite3, PyJWT). No importa `application/` ni `interfaces/`.

---

### Interfaces (`backend/interfaces/`)

**Adapta el mundo HTTP al interior del sistema. Traduce requests → llamadas a use cases → responses.**

| Archivo / carpeta | Responsabilidad |
|-------------------|----------------|
| `routers/` | Endpoints FastAPI. Reciben el HTTP request, llaman al use case correspondiente, capturan excepciones de dominio y las convierten en `HTTPException` con el código HTTP apropiado. |
| `schemas.py` | Modelos Pydantic para validar requests y serializar responses. Tienen métodos `.from_entity()` para convertir desde entidades de dominio. |
| `dependencies.py` | Fábricas de FastAPI `Depends()`: `get_current_user` (valida JWT), `require_admin`, `require_project_access`, `require_project_leader`, y factories que instancian repositorios y use cases. |

**Regla:** esta capa puede importar `application/`, `domain/` e `infrastructure/`. No contiene lógica de negocio.

---

## Flujo completo de una request

```
POST /tasks/  {group_id: 5, title: "Nueva tarea"}
  │
  ├─ FastAPI extrae el JWT del header
  ├─ Depends(get_current_user) → decode_token() → SQLiteUserRepository.get_by_id()
  ├─ Pydantic valida el body → TaskCreate
  │
  ├─ router/tasks.py llama a task_use_cases.create(group_id=5, title=..., ...)
  │     │
  │     ├─ application/task_use_cases.py
  │     │     ├─ group_repo.get_by_id(5)   → GroupNotFound si no existe → HTTPException 404
  │     │     ├─ Crea Task(group_id=5, title=...) 
  │     │     └─ task_repo.create(task) → devuelve Task con id asignado
  │     │           │
  │     │           └─ infrastructure/repositories/task_repository.py
  │     │                 └─ INSERT INTO tasks ... → SQLite
  │     │
  │     └─ devuelve Task entity
  │
  ├─ TaskResponse.from_entity(task) → JSON
  └─ HTTP 201
```

---

## Inyección de dependencias (`dependencies.py`)

FastAPI `Depends()` actúa como el contenedor de DI. Cada router declara sus dependencias como parámetros de función; FastAPI las resuelve antes de invocar el handler.

| Dependencia | Propósito |
|-------------|----------|
| `get_current_user` | Valida JWT Bearer → retorna `User` autenticado; 401 si inválido |
| `require_admin` | Verifica `user.is_admin`; 403 si no |
| `require_project_access` | Verifica owner/leader/member del proyecto; 403 si no |
| `require_project_leader` | Verifica owner o leader; 403 si no |
| `get_*_use_cases()` | Instancian use cases con sus repos concretos inyectados |

---

## Patrones notables

- **Sin ORM:** queries SQL escritas a mano en los repositorios. Evita N+1 con joins explícitos y da control total sobre el plan de ejecución.
- **Audit trail automático:** `created_at`, `modified_at`, `created_by`, `modified_by` se rellenan en los repositorios de infraestructura, no en el dominio.
- **Hard deletes + CASCADE:** no hay soft deletes; las FK tienen `ON DELETE CASCADE` / `ON DELETE SET NULL` según el caso.
- **Schemas ≠ Entities:** los schemas Pydantic solo existen en `interfaces/`. La conversión ocurre con `.from_entity()`, nunca en el dominio.
- **Primer admin automático:** si no existe ningún admin al arrancar, `_migrate()` promueve el primer usuario.

---

## Anexo: añadir un nuevo engine de base de datos

La arquitectura de persistencia está diseñada para que añadir un engine nuevo (p.ej. PostgreSQL) sea un cambio **aditivo y aislado en `infrastructure/persistence/`**. El dominio, los casos de uso, los routers y los repositorios existentes no se tocan.

### Cómo está estructurada la capa de persistencia

```
infrastructure/
├── database.py                  ← alias público (2 líneas); no tocar
├── persistence/
│   ├── factory.py               ← dispatch por DB_ENGINE; aquí se añade el nuevo engine
│   ├── common/
│   │   └── utils.py             ← helpers agnósticos (utcnow, ph, etc.)
│   ├── sqlite/                  ← implementación completa SQLite
│   │   ├── connection.py        ← wrapper; traduce %s → ?
│   │   ├── schema.py            ← DDL CREATE TABLE
│   │   ├── migrations.py        ← migraciones ad-hoc
│   │   ├── seed.py              ← datos demo
│   │   └── adapter.py           ← helpers: insert_returning_id, idempotent_insert, …
│   └── postgres/                ← (pendiente de implementar)
```

### Pasos para añadir PostgreSQL

#### 1. Dependencia

```
# backend/requirements.txt
psycopg2-binary>=2.9
```

#### 2. Crear `persistence/postgres/`

Implementar los mismos módulos que tiene `sqlite/`, adaptando las especificidades de PostgreSQL:

| Aspecto | SQLite (`sqlite/`) | PostgreSQL (`postgres/`) |
|---------|-------------------|--------------------------|
| Placeholders | `?` (o `%s` via wrapper) | `%s` nativo en psycopg2 |
| ID insertado | `cursor.lastrowid` | `RETURNING id` |
| Booleanos | `INTEGER` 0/1 | `BOOLEAN` nativo |
| Timestamps | `TEXT` + `datetime('now')` | `TIMESTAMPTZ` + `NOW()` |
| CHECK color | `SUBSTR(color,1,1)='#'` | `color ~ '^#[0-9A-Fa-f]{6}$'` |
| AUTO ID | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| FK enforcement | `PRAGMA foreign_keys = ON` | Activo por defecto |
| Migraciones | Introspección + tabla-rebuild | Alembic o SQL versionado |

Ejemplo `connection.py` para PostgreSQL — requiere un wrapper análogo a `SQLiteConnection`, porque psycopg2 no expone `.execute()` directamente en la conexión (solo en los cursors):

```python
import os
import psycopg2
import psycopg2.extensions
from psycopg2.extras import RealDictCursor

class PostgreSQLConnection:
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
    return PostgreSQLConnection(psycopg2.connect(os.environ["DATABASE_URL"]))
```

El wrapper expone la misma superficie `execute`/`executemany` que `SQLiteConnection` y devuelve filas accesibles por nombre (`row["id"]`) gracias a `RealDictCursor`.

#### 3. Extender `factory.py`

```python
# get_connection() y los helpers de dialecto despachan con este mapa
_ENGINE_PACKAGES = {
    "sqlite": "backend.infrastructure.persistence.sqlite",
    "postgres": "backend.infrastructure.persistence.postgres",   # ← añadir
}

def init_engine() -> None:
    engine = db_settings.engine
    if engine == "sqlite":
        # … (ya implementado)
    if engine == "postgres":
        from backend.infrastructure.persistence.postgres.schema import create_schema
        from backend.infrastructure.persistence.postgres.migrations import migrate
        from backend.infrastructure.persistence.postgres.seed import seed_db
        with get_connection() as conn:
            create_schema(conn)
            migrate(conn)
            conn.commit()
        seed_db()
        return
    raise _unsupported(engine)
```

#### 4. Activar el engine

```bash
DB_ENGINE=postgres DATABASE_URL=postgresql://user:pass@host:5432/jkanban uvicorn backend.main:app
```

### Resumen del alcance

| Capa | Cambios para añadir PostgreSQL |
|------|-------------------------------|
| `domain/` | **Ninguno** |
| `application/` | **Ninguno** |
| `interfaces/` | **Ninguno** |
| `infrastructure/repositories/` | **Ninguno** — ya usan el factory |
| `infrastructure/database.py` | **Ninguno** — es un alias |
| `infrastructure/persistence/factory.py` | Añadir `postgres` a `_ENGINE_PACKAGES` y una rama en `init_engine` |
| `infrastructure/persistence/postgres/` | Crear: `connection.py`, `schema.py`, `migrations.py`, `seed.py`, `adapter.py` |
| `requirements.txt` | Añadir `psycopg2-binary` |
