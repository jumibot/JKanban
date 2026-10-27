from abc import ABC, abstractmethod
from backend.domain.entities import (
    Flow, FlowState, FlowStateChange, Group, Priority, Project, ProjectContentCounts, Tag, Task,
    TodoItem, User,
)


class UserRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[User]: ...

    @abstractmethod
    def get_by_id(self, user_id: int) -> User | None: ...

    @abstractmethod
    def get_by_email(self, email: str) -> User | None: ...

    @abstractmethod
    def create(self, user: User) -> User: ...

    @abstractmethod
    def update(self, user: User) -> User: ...

    @abstractmethod
    def delete(self, user_id: int) -> None: ...

    @abstractmethod
    def count_owned_projects(self, user_id: int) -> int: ...

    @abstractmethod
    def delete_with_owned_projects(self, user_id: int) -> None:
        """Atomically delete the user and every project they own (with all its data)."""


class PriorityRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Priority]: ...

    @abstractmethod
    def get_by_project(self, project_id: int) -> list[Priority]: ...

    @abstractmethod
    def get_by_id(self, priority_id: int) -> Priority | None: ...

    @abstractmethod
    def create(self, priority: Priority) -> Priority: ...

    @abstractmethod
    def update(self, priority: Priority) -> Priority: ...

    @abstractmethod
    def delete(self, priority_id: int) -> None: ...


class ProjectRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Project]: ...

    @abstractmethod
    def get_by_id(self, project_id: int) -> Project | None: ...

    @abstractmethod
    def create(self, project: Project) -> Project: ...

    @abstractmethod
    def update(self, project: Project) -> Project: ...

    @abstractmethod
    def delete(self, project_id: int) -> None:
        """Delete the project; dependent data (groups, tasks, tags…) goes with it."""

    @abstractmethod
    def get_owned_by(self, owner_id: int) -> list[Project]: ...

    @abstractmethod
    def count_contents(self, project_id: int) -> ProjectContentCounts: ...

    @abstractmethod
    def get_members(self, project_id: int) -> list[User]: ...

    @abstractmethod
    def add_member(self, project_id: int, user_id: int) -> None: ...

    @abstractmethod
    def remove_member(self, project_id: int, user_id: int) -> None: ...

    @abstractmethod
    def is_member(self, project_id: int, user_id: int) -> bool: ...

    @abstractmethod
    def get_projects_for_user(self, user_id: int) -> list[Project]: ...


class GroupRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Group]: ...

    @abstractmethod
    def get_by_id(self, group_id: int) -> Group | None: ...

    @abstractmethod
    def count_by_project(self, project_id: int) -> int: ...

    @abstractmethod
    def create(self, group: Group) -> Group: ...

    @abstractmethod
    def update(self, group: Group) -> Group: ...

    @abstractmethod
    def delete(self, group_id: int) -> None: ...

    @abstractmethod
    def reorder(self, group_ids: list[int]) -> None: ...


class TaskRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Task]: ...

    @abstractmethod
    def get_by_id(self, task_id: int) -> Task | None: ...

    @abstractmethod
    def get_by_group(self, group_id: int) -> list[Task]: ...

    @abstractmethod
    def count_by_group(self, group_id: int) -> int: ...

    @abstractmethod
    def create(self, task: Task) -> Task: ...

    @abstractmethod
    def update(self, task: Task) -> Task: ...

    @abstractmethod
    def delete(self, task_id: int) -> None: ...

    @abstractmethod
    def reorder(self, task_ids: list[int]) -> None: ...


class TodoRepository(ABC):
    @abstractmethod
    def get_by_task(self, task_id: int) -> list[TodoItem]: ...

    @abstractmethod
    def get_by_id(self, todo_id: int) -> TodoItem | None: ...

    @abstractmethod
    def create(self, todo: TodoItem) -> TodoItem: ...

    @abstractmethod
    def update(self, todo: TodoItem) -> TodoItem: ...

    @abstractmethod
    def delete(self, todo_id: int) -> None: ...


class TagRepository(ABC):
    """Tags and their assignment to tasks/groups.

    `kind` is "task" or "group". Writes that change a flow state take the
    FlowStateChange to log, so assignment and log are saved together.
    """
    @abstractmethod
    def get_all(self) -> list[Tag]: ...

    @abstractmethod
    def get_global(self) -> list[Tag]: ...

    @abstractmethod
    def get_by_project(self, project_id: int) -> list[Tag]:
        """Only the project's own tags (not the global ones)."""

    @abstractmethod
    def get_by_id(self, tag_id: int) -> Tag | None: ...

    @abstractmethod
    def get_by_flow(self, flow_id: int) -> list[Tag]: ...

    @abstractmethod
    def create(self, tag: Tag) -> Tag: ...

    @abstractmethod
    def update(self, tag: Tag) -> Tag: ...

    @abstractmethod
    def delete(self, tag_id: int) -> None: ...

    @abstractmethod
    def count_assignments(self, tag_id: int) -> int: ...

    @abstractmethod
    def get_assignment(self, kind: str, item_id: int, tag_id: int) -> Tag | None:
        """The tag as assigned to the item (with state_*), or None."""

    @abstractmethod
    def assign(self, kind: str, item_id: int, tag_id: int, state_id: int | None,
               user_id: int | None, change: FlowStateChange | None) -> None: ...

    @abstractmethod
    def unassign(self, kind: str, item_id: int, tag_id: int,
                 change: FlowStateChange | None) -> None: ...

    @abstractmethod
    def set_state(self, kind: str, item_id: int, tag_id: int, state_id: int,
                  change: FlowStateChange) -> None: ...

    @abstractmethod
    def get_history(self, kind: str, item_id: int, tag_id: int) -> list[FlowStateChange]: ...


class FlowRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[Flow]: ...

    @abstractmethod
    def get_global(self) -> list[Flow]: ...

    @abstractmethod
    def get_by_project(self, project_id: int) -> list[Flow]:
        """Only the project's own flows (not the global ones)."""

    @abstractmethod
    def get_by_id(self, flow_id: int) -> Flow | None: ...

    @abstractmethod
    def create(self, flow: Flow, transitions: list[tuple[int, int]]) -> Flow:
        """Create flow + flow.states; transitions are (from, to) indexes into flow.states."""

    @abstractmethod
    def rename(self, flow_id: int, name: str, user_id: int | None) -> None: ...

    @abstractmethod
    def delete(self, flow_id: int) -> None: ...

    @abstractmethod
    def add_state(self, flow_id: int, state: FlowState, user_id: int | None) -> FlowState: ...

    @abstractmethod
    def update_state(self, state: FlowState, user_id: int | None) -> None:
        """Save name, color, sort_order; if is_initial, it becomes the only initial."""

    @abstractmethod
    def delete_state(self, flow_id: int, state_id: int, user_id: int | None) -> None:
        """Delete the state and its transitions."""

    @abstractmethod
    def add_transition(self, flow_id: int, from_state_id: int, to_state_id: int,
                       user_id: int | None) -> None: ...

    @abstractmethod
    def delete_transition(self, flow_id: int, from_state_id: int, to_state_id: int,
                          user_id: int | None) -> None: ...

    @abstractmethod
    def state_usage(self, state_id: int) -> tuple[list[int], list[int]]:
        """(task ids, group ids) whose tag is now in this state."""
