import hashlib
import hmac
import secrets

from backend.domain.entities import User
from backend.domain.exceptions import EmailAlreadyExists, InvalidCredentials, UserNotFound, UserOwnsProjects
from backend.domain.repositories import UserRepository


def hash_password(plain: str) -> str:
    """PBKDF2-SHA256 con salt aleatorio. Formato: pbkdf2$<salt>$<hex>"""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return f"pbkdf2${salt}${h.hex()}"


def verify_password(plain: str, stored_hash: str) -> bool:
    parts = stored_hash.split("$")
    if len(parts) != 3 or parts[0] != "pbkdf2":
        return False
    _, salt, stored_hex = parts
    h = hashlib.pbkdf2_hmac("sha256", plain.encode(), salt.encode(), 100_000)
    return hmac.compare_digest(h.hex(), stored_hex)


class UserUseCases:
    def __init__(self, user_repo: UserRepository):
        self._users = user_repo

    def get_all(self) -> list[User]:
        return self._users.get_all()

    def get_by_id(self, user_id: int) -> User:
        user = self._users.get_by_id(user_id)
        if user is None:
            raise UserNotFound(user_id)
        return user

    def create(self, name: str, email: str, password: str, avatar_url: str | None) -> User:
        if self._users.get_by_email(email) is not None:
            raise EmailAlreadyExists(email)
        return self._users.create(
            User(name=name, email=email, password_hash=hash_password(password), avatar_url=avatar_url)
        )

    def update(self, user_id: int, updates: dict) -> User:
        user = self.get_by_id(user_id)
        if "email" in updates:
            existing = self._users.get_by_email(updates["email"])
            if existing is not None and existing.id != user_id:
                raise EmailAlreadyExists(updates["email"])
        if "password" in updates:
            updates = {**updates, "password_hash": hash_password(updates.pop("password"))}
        for key, value in updates.items():
            setattr(user, key, value)
        return self._users.update(user)

    def login(self, email: str, password: str) -> User:
        user = self._users.get_by_email(email.lower())
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentials()
        return user

    def delete(self, user_id: int) -> None:
        self.get_by_id(user_id)
        count = self._users.count_owned_projects(user_id)
        if count > 0:
            raise UserOwnsProjects(user_id, count)
        self._users.delete(user_id)

    def delete_cascade(self, user_id: int) -> None:
        """Delete the user together with every project they own."""
        self.get_by_id(user_id)
        self._users.delete_with_owned_projects(user_id)
