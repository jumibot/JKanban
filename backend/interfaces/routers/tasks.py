from fastapi import APIRouter, Depends, HTTPException
from backend.application.task_use_cases import TaskUseCases
from backend.domain.entities import User
from backend.domain.exceptions import (
    GroupNotFound, PriorityNotFound, PriorityNotInProject, TaskNotFound, UserNotFound,
)
from backend.interfaces.dependencies import (
    get_current_user, get_group_use_cases, get_task_use_cases,
    get_user_project_ids, require_project_access,
)
from backend.interfaces.schemas import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _group_project_id(group_id: int) -> int | None:
    """Returns the project_id of a group, or None if group has no project or doesn't exist."""
    from backend.application.group_use_cases import GroupUseCases
    from backend.infrastructure.repositories.group_repository import SqlGroupRepository
    from backend.infrastructure.repositories.project_repository import SqlProjectRepository
    from backend.infrastructure.repositories.task_repository import SqlTaskRepository
    uc = GroupUseCases(
        group_repo=SqlGroupRepository(),
        task_repo=SqlTaskRepository(),
        project_repo=SqlProjectRepository(),
    )
    try:
        return uc.get_by_id(group_id).project_id
    except GroupNotFound:
        return None


@router.get("/", response_model=list[TaskResponse])
def list_tasks(
    current_user: User = Depends(get_current_user),
    use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    from backend.application.group_use_cases import GroupUseCases
    from backend.interfaces.dependencies import get_group_use_cases
    user_pids = get_user_project_ids(current_user.id)
    group_uc = get_group_use_cases()
    accessible_gids = {
        g.id for g in group_uc.get_all()
        if g.project_id is None or g.project_id in user_pids
    }
    return [
        TaskResponse.from_entity(t) for t in use_cases.get_all()
        if t.group_id in accessible_gids
    ]


@router.get("/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    try:
        task = use_cases.get_by_id(task_id)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    require_project_access(_group_project_id(task.group_id), current_user.id)
    return TaskResponse.from_entity(task)


@router.post("/", response_model=TaskResponse, status_code=201)
def create_task(
    body: TaskCreate,
    current_user: User = Depends(get_current_user),
    use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    require_project_access(_group_project_id(body.group_id), current_user.id)
    try:
        task = use_cases.create(
            group_id=body.group_id, title=body.title, description=body.description,
            completed=body.completed, user_id=body.user_id,
            priority_id=body.priority_id,
            estimated_duration=body.estimated_duration,
            estimated_start=body.estimated_start, estimated_end=body.estimated_end,
            actual_start=body.actual_start, actual_end=body.actual_end,
            sort_order=body.sort_order,
        )
        return TaskResponse.from_entity(task)
    except GroupNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Group {exc.group_id} not found")
    except UserNotFound as exc:
        raise HTTPException(status_code=404, detail=f"User {exc.user_id} not found")
    except PriorityNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Priority {exc.priority_id} not found")
    except PriorityNotInProject as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.patch("/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: int,
    body: TaskUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    try:
        task = use_cases.get_by_id(task_id)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    src_project = _group_project_id(task.group_id)
    require_project_access(src_project, current_user.id)
    if "group_id" in updates and updates["group_id"] != task.group_id:
        target_project = _group_project_id(updates["group_id"])
        if target_project is not None and target_project != src_project:
            raise HTTPException(
                status_code=400,
                detail="No se puede mover una tarea a un grupo de otro proyecto",
            )
    try:
        return TaskResponse.from_entity(use_cases.update(task_id, updates))
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    except GroupNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Group {exc.group_id} not found")
    except UserNotFound as exc:
        raise HTTPException(status_code=404, detail=f"User {exc.user_id} not found")
    except PriorityNotFound as exc:
        raise HTTPException(status_code=404, detail=f"Priority {exc.priority_id} not found")
    except PriorityNotInProject as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{task_id}", status_code=204)
def delete_task(
    task_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    try:
        task = use_cases.get_by_id(task_id)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
    require_project_access(_group_project_id(task.group_id), current_user.id)
    try:
        use_cases.delete(task_id)
    except TaskNotFound:
        raise HTTPException(status_code=404, detail="Task not found")
