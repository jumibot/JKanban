from fastapi import APIRouter, HTTPException
from backend.application.user_use_cases import UserUseCases
from backend.domain.exceptions import InvalidCredentials
from backend.infrastructure.jwt_handler import create_access_token
from backend.infrastructure.repositories.user_repository import SqlUserRepository
from backend.interfaces.schemas import LoginRequest, LoginResponse, UserResponse

router = APIRouter(prefix="/auth", tags=["auth"])


def _use_cases() -> UserUseCases:
    return UserUseCases(user_repo=SqlUserRepository())


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest):
    try:
        user = _use_cases().login(email=body.email, password=body.password)
        return LoginResponse(
            access_token=create_access_token(user.id),
            token_type="bearer",
            user=UserResponse.from_entity(user),
        )
    except InvalidCredentials as exc:
        raise HTTPException(status_code=401, detail=str(exc))
