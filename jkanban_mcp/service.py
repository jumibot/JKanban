"""Operaciones del proyecto SF traducidas a la API de JKanban.

Proyecto -> Project, Plan -> Group, Actividad -> Task, Paso -> TodoItem.
Etiquetas y prioridades son las del proyecto en JKanban.
Todas las funciones devuelven diccionarios JSON-serializables en vocabulario SF.
Las fechas se aceptan y devuelven como texto ISO 8601.
"""
from __future__ import annotations

from datetime import datetime

from jkanban_mcp.client import JKanbanClient, JKanbanError

# Campos de una actividad que se pueden vaciar (la API de tareas acepta null explícito).
CLEARABLE_ACTIVITY_FIELDS = {
    "description": "description",
    "priority": "priority_id",
    "estimated_duration": "estimated_duration",
    "estimated_start": "estimated_start",
    "estimated_end": "estimated_end",
    "actual_start": "actual_start",
    "actual_end": "actual_end",
}


def _drop_none(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None}


def _parse_dt(value: str | None) -> datetime | None:
    """ISO 8601 -> datetime sin zona (las fechas de JKanban no llevan zona)."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).replace(tzinfo=None)
    except ValueError as e:
        raise JKanbanError(422, f"fecha no válida: {value!r} (usa ISO 8601)") from e


def _is_overdue(activity: dict, now: datetime) -> bool:
    """Pendiente y con fin estimado ya pasado."""
    end = _parse_dt(activity.get("estimated_end"))
    return not activity["done"] and end is not None and end < now


def _public(a: dict) -> dict:
    return {k: v for k, v in a.items() if not k.startswith("_")}


def _same_ids(given: list[int], existing: list[int], what: str) -> None:
    """El MCP exige la lista completa y exacta (la API solo exige que sean del proyecto o grupo)."""
    if len(given) != len(set(given)):
        raise JKanbanError(422, f"hay ids repetidos en la lista de {what}")
    if set(given) != set(existing):
        missing = sorted(set(existing) - set(given))
        extra = sorted(set(given) - set(existing))
        raise JKanbanError(422, f"la lista de {what} debe contener exactamente sus ids actuales "
                                f"(faltan {missing}, sobran {extra})")


# ── Traducción de respuestas ──────────────────────────────────────────────

def _project(p: dict) -> dict:
    return {
        "id": p["id"],
        "name": p["name"],
        "description": p.get("description"),
        "owner": (p.get("owner") or {}).get("email"),
        "members": [m["email"] for m in p.get("members") or []],
        "created_at": p.get("created_at"),
        "modified_at": p.get("modified_at"),
    }


def _tag(t: dict) -> dict:
    return {"id": t["id"], "name": t["name"], "color": t["color"]}


def _priority(p: dict) -> dict:
    return {"id": p["id"], "name": p["name"], "icon": p["icon"], "color": p["color"]}


def _plan(g: dict) -> dict:
    return {
        "id": g["id"],
        "project_id": g.get("project_id"),
        "name": g["name"],
        "description": g.get("description"),
        "order": g.get("sort_order", 0),
        "tags": [t["name"] for t in g.get("tags") or []],
    }


def _step(t: dict) -> dict:
    return {"id": t["id"], "title": t["title"], "done": t["completed"], "order": t.get("order", 0)}


def _activity(t: dict, steps: list[dict] | None = None) -> dict:
    out = {
        "id": t["id"],
        "plan_id": t["group_id"],
        "title": t["title"],
        "description": t.get("description"),
        "done": t["completed"],
        "order": t.get("sort_order", 0),
        "priority": (t.get("priority") or {}).get("name"),
        "tags": [tag["name"] for tag in t.get("tags") or []],
        "assignee": (t.get("user") or {}).get("email"),
        "estimated_duration": t.get("estimated_duration"),
        "estimated_start": t.get("estimated_start"),
        "estimated_end": t.get("estimated_end"),
        "actual_start": t.get("actual_start"),
        "actual_end": t.get("actual_end"),
        "steps_total": t.get("todos_total", 0),
        "steps_done": t.get("todos_completed", 0),
        "modified_at": t.get("modified_at"),
    }
    if steps is not None:
        out["steps"] = [_step(s) for s in sorted(steps, key=lambda s: (s.get("order", 0), s["id"]))]
    return out


class SFService:
    def __init__(self, client: JKanbanClient):
        self._c = client

    # ── Proyectos ─────────────────────────────────────────────────────────

    def list_projects(self) -> list[dict]:
        return [_project(p) for p in self._c.get("/projects/")]

    def ensure_project(self, name: str, description: str | None = None) -> dict:
        """Devuelve el proyecto con ese nombre (sin distinguir mayúsculas) o lo crea."""
        wanted = name.strip().casefold()
        for p in self._c.get("/projects/"):
            if p["name"].strip().casefold() == wanted:
                return {"project": _project(p), "created": False}
        created = self._c.post("/projects/", _drop_none({"name": name.strip(), "description": description}))
        return {"project": _project(created), "created": True}

    def update_project(self, project_id: int, name: str | None = None,
                       description: str | None = None) -> dict:
        body = _drop_none({"name": name, "description": description})
        return _project(self._c.patch(f"/projects/{project_id}", body))

    def get_project(self, project_id: int, include_steps: bool = False) -> dict:
        """Proyecto completo: sus planes en orden y las actividades de cada plan."""
        project = _project(self._c.get(f"/projects/{project_id}"))
        plans = []
        for g in self._groups(project_id):
            plan = _plan(g)
            plan["activities"] = [
                _activity(t, self._c.get(f"/tasks/{t['id']}/todos") if include_steps else None)
                for t in self._tasks(g["id"])
            ]
            plans.append(plan)
        project["plans"] = plans
        return project

    # ── Miembros ──────────────────────────────────────────────────────────

    def list_members(self, project_id: int) -> list[dict]:
        return [{"id": u["id"], "name": u["name"], "email": u["email"]}
                for u in self._c.get(f"/projects/{project_id}/members")]

    def add_member(self, project_id: int, email: str) -> dict:
        self._c.post(f"/projects/{project_id}/members/{self._user_id(email)}")
        return _project(self._c.get(f"/projects/{project_id}"))

    def remove_member(self, project_id: int, email: str) -> dict:
        self._c.delete(f"/projects/{project_id}/members/{self._user_id(email)}")
        return _project(self._c.get(f"/projects/{project_id}"))

    # ── Planes ────────────────────────────────────────────────────────────

    def create_plan(self, project_id: int, name: str, description: str | None = None,
                    tags: list[str] | None = None) -> dict:
        body = _drop_none({"project_id": project_id, "name": name, "description": description})
        plan = self._c.post("/groups/", body)
        if tags:
            return self.tag_plan(plan["id"], add=tags)
        return _plan(plan)

    def update_plan(self, plan_id: int, name: str | None = None,
                    description: str | None = None) -> dict:
        body = _drop_none({"name": name, "description": description})
        return _plan(self._c.patch(f"/groups/{plan_id}", body))

    def reorder_plans(self, project_id: int, plan_ids: list[int]) -> list[dict]:
        _same_ids(plan_ids, [g["id"] for g in self._groups(project_id)], "planes del proyecto")
        self._c.patch("/groups/reorder", {"project_id": project_id, "group_ids": plan_ids})
        return [_plan(g) for g in self._groups(project_id)]

    def delete_plan(self, plan_id: int, with_activities: bool = False) -> dict:
        """Borra un plan. Si tiene actividades, solo lo hace con `with_activities=True`."""
        tasks = self._c.get(f"/groups/{plan_id}/tasks")
        if tasks and not with_activities:
            raise JKanbanError(409, f"el plan {plan_id} tiene {len(tasks)} actividades; "
                                    "usa with_activities=true para borrarlas también")
        for t in tasks:
            self._c.delete(f"/tasks/{t['id']}")
        self._c.delete(f"/groups/{plan_id}")
        return {"deleted_plan": plan_id, "deleted_activities": len(tasks)}

    def tag_plan(self, plan_id: int, add: list[str] | None = None,
                 remove: list[str] | None = None) -> dict:
        group = self._c.get(f"/groups/{plan_id}")
        self._retag(f"/groups/{plan_id}/tags", group["project_id"], add, remove)
        return _plan(self._c.get(f"/groups/{plan_id}"))

    # ── Actividades ───────────────────────────────────────────────────────

    def create_activity(self, plan_id: int, title: str, description: str | None = None,
                        steps: list[str] | None = None,
                        priority_id: int | None = None,
                        tags: list[str] | None = None,
                        estimated_duration: float | None = None,
                        estimated_start: str | None = None,
                        estimated_end: str | None = None) -> dict:
        task = self._c.post("/tasks/", _drop_none({
            "group_id": plan_id, "title": title, "description": description,
            "priority_id": priority_id, "estimated_duration": estimated_duration,
            "estimated_start": estimated_start, "estimated_end": estimated_end,
        }))
        for i, s in enumerate(steps or []):
            self._c.post(f"/tasks/{task['id']}/todos", {"title": s, "order": i})
        if tags:
            return self.tag_activity(task["id"], add=tags)
        return self.get_activity(task["id"])

    def get_activity(self, activity_id: int) -> dict:
        task = self._c.get(f"/tasks/{activity_id}")
        return _activity(task, self._c.get(f"/tasks/{activity_id}/todos"))

    def update_activity(self, activity_id: int, title: str | None = None,
                        description: str | None = None, done: bool | None = None,
                        plan_id: int | None = None,
                        priority_id: int | None = None,
                        estimated_duration: float | None = None,
                        estimated_start: str | None = None,
                        estimated_end: str | None = None,
                        actual_start: str | None = None,
                        actual_end: str | None = None,
                        clear: list[str] | None = None) -> dict:
        body = _drop_none({
            "title": title, "description": description, "completed": done,
            "group_id": plan_id, "priority_id": priority_id,
            "estimated_duration": estimated_duration,
            "estimated_start": estimated_start, "estimated_end": estimated_end,
            "actual_start": actual_start, "actual_end": actual_end,
        })
        for field in clear or []:
            if field not in CLEARABLE_ACTIVITY_FIELDS:
                raise JKanbanError(422, f"no se puede vaciar '{field}'; "
                                        f"válidos: {sorted(CLEARABLE_ACTIVITY_FIELDS)}")
            api_field = CLEARABLE_ACTIVITY_FIELDS[field]
            if api_field in body:
                raise JKanbanError(422, f"'{field}' no puede darse y vaciarse a la vez")
            body[api_field] = None
        if body:
            self._c.patch(f"/tasks/{activity_id}", body)
        return self.get_activity(activity_id)

    def reorder_activities(self, plan_id: int, activity_ids: list[int]) -> list[dict]:
        _same_ids(activity_ids, [t["id"] for t in self._tasks(plan_id)], "actividades del plan")
        self._c.patch(f"/groups/{plan_id}/tasks/reorder", {"task_ids": activity_ids})
        return [_activity(t) for t in self._tasks(plan_id)]

    def delete_activity(self, activity_id: int) -> dict:
        self._c.delete(f"/tasks/{activity_id}")
        return {"deleted_activity": activity_id}

    def tag_activity(self, activity_id: int, add: list[str] | None = None,
                     remove: list[str] | None = None) -> dict:
        task = self._c.get(f"/tasks/{activity_id}")
        project_id = self._c.get(f"/groups/{task['group_id']}")["project_id"]
        self._retag(f"/tasks/{activity_id}/tags", project_id, add, remove)
        return self.get_activity(activity_id)

    # ── Pasos ─────────────────────────────────────────────────────────────

    def add_steps(self, activity_id: int, steps: list[str]) -> dict:
        existing = self._c.get(f"/tasks/{activity_id}/todos")
        start = max((s.get("order", 0) for s in existing), default=-1) + 1
        for i, s in enumerate(steps):
            self._c.post(f"/tasks/{activity_id}/todos", {"title": s, "order": start + i})
        return self.get_activity(activity_id)

    def update_step(self, activity_id: int, step_id: int, done: bool | None = None,
                    title: str | None = None) -> dict:
        body = _drop_none({"completed": done, "title": title})
        if body:
            self._c.patch(f"/tasks/{activity_id}/todos/{step_id}", body)
        return self.get_activity(activity_id)

    def reorder_steps(self, activity_id: int, step_ids: list[int]) -> dict:
        existing = self._c.get(f"/tasks/{activity_id}/todos")
        _same_ids(step_ids, [s["id"] for s in existing], "pasos de la actividad")
        for order, step_id in enumerate(step_ids):
            self._c.patch(f"/tasks/{activity_id}/todos/{step_id}", {"order": order})
        return self.get_activity(activity_id)

    def delete_step(self, activity_id: int, step_id: int) -> dict:
        self._c.delete(f"/tasks/{activity_id}/todos/{step_id}")
        return self.get_activity(activity_id)

    # ── Etiquetas ─────────────────────────────────────────────────────────

    def list_tags(self, project_id: int) -> list[dict]:
        return [_tag(t) for t in self._c.get(f"/projects/{project_id}/tags/")]

    def create_tag(self, project_id: int, name: str, color: str | None = None) -> dict:
        return _tag(self._c.post(f"/projects/{project_id}/tags/",
                                 _drop_none({"name": name, "color": color})))

    def update_tag(self, project_id: int, tag_id: int, name: str | None = None,
                   color: str | None = None) -> dict:
        return _tag(self._c.patch(f"/projects/{project_id}/tags/{tag_id}",
                                  _drop_none({"name": name, "color": color})))

    def delete_tag(self, project_id: int, tag_id: int) -> dict:
        self._c.delete(f"/projects/{project_id}/tags/{tag_id}")
        return {"deleted_tag": tag_id}

    # ── Prioridades ───────────────────────────────────────────────────────

    def list_priorities(self, project_id: int) -> list[dict]:
        return [_priority(p) for p in self._c.get(f"/projects/{project_id}/priorities/")]

    def create_priority(self, project_id: int, name: str, icon: str | None = None,
                        color: str | None = None) -> dict:
        return _priority(self._c.post(f"/projects/{project_id}/priorities/",
                                      _drop_none({"name": name, "icon": icon, "color": color})))

    def update_priority(self, project_id: int, priority_id: int, name: str | None = None,
                        icon: str | None = None, color: str | None = None) -> dict:
        return _priority(self._c.patch(f"/projects/{project_id}/priorities/{priority_id}",
                                       _drop_none({"name": name, "icon": icon, "color": color})))

    def delete_priority(self, project_id: int, priority_id: int) -> dict:
        self._c.delete(f"/projects/{project_id}/priorities/{priority_id}")
        return {"deleted_priority": priority_id}

    # ── Vista general y consultas (todos los proyectos) ───────────────────

    def overview(self, next_count: int = 3) -> dict:
        """Resumen de todos los proyectos con tres llamadas a la API, sin recorrerlos uno a uno."""
        projects, plans, activities = self._snapshot()
        now = self._now()
        rows = []
        for p in projects:
            p_plans = [g for g in plans if g["project_id"] == p["id"]]
            acts = [a for a in activities if a["_project"]["id"] == p["id"]]
            done = [a for a in acts if a["done"]]
            pending = [a for a in acts if not a["done"]]
            stamps = [a["modified_at"] or a["_created_at"] for a in acts if a["modified_at"] or a["_created_at"]]
            rows.append({
                "id": p["id"],
                "name": p["name"],
                "plans": len(p_plans),
                "activities_total": len(acts),
                "activities_done": len(done),
                "progress": round(len(done) / len(acts), 2) if acts else None,
                "steps_total": sum(a["steps_total"] for a in acts),
                "steps_done": sum(a["steps_done"] for a in acts),
                "in_progress": sum(1 for a in pending if a["actual_start"]),
                "overdue": sum(1 for a in pending if _is_overdue(a, now)),
                "last_activity_at": max(stamps) if stamps else p.get("modified_at") or p.get("created_at"),
                "next": [{"id": a["id"], "title": a["title"], "plan": a["plan"]}
                         for a in pending[:next_count]],
            })
        totals = {k: sum(r[k] for r in rows) for k in
                  ("plans", "activities_total", "activities_done", "steps_total", "steps_done",
                   "in_progress", "overdue")}
        return {"generated_at": now.isoformat(timespec="seconds"), "projects": rows,
                "totals": {"projects": len(rows), **totals}}

    def find_activities(self, project_id: int | None = None, plan_id: int | None = None,
                        done: bool | None = None, tags: list[str] | None = None,
                        priority: str | None = None, text: str | None = None,
                        overdue: bool | None = None, in_progress: bool | None = None,
                        modified_since: str | None = None, limit: int = 50) -> dict:
        """Actividades de todos los proyectos que cumplen todos los filtros dados."""
        _, _, activities = self._snapshot()
        now = self._now()
        wanted_tags = {t.strip().casefold() for t in tags or []}
        since = _parse_dt(modified_since) if modified_since else None
        needle = text.casefold() if text else None

        def keep(a: dict) -> bool:
            if project_id is not None and a["_project"]["id"] != project_id:
                return False
            if plan_id is not None and a["plan_id"] != plan_id:
                return False
            if done is not None and a["done"] != done:
                return False
            if wanted_tags and not wanted_tags <= {t.casefold() for t in a["tags"]}:
                return False
            if priority is not None and (a["priority"] or "").casefold() != priority.casefold():
                return False
            if needle and needle not in f"{a['title']}\n{a['description'] or ''}".casefold():
                return False
            if overdue is not None and _is_overdue(a, now) != overdue:
                return False
            if in_progress is not None and (bool(a["actual_start"]) and not a["done"]) != in_progress:
                return False
            if since is not None:
                stamp = _parse_dt(a["modified_at"] or a["_created_at"])
                if stamp is None or stamp < since:
                    return False
            return True

        found = [a for a in activities if keep(a)]
        return {"total": len(found), "returned": min(len(found), limit),
                "activities": [_public(a) for a in found[:limit]]}

    def _snapshot(self) -> tuple[list[dict], list[dict], list[dict]]:
        """Proyectos, planes y actividades accesibles, en orden de tablero."""
        projects = sorted(self._c.get("/projects/"), key=lambda p: p["id"])
        by_pid = {p["id"]: p for p in projects}
        plans = sorted((g for g in self._c.get("/groups/") if g.get("project_id") in by_pid),
                       key=lambda g: (g["project_id"], g.get("sort_order", 0), g["id"]))
        plan_pos = {g["id"]: i for i, g in enumerate(plans)}
        by_gid = {g["id"]: g for g in plans}
        activities = []
        for t in sorted((t for t in self._c.get("/tasks/") if t["group_id"] in by_gid),
                        key=lambda t: (plan_pos[t["group_id"]], t.get("sort_order", 0), t["id"])):
            g = by_gid[t["group_id"]]
            a = _activity(t)
            a["plan"] = g["name"]
            a["project"] = by_pid[g["project_id"]]["name"]
            a["project_id"] = g["project_id"]
            a["_project"] = by_pid[g["project_id"]]
            a["_created_at"] = t.get("created_at")
            activities.append(a)
        return projects, plans, activities

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    # ── Internos ──────────────────────────────────────────────────────────

    def _groups(self, project_id: int) -> list[dict]:
        return sorted(self._c.get(f"/projects/{project_id}/groups"),
                      key=lambda g: (g.get("sort_order", 0), g["id"]))

    def _tasks(self, plan_id: int) -> list[dict]:
        return sorted(self._c.get(f"/groups/{plan_id}/tasks"),
                      key=lambda t: (t.get("sort_order", 0), t["id"]))

    def _user_id(self, email: str) -> int:
        wanted = email.strip().lower()
        for u in self._c.get("/users/"):
            if u["email"] == wanted:
                return u["id"]
        raise JKanbanError(404, f"no hay ningún usuario con email {email}")

    def _retag(self, base: str, project_id: int, add: list[str] | None,
               remove: list[str] | None) -> None:
        """Añade y quita etiquetas por nombre. Las que se añaden y no existen se crean."""
        by_name = {t["name"].casefold(): t for t in self._c.get(f"/projects/{project_id}/tags/")}
        for name in add or []:
            tag = by_name.get(name.strip().casefold())
            if tag is None:
                tag = self._c.post(f"/projects/{project_id}/tags/", {"name": name.strip()})
                by_name[tag["name"].casefold()] = tag
            self._c.post(f"{base}/{tag['id']}")
        for name in remove or []:
            tag = by_name.get(name.strip().casefold())
            if tag is None:
                raise JKanbanError(404, f"la etiqueta '{name}' no existe en el proyecto")
            self._c.delete(f"{base}/{tag['id']}")
