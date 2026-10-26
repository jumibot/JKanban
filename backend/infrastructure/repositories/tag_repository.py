from datetime import datetime
from backend.domain.entities import Tag
from backend.domain.exceptions import TagNameAlreadyExists
from backend.domain.repositories import TagRepository
from backend.infrastructure.persistence.common.utils import utcnow
from backend.infrastructure.persistence.factory import (
    get_connection,
    idempotent_insert,
    insert_returning_id,
    map_integrity_error,
)


class SQLiteTagRepository(TagRepository):

    def get_all(self) -> list[Tag]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM tags ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_project(self, project_id: int) -> list[Tag]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM tags WHERE project_id = %s ORDER BY id", (project_id,)
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, tag_id: int) -> Tag | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM tags WHERE id = %s", (tag_id,)).fetchone()
        return self._to_entity(row) if row else None

    def create(self, tag: Tag) -> Tag:
        with get_connection() as conn:
            with map_integrity_error(lambda: TagNameAlreadyExists(tag.name)):
                new_id = insert_returning_id(
                    conn,
                    "INSERT INTO tags (name, color, project_id) VALUES (%s,%s,%s)",
                    (tag.name, tag.color, tag.project_id),
                )
            conn.commit()
            row = conn.execute("SELECT * FROM tags WHERE id = %s", (new_id,)).fetchone()
        return self._to_entity(row)

    def update(self, tag: Tag) -> Tag:
        with get_connection() as conn:
            with map_integrity_error(lambda: TagNameAlreadyExists(tag.name)):
                conn.execute(
                    "UPDATE tags SET name=%s, color=%s, modified_at=%s WHERE id=%s",
                    (tag.name, tag.color, utcnow(), tag.id),
                )
            conn.commit()
            row = conn.execute("SELECT * FROM tags WHERE id = %s", (tag.id,)).fetchone()
        return self._to_entity(row)

    def delete(self, tag_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM tags WHERE id = %s", (tag_id,))
            conn.commit()

    def assign_to_task(self, task_id: int, tag_id: int) -> None:
        with get_connection() as conn:
            idempotent_insert(
                conn, "INSERT INTO task_tags (task_id, tag_id) VALUES (%s,%s)", (task_id, tag_id)
            )
            conn.commit()

    def unassign_from_task(self, task_id: int, tag_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM task_tags WHERE task_id=%s AND tag_id=%s", (task_id, tag_id)
            )
            conn.commit()

    def assign_to_group(self, group_id: int, tag_id: int) -> None:
        with get_connection() as conn:
            idempotent_insert(
                conn, "INSERT INTO group_tags (group_id, tag_id) VALUES (%s,%s)", (group_id, tag_id)
            )
            conn.commit()

    def unassign_from_group(self, group_id: int, tag_id: int) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM group_tags WHERE group_id=%s AND tag_id=%s", (group_id, tag_id)
            )
            conn.commit()

    @staticmethod
    def _to_entity(row) -> Tag:
        keys = row.keys()
        def _opt(col): return row[col] if col in keys and row[col] is not None else None
        def _dt(col):
            v = _opt(col)
            return datetime.fromisoformat(v) if v else None
        return Tag(
            id=row["id"],
            name=row["name"],
            project_id=_opt("project_id"),
            color=row["color"],
            created_at=_dt("created_at"),
            modified_at=_dt("modified_at"),
            created_by=_opt("created_by"),
            modified_by=_opt("modified_by"),
        )
