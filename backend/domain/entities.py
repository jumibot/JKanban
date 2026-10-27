from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class User:
    name: str
    email: str
    password_hash: str
    avatar_url: str | None = None
    is_admin: bool = False
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None


@dataclass
class FlowState:
    name: str
    color: str = "#6B7280"
    sort_order: int = 0
    is_initial: bool = False
    flow_id: int | None = None
    id: int | None = None


@dataclass
class FlowTransition:
    from_state_id: int
    to_state_id: int


@dataclass
class Flow:
    """States (exactly one initial) and the allowed transitions between them.
    project_id None = global flow."""
    name: str
    project_id: int | None = None
    states: list[FlowState] = field(default_factory=list)
    transitions: list[FlowTransition] = field(default_factory=list)
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None

    def state(self, state_id: int) -> FlowState | None:
        return next((s for s in self.states if s.id == state_id), None)

    def initial_state(self) -> FlowState | None:
        return next((s for s in self.states if s.is_initial), None)

    def targets(self, from_state_id: int) -> list[FlowState]:
        """States reachable from from_state_id, in state order."""
        ids = {t.to_state_id for t in self.transitions if t.from_state_id == from_state_id}
        return [s for s in self.states if s.id in ids]


@dataclass
class FlowStateChange:
    """One entry of the state history of a tag on a task or a group.
    States are stored by name so the log stays readable after renames/deletes."""
    tag_id: int
    from_state: str | None
    to_state: str | None
    task_id: int | None = None
    group_id: int | None = None
    note: str | None = None
    changed_by: int | None = None
    changed_at: datetime | None = None
    id: int | None = None


@dataclass
class Tag:
    """project_id None = global tag. flow_* describe the tag's flow;
    state_* are filled only when the tag is read as assigned to a task/group."""
    name: str
    project_id: int | None = None
    color: str = "#6B7280"
    flow_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None
    flow_name: str | None = None
    state_id: int | None = None
    state_name: str | None = None


@dataclass
class Priority:
    name: str
    project_id: int | None = None
    color: str = "#6B7280"
    icon: str = "flag"
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None


@dataclass
class Project:
    name: str
    owner_id: int
    description: str | None = None
    icon: str = "folder"
    color: str = "#3B82F6"
    leader_id: int | None = None
    priority_id: int | None = None
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None
    owner: "User | None" = None
    leader: "User | None" = None
    priority: Priority | None = None
    members: "list[User]" = field(default_factory=list)


@dataclass
class ProjectContentCounts:
    """How much dependent data a project holds (used to preview cascade deletes)."""
    groups: int = 0
    tasks: int = 0
    tags: int = 0
    priorities: int = 0
    members: int = 0


@dataclass
class Group:
    name: str
    description: str | None = None
    color: str = "#3B82F6"
    project_id: int | None = None
    sort_order: int = 0
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None
    tags: list[Tag] = field(default_factory=list)


@dataclass
class TodoItem:
    task_id: int
    title: str
    order: int = 0
    completed: bool = False
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None


@dataclass
class Task:
    group_id: int
    title: str
    description: str | None = None
    completed: bool = False
    user_id: int | None = None
    priority_id: int | None = None
    estimated_duration: float | None = None
    estimated_start: datetime | None = None
    estimated_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    sort_order: int = 0
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None
    user: "User | None" = None
    priority: Priority | None = None
    tags: list[Tag] = field(default_factory=list)
    todos_total: int = 0
    todos_completed: int = 0
