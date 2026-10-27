"""Tags: global (/tags/, managed by the admin) or per project
(/projects/{pid}/tags/, managed by its owner or leader; its GET also lists the
global ones). Assignment to tasks/groups, flow state and its history.
"""
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException

from backend.application.tag_use_cases import TagUseCases
from backend.domain.entities import Tag, User
from backend.domain.exceptions import (
    FlowInUse, FlowNotFound, FlowNotInScope, FlowStateNotFound, GroupNotFound,
    InvalidFlowTransition, TagHasNoFlow, TagNameAlreadyExists, TagNotAssigned, TagNotFound,
    TagNotInProject, TaskNotFound,
)
from backend.interfaces.dependencies import (
    get_current_user, get_tag_use_cases, require_admin, require_project_access,
    require_project_leader,
)
from backend.interfaces.schemas import (
    FlowStateChangeResponse, TagCreate, TagResponse, TagStateUpdate, TagUpdate,
)


@contextmanager
def _http_errors():
    try:
        yield
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
    except TagNotFound:
        raise HTTPException(status_code=404, detail="Tag not found")
    except (TagNotAssigned, FlowNotFound, FlowStateNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except (TagNotInProject, FlowNotInScope, TagHasNoFlow) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (TagNameAlreadyExists, FlowInUse, InvalidFlowTransition) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


def _tag(use_cases: TagUseCases, tag_id: int) -> Tag:
    with _http_errors():
        return use_cases.get_by_id(tag_id)


def _updates(body: TagUpdate) -> dict:
    updates = body.model_dump(exclude_unset=True)
    # name/color null mean "no change"; flow_id null means "remove the flow".
    updates = {k: v for k, v in updates.items() if v is not None or k == "flow_id"}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    return updates


# ── Project tags ──────────────────────────────────────────────────────────────
router = APIRouter(prefix="/projects/{project_id}/tags", tags=["tags"])


@router.get("/", response_model=list[TagResponse])
def list_tags(
    project_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    """Global tags first, then the project's own."""
    require_project_access(project_id, current_user.id)
    return [TagResponse.from_entity(t) for t in use_cases.get_by_project(project_id)]


@router.get("/{tag_id}", response_model=TagResponse)
def get_tag(
    project_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_project_access(project_id, current_user.id)
    tag = _tag(use_cases, tag_id)
    if tag.project_id not in (project_id, None):
        raise HTTPException(status_code=404, detail="Tag not found")
    return TagResponse.from_entity(tag)


@router.post("/", response_model=TagResponse, status_code=201)
def create_tag(
    project_id: int,
    body: TagCreate,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_project_leader(project_id, current_user.id)
    with _http_errors():
        tag = use_cases.create(body.name, body.color, project_id, body.flow_id, current_user.id)
    return TagResponse.from_entity(tag)


def _own_project_tag(use_cases: TagUseCases, project_id: int, tag_id: int) -> Tag:
    tag = _tag(use_cases, tag_id)
    if tag.project_id != project_id:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.patch("/{tag_id}", response_model=TagResponse)
def update_tag(
    project_id: int,
    tag_id: int,
    body: TagUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    updates = _updates(body)
    require_project_leader(project_id, current_user.id)
    _own_project_tag(use_cases, project_id, tag_id)
    with _http_errors():
        return TagResponse.from_entity(use_cases.update(tag_id, updates, current_user.id))


@router.delete("/{tag_id}", status_code=204)
def delete_tag(
    project_id: int,
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_project_leader(project_id, current_user.id)
    _own_project_tag(use_cases, project_id, tag_id)
    use_cases.delete(tag_id)


# ── Global tags ───────────────────────────────────────────────────────────────
global_router = APIRouter(prefix="/tags", tags=["tags"])


def _global_tag(use_cases: TagUseCases, tag_id: int) -> Tag:
    tag = _tag(use_cases, tag_id)
    if tag.project_id is not None:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@global_router.get("/", response_model=list[TagResponse])
def list_global_tags(
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    return [TagResponse.from_entity(t) for t in use_cases.get_global()]


@global_router.get("/{tag_id}", response_model=TagResponse)
def get_global_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    return TagResponse.from_entity(_global_tag(use_cases, tag_id))


@global_router.post("/", response_model=TagResponse, status_code=201)
def create_global_tag(
    body: TagCreate,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_admin(current_user)
    with _http_errors():
        tag = use_cases.create(body.name, body.color, None, body.flow_id, current_user.id)
    return TagResponse.from_entity(tag)


@global_router.patch("/{tag_id}", response_model=TagResponse)
def update_global_tag(
    tag_id: int,
    body: TagUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    updates = _updates(body)
    require_admin(current_user)
    _global_tag(use_cases, tag_id)
    with _http_errors():
        return TagResponse.from_entity(use_cases.update(tag_id, updates, current_user.id))


@global_router.delete("/{tag_id}", status_code=204)
def delete_global_tag(
    tag_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TagUseCases = Depends(get_tag_use_cases),
):
    require_admin(current_user)
    _global_tag(use_cases, tag_id)
    use_cases.delete(tag_id)


# ── Assignment, state and history (tasks and groups) ──────────────────────────
assign_router = APIRouter(tags=["tag-assignments"])


def _check_item_access(use_cases: TagUseCases, kind: str, item_id: int, user: User) -> None:
    with _http_errors():
        project_id = use_cases.item_project_id(kind, item_id)
    require_project_access(project_id, user.id)


def _assign(kind, item_id, tag_id, user, use_cases):
    _check_item_access(use_cases, kind, item_id, user)
    with _http_errors():
        use_cases.assign(kind, item_id, tag_id, user.id)


def _unassign(kind, item_id, tag_id, user, use_cases):
    _check_item_access(use_cases, kind, item_id, user)
    with _http_errors():
        use_cases.unassign(kind, item_id, tag_id, user.id)


def _set_state(kind, item_id, tag_id, body, user, use_cases) -> TagResponse:
    _check_item_access(use_cases, kind, item_id, user)
    with _http_errors():
        tag = use_cases.set_state(kind, item_id, tag_id, body.state_id, body.note, user.id)
    return TagResponse.from_entity(tag)


def _history(kind, item_id, tag_id, user, use_cases) -> list[FlowStateChangeResponse]:
    _check_item_access(use_cases, kind, item_id, user)
    with _http_errors():
        changes = use_cases.history(kind, item_id, tag_id)
    return [FlowStateChangeResponse.from_entity(c) for c in changes]


@assign_router.post("/tasks/{task_id}/tags/{tag_id}", status_code=204)
def assign_tag_to_task(task_id: int, tag_id: int,
                       current_user: User = Depends(get_current_user),
                       use_cases: TagUseCases = Depends(get_tag_use_cases)):
    """With a flow, the task enters the flow's initial state."""
    _assign("task", task_id, tag_id, current_user, use_cases)


@assign_router.delete("/tasks/{task_id}/tags/{tag_id}", status_code=204)
def unassign_tag_from_task(task_id: int, tag_id: int,
                           current_user: User = Depends(get_current_user),
                           use_cases: TagUseCases = Depends(get_tag_use_cases)):
    _unassign("task", task_id, tag_id, current_user, use_cases)


@assign_router.patch("/tasks/{task_id}/tags/{tag_id}/state", response_model=TagResponse)
def set_task_tag_state(task_id: int, tag_id: int, body: TagStateUpdate,
                       current_user: User = Depends(get_current_user),
                       use_cases: TagUseCases = Depends(get_tag_use_cases)):
    return _set_state("task", task_id, tag_id, body, current_user, use_cases)


@assign_router.get("/tasks/{task_id}/tags/{tag_id}/history",
                   response_model=list[FlowStateChangeResponse])
def task_tag_history(task_id: int, tag_id: int,
                     current_user: User = Depends(get_current_user),
                     use_cases: TagUseCases = Depends(get_tag_use_cases)):
    return _history("task", task_id, tag_id, current_user, use_cases)


@assign_router.post("/groups/{group_id}/tags/{tag_id}", status_code=204)
def assign_tag_to_group(group_id: int, tag_id: int,
                        current_user: User = Depends(get_current_user),
                        use_cases: TagUseCases = Depends(get_tag_use_cases)):
    """With a flow, the group enters the flow's initial state."""
    _assign("group", group_id, tag_id, current_user, use_cases)


@assign_router.delete("/groups/{group_id}/tags/{tag_id}", status_code=204)
def unassign_tag_from_group(group_id: int, tag_id: int,
                            current_user: User = Depends(get_current_user),
                            use_cases: TagUseCases = Depends(get_tag_use_cases)):
    _unassign("group", group_id, tag_id, current_user, use_cases)


@assign_router.patch("/groups/{group_id}/tags/{tag_id}/state", response_model=TagResponse)
def set_group_tag_state(group_id: int, tag_id: int, body: TagStateUpdate,
                        current_user: User = Depends(get_current_user),
                        use_cases: TagUseCases = Depends(get_tag_use_cases)):
    return _set_state("group", group_id, tag_id, body, current_user, use_cases)


@assign_router.get("/groups/{group_id}/tags/{tag_id}/history",
                   response_model=list[FlowStateChangeResponse])
def group_tag_history(group_id: int, tag_id: int,
                      current_user: User = Depends(get_current_user),
                      use_cases: TagUseCases = Depends(get_tag_use_cases)):
    return _history("group", group_id, tag_id, current_user, use_cases)
