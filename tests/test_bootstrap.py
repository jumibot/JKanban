"""Arranque en vacío (JKANBAN_DEMO_DATA) y comando create_admin.

Cada test usa su propia base de datos en tmp_path (SQLITE_PATH se lee en cada
conexión), así que ni siembra ni toca la base de datos compartida de la suite.
"""
import pytest

from backend.config import db_settings
from backend.create_admin import main as create_admin
from backend.infrastructure.persistence.factory import init_engine as init_db
from backend.interfaces.dependencies import get_group_use_cases, get_user_use_cases


@pytest.fixture
def fresh_db(tmp_path, monkeypatch):
    """Base de datos nueva y vacía, con la demo desactivada."""
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "fresh.db"))
    monkeypatch.setenv("JKANBAN_DEMO_DATA", "0")
    monkeypatch.delenv("JKANBAN_ADMIN_PASSWORD", raising=False)
    return tmp_path / "fresh.db"


def _users():
    return get_user_use_cases().get_all()


def _login(client, email, password):
    return client.post("/auth/login", json={"email": email, "password": password})


# ── JKANBAN_DEMO_DATA ─────────────────────────────────────────────────────

@pytest.mark.parametrize("value,expected", [
    (None, True), ("1", True), ("true", True), ("yes", True),
    ("0", False), ("false", False), ("No", False), (" off ", False),
])
def test_demo_data_setting(monkeypatch, value, expected):
    if value is None:
        monkeypatch.delenv("JKANBAN_DEMO_DATA", raising=False)
    else:
        monkeypatch.setenv("JKANBAN_DEMO_DATA", value)
    assert db_settings.demo_data is expected


def test_empty_start_creates_schema_without_demo_data(fresh_db):
    init_db()
    assert fresh_db.exists()
    assert _users() == []
    assert get_group_use_cases().get_all() == []


def test_default_start_loads_demo_data(fresh_db, monkeypatch):
    monkeypatch.delenv("JKANBAN_DEMO_DATA")
    init_db()
    assert any(u.is_admin for u in _users())
    assert get_group_use_cases().get_all() != []


def test_demo_data_never_loads_on_a_database_with_users(fresh_db, monkeypatch):
    assert create_admin(["--email", "a@x.com", "--name", "A", "--password", "secret1"]) == 0
    monkeypatch.delenv("JKANBAN_DEMO_DATA")
    init_db()
    assert [u.email for u in _users()] == ["a@x.com"]


# ── create_admin ──────────────────────────────────────────────────────────

def test_creates_first_admin_on_empty_database(fresh_db, client, capsys):
    code = create_admin(["--email", " SF-Bot@Example.com ", "--name", "SF", "--password", "sfbot-1234"])
    assert code == 0
    (user,) = _users()
    assert (user.email, user.name, user.is_admin) == ("sf-bot@example.com", "SF", True)
    assert "Administrador creado" in capsys.readouterr().out
    r = _login(client, "sf-bot@example.com", "sfbot-1234")
    assert r.status_code == 200
    assert r.json()["user"]["is_admin"] is True


def test_admin_can_use_admin_endpoints(fresh_db, client):
    create_admin(["--email", "boss@x.com", "--name", "Boss", "--password", "secret1"])
    token = _login(client, "boss@x.com", "secret1").json()["access_token"]
    victim = client.post("/users/", json={"name": "V", "email": "v@x.com", "password": "secret1"}).json()
    r = client.get(f"/admin/users/{victim['id']}/deletion-preview",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200


def test_password_from_environment(fresh_db, client, monkeypatch):
    monkeypatch.setenv("JKANBAN_ADMIN_PASSWORD", "from-env-1")
    assert create_admin(["--email", "a@x.com", "--name", "A"]) == 0
    assert _login(client, "a@x.com", "from-env-1").status_code == 200


def test_promotes_existing_user_keeping_password(fresh_db, client):
    init_db()
    client.post("/users/", json={"name": "Ana", "email": "ana@x.com", "password": "anapass1"})
    assert create_admin(["--email", "ana@x.com"]) == 0
    (user,) = _users()
    assert (user.name, user.is_admin) == ("Ana", True)
    assert _login(client, "ana@x.com", "anapass1").status_code == 200


def test_promotes_existing_user_and_sets_password(fresh_db, client):
    init_db()
    client.post("/users/", json={"name": "Ana", "email": "ana@x.com", "password": "anapass1"})
    assert create_admin(["--email", "ana@x.com", "--password", "newpass1"]) == 0
    assert _login(client, "ana@x.com", "anapass1").status_code == 401
    assert _login(client, "ana@x.com", "newpass1").status_code == 200


def test_running_twice_is_harmless(fresh_db):
    args = ["--email", "a@x.com", "--name", "A", "--password", "secret1"]
    assert create_admin(args) == 0
    assert create_admin(args) == 0
    assert len(_users()) == 1


@pytest.mark.parametrize("args,message", [
    (["--email", "no-es-email", "--name", "A", "--password", "secret1"], "email no válido"),
    (["--email", "a@x.com", "--password", "secret1"], "indica --name"),
    (["--email", "a@x.com", "--name", "A"], "falta la contraseña"),
    (["--email", "a@x.com", "--name", "A", "--password", "corta"], "al menos 6"),
])
def test_invalid_input_returns_2_and_creates_nothing(fresh_db, capsys, args, message):
    init_db()
    assert create_admin(args) == 2
    assert message in capsys.readouterr().err
    assert _users() == []
