"""SQLite connection adapter.

Single point of contact with the sqlite3 driver.
All SQLite-specific concerns (PRAGMA, row_factory, ? placeholder style)
are confined here and must not leak into repositories or use-cases.
"""
import sqlite3

from backend.config import db_settings


class SQLiteConnection:
    """Thin wrapper around sqlite3.Connection.

    Purpose: translate portable %s placeholders to SQLite's ? style so that
    repository SQL is written in the widely-supported pyformat style (%s)
    without any driver knowledge leaking into the repos.

    A future PostgreSQL adapter using psycopg2 accepts %s natively, meaning
    the same repository SQL can be reused without modification.

    Notes:
    - row_factory and PRAGMA foreign_keys are set on the raw connection
      before wrapping, keeping them out of the wrapper's public interface.
    - __getattr__ delegates unknown attributes to the raw connection, so
      callers can access cursor attributes (lastrowid, rowcount, etc.) on
      cursors returned by execute() without any extra wrapping.
    """

    def __init__(self, raw: sqlite3.Connection) -> None:
        self._c = raw

    # ── Core DBAPI2 surface ───────────────────────────────────────────────────

    def execute(self, sql: str, params=()) -> sqlite3.Cursor:
        return self._c.execute(sql.replace("%s", "?"), params)

    def executemany(self, sql: str, seq) -> sqlite3.Cursor:
        return self._c.executemany(sql.replace("%s", "?"), seq)

    def commit(self) -> None:
        self._c.commit()

    def close(self) -> None:
        self._c.close()

    # ── Context manager ───────────────────────────────────────────────────────

    def __enter__(self) -> "SQLiteConnection":
        self._c.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # sqlite3's own __exit__ only commits / rolls back; it does NOT close.
        # Closing here releases the file handle deterministically instead of
        # waiting for garbage collection (and matches what server engines need).
        try:
            return self._c.__exit__(exc_type, exc_val, exc_tb)
        finally:
            self._c.close()

    # ── Attribute delegation ──────────────────────────────────────────────────

    def __getattr__(self, name: str):
        # Delegates everything not explicitly defined above to the raw
        # connection (e.g. .row_factory, .isolation_level, cursor methods).
        return getattr(self._c, name)


def get_connection() -> SQLiteConnection:
    """Open and return a wrapped SQLite connection.

    SQLite-specific setup (row_factory, foreign keys pragma) lives here
    and nowhere else.
    """
    raw = sqlite3.connect(str(db_settings.sqlite_path))
    raw.row_factory = sqlite3.Row
    raw.execute("PRAGMA foreign_keys = ON")
    return SQLiteConnection(raw)
