from datetime import datetime
from backend.domain.entities import Resource
from backend.domain.repositories import ResourceRepository
from backend.infrastructure.persistence.factory import get_connection, insert_returning_id


class SQLiteResourceRepository(ResourceRepository):

    def get_all(self) -> list[Resource]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM resources ORDER BY id").fetchall()
        return [self._to_entity(r) for r in rows]

    def get_by_id(self, resource_id: int) -> Resource | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM resources WHERE id = %s", (resource_id,)).fetchone()
        return self._to_entity(row) if row else None

    def get_by_email(self, email: str) -> Resource | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM resources WHERE email = %s", (email,)).fetchone()
        return self._to_entity(row) if row else None

    def create(self, resource: Resource) -> Resource:
        with get_connection() as conn:
            new_id = insert_returning_id(
                conn,
                "INSERT INTO resources (name, email, avatar_url) VALUES (%s, %s, %s)",
                (resource.name, resource.email, resource.avatar_url),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM resources WHERE id = %s", (new_id,)).fetchone()
        return self._to_entity(row)

    def update(self, resource: Resource) -> Resource:
        with get_connection() as conn:
            conn.execute(
                "UPDATE resources SET name = %s, email = %s, avatar_url = %s WHERE id = %s",
                (resource.name, resource.email, resource.avatar_url, resource.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM resources WHERE id = %s", (resource.id,)).fetchone()
        return self._to_entity(row)

    def delete(self, resource_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM resources WHERE id = %s", (resource_id,))
            conn.commit()

    @staticmethod
    def _to_entity(row) -> Resource:
        return Resource(
            id=row["id"],
            name=row["name"],
            email=row["email"],
            avatar_url=row["avatar_url"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
