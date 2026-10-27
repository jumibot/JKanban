import os
from datetime import datetime, timedelta, timezone

import jwt

_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production-32b")
_ALGORITHM = "HS256"
_EXPIRE_DAYS = 7


def create_access_token(user_id: int) -> str:
    exp = datetime.now(timezone.utc) + timedelta(days=_EXPIRE_DAYS)
    return jwt.encode({"sub": str(user_id), "exp": exp}, _SECRET, algorithm=_ALGORITHM)


def decode_access_token(token: str) -> int:
    """Decode token and return user_id. Raises ValueError on invalid/expired token."""
    try:
        payload = jwt.decode(token, _SECRET, algorithms=[_ALGORITHM])
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise ValueError("Invalid or expired token") from exc
