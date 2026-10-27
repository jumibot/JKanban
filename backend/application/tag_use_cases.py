"""Tags (global or per project), their assignment to tasks/groups and, for tags
with a flow, the state of each assignment.

`kind` is "task" or "group". Names follow the same scope rule as flows (see
flow_use_cases.name_taken_in_scope). A global tag may only use a global flow;
a project tag, a global flow or one of its project.
"""
from backend.application.flow_use_cases import name_taken_in_scope
from backend.domain.entities import FlowStateChange, Tag
from backend.domain.exceptions import (
    FlowInUse, FlowNotFound, FlowNotInScope, FlowStateNotFound, GroupNotFound,
    InvalidFlowTransition, TagHasNoFlow, TagNameAlreadyExists, TagNotAssigned, TagNotFound,
    TagNotInProject, TaskNotFound,
)
from backend.domain.repositories import (
    FlowRepository, GroupRepository, TagRepository, TaskRepository,
)

KINDS = ("task", "group")


class TagUseCases:
    def __init__(self, tag_repo: TagRepository, task_repo: TaskRepository,
                 group_repo: GroupRepository, flow_repo: FlowRepository):
        self._tags = tag_repo
        self._tasks = task_repo
        self._groups = group_repo
        self._flows = flow_repo

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_all(self) -> list[Tag]:
        return self._tags.get_all()

    def get_global(self) -> list[Tag]:
        return self._tags.get_global()

    def get_by_project(self, project_id: int) -> list[Tag]:
        """Global tags first, then the project's own."""
        return self._tags.get_global() + self._tags.get_by_project(project_id)

    def get_by_id(self, tag_id: int) -> Tag:
        tag = self._tags.get_by_id(tag_id)
        if tag is None:
            raise TagNotFound(tag_id)
        return tag

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create(self, name: str, color: str, project_id: int | None,
               flow_id: int | None = None, user_id: int | None = None) -> Tag:
        name = name.strip()
        self._check_name(name, project_id)
        if flow_id is not None:
            self._check_flow(flow_id, project_id)
        return self._tags.create(
            Tag(name=name, color=color, project_id=project_id, flow_id=flow_id, created_by=user_id)
        )

    def update(self, tag_id: int, updates: dict, user_id: int | None = None) -> Tag:
        """updates: name, color, flow_id (None removes the flow)."""
        tag = self.get_by_id(tag_id)
        if "name" in updates:
            updates["name"] = updates["name"].strip()
            self._check_name(updates["name"], tag.project_id, exclude_id=tag_id)
        if "flow_id" in updates and updates["flow_id"] != tag.flow_id:
            if updates["flow_id"] is not None:
                self._check_flow(updates["flow_id"], tag.project_id)
            used = self._tags.count_assignments(tag_id)
            if used:
                raise FlowInUse(
                    f"Tag '{tag.name}' is assigned to {used} item(s): "
                    "unassign it before changing its flow"
                )
        for key, value in updates.items():
            setattr(tag, key, value)
        tag.modified_by = user_id
        return self._tags.update(tag)

    def delete(self, tag_id: int) -> None:
        self.get_by_id(tag_id)
        self._tags.delete(tag_id)

    # ── Assignment and state ──────────────────────────────────────────────────

    def item_project_id(self, kind: str, item_id: int) -> int | None:
        """Project of a task or group; raises TaskNotFound / GroupNotFound."""
        if kind == "task":
            task = self._tasks.get_by_id(item_id)
            if task is None:
                raise TaskNotFound(item_id)
            group = self._groups.get_by_id(task.group_id)
            return group.project_id if group else None
        if kind == "group":
            group = self._groups.get_by_id(item_id)
            if group is None:
                raise GroupNotFound(item_id)
            return group.project_id
        raise ValueError(f"Unknown tag target: {kind!r}")

    def assign(self, kind: str, item_id: int, tag_id: int, user_id: int | None = None) -> None:
        """Idempotent. A tag with a flow enters its initial state (and it is logged)."""
        project_id = self.item_project_id(kind, item_id)
        tag = self.get_by_id(tag_id)
        if tag.project_id is not None and tag.project_id != project_id:
            raise TagNotInProject(tag_id, project_id)
        if self._tags.get_assignment(kind, item_id, tag_id) is not None:
            return
        state_id, change = None, None
        if tag.flow_id is not None:
            initial = self._flow(tag.flow_id).initial_state()
            state_id = initial.id
            change = self._change(kind, item_id, tag_id, None, initial.name, None, user_id)
        self._tags.assign(kind, item_id, tag_id, state_id, user_id, change)

    def unassign(self, kind: str, item_id: int, tag_id: int, user_id: int | None = None) -> None:
        """Always allowed (idempotent). Leaving a flow is logged."""
        self.item_project_id(kind, item_id)
        current = self._tags.get_assignment(kind, item_id, tag_id)
        if current is None:
            return
        change = None
        if current.flow_id is not None:
            change = self._change(kind, item_id, tag_id, current.state_name, None, None, user_id)
        self._tags.unassign(kind, item_id, tag_id, change)

    def set_state(self, kind: str, item_id: int, tag_id: int, state_id: int,
                  note: str | None = None, user_id: int | None = None) -> Tag:
        """Move the tag's state on the item, only along a transition of its flow."""
        self.item_project_id(kind, item_id)
        current = self._tags.get_assignment(kind, item_id, tag_id)
        if current is None:
            self.get_by_id(tag_id)
            raise TagNotAssigned(tag_id, kind, item_id)
        if current.flow_id is None:
            raise TagHasNoFlow(tag_id)
        flow = self._flow(current.flow_id)
        target = flow.state(state_id)
        if target is None:
            raise FlowStateNotFound(state_id, flow.id)
        # Without a current state (should not happen) any state is a valid way back in.
        if current.state_id is not None:
            allowed = flow.targets(current.state_id)
            if target not in allowed:
                raise InvalidFlowTransition(current.state_name, target.name, [s.name for s in allowed])
        change = self._change(kind, item_id, tag_id, current.state_name, target.name, note, user_id)
        self._tags.set_state(kind, item_id, tag_id, target.id, change)
        return self._tags.get_assignment(kind, item_id, tag_id)

    def history(self, kind: str, item_id: int, tag_id: int) -> list[FlowStateChange]:
        """State log of the tag on the item; kept after unassigning."""
        self.item_project_id(kind, item_id)
        self.get_by_id(tag_id)
        return self._tags.get_history(kind, item_id, tag_id)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _check_name(self, name: str, project_id: int | None, exclude_id: int | None = None):
        others = [t for t in self._tags.get_all() if t.id != exclude_id]
        if name_taken_in_scope(name, project_id, others):
            raise TagNameAlreadyExists(name)

    def _check_flow(self, flow_id: int, project_id: int | None):
        flow = self._flow(flow_id)
        if flow.project_id is not None and flow.project_id != project_id:
            raise FlowNotInScope(flow_id, project_id)

    def _flow(self, flow_id: int):
        flow = self._flows.get_by_id(flow_id)
        if flow is None:
            raise FlowNotFound(flow_id)
        return flow

    @staticmethod
    def _change(kind, item_id, tag_id, from_state, to_state, note, user_id) -> FlowStateChange:
        return FlowStateChange(
            tag_id=tag_id,
            task_id=item_id if kind == "task" else None,
            group_id=item_id if kind == "group" else None,
            from_state=from_state,
            to_state=to_state,
            note=note,
            changed_by=user_id,
        )
