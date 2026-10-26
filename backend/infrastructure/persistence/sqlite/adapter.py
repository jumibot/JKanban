"""SQLite-specific persistence helpers.

These functions wrap the three main points of SQLite specificity that would
otherwise propagate into every repository:

  - insert_returning_id  →  isolates cursor.lastrowid
  - idempotent_insert    →  isolates INSERT OR IGNORE
  - map_integrity_error  →  isolates sqlite3.IntegrityError

Repositories import from here instead of touching sqlite3 directly.
When a PostgreSQL adapter is added, it supplies its own version of these
helpers; repositories remain unchanged.

PostgreSQL equivalents (for future reference):
  - insert_returning_id  →  INSERT ... RETURNING id
  - idempotent_insert    →  INSERT ... ON CONFLICT DO NOTHING
  - map_integrity_error  →  catch psycopg2.errors.UniqueViolation
"""
import sqlite3
from contextlib import contextmanager
from typing import Callable


def insert_returning_id(conn, sql: str, params) -> int:
    """Execute an INSERT and return the auto-generated row ID.

    SQLite implementation uses cursor.lastrowid.
    PostgreSQL implementation would use RETURNING id.

    The sql parameter uses %s placeholders (translated by SQLiteConnection).
    """
    return conn.execute(sql, params).lastrowid


def idempotent_insert(conn, sql: str, params) -> None:
    """INSERT that silently ignores duplicate key / unique constraint violations.

    The sql must be a standard INSERT INTO statement (no dialect clauses).
    This adapter rewrites INSERT INTO → INSERT OR IGNORE INTO.
    PostgreSQL equivalent: append ON CONFLICT DO NOTHING.
    """
    adapted = sql.replace("INSERT INTO ", "INSERT OR IGNORE INTO ", 1)
    conn.execute(adapted, params)


def reset_tables(conn, tables: list[str]) -> None:
    """Empty the given tables (in order) and restart their ID counters.

    Intended for tests and maintenance scripts.
    PostgreSQL equivalent: TRUNCATE t1, t2, … RESTART IDENTITY CASCADE.
    """
    for table in tables:
        conn.execute(f"DELETE FROM {table}")
    conn.execute(
        f"DELETE FROM sqlite_sequence WHERE name IN ({', '.join('?' * len(tables))})", tables
    )


@contextmanager
def map_integrity_error(exc_factory: Callable):
    """Translate a SQLite IntegrityError into a domain exception.

    Confines sqlite3.IntegrityError knowledge to this module.

    Usage:
        with map_integrity_error(lambda: TagNameAlreadyExists(name)):
            insert_returning_id(conn, sql, params)
    """
    try:
        yield
    except sqlite3.IntegrityError as e:
        raise exc_factory() from e
