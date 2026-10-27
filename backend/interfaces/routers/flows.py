"""Flows: global (/flows/, managed by the admin) or per project
(/projects/{pid}/flows/, managed by its owner or leader).

Viewing a global flow needs only authentication; a project flow, access to
its project. /flows/{id} and its states/transitions work for both scopes.
"""
from contextlib import contextmanager

from fastapi import APIRouter, Depends, HTTPException

from backend.application.flow_use_cases import FlowUseCases
from backend.domain.entities import Flow, User
from backend.domain.exceptions import (
    FlowInUse, FlowNameAlreadyExists, FlowNotFound, FlowStateInUse, FlowStateNotFound,
    FlowTransitionNotFound, InvalidFlowDefinition,
)
from backend.interfaces.dependencies import (
    get_current_user, get_flow_use_cases, require_admin, require_project_access,
    require_project_leader,
)
from backend.interfaces.schemas import (
    FlowCreate, FlowResponse, FlowStateCreate, FlowStateUpdate, FlowTransitionCreate, FlowUpdate,
)

router = APIRouter(tags=["flows"])


@contextmanager
def _http_errors():
    try:
        yield
    except (FlowNotFound, FlowStateNotFound, FlowTransitionNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidFlowDefinition as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (FlowNameAlreadyExists, FlowInUse, FlowStateInUse) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


def _flow(use_cases: FlowUseCases, flow_id: int) -> Flow:
    with _http_errors():
        return use_cases.get(flow_id)


def _can_view(flow: Flow, user: User) -> None:
    if flow.project_id is not None:
        require_project_access(flow.project_id, user.id)


def _can_manage(flow: Flow, user: User) -> None:
    if flow.project_id is None:
        require_admin(user)
    else:
        require_project_leader(flow.project_id, user.id)


def _create(use_cases: FlowUseCases, body: FlowCreate, project_id: int | None, user: User) -> FlowResponse:
    with _http_errors():
        flow = use_cases.create(
            name=body.name,
            states=[(s.name, s.color) for s in body.states],
            initial=body.initial,
            transitions=[(t.from_, t.to) for t in body.transitions],
            project_id=project_id,
            user_id=user.id,
        )
    return FlowResponse.from_entity(flow)


# ── Collections ───────────────────────────────────────────────────────────────

@router.get("/flows/", response_model=list[FlowResponse])
def list_global_flows(
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    return [FlowResponse.from_entity(f) for f in use_cases.list_global()]


@router.post("/flows/", response_model=FlowResponse, status_code=201)
def create_global_flow(
    body: FlowCreate,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    require_admin(current_user)
    return _create(use_cases, body, None, current_user)


@router.get("/projects/{project_id}/flows/", response_model=list[FlowResponse])
def list_project_flows(
    project_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    """Global flows first, then the project's own."""
    require_project_access(project_id, current_user.id)
    return [FlowResponse.from_entity(f) for f in use_cases.list_for_project(project_id)]


@router.post("/projects/{project_id}/flows/", response_model=FlowResponse, status_code=201)
def create_project_flow(
    project_id: int,
    body: FlowCreate,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    require_project_leader(project_id, current_user.id)
    return _create(use_cases, body, project_id, current_user)


# ── One flow ──────────────────────────────────────────────────────────────────

@router.get("/flows/{flow_id}", response_model=FlowResponse)
def get_flow(
    flow_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    flow = _flow(use_cases, flow_id)
    _can_view(flow, current_user)
    return FlowResponse.from_entity(flow)


@router.patch("/flows/{flow_id}", response_model=FlowResponse)
def rename_flow(
    flow_id: int,
    body: FlowUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    _can_manage(_flow(use_cases, flow_id), current_user)
    with _http_errors():
        return FlowResponse.from_entity(use_cases.rename(flow_id, body.name, current_user.id))


@router.delete("/flows/{flow_id}", status_code=204)
def delete_flow(
    flow_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    _can_manage(_flow(use_cases, flow_id), current_user)
    with _http_errors():
        use_cases.delete(flow_id)


# ── States ────────────────────────────────────────────────────────────────────

@router.post("/flows/{flow_id}/states", response_model=FlowResponse, status_code=201)
def add_state(
    flow_id: int,
    body: FlowStateCreate,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    _can_manage(_flow(use_cases, flow_id), current_user)
    with _http_errors():
        flow = use_cases.add_state(flow_id, body.name, body.color, body.is_initial, current_user.id)
    return FlowResponse.from_entity(flow)


@router.patch("/flows/{flow_id}/states/{state_id}", response_model=FlowResponse)
def update_state(
    flow_id: int,
    state_id: int,
    body: FlowStateUpdate,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    updates = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")
    _can_manage(_flow(use_cases, flow_id), current_user)
    with _http_errors():
        flow = use_cases.update_state(flow_id, state_id, updates, current_user.id)
    return FlowResponse.from_entity(flow)


@router.delete("/flows/{flow_id}/states/{state_id}", status_code=204)
def delete_state(
    flow_id: int,
    state_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    _can_manage(_flow(use_cases, flow_id), current_user)
    with _http_errors():
        use_cases.delete_state(flow_id, state_id, current_user.id)


# ── Transitions ───────────────────────────────────────────────────────────────

@router.post("/flows/{flow_id}/transitions", response_model=FlowResponse, status_code=201)
def add_transition(
    flow_id: int,
    body: FlowTransitionCreate,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    _can_manage(_flow(use_cases, flow_id), current_user)
    with _http_errors():
        flow = use_cases.add_transition(flow_id, body.from_state_id, body.to_state_id, current_user.id)
    return FlowResponse.from_entity(flow)


@router.delete("/flows/{flow_id}/transitions/{from_state_id}/{to_state_id}", status_code=204)
def delete_transition(
    flow_id: int,
    from_state_id: int,
    to_state_id: int,
    current_user: User = Depends(get_current_user),
    use_cases: FlowUseCases = Depends(get_flow_use_cases),
):
    _can_manage(_flow(use_cases, flow_id), current_user)
    with _http_errors():
        use_cases.delete_transition(flow_id, from_state_id, to_state_id, current_user.id)
