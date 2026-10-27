"""Centralised backend configuration.

Values are read from environment variables so every deployment context
(local, Docker, CI, test) can override without touching source code.

Variables:
    DB_ENGINE          – persistence backend (default: sqlite)
    SQLITE_PATH        – path to the SQLite file (default: <repo_root>/tasks.db)
    JKANBAN_DEMO_DATA  – load demo data into an empty database (default: 1;
                         0/false/no/off starts JKanban empty)
"""
import os
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent


class _DBSettings:
    """Lazy-read settings: properties re-read env vars on each access.

    This is intentional: tests can set os.environ["SQLITE_PATH"] before
    importing the app and the value will be picked up correctly, without
    any monkey-patching of module-level attributes.
    """

    @property
    def engine(self) -> str:
        return os.environ.get("DB_ENGINE", "sqlite")

    @property
    def sqlite_path(self) -> Path:
        return Path(os.environ.get("SQLITE_PATH", str(_REPO_ROOT / "tasks.db")))

    @property
    def demo_data(self) -> bool:
        value = os.environ.get("JKANBAN_DEMO_DATA", "1").strip().lower()
        return value not in ("0", "false", "no", "off")


db_settings = _DBSettings()
