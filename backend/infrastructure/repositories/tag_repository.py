from backend.domain.entities import FlowStateChange, Tag
from backend.domain.exceptions import TagNameAlreadyExists
from backend.domain.repositories import TagRepository
from backend.infrastructure.persistence.common.utils import row_dt, row_opt, utcnow
from backend.infrastructure.persistence.factory import (
    get_connection,
    idempotent_insert,
    insert_returning_id,
    map_integrity_error,
)

# kind → (assignment table, item column). Fixed values: safe to put in SQL.
_ITEMS = {"task": ("task_tags", "task_id"), "group": ("group_tags", "group_id")}

_SELECT_TAG = """SELECT t.*, f.name AS flow_name
                 FROM tags t LEFT JOIN flows f ON f.id = t.flow_id"""


def _item(kind: str) -> tuple[str, str]:
    if kind not in _ITEMS:
        raise ValueError(f"Unknown tag target: {kind!r}")
    return _ITEMS[kind]


class SqlTagRepository(TagRepository):

    def get_all(self) -> list[Tag]:
        with get_connection() as conn:
            rows = conn.execute(f"{_SELECT_TAG} ORDER BY t.id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_global(self) -> list[Tag]:
        with get_connection() as conn:
            rows = conn.execute(f"{_SELECT_TAG} WHERE t.project_id IS NULL ORDER BY t.id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_project(self, project_id: int) -> list[Tag]:
        with get_connection() as conn:
            rows = conn.execute(
                f"{_SELECT_TAG} WHERE t.project_id = %s ORDER BY t.id", (project_id,)
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, tag_id: int) -> Tag | None:
        with get_connection() as conn:
            row = conn.execute(f"{_SELECT_TAG} WHERE t.id = %s", (tag_id,)).fetchone()
        return self._to_entity(row) if row else None

    def get_by_flow(self, flow_id: int) -> list[Tag]:
        with get_connection() as conn:
            rows = conn.execute(
                f"{_SELECT_TAG} WHERE t.flow_id = %s ORDER BY t.id", (flow_id,)
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def create(self, tag: Tag) -> Tag:
        with get_connection() as conn:
            with map_integrity_error(lambda: TagNameAlreadyExists(tag.name)):
                new_id = insert_returning_id(
                    conn,
                    "INSERT INTO tags (name, color, project_id, flow_id, created_at, created_by)"
                    " VALUES (%s,%s,%s,%s,%s,%s)",
                    (tag.name, tag.color, tag.project_id, tag.flow_id, utcnow(), tag.created_by),
                )
            conn.commit()
        return self.get_by_id(new_id)

    def update(self, tag: Tag) -> Tag:
        with get_connection() as conn:
            with map_integrity_error(lambda: TagNameAlreadyExists(tag.name)):
                conn.execute(
                    "UPDATE tags SET name=%s, color=%s, flow_id=%s, modified_at=%s, modified_by=%s"
                    " WHERE id=%s",
                    (tag.name, tag.color, tag.flow_id, utcnow(), tag.modified_by, tag.id),
                )
            conn.commit()
        return self.get_by_id(tag.id)

    def delete(self, tag_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
            conn.commit()

    def count_assignments(self, tag_id: int) -> int:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT (SELECT COUNT(*) FROM task_tags WHERE tag_id = %s)
                        + (SELECT COUNT(*) FROM group_tags WHERE tag_id = %s) AS n""",
                (tag_id, tag_id),
            ).fetchone()
        return row["n"]

    # ── Assignments and flow state ────────────────────────────────────────────

    def get_assignment(self, kind: str, item_id: int, tag_id: int) -> Tag | None:
        table, col = _item(kind)
        with get_connection() as conn:
            row = conn.execute(
                f"""SELECT t.*, f.name AS flow_name, a.state_id AS state_id, s.name AS state_name
                    FROM {table} a
                    JOIN tags t ON t.id = a.tag_id
                    LEFT JOIN flows f ON f.id = t.flow_id
                    LEFT JOIN flow_states s ON s.id = a.state_id
                    WHERE a.{col} = %s AND a.tag_id = %s""",
                (item_id, tag_id),
            ).fetchone()
        return self._to_entity(row) if row else None

    def assign(self, kind, item_id, tag_id, state_id, user_id, change) -> None:
        table, col = _item(kind)
        with get_connection() as conn:
            idempotent_insert(
                conn,
                f"INSERT INTO {table} ({col}, tag_id, state_id, created_at, created_by)"
                " VALUES (%s,%s,%s,%s,%s)",
                (item_id, tag_id, state_id, utcnow(), user_id),
            )
            if change is not None:
                self._log(conn, change)
            conn.commit()

    def unassign(self, kind, item_id, tag_id, change) -> None:
        table, col = _item(kind)
        with get_connection() as conn:
            conn.execute(f"DELETE FROM {table} WHERE {col}=%s AND tag_id=%s", (item_id, tag_id))
            if change is not None:
                self._log(conn, change)
            conn.commit()

    def set_state(self, kind, item_id, tag_id, state_id, change) -> None:
        table, col = _item(kind)
        with get_connection() as conn:
            conn.execute(
                f"UPDATE {table} SET state_id=%s WHERE {col}=%s AND tag_id=%s",
                (state_id, item_id, tag_id),
            )
            self._log(conn, change)
            conn.commit()

    def get_history(self, kind: str, item_id: int, tag_id: int) -> list[FlowStateChange]:
        _, col = _item(kind)
        with get_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM flow_state_changes WHERE {col}=%s AND tag_id=%s ORDER BY id",
                (item_id, tag_id),
            ).fetchall()
        return [
            FlowStateChange(
                id=r["id"],
                tag_id=r["tag_id"],
                task_id=row_opt(r, "task_id"),
                group_id=row_opt(r, "group_id"),
                from_state=row_opt(r, "from_state"),
                to_state=row_opt(r, "to_state"),
                note=row_opt(r, "note"),
                changed_by=row_opt(r, "changed_by"),
                changed_at=row_dt(r, "changed_at"),
            )
            for r in rows
        ]

    @staticmethod
    def _log(conn, change: FlowStateChange) -> None:
        conn.execute(
            """INSERT INTO flow_state_changes
                   (task_id, group_id, tag_id, from_state, to_state, note, changed_by, changed_at)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (change.task_id, change.group_id, change.tag_id, change.from_state,
             change.to_state, change.note, change.changed_by, utcnow()),
        )

    @staticmethod
    def _to_entity(row) -> Tag:
        return Tag(
            id=row["id"],
            name=row["name"],
            project_id=row_opt(row, "project_id"),
            color=row["color"],
            flow_id=row_opt(row, "flow_id"),
            flow_name=row_opt(row, "flow_name"),
            state_id=row_opt(row, "state_id"),
            state_name=row_opt(row, "state_name"),
            created_at=row_dt(row, "created_at"),
            modified_at=row_dt(row, "modified_at"),
            created_by=row_opt(row, "created_by"),
            modified_by=row_opt(row, "modified_by"),
        )
