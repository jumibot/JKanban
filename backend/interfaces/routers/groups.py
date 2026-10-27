from fastapi import APIRouter, Depends, HTTPException
from backend.application.group_use_cases import GroupUseCases
from backend.application.task_use_cases import TaskUseCases
from backend.domain.entities import User
from backend.domain.exceptions import GroupNotFound, ProjectNotFound, TaskNotFound
from backend.interfaces.dependencies import (
    get_current_user, get_group_use_cases, get_task_use_cases,
    get_user_project_ids, require_project_access,
)
from backend.interfaces.schemas import GroupCreate, GroupReorderRequest, GroupResponse, GroupUpdate, TaskReorderRequest, TaskResponse

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/", response_model=list[GroupResponse])
def list_groups(
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
):
    user_pids = get_user_project_ids(current_user.id)
    return [
        GroupResponse.from_entity(g) for g in use_cases.get_all()
        if g.project_id in user_pids
    ]


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
):
    try:
        group = use_cases.get_by_id(group_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
    require_project_access(group.project_id, current_user.id)
    return GroupResponse.from_entity(group)


@router.get("/{group_id}/tasks", response_model=list[TaskResponse])
def list_group_tasks(
    group_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
):
    try:
        group = use_cases.get_by_id(group_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
    require_project_access(group.project_id, current_user.id)
    return [TaskResponse.from_entity(t) for t in use_cases.get_tasks(group_id)]


@router.patch("/reorder", status_code=204)
def reorder_groups(
    body: GroupReorderRequest,
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
):
    require_project_access(body.project_id, current_user.id)
    try:
        use_cases.reorder_in_project(body.project_id, body.group_ids)
    except GroupNotFound as exc:
        raise HTTPException(
            status_code=404, detail=f"Group {exc.group_id} not found in project {body.project_id}")


@router.patch("/{group_id}/tasks/reorder", status_code=204)
def reorder_group_tasks(
    group_id: int,
    body: TaskReorderRequest,
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
    task_use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    try:
        group = use_cases.get_by_id(group_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
    require_project_access(group.project_id, current_user.id)
    try:
        task_use_cases.reorder_in_group(group_id, body.task_ids)
    except TaskNotFound as exc:
        raise HTTPException(
            status_code=404, detail=f"Task {exc.task_id} not found in group {group_id}")


@router.post("/", response_model=GroupResponse, status_code=201)
def create_group(
    body: GroupCreate,
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
):
    require_project_access(body.project_id, current_user.id)
    try:
        return GroupResponse.from_entity(
            use_cases.create(
                name=body.name, description=body.description,
                color=body.color, project_id=body.project_id,
                sort_order=body.sort_order,
            )
        )
    except ProjectNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(
    group_id: int,
    body: GroupUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    try:
        group = use_cases.get_by_id(group_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
    require_project_access(group.project_id, current_user.id)
    try:
        return GroupResponse.from_entity(use_cases.update(group_id, updates))
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")


@router.delete("/{group_id}", status_code=204)
def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: GroupUseCases = Depends(get_group_use_cases),
):
    try:
        group = use_cases.get_by_id(group_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
    require_project_access(group.project_id, current_user.id)
    try:
        use_cases.delete(group_id)
    except GroupNotFound:
        raise HTTPException(status_code=404, detail="Group not found")
