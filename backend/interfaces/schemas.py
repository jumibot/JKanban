import re
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from backend.domain.entities import Group, Priority, Project, Tag, Task, TodoItem, User

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=6, max_length=128)
    avatar_url: str | None = None

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v.lower()


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    avatar_url: str | None = None
    is_admin: bool | None = None

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v.lower()


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    avatar_url: str | None
    is_admin: bool = False
    created_at: datetime
    modified_at: datetime | None = None

    @classmethod
    def from_entity(cls, u: User) -> "UserResponse":
        return cls(
            id=u.id, name=u.name, email=u.email,
            avatar_url=u.avatar_url, is_admin=u.is_admin,
            created_at=u.created_at, modified_at=u.modified_at,
        )


# ---------------------------------------------------------------------------
# Priorities
# ---------------------------------------------------------------------------

class PriorityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    icon: str = "flag"
    color: str = "#6B7280"

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


class PriorityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    icon: str | None = None
    color: str | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


class PriorityResponse(BaseModel):
    id: int
    name: str
    icon: str
    color: str
    project_id: int | None = None

    @classmethod
    def from_entity(cls, p: Priority) -> "PriorityResponse":
        return cls(id=p.id, name=p.name, icon=p.icon, color=p.color, project_id=p.project_id)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------

class TagCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    color: str = "#6B7280"

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


class TagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    color: str | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


class TagResponse(BaseModel):
    id: int
    name: str
    color: str
    project_id: int | None = None

    @classmethod
    def from_entity(cls, t: Tag) -> "TagResponse":
        return cls(id=t.id, name=t.name, color=t.color, project_id=t.project_id)


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    icon: str = "folder"
    color: str = "#3B82F6"
    leader_id: int | None = None
    priority_id: int | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    icon: str | None = None
    color: str | None = None
    owner_id: int | None = None
    leader_id: int | None = None
    priority_id: int | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


class ProjectResponse(BaseModel):
    id: int
    name: str
    description: str | None
    icon: str
    color: str
    created_at: datetime
    modified_at: datetime | None = None
    owner: UserResponse | None = None
    leader: UserResponse | None = None
    priority: PriorityResponse | None = None
    members: list[UserResponse] = []

    @classmethod
    def from_entity(cls, p: Project) -> "ProjectResponse":
        return cls(
            id=p.id, name=p.name, description=p.description,
            icon=p.icon, color=p.color, created_at=p.created_at,
            modified_at=p.modified_at,
            owner=UserResponse.from_entity(p.owner) if p.owner else None,
            leader=UserResponse.from_entity(p.leader) if p.leader else None,
            priority=PriorityResponse.from_entity(p.priority) if p.priority else None,
            members=[UserResponse.from_entity(m) for m in p.members],
        )


# ---------------------------------------------------------------------------
# Groups
# ---------------------------------------------------------------------------

class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    color: str = "#3B82F6"
    project_id: int
    sort_order: int | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str) -> str:
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    color: str | None = None
    project_id: int | None = None
    sort_order: int | None = None

    @field_validator("color")
    @classmethod
    def validate_color(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if not _HEX_RE.match(v):
            raise ValueError("Color must be in #RRGGBB hex format")
        return v.upper()


def _unique_ids(v: list[int]) -> list[int]:
    if len(v) != len(set(v)):
        raise ValueError("ids must not repeat")
    return v


class GroupReorderRequest(BaseModel):
    project_id: int
    group_ids: list[int]

    _unique = field_validator("group_ids")(_unique_ids)


class GroupResponse(BaseModel):
    id: int
    name: str
    description: str | None
    color: str
    project_id: int | None
    sort_order: int = 0
    created_at: datetime
    modified_at: datetime | None = None
    tags: list[TagResponse] = []

    @classmethod
    def from_entity(cls, g: Group) -> "GroupResponse":
        return cls(
            id=g.id, name=g.name, description=g.description,
            color=g.color, project_id=g.project_id, sort_order=g.sort_order,
            created_at=g.created_at, modified_at=g.modified_at,
            tags=[TagResponse.from_entity(t) for t in g.tags],
        )


# ---------------------------------------------------------------------------
# TodoItems
# ---------------------------------------------------------------------------

class TodoCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    completed: bool = False
    order: int | None = None


class TodoUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    completed: bool | None = None
    order: int | None = None


class TodoResponse(BaseModel):
    id: int
    task_id: int
    title: str
    completed: bool
    order: int
    created_at: datetime | None = None
    modified_at: datetime | None = None

    @classmethod
    def from_entity(cls, t: TodoItem) -> "TodoResponse":
        return cls(
            id=t.id, task_id=t.task_id, title=t.title,
            completed=t.completed, order=t.order,
            created_at=t.created_at, modified_at=t.modified_at,
        )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class TaskCreate(BaseModel):
    group_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = None
    completed: bool = False
    user_id: int | None = None
    priority_id: int | None = None
    estimated_duration: float | None = Field(default=None, ge=0)
    estimated_start: datetime | None = None
    estimated_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    sort_order: int | None = None


class TaskUpdate(BaseModel):
    group_id: int | None = None
    user_id: int | None = None
    priority_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    completed: bool | None = None
    estimated_duration: float | None = Field(default=None, ge=0)
    estimated_start: datetime | None = None
    estimated_end: datetime | None = None
    actual_start: datetime | None = None
    actual_end: datetime | None = None
    sort_order: int | None = None


class TaskReorderRequest(BaseModel):
    task_ids: list[int]

    _unique = field_validator("task_ids")(_unique_ids)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, v: str) -> str:
        return v.lower()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ---------------------------------------------------------------------------
# Project with role
# ---------------------------------------------------------------------------

class ProjectRoleResponse(BaseModel):
    role: str  # "owner" | "leader" | "member"


class ProjectWithRoleResponse(ProjectResponse):
    role: str

    @classmethod
    def from_entity_and_role(cls, p: Project, role: str) -> "ProjectWithRoleResponse":
        base = ProjectResponse.from_entity(p)
        return cls(**base.model_dump(), role=role)


class TaskResponse(BaseModel):
    id: int
    group_id: int
    title: str
    description: str | None
    completed: bool
    sort_order: int = 0
    user: UserResponse | None = None
    priority: PriorityResponse | None = None
    estimated_duration: float | None
    estimated_start: datetime | None
    estimated_end: datetime | None
    actual_start: datetime | None
    actual_end: datetime | None
    created_at: datetime
    modified_at: datetime | None = None
    tags: list[TagResponse] = []
    todos_total: int = 0
    todos_completed: int = 0

    @classmethod
    def from_entity(cls, t: Task) -> "TaskResponse":
        return cls(
            id=t.id, group_id=t.group_id, title=t.title, description=t.description,
            completed=t.completed, sort_order=t.sort_order,
            user=UserResponse.from_entity(t.user) if t.user else None,
            priority=PriorityResponse.from_entity(t.priority) if t.priority else None,
            estimated_duration=t.estimated_duration,
            estimated_start=t.estimated_start, estimated_end=t.estimated_end,
            actual_start=t.actual_start, actual_end=t.actual_end,
            created_at=t.created_at, modified_at=t.modified_at,
            tags=[TagResponse.from_entity(tag) for tag in t.tags],
            todos_total=t.todos_total,
            todos_completed=t.todos_completed,
        )
