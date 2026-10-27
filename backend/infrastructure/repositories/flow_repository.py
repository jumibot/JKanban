from backend.domain.entities import Flow, FlowState, FlowTransition
from backend.domain.exceptions import InvalidFlowDefinition
from backend.domain.repositories import FlowRepository
from backend.infrastructure.persistence.common.utils import ph, row_dt, row_opt, utcnow
from backend.infrastructure.persistence.factory import (
    get_connection,
    insert_returning_id,
    map_integrity_error,
)


def _duplicate_state(name: str):
    return lambda: InvalidFlowDefinition(f"State name '{name}' is repeated in the flow")


class SqlFlowRepository(FlowRepository):

    def get_all(self) -> list[Flow]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM flows ORDER BY id").fetchall()
            return self._load(conn, rows)

    def get_global(self) -> list[Flow]:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM flows WHERE project_id IS NULL ORDER BY id").fetchall()
            return self._load(conn, rows)

    def get_by_project(self, project_id: int) -> list[Flow]:
        with get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM flows WHERE project_id = %s ORDER BY id", (project_id,)
            ).fetchall()
            return self._load(conn, rows)

    def get_by_id(self, flow_id: int) -> Flow | None:
        with get_connection() as conn:
            rows = conn.execute("SELECT * FROM flows WHERE id = %s", (flow_id,)).fetchall()
            flows = self._load(conn, rows)
        return flows[0] if flows else None

    def create(self, flow: Flow, transitions: list[tuple[int, int]]) -> Flow:
        with get_connection() as conn:
            flow_id = insert_returning_id(
                conn,
                "INSERT INTO flows (name, project_id, created_at, created_by) VALUES (%s,%s,%s,%s)",
                (flow.name, flow.project_id, utcnow(), flow.created_by),
            )
            state_ids = []
            for order, state in enumerate(flow.states):
                with map_integrity_error(_duplicate_state(state.name)):
                    state_ids.append(insert_returning_id(
                        conn,
                        "INSERT INTO flow_states (flow_id, name, color, sort_order, is_initial)"
                        " VALUES (%s,%s,%s,%s,%s)",
                        (flow_id, state.name, state.color, order, bool(state.is_initial)),
                    ))
            for i, j in transitions:
                conn.execute(
                    "INSERT INTO flow_transitions (flow_id, from_state_id, to_state_id)"
                    " VALUES (%s,%s,%s)",
                    (flow_id, state_ids[i], state_ids[j]),
                )
            conn.commit()
        return self.get_by_id(flow_id)

    def rename(self, flow_id: int, name: str, user_id: int | None) -> None:
        with get_connection() as conn:
            conn.execute(
                "UPDATE flows SET name=%s, modified_at=%s, modified_by=%s WHERE id=%s",
                (name, utcnow(), user_id, flow_id),
            )
            conn.commit()

    def delete(self, flow_id: int) -> None:
        with get_connection() as conn:
            conn.execute("DELETE FROM flows WHERE id = %s", (flow_id,))
            conn.commit()

    def add_state(self, flow_id: int, state: FlowState, user_id: int | None) -> FlowState:
        with get_connection() as conn:
            order = conn.execute(
                "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM flow_states WHERE flow_id = %s",
                (flow_id,),
            ).fetchone()["n"]
            if state.is_initial:
                self._clear_initial(conn, flow_id)
            with map_integrity_error(_duplicate_state(state.name)):
                state_id = insert_returning_id(
                    conn,
                    "INSERT INTO flow_states (flow_id, name, color, sort_order, is_initial)"
                    " VALUES (%s,%s,%s,%s,%s)",
                    (flow_id, state.name, state.color, order, bool(state.is_initial)),
                )
            self._touch(conn, flow_id, user_id)
            conn.commit()
        return FlowState(id=state_id, flow_id=flow_id, name=state.name, color=state.color,
                         sort_order=order, is_initial=bool(state.is_initial))

    def update_state(self, state: FlowState, user_id: int | None) -> None:
        with get_connection() as conn:
            if state.is_initial:
                self._clear_initial(conn, state.flow_id)
            with map_integrity_error(_duplicate_state(state.name)):
                conn.execute(
                    "UPDATE flow_states SET name=%s, color=%s, sort_order=%s, is_initial=%s"
                    " WHERE id=%s",
                    (state.name, state.color, state.sort_order, bool(state.is_initial), state.id),
                )
            self._touch(conn, state.flow_id, user_id)
            conn.commit()

    def delete_state(self, flow_id: int, state_id: int, user_id: int | None) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM flow_transitions WHERE from_state_id=%s OR to_state_id=%s",
                (state_id, state_id),
            )
            conn.execute("DELETE FROM flow_states WHERE id=%s", (state_id,))
            self._touch(conn, flow_id, user_id)
            conn.commit()

    def add_transition(self, flow_id, from_state_id, to_state_id, user_id) -> None:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO flow_transitions (flow_id, from_state_id, to_state_id) VALUES (%s,%s,%s)",
                (flow_id, from_state_id, to_state_id),
            )
            self._touch(conn, flow_id, user_id)
            conn.commit()

    def delete_transition(self, flow_id, from_state_id, to_state_id, user_id) -> None:
        with get_connection() as conn:
            conn.execute(
                "DELETE FROM flow_transitions WHERE flow_id=%s AND from_state_id=%s AND to_state_id=%s",
                (flow_id, from_state_id, to_state_id),
            )
            self._touch(conn, flow_id, user_id)
            conn.commit()

    def state_usage(self, state_id: int) -> tuple[list[int], list[int]]:
        with get_connection() as conn:
            tasks = conn.execute(
                "SELECT task_id AS id FROM task_tags WHERE state_id = %s ORDER BY task_id", (state_id,)
            ).fetchall()
            groups = conn.execute(
                "SELECT group_id AS id FROM group_tags WHERE state_id = %s ORDER BY group_id", (state_id,)
            ).fetchall()
        return [r["id"] for r in tasks], [r["id"] for r in groups]

    # ── helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clear_initial(conn, flow_id: int) -> None:
        conn.execute("UPDATE flow_states SET is_initial=%s WHERE flow_id=%s", (False, flow_id))

    @staticmethod
    def _touch(conn, flow_id: int, user_id: int | None) -> None:
        conn.execute(
            "UPDATE flows SET modified_at=%s, modified_by=%s WHERE id=%s",
            (utcnow(), user_id, flow_id),
        )

    @staticmethod
    def _load(conn, rows) -> list[Flow]:
        flows = [
            Flow(
                id=r["id"],
                name=r["name"],
                project_id=row_opt(r, "project_id"),
                created_at=row_dt(r, "created_at"),
                modified_at=row_dt(r, "modified_at"),
                created_by=row_opt(r, "created_by"),
                modified_by=row_opt(r, "modified_by"),
            )
            for r in rows
        ]
        if not flows:
            return flows
        by_id = {f.id: f for f in flows}
        ids = list(by_id)
        for r in conn.execute(
            f"SELECT * FROM flow_states WHERE flow_id IN ({ph(len(ids))}) ORDER BY sort_order, id", ids
        ).fetchall():
            by_id[r["flow_id"]].states.append(FlowState(
                id=r["id"], flow_id=r["flow_id"], name=r["name"], color=r["color"],
                sort_order=r["sort_order"], is_initial=bool(r["is_initial"]),
            ))
        for r in conn.execute(
            f"SELECT * FROM flow_transitions WHERE flow_id IN ({ph(len(ids))})"
            " ORDER BY from_state_id, to_state_id", ids
        ).fetchall():
            by_id[r["flow_id"]].transitions.append(
                FlowTransition(from_state_id=r["from_state_id"], to_state_id=r["to_state_id"])
            )
        return flows
