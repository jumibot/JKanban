"""Tests de jkanban_mcp.service contra la API real (TestClient como transporte).

No dependen del SDK de MCP: solo prueban la traducción SF -> API de JKanban.
"""
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from jkanban_mcp.client import JKanbanClient, JKanbanError
from jkanban_mcp.service import SFService

EMAIL, PASSWORD = "sf-bot@test.com", "sfbotpass123"


@pytest.fixture
def sf(client: TestClient) -> SFService:
    client.post("/users/", json={"name": "SF Bot", "email": EMAIL, "password": PASSWORD})
    return SFService(JKanbanClient("http://testserver", EMAIL, PASSWORD, http=client))


@pytest.fixture
def project_id(sf: SFService) -> int:
    return sf.ensure_project("Proyecto SF", "desc")["project"]["id"]


# ── Proyectos ─────────────────────────────────────────────────────────────

def test_ensure_project_creates_then_reuses(sf):
    first = sf.ensure_project("Alfa", "primera")
    again = sf.ensure_project("  alfa ")
    assert first["created"] is True
    assert again["created"] is False
    assert again["project"]["id"] == first["project"]["id"]
    assert first["project"]["owner"] == EMAIL
    assert [p["name"] for p in sf.list_projects()] == ["Alfa"]


def test_update_project(sf, project_id):
    p = sf.update_project(project_id, description="nueva")
    assert p["name"] == "Proyecto SF"
    assert p["description"] == "nueva"


def test_get_project_tree_in_order(sf, project_id):
    p1 = sf.create_plan(project_id, "Plan 1")
    p2 = sf.create_plan(project_id, "Plan 2", "segundo")
    a = sf.create_activity(p1["id"], "A", steps=["x", "y"])
    sf.create_activity(p1["id"], "B")
    sf.create_activity(p2["id"], "C")
    sf.update_step(a["id"], a["steps"][0]["id"], done=True)

    tree = sf.get_project(project_id)
    assert [pl["name"] for pl in tree["plans"]] == ["Plan 1", "Plan 2"]
    assert [ac["title"] for ac in tree["plans"][0]["activities"]] == ["A", "B"]
    first = tree["plans"][0]["activities"][0]
    assert (first["steps_total"], first["steps_done"]) == (2, 1)
    assert "steps" not in first

    detailed = sf.get_project(project_id, include_steps=True)
    assert [s["title"] for s in detailed["plans"][0]["activities"][0]["steps"]] == ["x", "y"]


# ── Planes ────────────────────────────────────────────────────────────────

def test_create_and_update_plan(sf, project_id):
    plan = sf.create_plan(project_id, "Fase 1", "desc")
    assert plan["project_id"] == project_id
    updated = sf.update_plan(plan["id"], name="Fase 1 bis")
    assert updated["name"] == "Fase 1 bis"
    assert updated["description"] == "desc"


def test_delete_plan_with_activities_requires_flag(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")
    sf.create_activity(plan["id"], "A")
    with pytest.raises(JKanbanError) as e:
        sf.delete_plan(plan["id"])
    assert e.value.status == 409
    assert sf.delete_plan(plan["id"], with_activities=True) == {
        "deleted_plan": plan["id"], "deleted_activities": 1}
    assert sf.get_project(project_id)["plans"] == []


# ── Actividades ───────────────────────────────────────────────────────────

def test_create_activity_with_steps_and_dates(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")
    a = sf.create_activity(plan["id"], "Diseño", "detalle", steps=["uno", "dos"],
                           estimated_duration=3.5, estimated_start="2026-11-02",
                           estimated_end="2026-11-03T18:00:00")
    assert a["plan_id"] == plan["id"]
    assert a["done"] is False
    assert a["estimated_duration"] == 3.5
    assert a["estimated_start"].startswith("2026-11-02")
    assert [s["title"] for s in a["steps"]] == ["uno", "dos"]
    assert (a["steps_total"], a["steps_done"]) == (2, 0)


def test_update_activity_only_changes_given_fields(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")
    other = sf.create_plan(project_id, "Otra")
    a = sf.create_activity(plan["id"], "Tarea", "desc")
    u = sf.update_activity(a["id"], done=True, actual_end="2026-11-05", plan_id=other["id"])
    assert u["done"] is True
    assert u["plan_id"] == other["id"]
    assert u["actual_end"].startswith("2026-11-05")
    assert u["title"] == "Tarea"
    assert u["description"] == "desc"


def test_delete_activity(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")
    a = sf.create_activity(plan["id"], "Tarea")
    sf.delete_activity(a["id"])
    with pytest.raises(JKanbanError) as e:
        sf.get_activity(a["id"])
    assert e.value.status == 404


# ── Pasos ─────────────────────────────────────────────────────────────────

def test_steps_add_update_delete(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")
    a = sf.create_activity(plan["id"], "Tarea", steps=["uno"])
    a = sf.add_steps(a["id"], ["dos", "tres"])
    assert [s["title"] for s in a["steps"]] == ["uno", "dos", "tres"]
    a = sf.update_step(a["id"], a["steps"][1]["id"], done=True, title="DOS")
    assert [(s["title"], s["done"]) for s in a["steps"]] == [
        ("uno", False), ("DOS", True), ("tres", False)]
    a = sf.delete_step(a["id"], a["steps"][0]["id"])
    assert [s["title"] for s in a["steps"]] == ["DOS", "tres"]


# ── Cliente ───────────────────────────────────────────────────────────────

def test_bad_credentials_raise(client):
    sf = SFService(JKanbanClient("http://testserver", "nadie@test.com", "xxxxxx", http=client))
    with pytest.raises(JKanbanError) as e:
        sf.list_projects()
    assert e.value.status == 401


def test_relogin_after_expired_token(sf):
    sf.list_projects()
    sf._c._token = "token-caducado"
    assert sf.list_projects() == []


def test_other_users_projects_are_not_visible(sf, client, auth):
    _, headers = auth
    client.post("/projects/", json={"name": "Ajeno"}, headers=headers)
    assert sf.list_projects() == []


# ── Orden ─────────────────────────────────────────────────────────────────

def test_reorder_plans(sf, project_id):
    a, b, c = (sf.create_plan(project_id, n)["id"] for n in "ABC")
    result = sf.reorder_plans(project_id, [c, a, b])
    assert [p["name"] for p in result] == ["C", "A", "B"]
    assert [p["name"] for p in sf.get_project(project_id)["plans"]] == ["C", "A", "B"]


def test_reorder_plans_requires_exact_ids(sf, project_id):
    a, b = (sf.create_plan(project_id, n)["id"] for n in "AB")
    other = sf.ensure_project("Otro")["project"]["id"]
    foreign = sf.create_plan(other, "Ajeno")["id"]
    for bad in ([a], [a, b, foreign], [a, a, b]):
        with pytest.raises(JKanbanError) as e:
            sf.reorder_plans(project_id, bad)
        assert e.value.status == 422
    assert [p["name"] for p in sf.get_project(project_id)["plans"]] == ["A", "B"]


def test_reorder_activities(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")["id"]
    a, b, c = (sf.create_activity(plan, n)["id"] for n in "ABC")
    assert [x["title"] for x in sf.reorder_activities(plan, [b, c, a])] == ["B", "C", "A"]
    assert [x["title"] for x in sf.get_project(project_id)["plans"][0]["activities"]] == ["B", "C", "A"]
    with pytest.raises(JKanbanError):
        sf.reorder_activities(plan, [a, b])


def test_reorder_steps(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")["id"]
    act = sf.create_activity(plan, "T", steps=["uno", "dos", "tres"])
    ids = [s["id"] for s in act["steps"]]
    act = sf.reorder_steps(act["id"], [ids[2], ids[0], ids[1]])
    assert [s["title"] for s in act["steps"]] == ["tres", "uno", "dos"]
    with pytest.raises(JKanbanError):
        sf.reorder_steps(act["id"], ids[:2])


def test_new_items_go_last_after_reorder(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")["id"]
    a, b = (sf.create_activity(plan, n)["id"] for n in "AB")
    sf.reorder_activities(plan, [b, a])
    sf.create_activity(plan, "C")
    assert [x["title"] for x in sf.get_project(project_id)["plans"][0]["activities"]] == ["B", "A", "C"]


# ── Prioridades ───────────────────────────────────────────────────────────

def test_priorities_crud_and_assignment(sf, project_id):
    alta = sf.create_priority(project_id, "Alta", icon="bolt", color="#ff0000")
    assert alta == {"id": alta["id"], "name": "Alta", "icon": "bolt", "color": "#FF0000"}
    baja = sf.create_priority(project_id, "Baja")
    assert sf.update_priority(project_id, baja["id"], name="Baja+")["name"] == "Baja+"
    assert [p["name"] for p in sf.list_priorities(project_id)] == ["Alta", "Baja+"]

    plan = sf.create_plan(project_id, "Fase")["id"]
    act = sf.create_activity(plan, "T", priority_id=alta["id"])
    assert act["priority"] == "Alta"
    assert sf.update_activity(act["id"], priority_id=baja["id"])["priority"] == "Baja+"
    assert sf.get_project(project_id)["plans"][0]["activities"][0]["priority"] == "Baja+"

    sf.delete_priority(project_id, alta["id"])
    assert [p["name"] for p in sf.list_priorities(project_id)] == ["Baja+"]


def test_priority_from_other_project_is_rejected(sf, project_id):
    other = sf.ensure_project("Otro")["project"]["id"]
    foreign = sf.create_priority(other, "Ajena")["id"]
    plan = sf.create_plan(project_id, "Fase")["id"]
    with pytest.raises(JKanbanError) as e:
        sf.create_activity(plan, "T", priority_id=foreign)
    assert e.value.status == 422
    act = sf.create_activity(plan, "T")["id"]
    with pytest.raises(JKanbanError) as e:
        sf.update_activity(act, priority_id=foreign)
    assert e.value.status == 422
    assert sf.get_activity(act)["priority"] is None
    assert [a["title"] for a in sf.get_project(project_id)["plans"][0]["activities"]] == ["T"]


# ── Vaciar campos ─────────────────────────────────────────────────────────

def test_clear_activity_fields(sf, project_id):
    prio = sf.create_priority(project_id, "Alta")["id"]
    plan = sf.create_plan(project_id, "Fase")["id"]
    act = sf.create_activity(plan, "T", "desc", priority_id=prio, estimated_duration=2,
                             estimated_start="2026-11-02")
    act = sf.update_activity(act["id"], clear=["description", "priority", "estimated_start"])
    assert act["description"] is None
    assert act["priority"] is None
    assert act["estimated_start"] is None
    assert act["estimated_duration"] == 2
    assert act["title"] == "T"


def test_clear_rejects_unknown_or_conflicting_fields(sf, project_id):
    plan = sf.create_plan(project_id, "Fase")["id"]
    act = sf.create_activity(plan, "T")["id"]
    for kwargs in ({"clear": ["title"]}, {"description": "x", "clear": ["description"]}):
        with pytest.raises(JKanbanError) as e:
            sf.update_activity(act, **kwargs)
        assert e.value.status == 422


# ── Etiquetas ─────────────────────────────────────────────────────────────

def test_tags_crud(sf, project_id):
    t = sf.create_tag("backend", project_id, color="#00ff00")
    assert t["color"] == "#00FF00"
    assert sf.update_tag(t["id"], project_id, name="Backend")["name"] == "Backend"
    assert [x["name"] for x in sf.list_tags(project_id)] == ["Backend"]
    sf.delete_tag(t["id"], project_id)
    assert sf.list_tags(project_id) == []


def test_tag_activity_by_name_creates_missing_tags(sf, project_id):
    sf.create_tag("Backend", project_id)
    plan = sf.create_plan(project_id, "Fase")["id"]
    act = sf.create_activity(plan, "T", tags=["backend", "bloqueada"])
    assert sorted(act["tags"]) == ["Backend", "bloqueada"]
    assert sorted(t["name"] for t in sf.list_tags(project_id)) == ["Backend", "bloqueada"]

    act = sf.tag_activity(act["id"], add=["revisión"], remove=["BLOQUEADA"])
    assert sorted(act["tags"]) == ["Backend", "revisión"]
    assert sorted(sf.get_project(project_id)["plans"][0]["activities"][0]["tags"]) == ["Backend", "revisión"]

    with pytest.raises(JKanbanError) as e:
        sf.tag_activity(act["id"], remove=["no-existe"])
    assert e.value.status == 404


def test_tag_plan(sf, project_id):
    plan = sf.create_plan(project_id, "Fase", tags=["devslice"])
    assert plan["tags"] == ["devslice"]
    plan = sf.tag_plan(plan["id"], add=["F1"], remove=["devslice"])
    assert plan["tags"] == ["F1"]
    assert sf.get_project(project_id)["plans"][0]["tags"] == ["F1"]


def test_tags_are_per_project(sf, project_id):
    other = sf.ensure_project("Otro")["project"]["id"]
    sf.create_tag("compartida", other)
    plan = sf.create_plan(project_id, "Fase")["id"]
    act = sf.create_activity(plan, "T", tags=["compartida"])
    assert act["tags"] == ["compartida"]
    assert [t["name"] for t in sf.list_tags(project_id)] == ["compartida"]
    assert len(sf.list_tags(other)) == 1


# ── Miembros ──────────────────────────────────────────────────────────────

def test_members_add_list_remove(sf, client, project_id):
    client.post("/users/", json={"name": "Owner", "email": "owner@test.com", "password": "ownerpass1"})
    p = sf.add_member(project_id, "Owner@Test.com")
    assert p["members"] == ["owner@test.com"]
    assert [m["email"] for m in sf.list_members(project_id)] == ["owner@test.com"]

    # El miembro ve el proyecto con su propio usuario
    owner = SFService(JKanbanClient("http://testserver", "owner@test.com", "ownerpass1", http=client))
    assert [x["name"] for x in owner.list_projects()] == ["Proyecto SF"]

    assert sf.remove_member(project_id, "owner@test.com")["members"] == []
    assert owner.list_projects() == []


@pytest.fixture
def two_projects(sf, monkeypatch):
    """Dos proyectos con actividades variadas y 'hoy' fijado al 2026-11-10."""
    monkeypatch.setattr(sf, "_now", lambda: datetime(2026, 11, 10, 12, 0))
    alfa = sf.ensure_project("Alfa")["project"]["id"]
    beta = sf.ensure_project("Beta")["project"]["id"]
    alta = sf.create_priority(alfa, "Alta")["id"]
    a1 = sf.create_plan(alfa, "Análisis")["id"]
    a2 = sf.create_plan(alfa, "Diseño")["id"]
    b1 = sf.create_plan(beta, "Única")["id"]
    ids = {
        "hecha": sf.create_activity(a1, "Entrevistas", steps=["x", "y"], tags=["backend"])["id"],
        "vencida": sf.create_activity(a1, "Informe API", "resumen de la api", priority_id=alta,
                                      tags=["backend", "bloqueada"], estimated_end="2026-11-05")["id"],
        "en_curso": sf.create_activity(a2, "Bocetos", estimated_end="2026-12-01")["id"],
        "montar": sf.create_activity(b1, "Montar entorno", tags=["Backend"])["id"],
    }
    sf.update_activity(ids["hecha"], done=True, estimated_end="2026-11-01")
    sf.update_step(ids["hecha"], sf.get_activity(ids["hecha"])["steps"][0]["id"], done=True)
    sf.update_activity(ids["en_curso"], actual_start="2026-11-08")
    return {"alfa": alfa, "beta": beta, "a1": a1, **ids}


def _titles(result):
    return [a["title"] for a in result["activities"]]


def test_overview_summarises_every_project(sf, two_projects):
    ov = sf.overview()
    assert ov["generated_at"] == "2026-11-10T12:00:00"
    alfa, beta = ov["projects"]
    assert (alfa["name"], beta["name"]) == ("Alfa", "Beta")
    assert alfa["plans"] == 2
    assert (alfa["activities_done"], alfa["activities_total"], alfa["progress"]) == (1, 3, 0.33)
    assert (alfa["steps_done"], alfa["steps_total"]) == (1, 2)
    assert (alfa["in_progress"], alfa["overdue"]) == (1, 1)
    assert [n["title"] for n in alfa["next"]] == ["Informe API", "Bocetos"]
    assert alfa["next"][0]["plan"] == "Análisis"
    assert alfa["last_activity_at"] is not None
    assert (beta["activities_total"], beta["progress"], beta["overdue"]) == (1, 0.0, 0)
    assert ov["totals"] == {"projects": 2, "plans": 3, "activities_total": 4, "activities_done": 1,
                            "steps_total": 2, "steps_done": 1, "in_progress": 1, "overdue": 1}


def test_overview_empty_project_and_next_count(sf, two_projects):
    sf.ensure_project("Vacío")
    ov = sf.overview(next_count=1)
    empty = ov["projects"][-1]
    assert (empty["name"], empty["activities_total"], empty["progress"], empty["next"]) == ("Vacío", 0, None, [])
    assert len(ov["projects"][0]["next"]) == 1


def test_overview_only_shows_own_projects(sf, client, auth, two_projects):
    _, h = auth
    client.post("/projects/", json={"name": "Ajeno"}, headers=h)
    assert [p["name"] for p in sf.overview()["projects"]] == ["Alfa", "Beta"]


def test_find_activities_without_filters_lists_all_in_board_order(sf, two_projects):
    r = sf.find_activities()
    assert r["total"] == r["returned"] == 4
    assert _titles(r) == ["Entrevistas", "Informe API", "Bocetos", "Montar entorno"]
    first = r["activities"][0]
    assert (first["project"], first["project_id"], first["plan"]) == ("Alfa", two_projects["alfa"], "Análisis")
    assert not any(k.startswith("_") for k in first)


@pytest.mark.parametrize("filters,expected", [
    ({"done": False}, ["Informe API", "Bocetos", "Montar entorno"]),
    ({"done": True}, ["Entrevistas"]),
    ({"tags": ["BACKEND"]}, ["Entrevistas", "Informe API", "Montar entorno"]),
    ({"tags": ["backend", "bloqueada"]}, ["Informe API"]),
    ({"priority": "alta"}, ["Informe API"]),
    ({"text": "API"}, ["Informe API"]),
    ({"text": "resumen"}, ["Informe API"]),
    ({"overdue": True}, ["Informe API"]),
    ({"in_progress": True}, ["Bocetos"]),
    ({"done": False, "tags": ["backend"]}, ["Informe API", "Montar entorno"]),
])
def test_find_activities_filters(sf, two_projects, filters, expected):
    assert _titles(sf.find_activities(**filters)) == expected


def test_find_activities_by_project_and_plan(sf, two_projects):
    assert _titles(sf.find_activities(project_id=two_projects["beta"])) == ["Montar entorno"]
    assert _titles(sf.find_activities(plan_id=two_projects["a1"])) == ["Entrevistas", "Informe API"]


def test_find_activities_modified_since(sf, two_projects):
    assert sf.find_activities(modified_since="2000-01-01")["total"] == 4
    assert sf.find_activities(modified_since="2999-01-01")["total"] == 0
    with pytest.raises(JKanbanError) as e:
        sf.find_activities(modified_since="ayer")
    assert e.value.status == 422


def test_find_activities_limit(sf, two_projects):
    r = sf.find_activities(limit=2)
    assert (r["total"], r["returned"], len(r["activities"])) == (4, 2, 2)


def test_add_member_unknown_email(sf, project_id):
    with pytest.raises(JKanbanError) as e:
        sf.add_member(project_id, "nadie@test.com")
    assert e.value.status == 404
