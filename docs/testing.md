# Tests

## Índice

- [Setup](#setup-testsconftestpy)
- [Archivos de test](#archivos-de-test)
- [Patrón de test típico](#patrón-de-test-típico)
- [Ejecución](#ejecución)
- [Notas importantes](#notas-importantes)

---

## Setup (`tests/conftest.py`)

- **Framework:** Pytest + `httpx.TestClient` (FastAPI)
- **Base de datos de test:** fichero SQLite temporal (creado por `conftest.py` vía `SQLITE_PATH`) — independiente de `tasks.db`. Detalle completo en [Aislamiento de BD en tests](testing-db.md).
- **Fixtures principales:**

| Fixture | Scope | Descripción |
|---------|-------|-------------|
| `client` | module | `TestClient(app)` con BD temporal |
| `auth` | function | Crea usuario de test + retorna `(user, headers)` |
| `admin_auth` | function | Crea usuario, lo promueve a admin (vía caso de uso) + retorna `(user, headers)` |
| `clean_db` | function (autouse) | Vacía todas las tablas y reinicia los IDs antes de cada test (`factory.reset_tables()`) |

El fixture `auth` devuelve `(user_dict, {"Authorization": "Bearer <token>"})`.

`conftest.py` no contiene SQL: funciona con cualquier engine configurado en `DB_ENGINE`.

---

## Archivos de test

490 tests en total (más 1 que se salta en `.venv`: la capa MCP, que corre en `.venv-mcp`).

| Archivo | Tests | Qué cubre |
|---------|------:|-----------|
| `test_auth.py` | 21 | Login correcto, credenciales incorrectas, validación de campos |
| `test_users.py` | 45 | CRUD usuarios, auto-delete, permisos (propio vs admin) |
| `test_projects.py` | 54 | CRUD proyectos, miembros, roles, deletion preview, cascade delete |
| `test_groups.py` | 26 | CRUD grupos, reordenación, FK con proyecto |
| `test_tasks.py` | 34 | CRUD tareas, asignación user/priority/tags, reordenación |
| `test_todos.py` | 27 | CRUD subtareas, orden, FK con tarea |
| `test_tags.py` | 42 | CRUD etiquetas, unicidad por proyecto, asignación a tareas |
| `test_flows.py` | 63 | Flujos y etiquetas globales: definición, ámbitos y nombres, permisos, asignación y estados, registro, modificación en uso |
| `test_flows_migration.py` | 4 | Migración de una BD anterior a los flujos (única excepción a «los tests no ejecutan SQL»: fabrica el esquema antiguo con `sqlite3`) |
| `test_reorder.py` | 14 | Endpoints de ordenar: ids de otro proyecto/grupo, repetidos |
| `test_task_priority_scope.py` | 7 | Prioridad de otro proyecto en una tarea (422) |
| `test_bootstrap.py` | 21 | Arranque en vacío (`JKANBAN_DEMO_DATA`) y comando `create_admin` |
| `test_mcp_service.py` | 44 | `SFService` del MCP contra la API real |
| `test_priorities.py` | 30 | CRUD prioridades, unicidad por proyecto |
| `test_admin.py` | 14 | Panel admin: deletion preview, cascade delete con contraseña |
| `test_persistence_portability.py` | 44 | Guardas de arquitectura: SQL portable en repositorios, ningún acceso a BD fuera de ellos, cierre de conexiones, engines no soportados, normalización de fechas |

---

## Patrón de test típico

```python
def test_create_task(client, auth):
    user, headers = auth
    # Crear dependencias necesarias
    project = client.post("/projects/", json={...}, headers=headers).json()
    group   = client.post("/groups/", json={"project_id": project["id"], ...}, headers=headers).json()
    # Acción bajo test
    r = client.post("/tasks/", json={"group_id": group["id"], "title": "Test"}, headers=headers)
    # Assertions
    assert r.status_code == 201
    assert r.json()["title"] == "Test"

def test_unauthorized(client, auth):
    _, headers = auth
    r = client.get("/admin/users/1/deletion-preview", headers=headers)
    assert r.status_code == 403
```

---

## Ejecución

```bash
# Todos los tests
pytest

# Con detalle
pytest -v

# Un archivo concreto
pytest tests/test_projects.py

# Una clase o un test concreto
pytest tests/test_projects.py::TestCascadeDeleteProject -v
pytest tests/test_projects.py::TestCascadeDeleteProject::test_other_projects_unaffected -v

# Con cobertura (requiere pytest-cov)
pytest --cov=backend --cov-report=term-missing

# Solo las guardas de portabilidad / arquitectura
pytest tests/test_persistence_portability.py
```

---

## Notas importantes

- Los tests **no usan mocks de base de datos** — cada test corre contra una BD SQLite real (fichero temporal) para garantizar que las queries SQL y las cascadas FK funcionan como en producción.
- `clean_db` vacía en el orden correcto para respetar FK constraints: `todo_items → task_tags → group_tags → tasks → tags → project_members → groups → projects → users → priorities`.
- Los tests no ejecutan SQL: para preparar datos usan la API o un caso de uso (p.ej. `get_user_use_cases().update(uid, {"is_admin": True})`).
- Los tests de admin requieren el fixture `admin_auth` (usuario con `is_admin=True`).
- El `TestClient` de FastAPI levanta la app completa incluida la inicialización de BD — no hay que arrancar el servidor por separado.
