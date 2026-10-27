"""Cliente HTTP mínimo de la API REST de JKanban."""
from __future__ import annotations

from typing import Any

import httpx


class JKanbanError(Exception):
    """Error devuelto por la API (o de conexión con ella)."""

    def __init__(self, status: int | None, detail: Any):
        self.status = status
        self.detail = detail
        prefix = f"HTTP {status}" if status is not None else "Sin conexión"
        super().__init__(f"{prefix}: {detail}")


class JKanbanClient:
    """Habla con la API de JKanban como un usuario concreto.

    Inicia sesión la primera vez que hace falta y repite la petición una vez
    si el token caduca (401). `http` permite inyectar otro cliente httpx,
    por ejemplo el `TestClient` de FastAPI en los tests.
    """

    def __init__(self, base_url: str, email: str, password: str,
                 http: httpx.Client | None = None, timeout: float = 15.0):
        self._email = email
        self._password = password
        self._http = http or httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)
        self._token: str | None = None
        self.user: dict | None = None

    # ── Sesión ────────────────────────────────────────────────────────────

    def login(self) -> dict:
        data = self._send("POST", "/auth/login",
                          json={"email": self._email, "password": self._password},
                          authenticated=False)
        self._token = data["access_token"]
        self.user = data["user"]
        return self.user

    # ── Verbos ────────────────────────────────────────────────────────────

    def get(self, path: str) -> Any:
        return self._request("GET", path)

    def post(self, path: str, json: dict | None = None) -> Any:
        return self._request("POST", path, json=json)

    def patch(self, path: str, json: dict | None = None) -> Any:
        return self._request("PATCH", path, json=json)

    def delete(self, path: str) -> None:
        self._request("DELETE", path)

    # ── Internos ──────────────────────────────────────────────────────────

    def _request(self, method: str, path: str, json: dict | None = None) -> Any:
        if self._token is None:
            self.login()
        try:
            return self._send(method, path, json=json)
        except JKanbanError as e:
            if e.status != 401:
                raise
            self.login()
            return self._send(method, path, json=json)

    def _send(self, method: str, path: str, json: dict | None = None,
              authenticated: bool = True) -> Any:
        headers = {"Authorization": f"Bearer {self._token}"} if authenticated else {}
        try:
            r = self._http.request(method, path, json=json, headers=headers)
        except httpx.HTTPError as e:
            raise JKanbanError(None, f"no se pudo contactar con JKanban ({e})") from e
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise JKanbanError(r.status_code, detail)
        if r.status_code == 204 or not r.content:
            return None
        return r.json()
