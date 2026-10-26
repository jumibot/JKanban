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
class Tag:
    name: str
    project_id: int | None = None
    color: str = "#6B7280"
    id: int | None = None
    created_at: datetime | None = None
    modified_at: datetime | None = None
    created_by: int | None = None
    modified_by: int | None = None


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
