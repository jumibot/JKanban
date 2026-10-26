from backend.domain.entities import Priority
from backend.domain.repositories import PriorityRepository
from backend.infrastructure.persistence.common.utils import row_dt, row_opt, utcnow
from backend.infrastructure.persistence.factory import get_connection, insert_returning_id


class SqlPriorityRepository(PriorityRepository):

    def get_all(self) -> list[Priority]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM priorities ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_project(self, project_id: int) -> list[Priority]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM priorities WHERE project_id = %s ORDER BY id", (project_id,)
            ).fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, priority_id: int) -> Priority | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM priorities WHERE id = %s", (priority_id,)).fetchone()
        return self._to_entity(row) if row else None

    def create(self, priority: Priority) -> Priority:
        with get_connection() as conn:
            new_id = insert_returning_id(
                conn,
                "INSERT INTO priorities (name, icon, color, project_id) VALUES (%s,%s,%s,%s)",
                (priority.name, priority.icon, priority.color, priority.project_id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM priorities WHERE id = %s", (new_id,)).fetchone()
        return self._to_entity(row)

    def update(self, priority: Priority) -> Priority:
        with get_connection() as conn:
            conn.execute(
                "UPDATE priorities SET name=%s, icon=%s, color=%s, modified_at=%s WHERE id=%s",
                (priority.name, priority.icon, priority.color, utcnow(), priority.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM priorities WHERE id = %s", (priority.id,)).fetchone()
        return self._to_entity(row)

    def delete(self, priority_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM priorities WHERE id = %s", (priority_id,))
            conn.commit()

    @staticmethod
    def _to_entity(row) -> Priority:
        return Priority(
            id=row["id"],
            name=row["name"],
            project_id=row_opt(row, "project_id"),
            icon=row["icon"],
            color=row["color"],
            created_at=row_dt(row, "created_at"),
            modified_at=row_dt(row, "modified_at"),
            created_by=row_opt(row, "created_by"),
            modified_by=row_opt(row, "modified_by"),
        )
