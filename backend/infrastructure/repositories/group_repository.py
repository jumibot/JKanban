from backend.domain.entities import Group, Tag
from backend.domain.repositories import GroupRepository
from backend.infrastructure.persistence.common.utils import ph, row_dt, row_opt, utcnow
from backend.infrastructure.persistence.factory import get_connection, insert_returning_id


class SqlGroupRepository(GroupRepository):

    def get_all(self) -> list[Group]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM groups ORDER BY sort_order, id").fetchall()
            groups = [self._to_entity(r) for r in rows]
            self._load_tags(conn, groups)
        return groups

    def get_by_id(self, group_id: int) -> Group | None:
        with get_connection() as conn:
            row = conn.execute("SELECT * FROM groups WHERE id = %s", (group_id,)).fetchone()
            if row is None:
                return None
            group = self._to_entity(row)
            self._load_tags(conn, [group])
        return group

    def count_by_project(self, project_id: int) -> int:
        with get_connection() as conn:
            return conn.execute(
                "SELECT COUNT(*) AS n FROM groups WHERE project_id = %s", (project_id,)
            ).fetchone()["n"]

    def create(self, group: Group) -> Group:
        with get_connection() as conn:
            new_id = insert_returning_id(
                conn,
                "INSERT INTO groups (name, description, color, project_id, sort_order) VALUES (%s,%s,%s,%s,%s)",
                (group.name, group.description, group.color, group.project_id, group.sort_order),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM groups WHERE id = %s", (new_id,)).fetchone()
            result = self._to_entity(row)
            self._load_tags(conn, [result])
        return result

    def update(self, group: Group) -> Group:
        with get_connection() as conn:
            conn.execute(
                """UPDATE groups
                   SET name=%s, description=%s, color=%s, project_id=%s, sort_order=%s, modified_at=%s
                   WHERE id=%s""",
                (group.name, group.description, group.color, group.project_id, group.sort_order, utcnow(), group.id),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM groups WHERE id = %s", (group.id,)).fetchone()
            result = self._to_entity(row)
            self._load_tags(conn, [result])
        return result

    def delete(self, group_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM groups WHERE id = %s", (group_id,))
            conn.commit()

    def reorder(self, group_ids: list[int]) -> None:
        with get_connection() as conn:
            for order, group_id in enumerate(group_ids):
                conn.execute("UPDATE groups SET sort_order=%s WHERE id=%s", (order, group_id))
            conn.commit()

    @staticmethod
    def _load_tags(conn, groups: list[Group]) -> None:
        if not groups:
            return
        ids = [g.id for g in groups]
        rows = conn.execute(
            f"""SELECT gt.group_id, t.id, t.name, t.color
                FROM group_tags gt JOIN tags t ON t.id = gt.tag_id
                WHERE gt.group_id IN ({ph(len(ids))}) ORDER BY gt.group_id, t.id""",
            ids,
        ).fetchall()
        by_group: dict[int, list[Tag]] = {g.id: [] for g in groups}
        for r in rows:
            by_group[r["group_id"]].append(Tag(id=r["id"], name=r["name"], color=r["color"]))
        for group in groups:
            group.tags = by_group.get(group.id, [])

    @staticmethod
    def _to_entity(row) -> Group:
        return Group(
            id=row["id"],
            name=row["name"],
            description=row_opt(row, "description"),
            color=row["color"],
            project_id=row_opt(row, "project_id"),
            sort_order=row["sort_order"] if "sort_order" in row.keys() else 0,
            created_at=row_dt(row, "created_at"),
            modified_at=row_dt(row, "modified_at"),
            created_by=row_opt(row, "created_by"),
            modified_by=row_opt(row, "modified_by"),
        )
