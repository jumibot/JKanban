"""Crea el primer administrador de JKanban (o convierte en administrador a un usuario).

Uso:
    python -m backend.create_admin --email admin@example.com --name "Admin" --password "…"

- Si el email no existe, crea el usuario como administrador (requiere --name).
- Si existe, lo convierte en administrador; con contraseña, además la fija.
- La contraseña se toma de --password, de la variable JKANBAN_ADMIN_PASSWORD o,
  si no hay ninguna y la consola es interactiva, se pide sin mostrarla.
- Usa la misma base de datos que la app (SQLITE_PATH) y la crea si no existe.
  Respeta JKANBAN_DEMO_DATA: con 0, una base de datos nueva queda vacía.

Pasa por los casos de uso: nada de SQL aquí.
"""
from __future__ import annotations

import argparse
import getpass
import os
import sys

from backend.infrastructure.database import init_db
from backend.interfaces.dependencies import get_user_use_cases

MIN_PASSWORD = 6  # mismo mínimo que UserCreate


def _password(args, required: bool) -> str | None:
    pw = args.password or os.environ.get("JKANBAN_ADMIN_PASSWORD")
    if pw is None and required and sys.stdin.isatty():
        pw = getpass.getpass("Contraseña: ")
    return pw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m backend.create_admin",
                                     description="Crea o promueve un administrador de JKanban.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", help="obligatorio si el usuario no existe")
    parser.add_argument("--password", help="también JKANBAN_ADMIN_PASSWORD")
    args = parser.parse_args(argv)

    email = args.email.strip().lower()
    if "@" not in email:
        print("Error: email no válido.", file=sys.stderr)
        return 2

    init_db()
    users = get_user_use_cases()
    existing = next((u for u in users.get_all() if u.email == email), None)

    password = _password(args, required=existing is None)
    if password is not None and len(password) < MIN_PASSWORD:
        print(f"Error: la contraseña debe tener al menos {MIN_PASSWORD} caracteres.", file=sys.stderr)
        return 2

    if existing is None:
        if not args.name or not args.name.strip():
            print("Error: el usuario no existe; indica --name para crearlo.", file=sys.stderr)
            return 2
        if password is None:
            print("Error: falta la contraseña (--password o JKANBAN_ADMIN_PASSWORD).", file=sys.stderr)
            return 2
        user = users.create(name=args.name.strip(), email=email, password=password, avatar_url=None)
        users.update(user.id, {"is_admin": True})
        print(f"Administrador creado: {email} (id {user.id})")
        return 0

    updates: dict = {"is_admin": True}
    if password is not None:
        updates["password"] = password
    users.update(existing.id, updates)
    detail = " y contraseña actualizada" if password is not None else ""
    print(f"Usuario existente convertido en administrador{detail}: {email} (id {existing.id})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
