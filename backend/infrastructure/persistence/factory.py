"""Engine dispatch: the only module that knows which DB engine is active.

Repositories (and any other code outside persistence/) must import
connections and dialect helpers from here, never from an engine package
such as persistence/sqlite/. That keeps them engine-agnostic: adding a new
engine only means adding it to _ENGINE_PACKAGES and to init_engine().
"""
import importlib
from types import ModuleType
from typing import Callable

from backend.config import db_settings

# Each engine package must provide connection.py (get_connection) and
# adapter.py (insert_returning_id, idempotent_insert, map_integrity_error).
_ENGINE_PACKAGES = {
    "sqlite": "backend.infrastructure.persistence.sqlite",
}


def _unsupported(engine: str) -> ValueError:
    return ValueError(f"Unsupported DB engine: {engine!r}")


def _engine_module(name: str) -> ModuleType:
    """Return the `name` module (connection, adapter…) of the active engine."""
    engine = db_settings.engine
    package = _ENGINE_PACKAGES.get(engine)
    if package is None:
        raise _unsupported(engine)
    return importlib.import_module(f"{package}.{name}")


# ── Connection ────────────────────────────────────────────────────────────────

def get_connection():
    """Return an open connection for the configured DB engine.

    Always use it as a context manager: on exit the transaction is committed
    (or rolled back on error) and the connection is closed.
    """
    return _engine_module("connection").get_connection()


# ── Dialect helpers (delegated to the active engine's adapter) ────────────────

def insert_returning_id(conn, sql: str, params) -> int:
    """Execute an INSERT (with %s placeholders) and return the new row ID."""
    return _engine_module("adapter").insert_returning_id(conn, sql, params)


def idempotent_insert(conn, sql: str, params) -> None:
    """Plain INSERT INTO … that silently ignores duplicate-key violations."""
    _engine_module("adapter").idempotent_insert(conn, sql, params)


def map_integrity_error(exc_factory: Callable):
    """Context manager: translate the engine's integrity error into exc_factory()."""
    return _engine_module("adapter").map_integrity_error(exc_factory)


# ── Initialisation ────────────────────────────────────────────────────────────

def init_engine() -> None:
    """Create schema, run migrations, and seed demo data for the configured engine."""
    engine = db_settings.engine
    if engine == "sqlite":
        from backend.infrastructure.persistence.sqlite.migrations import migrate
        from backend.infrastructure.persistence.sqlite.schema import create_schema
        from backend.infrastructure.persistence.sqlite.seed import seed_db

        with get_connection() as conn:
            create_schema(conn)
            migrate(conn)
            conn.commit()
        seed_db()
        return
    raise _unsupported(engine)
