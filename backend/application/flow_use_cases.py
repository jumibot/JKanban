"""Flows: states (exactly one initial) and transitions, global or per project.

Names are compared ignoring case, both for flows (within their scope) and for
states (within their flow). Scope rule: a global name may not repeat any other
flow's name; a project name may not repeat a global one or another of its project.
"""
from backend.domain.entities import Flow, FlowState
from backend.domain.exceptions import (
    FlowInUse, FlowNameAlreadyExists, FlowNotFound, FlowStateInUse, FlowStateNotFound,
    FlowTransitionNotFound, InvalidFlowDefinition,
)
from backend.domain.repositories import FlowRepository, TagRepository


def _key(name: str) -> str:
    return name.strip().casefold()


def name_taken_in_scope(name: str, project_id: int | None, others) -> bool:
    """True if `name` clashes with any of `others` (objects with .name/.project_id)
    under the global-vs-project rule. Shared with tags."""
    key = _key(name)
    return any(
        _key(o.name) == key
        and (project_id is None or o.project_id is None or o.project_id == project_id)
        for o in others
    )


class FlowUseCases:
    def __init__(self, flow_repo: FlowRepository, tag_repo: TagRepository):
        self._flows = flow_repo
        self._tags = tag_repo

    # ── Queries ───────────────────────────────────────────────────────────────

    def list_global(self) -> list[Flow]:
        return self._flows.get_global()

    def list_for_project(self, project_id: int) -> list[Flow]:
        """Global flows first, then the project's own."""
        return self._flows.get_global() + self._flows.get_by_project(project_id)

    def get(self, flow_id: int) -> Flow:
        flow = self._flows.get_by_id(flow_id)
        if flow is None:
            raise FlowNotFound(flow_id)
        return flow

    # ── Flow ──────────────────────────────────────────────────────────────────

    def create(
        self,
        name: str,
        states: list[tuple[str, str]],
        initial: str,
        transitions: list[tuple[str, str]],
        project_id: int | None,
        user_id: int | None,
    ) -> Flow:
        """states: (name, color); initial and transitions refer to states by name."""
        name = name.strip()
        self._check_flow_name(name, project_id)
        if not states:
            raise InvalidFlowDefinition("A flow needs at least one state")
        index: dict[str, int] = {}
        for i, (state_name, _) in enumerate(states):
            if not state_name.strip():
                raise InvalidFlowDefinition("State names cannot be empty")
            if _key(state_name) in index:
                raise InvalidFlowDefinition(f"State name '{state_name}' is repeated")
            index[_key(state_name)] = i
        if _key(initial) not in index:
            raise InvalidFlowDefinition(f"Initial state '{initial}' is not one of the states")
        pairs: list[tuple[int, int]] = []
        for a, b in transitions:
            for end in (a, b):
                if _key(end) not in index:
                    raise InvalidFlowDefinition(f"Transition uses unknown state '{end}'")
            pair = (index[_key(a)], index[_key(b)])
            if pair[0] == pair[1]:
                raise InvalidFlowDefinition(f"Transition from '{a}' to itself is not allowed")
            if pair in pairs:
                raise InvalidFlowDefinition(f"Transition '{a}' → '{b}' is repeated")
            pairs.append(pair)
        flow = Flow(
            name=name,
            project_id=project_id,
            created_by=user_id,
            states=[
                FlowState(name=n.strip(), color=c, is_initial=(i == index[_key(initial)]))
                for i, (n, c) in enumerate(states)
            ],
        )
        return self._flows.create(flow, pairs)

    def rename(self, flow_id: int, name: str, user_id: int | None) -> Flow:
        flow = self.get(flow_id)
        name = name.strip()
        self._check_flow_name(name, flow.project_id, exclude_id=flow_id)
        self._flows.rename(flow_id, name, user_id)
        return self.get(flow_id)

    def delete(self, flow_id: int) -> None:
        self.get(flow_id)
        tags = self._tags.get_by_flow(flow_id)
        if tags:
            names = ", ".join(f"'{t.name}'" for t in tags)
            raise FlowInUse(f"Flow {flow_id} is used by tag(s) {names}")
        self._flows.delete(flow_id)

    # ── States ────────────────────────────────────────────────────────────────

    def add_state(self, flow_id: int, name: str, color: str, is_initial: bool,
                  user_id: int | None) -> Flow:
        flow = self.get(flow_id)
        name = name.strip()
        self._check_state_name(flow, name)
        self._flows.add_state(flow_id, FlowState(name=name, color=color, is_initial=is_initial), user_id)
        return self.get(flow_id)

    def update_state(self, flow_id: int, state_id: int, updates: dict, user_id: int | None) -> Flow:
        """updates: name, color, sort_order, is_initial. is_initial=True makes it
        the only initial state; False is only accepted on a non-initial state."""
        flow = self.get(flow_id)
        state = self._state(flow, state_id)
        if "name" in updates:
            updates["name"] = updates["name"].strip()
            self._check_state_name(flow, updates["name"], exclude_id=state_id)
        if updates.get("is_initial") is False and state.is_initial:
            raise InvalidFlowDefinition(
                "A flow needs an initial state: mark another state as initial instead"
            )
        for key, value in updates.items():
            setattr(state, key, value)
        self._flows.update_state(state, user_id)
        return self.get(flow_id)

    def delete_state(self, flow_id: int, state_id: int, user_id: int | None) -> Flow:
        flow = self.get(flow_id)
        state = self._state(flow, state_id)
        if state.is_initial:
            raise InvalidFlowDefinition(
                f"'{state.name}' is the initial state: mark another state as initial first"
            )
        task_ids, group_ids = self._flows.state_usage(state_id)
        if task_ids or group_ids:
            raise FlowStateInUse(state.name, task_ids, group_ids)
        self._flows.delete_state(flow_id, state_id, user_id)
        return self.get(flow_id)

    # ── Transitions ───────────────────────────────────────────────────────────

    def add_transition(self, flow_id: int, from_state_id: int, to_state_id: int,
                       user_id: int | None) -> Flow:
        flow = self.get(flow_id)
        a = self._state(flow, from_state_id)
        b = self._state(flow, to_state_id)
        if a.id == b.id:
            raise InvalidFlowDefinition(f"Transition from '{a.name}' to itself is not allowed")
        if self._has_transition(flow, a.id, b.id):
            raise InvalidFlowDefinition(f"Transition '{a.name}' → '{b.name}' already exists")
        self._flows.add_transition(flow_id, a.id, b.id, user_id)
        return self.get(flow_id)

    def delete_transition(self, flow_id: int, from_state_id: int, to_state_id: int,
                          user_id: int | None) -> Flow:
        flow = self.get(flow_id)
        if not self._has_transition(flow, from_state_id, to_state_id):
            raise FlowTransitionNotFound(flow_id, from_state_id, to_state_id)
        self._flows.delete_transition(flow_id, from_state_id, to_state_id, user_id)
        return self.get(flow_id)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _check_flow_name(self, name: str, project_id: int | None, exclude_id: int | None = None):
        others = [f for f in self._flows.get_all() if f.id != exclude_id]
        if name_taken_in_scope(name, project_id, others):
            raise FlowNameAlreadyExists(name)

    @staticmethod
    def _check_state_name(flow: Flow, name: str, exclude_id: int | None = None):
        if not name:
            raise InvalidFlowDefinition("State names cannot be empty")
        if any(_key(s.name) == _key(name) for s in flow.states if s.id != exclude_id):
            raise InvalidFlowDefinition(f"State name '{name}' is repeated in the flow")

    @staticmethod
    def _state(flow: Flow, state_id: int) -> FlowState:
        state = flow.state(state_id)
        if state is None:
            raise FlowStateNotFound(state_id, flow.id)
        return state

    @staticmethod
    def _has_transition(flow: Flow, a: int, b: int) -> bool:
        return any(t.from_state_id == a and t.to_state_id == b for t in flow.transitions)
