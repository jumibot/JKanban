"""Migración de una base de datos anterior a los flujos (docs/flows.md §8).

Excepción a la regla «los tests no ejecutan SQL»: para tener el esquema
anterior hay que fabricarlo. Se crea una BD actual con datos (vía casos de
uso), se degrada con sqlite3 a como era antes de los flujos (tags.project_id
NOT NULL, sin flow_id ni state_id, sin tablas de flujos) y se comprueba que
init_db() la migra sin perder datos. Es específico de SQLite, como migrations.py.
"""
import sqlite3

import pytest

from backend.infrastructure.database import init_db
from backend.interfaces.dependencies import (
    get_flow_use_cases, get_group_use_cases, get_project_use_cases, get_tag_use_cases,
    get_task_use_cases, get_user_use_cases,
)

_OLD_TAGS = """
    CREATE TABLE tags_old (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL,
        project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
        color       TEXT NOT NULL DEFAULT '#6B7280' CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#'),
        created_at  TEXT NOT NULL DEFAULT (datetime('now')),
        modified_at TEXT,
        created_by  INTEGER REFERENCES users(id) ON DELETE SET NULL,
        modified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        UNIQUE(name, project_id)
    )"""

_OLD_LINK = """
    CREATE TABLE {table}_old (
        {col}      INTEGER NOT NULL REFERENCES {parent}(id) ON DELETE CASCADE,
        tag_id     INTEGER NOT NULL REFERENCES tags(id)   ON DELETE CASCADE,
        created_at TEXT    NOT NULL DEFAULT (datetime('now')),
        created_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
        PRIMARY KEY ({col}, tag_id)
    )"""


def _downgrade(path) -> None:
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = OFF")
    for t in ("flow_state_changes", "flow_transitions", "flow_states", "flows"):
        conn.execute(f"DROP TABLE {t}")
    conn.execute(_OLD_TAGS)
    conn.execute("""INSERT INTO tags_old (id, name, project_id, color, created_at)
                    SELECT id, name, project_id, color, created_at FROM tags""")
    conn.execute("DROP TABLE tags")
    conn.execute("ALTER TABLE tags_old RENAME TO tags")
    for table, col, parent in (("task_tags", "task_id", "tasks"), ("group_tags", "group_id", "groups")):
        conn.execute(_OLD_LINK.format(table=table, col=col, parent=parent))
        conn.execute(f"INSERT INTO {table}_old ({col}, tag_id, created_at) "
                     f"SELECT {col}, tag_id, created_at FROM {table}")
        conn.execute(f"DROP TABLE {table}")
        conn.execute(f"ALTER TABLE {table}_old RENAME TO {table}")
    conn.commit()
    conn.close()


def _columns(path, table) -> dict[str, int]:
    conn = sqlite3.connect(path)
    try:
        return {r[1]: r[3] for r in conn.execute(f"PRAGMA table_info({table})")}
    finally:
        conn.close()


@pytest.fixture
def old_db(tmp_path, monkeypatch):
    """A pre-flows database with a project tag on a task and on a group."""
    path = tmp_path / "old.db"
    monkeypatch.setenv("SQLITE_PATH", str(path))
    monkeypatch.setenv("JKANBAN_DEMO_DATA", "0")
    init_db()
    user = get_user_use_cases().create(name="A", email="a@x.com", password="secret1", avatar_url=None)
    project = get_project_use_cases().create("P", None, "folder", "#3B82F6", user.id, None, None)
    group = get_group_use_cases().create("G", None, "#3B82F6", project.id)
    task = get_task_use_cases().create(group.id, "T", None, False, None, None, None, None, None,
                                       None, None)
    tags = get_tag_use_cases()
    tag = tags.create("Bug", "#EF4444", project.id)
    tags.assign("task", task.id, tag.id)
    tags.assign("group", group.id, tag.id)
    _downgrade(path)
    assert "flow_id" not in _columns(path, "tags")
    return path, project.id, group.id, task.id, tag.id


def test_migration_keeps_tags_and_assignments(old_db):
    path, pid, gid, tid, tag_id = old_db
    init_db()
    cols = _columns(path, "tags")
    assert "flow_id" in cols and cols["project_id"] == 0          # nullable now
    assert "state_id" in _columns(path, "task_tags")
    assert "state_id" in _columns(path, "group_tags")
    tags = get_tag_use_cases()
    (tag,) = tags.get_by_project(pid)
    assert (tag.id, tag.name, tag.project_id, tag.color, tag.flow_id) == (tag_id, "Bug", pid, "#EF4444", None)
    assert [t.id for t in get_task_use_cases().get_by_id(tid).tags] == [tag_id]
    assert [t.id for t in get_group_use_cases().get_by_id(gid).tags] == [tag_id]


def test_migrated_database_supports_flows_and_global_tags(old_db):
    path, pid, gid, tid, tag_id = old_db
    init_db()
    flow = get_flow_use_cases().create("F", [("A", "#6B7280"), ("B", "#6B7280")], "A", [("A", "B")],
                                       None, None)
    tags = get_tag_use_cases()
    glob = tags.create("Slice", "#6B7280", None, flow.id)
    tags.assign("task", tid, glob.id)
    tags.set_state("task", tid, glob.id, flow.states[1].id, "ok")
    assert [c.to_state for c in tags.history("task", tid, glob.id)] == ["A", "B"]


def test_migration_is_idempotent(old_db):
    path, pid, *_ = old_db
    init_db()
    init_db()
    assert [t.name for t in get_tag_use_cases().get_by_project(pid)] == ["Bug"]


def test_rebuilding_a_parent_table_keeps_child_rows(old_db):
    """Regression: PRAGMA foreign_keys = OFF used to be ignored inside the
    migration transaction, so rebuilding projects cascade-deleted its groups."""
    path, pid, gid, tid, _ = old_db
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = OFF")
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name='projects'").fetchone()[0]
    conn.execute(sql.replace("CREATE TABLE projects", "CREATE TABLE projects_old")
                    .replace(" CHECK(LENGTH(color)=7 AND SUBSTR(color,1,1)='#')", ""))
    conn.execute("INSERT INTO projects_old SELECT * FROM projects")
    conn.execute("DROP TABLE projects")
    conn.execute("ALTER TABLE projects_old RENAME TO projects")
    conn.commit()
    conn.close()
    init_db()
    assert get_group_use_cases().get_by_id(gid) is not None
    assert get_task_use_cases().get_by_id(tid).group_id == gid
