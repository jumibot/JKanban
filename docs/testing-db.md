# Especificación técnica: base de datos en tests

## Principio fundamental

Los tests nunca tocan `tasks.db` ni ninguna base de datos de desarrollo o producción. Cada ejecución de `pytest` opera sobre un fichero SQLite temporal creado al arrancar la sesión y descartado al terminar.

---

## Mecanismo de aislamiento

### 1. Fichero temporal por sesión de pytest

`tests/conftest.py` crea un fichero `.db` vacío en la carpeta de temporales del SO **antes de importar la aplicación**:

```python
import os, tempfile

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["SQLITE_PATH"] = _tmp_db.name   # p.ej. /tmp/tmpXXXXXX.db
```

El fichero persiste durante toda la sesión (`delete=False`) y se reutiliza por todos los módulos de test. No se borra automáticamente al terminar — el SO lo limpia eventualmente; si se quiere limpieza explícita, se puede añadir un fixture `session`-scoped con `yield` + `os.unlink`.

### 2. Por qué se usa `os.environ["SQLITE_PATH"]` y no un atributo de módulo

`db_settings.sqlite_path` lee `os.environ` en cada acceso (lazy-read). Establecer la variable de entorno **antes de cualquier import de la app** garantiza que toda llamada a `get_connection()` abra el fichero temporal, independientemente del orden de importación de módulos.

Asignar `db_module.DB_PATH = ...` era el mecanismo antiguo y dejó de funcionar al pasar la conexión al factory (el antiguo `database.py` se retiró en la v1.0.0).

### 3. El import de la app ocurre después

```python
os.environ["SQLITE_PATH"] = _tmp_db.name   # 1. fijar ruta

from backend.main import app               # 2. importar → init_engine() usa el temp file
```

`backend.main` llama `init_engine()` al importarse. Si la variable de entorno no está fijada antes, `init_engine()` inicializaría `tasks.db`.

---

## Ciclo de vida de la BD durante los tests

```
pytest arranca
  │
  ├── conftest.py ejecuta (scope global)
  │     ├── crea /tmp/tmpXXX.db
  │     ├── os.environ["SQLITE_PATH"] = "/tmp/tmpXXX.db"
  │     └── importa backend.main → init_engine() → schema + migrations + seed en tmpXXX.db
  │
  ├── por cada test:
  │     ├── clean_db (autouse) — trunca todas las tablas en tmpXXX.db
  │     ├── auth / admin_auth — crea usuarios de prueba en tmpXXX.db
  │     └── el test se ejecuta
  │
  └── pytest termina — tmpXXX.db queda en /tmp (el SO lo limpia)
```

---

## Fixtures disponibles

| Fixture | Scope | Descripción |
|---------|-------|-------------|
| `client` | `module` | `TestClient(app)` reutilizado en todo el módulo de test |
| `clean_db` | `function` (autouse) | Trunca todas las tablas + resetea secuencias antes de cada test |
| `auth` | `function` | Crea un usuario normal y devuelve `(user_dict, headers_con_JWT)` |
| `admin_auth` | `function` | Crea un usuario y lo promueve a admin; devuelve `(user_dict, headers_con_JWT)` |

### `clean_db` — orden de borrado

Las tablas se borran respetando las FK (hijos antes que padres):

```
todo_items → task_tags → group_tags → tasks → tags
→ project_members → groups → projects → users → priorities
```

El borrado y el reinicio de los contadores de ID (para que empiecen en 1 en cada test) los hace `factory.reset_tables(tablas)`, que delega en el `adapter.py` del engine activo: en SQLite, `DELETE` + `sqlite_sequence`; en PostgreSQL sería `TRUNCATE … RESTART IDENTITY CASCADE`. `conftest.py` no contiene SQL.

---

## Convenciones para escribir tests

### Crear datos de prueba dentro del test

```python
def test_algo(client, auth):
    user, headers = auth
    # Crear recursos necesarios para el test
    project = client.post("/projects/", json={...}, headers=headers).json()
    # Assertions
    assert ...
```

No compartir estado entre tests: `clean_db` borra todo antes de cada uno. Si un test necesita datos previos, los crea él mismo.

### Uso de `auth` vs `admin_auth`

- `auth` → usuario normal sin privilegios especiales
- `admin_auth` → usuario con `is_admin=True`; usar solo cuando el endpoint lo requiera

### Verificar efectos secundarios en la BD

Para verificar que una operación persistió correctamente, usa el `client` para hacer un GET, no `get_connection()` directamente. Reserva el acceso directo a la BD para casos imposibles de verificar vía API (p.ej. comprobar que un campo interno no se expone).

```python
# ✓ Verificar vía API
r = client.get(f"/projects/{pid}", headers=headers)
assert r.json()["name"] == "Nuevo nombre"

# Solo si no hay endpoint para ello: pasar por un caso de uso / repositorio
from backend.interfaces.dependencies import get_user_use_cases
assert get_user_use_cases().get_by_id(uid).password_hash.startswith("pbkdf2$")
```

---

## Variables de entorno relevantes

| Variable | Efecto en tests |
|----------|----------------|
| `SQLITE_PATH` | Ruta al fichero SQLite que usarán todos los tests. `conftest.py` la fija a un temp file. |
| `DB_ENGINE` | Con un valor distinto de `sqlite` (p.ej. `postgres`), `conftest.py` no crea el fichero temporal y los tests usan la BD que indique el entorno (`DATABASE_URL`). Debe ser una BD desechable: `clean_db` la vacía antes de cada test. |
| `JWT_SECRET` | Si no se fija, usa el valor por defecto de desarrollo. No afecta al aislamiento de BD. |

---

## Qué NO hacer

| Patrón | Por qué evitarlo |
|--------|-----------------|
| `db_module.DB_PATH = ...` | Atributo obsoleto; ya no afecta a `get_connection()` |
| Compartir objetos mutables entre tests | `clean_db` asume estado limpio al inicio de cada test |
| Hardcodear IDs en assertions (`assert r.json()["id"] == 3`) | Los IDs pueden variar según el orden de ejecución; usar el ID devuelto en la creación |
| Conectar a `tasks.db` desde los tests | Contamina datos de desarrollo y viola el aislamiento |
