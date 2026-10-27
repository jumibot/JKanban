import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Con SQLite (engine por defecto) se redirige la BD a un fichero temporal ANTES
# de importar la app. db_settings.sqlite_path lee os.environ["SQLITE_PATH"] en
# cada acceso (lazy), así que init_db() y todos los get_connection() posteriores
# abren el temp file, nunca tasks.db.
# Con otro engine (DB_ENGINE=postgres…) la conexión de pruebas se configura por
# entorno (p.ej. DATABASE_URL apuntando a una BD desechable de tests).
if os.environ.get("DB_ENGINE", "sqlite") == "sqlite":
    _tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    _tmp_db.close()
    os.environ["SQLITE_PATH"] = _tmp_db.name

from backend.infrastructure.persistence.factory import reset_tables  # noqa: E402
from backend.interfaces.dependencies import get_user_use_cases  # noqa: E402
from backend.main import app  # noqa: E402

# Orden hijo → padre para respetar las FKs
_TABLES = [
    "flow_state_changes", "todo_items", "task_tags", "group_tags", "tasks", "tags",
    "flow_transitions", "flow_states", "flows",
    "project_members", "groups", "projects", "users", "priorities",
]


def make_admin(user_id: int) -> None:
    """Promote a user to platform admin (no SQL: goes through the use case)."""
    get_user_use_cases().update(user_id, {"is_admin": True})


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth(client: TestClient):
    """Creates a fresh test user and returns (user_data, auth_headers).
    Runs after clean_db so the user is the only one in the DB.
    """
    r = client.post("/users/", json={
        "name": "AuthUser", "email": "_auth@test.com", "password": "authpass123",
    })
    user = r.json()
    lr = client.post("/auth/login", json={"email": "_auth@test.com", "password": "authpass123"})
    token = lr.json()["access_token"]
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_auth(client: TestClient):
    """Creates a test admin user and returns (user_data, auth_headers)."""
    r = client.post("/users/", json={
        "name": "AdminUser", "email": "_admin@test.com", "password": "adminpass123",
    })
    user = r.json()
    make_admin(user["id"])
    lr = client.post("/auth/login", json={"email": "_admin@test.com", "password": "adminpass123"})
    token = lr.json()["access_token"]
    user["is_admin"] = True
    return user, {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clean_db():
    """Vacía todas las tablas antes de cada test y reinicia los contadores de ID."""
    reset_tables(_TABLES)
