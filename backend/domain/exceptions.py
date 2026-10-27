class UserNotFound(Exception):
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"User {user_id} not found")


class EmailAlreadyExists(Exception):
    def __init__(self, email: str):
        self.email = email
        super().__init__(f"Email '{email}' is already in use")


class UserOwnsProjects(Exception):
    def __init__(self, user_id: int, count: int):
        self.user_id = user_id
        self.count = count
        super().__init__(
            f"User {user_id} owns {count} project(s). Transfer ownership before deleting."
        )


class TaskNotFound(Exception):
    def __init__(self, task_id: int):
        self.task_id = task_id
        super().__init__(f"Task {task_id} not found")


class GroupNotFound(Exception):
    def __init__(self, group_id: int):
        self.group_id = group_id
        super().__init__(f"Group {group_id} not found")


class GroupHasTasks(Exception):
    def __init__(self, group_id: int, count: int):
        self.group_id = group_id
        self.count = count
        super().__init__(f"Group {group_id} has {count} task(s). Move or delete them first.")


class TodoNotFound(Exception):
    def __init__(self, todo_id: int):
        self.todo_id = todo_id
        super().__init__(f"TodoItem {todo_id} not found")


class TagNotFound(Exception):
    def __init__(self, tag_id: int):
        self.tag_id = tag_id
        super().__init__(f"Tag {tag_id} not found")


class TagNameAlreadyExists(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Tag name '{name}' is already in use")


class TagNotInProject(Exception):
    def __init__(self, tag_id: int, project_id: int | None):
        self.tag_id = tag_id
        self.project_id = project_id
        super().__init__(f"Tag {tag_id} does not belong to project {project_id}")


class PriorityNotFound(Exception):
    def __init__(self, priority_id: int):
        self.priority_id = priority_id
        super().__init__(f"Priority {priority_id} not found")


class PriorityNameAlreadyExists(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Priority name '{name}' is already in use")


class PriorityNotInProject(Exception):
    def __init__(self, priority_id: int, project_id: int | None):
        self.priority_id = priority_id
        self.project_id = project_id
        super().__init__(f"Priority {priority_id} does not belong to project {project_id}")


class ProjectNotFound(Exception):
    def __init__(self, project_id: int):
        self.project_id = project_id
        super().__init__(f"Project {project_id} not found")


class ProjectHasGroups(Exception):
    def __init__(self, project_id: int, count: int):
        self.project_id = project_id
        self.count = count
        super().__init__(f"Project {project_id} has {count} group(s). Move or delete them first.")


class MemberAlreadyInProject(Exception):
    def __init__(self, user_id: int, project_id: int):
        super().__init__(f"User {user_id} is already a member of project {project_id}")


class MemberNotInProject(Exception):
    def __init__(self, user_id: int, project_id: int):
        super().__init__(f"User {user_id} is not a member of project {project_id}")


class AdminCannotDeleteSelf(Exception):
    def __init__(self):
        super().__init__("An administrator cannot delete their own account")


class ProjectLeaderRequired(Exception):
    def __init__(self):
        super().__init__("A project must always have a leader")


class InvalidCredentials(Exception):
    def __init__(self):
        super().__init__("Invalid email or password")


class UserNotInProject(Exception):
    def __init__(self, user_id: int, project_id: int):
        super().__init__(f"User {user_id} has no role in project {project_id}")


# ── Flows ─────────────────────────────────────────────────────────────────────

class FlowNotFound(Exception):
    def __init__(self, flow_id: int):
        self.flow_id = flow_id
        super().__init__(f"Flow {flow_id} not found")


class FlowStateNotFound(Exception):
    def __init__(self, state_id: int, flow_id: int | None = None):
        self.state_id = state_id
        self.flow_id = flow_id
        where = f" in flow {flow_id}" if flow_id is not None else ""
        super().__init__(f"State {state_id} not found{where}")


class FlowTransitionNotFound(Exception):
    def __init__(self, flow_id: int, from_state_id: int, to_state_id: int):
        super().__init__(
            f"Flow {flow_id} has no transition from state {from_state_id} to state {to_state_id}"
        )


class InvalidFlowDefinition(Exception):
    """The flow would break a definition rule (states, initial, transitions)."""


class FlowNameAlreadyExists(Exception):
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Flow name '{name}' is already in use")


class FlowNotInScope(Exception):
    def __init__(self, flow_id: int, project_id: int | None):
        scope = "global tags" if project_id is None else f"tags of project {project_id}"
        super().__init__(f"Flow {flow_id} cannot be used by {scope}")


class FlowInUse(Exception):
    def __init__(self, message: str):
        super().__init__(message)


class FlowStateInUse(Exception):
    def __init__(self, state_name: str, task_ids: list[int], group_ids: list[int]):
        self.task_ids = task_ids
        self.group_ids = group_ids
        parts = []
        if task_ids:
            parts.append(f"{len(task_ids)} task(s) {task_ids}")
        if group_ids:
            parts.append(f"{len(group_ids)} group(s) {group_ids}")
        super().__init__(f"State '{state_name}' is in use by {' and '.join(parts)}")


class InvalidFlowTransition(Exception):
    def __init__(self, from_state: str | None, to_state: str, allowed: list[str]):
        self.allowed = allowed
        options = ", ".join(f"'{a}'" for a in allowed) or "none"
        super().__init__(
            f"Cannot move from '{from_state}' to '{to_state}'. Allowed: {options}"
        )


class TagHasNoFlow(Exception):
    def __init__(self, tag_id: int):
        super().__init__(f"Tag {tag_id} has no flow")


class TagNotAssigned(Exception):
    def __init__(self, tag_id: int, kind: str, item_id: int):
        super().__init__(f"Tag {tag_id} is not assigned to {kind} {item_id}")
