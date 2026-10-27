"""Tools de flujos y estados del MCP (SFService) contra la API real.

El usuario del MCP es administrador, como en la SF (docs/flows.md §4.5).
"""
import pytest
from fastapi.testclient import TestClient

from jkanban_mcp.client import JKanbanClient, JKanbanError
from jkanban_mcp.service import SFService
from tests.conftest import make_admin

EMAIL, PASSWORD = "sf-bot@test.com", "sfbotpass123"

DEVSLICE = dict(
    name="Devslice",
    states=[{"name": "Planificada", "color": "#94A3B8"}, "En desarrollo", "En verificación", "Terminada"],
    initial="Planificada",
    transitions=[{"from": "Planificada", "to": "En desarrollo"},
                 {"from": "En desarrollo", "to": "En verificación"},
                 {"from": "En verificación", "to": "En desarrollo"},
                 {"from": "En verificación", "to": "Terminada"}],
)


def _service(client, email, password, admin=False) -> SFService:
    uid = client.post("/users/", json={"name": email, "email": email, "password": password}).json()["id"]
    if admin:
        make_admin(uid)
    return SFService(JKanbanClient("http://testserver", email, password, http=client))


@pytest.fixture
def sf(client: TestClient) -> SFService:
    return _service(client, EMAIL, PASSWORD, admin=True)


@pytest.fixture
def person(client: TestClient) -> SFService:
    """Un usuario normal (no administrador)."""
    return _service(client, "ana@test.com", "anapass123")


@pytest.fixture
def setup(sf):
    """Flujo y etiqueta globales; proyecto con un plan y una actividad."""
    flow = sf.ensure_flow(**DEVSLICE)["flow"]
    sf.create_tag("Devslice", flow="devslice")
    pid = sf.ensure_project("Proyecto SF")["project"]["id"]
    plan = sf.create_plan(pid, "Fase 1")["id"]
    act = sf.create_activity(plan, "Login", tags=["devslice"])["id"]
    return {"flow": flow, "pid": pid, "plan": plan, "act": act}


# ── Definir flujos ────────────────────────────────────────────────────────

def test_ensure_flow_creates_global_flow(sf):
    r = sf.ensure_flow(**DEVSLICE)
    assert r["created"] is True
    f = r["flow"]
    assert (f["name"], f["scope"], f["project_id"], f["initial"]) == ("Devslice", "global", None, "Planificada")
    assert [s["name"] for s in f["states"]] == ["Planificada", "En desarrollo", "En verificación", "Terminada"]
    assert f["states"][0]["color"] == "#94A3B8"
    assert {"from": "En verificación", "to": "En desarrollo"} in f["transitions"]
    assert [x["name"] for x in sf.list_flows()] == ["Devslice"]


def test_ensure_flow_is_repeatable(sf):
    sf.ensure_flow(**DEVSLICE)
    again = sf.ensure_flow(**{**DEVSLICE, "name": "DEVSLICE"})
    assert again["created"] is False
    assert again["added_states"] == again["added_transitions"] == []
    assert again["extra_states"] == again["extra_transitions"] == []
    assert again["initial_differs"] is False
    assert len(sf.list_flows()) == 1


def test_ensure_flow_adds_missing_and_reports_differences(sf):
    sf.ensure_flow(**DEVSLICE)
    r = sf.ensure_flow(
        name="Devslice",
        states=[{"name": "planificada", "color": "#000000"}, "En desarrollo", "Bloqueada", "Terminada"],
        initial="En desarrollo",
        transitions=[{"from": "En desarrollo", "to": "Bloqueada"},
                     {"from": "Bloqueada", "to": "En desarrollo"},
                     {"from": "Planificada", "to": "En desarrollo"}],
    )
    assert r["added_states"] == ["Bloqueada"]
    assert r["added_transitions"] == [{"from": "En desarrollo", "to": "Bloqueada"},
                                      {"from": "Bloqueada", "to": "En desarrollo"}]
    assert r["extra_states"] == ["En verificación"]
    assert {"from": "En verificación", "to": "Terminada"} in r["extra_transitions"]
    assert len(r["extra_transitions"]) == 3
    assert r["initial_differs"] is True
    f = r["flow"]
    # nada existente cambia: ni el inicial ni los colores ni lo que sobra
    assert f["initial"] == "Planificada"
    assert f["states"][0]["color"] == "#94A3B8"
    assert [s["name"] for s in f["states"]][-1] == "Bloqueada"
    assert "En verificación" in [s["name"] for s in f["states"]]


@pytest.mark.parametrize("override", [
    {"states": []},
    {"initial": "Nada"},
    {"states": ["A", "a"], "initial": "A", "transitions": []},
    {"transitions": [{"from": "Planificada", "to": "Nada"}]},
    {"transitions": [{"from": "Terminada", "to": "terminada"}]},
])
def test_invalid_definition_changes_nothing(sf, override):
    sf.ensure_flow(**DEVSLICE)
    with pytest.raises(JKanbanError) as e:
        sf.ensure_flow(**{**DEVSLICE, "states": DEVSLICE["states"] + ["Nuevo"], **override})
    assert e.value.status == 422
    assert "Nuevo" not in [s["name"] for s in sf.list_flows()[0]["states"]]


def test_project_flows(sf):
    pid = sf.ensure_project("P")["project"]["id"]
    sf.ensure_flow(**DEVSLICE)
    local = sf.create_flow("Revisión", ["Pendiente", "Hecha"], "Pendiente",
                           [{"from": "Pendiente", "to": "Hecha"}], project_id=pid)
    assert (local["scope"], local["project_id"]) == ("project", pid)
    assert [f["name"] for f in sf.list_flows(pid)] == ["Devslice", "Revisión"]
    assert [f["name"] for f in sf.list_flows()] == ["Devslice"]
    # ensure_flow busca solo en su ámbito
    assert sf.ensure_flow("Revisión", ["Pendiente", "Hecha"], "Pendiente", project_id=pid)["created"] is False


def test_only_admin_defines_global_flows_and_tags(sf, person):
    with pytest.raises(JKanbanError) as e:
        person.ensure_flow(**DEVSLICE)
    assert e.value.status == 403
    with pytest.raises(JKanbanError) as e:
        person.create_tag("Global")
    assert e.value.status == 403


def test_edit_flow_states_and_transitions_by_name(sf):
    fid = sf.ensure_flow(**DEVSLICE)["flow"]["id"]
    f = sf.update_flow(fid, "Slice")
    assert f["name"] == "Slice"
    f = sf.add_flow_state(fid, "Bloqueada", color="#ff0000")
    assert f["states"][-1] == {"id": f["states"][-1]["id"], "name": "Bloqueada", "color": "#FF0000",
                               "initial": False}
    f = sf.add_flow_transition(fid, "en desarrollo", "Bloqueada")
    assert {"from": "En desarrollo", "to": "Bloqueada"} in f["transitions"]
    f = sf.update_flow_state(fid, "bloqueada", name="Parada")
    assert {"from": "En desarrollo", "to": "Parada"} in f["transitions"]
    f = sf.update_flow_state(fid, "Terminada", initial=True)
    assert f["initial"] == "Terminada"
    state_id = f["states"][0]["id"]
    f = sf.update_flow_state(fid, str(state_id), order=99)   # id como texto
    assert f["states"][-1]["name"] == "Planificada"
    f = sf.remove_flow_transition(fid, "En desarrollo", "Parada")
    assert {"from": "En desarrollo", "to": "Parada"} not in f["transitions"]
    f = sf.delete_flow_state(fid, "Parada")
    assert "Parada" not in [s["name"] for s in f["states"]]
    with pytest.raises(JKanbanError) as e:
        sf.delete_flow_state(fid, "No existe")
    assert e.value.status == 404 and "Planificada" in str(e.value)
    assert sf.delete_flow(fid) == {"deleted_flow": fid}
    assert sf.list_flows() == []


# ── Etiquetas con flujo ───────────────────────────────────────────────────

def test_global_and_project_tags(sf):
    sf.ensure_flow(**DEVSLICE)
    pid = sf.ensure_project("P")["project"]["id"]
    g = sf.create_tag("Devslice", flow="devslice")
    assert (g["scope"], g["project_id"], g["flow"]) == ("global", None, "Devslice")
    local = sf.create_tag("Docs", pid)
    assert (local["scope"], local["flow"]) == ("project", None)
    assert [t["name"] for t in sf.list_tags()] == ["Devslice"]
    assert [t["name"] for t in sf.list_tags(pid)] == ["Devslice", "Docs"]
    assert sf.update_tag(local["id"], pid, flow="Devslice")["flow"] == "Devslice"
    assert sf.update_tag(local["id"], pid, remove_flow=True)["flow"] is None
    assert sf.update_tag(g["id"], color="#123456")["color"] == "#123456"
    with pytest.raises(JKanbanError) as e:
        sf.create_tag("X", flow="no-existe")
    assert e.value.status == 404
    with pytest.raises(JKanbanError):
        sf.update_tag(g["id"], flow="Devslice", remove_flow=True)
    sf.delete_tag(local["id"], pid)
    sf.delete_tag(g["id"])
    assert sf.list_tags(pid) == []


def test_flow_of_assigned_tag_cannot_change(sf, setup):
    tag = sf.list_tags()[0]["id"]
    with pytest.raises(JKanbanError) as e:
        sf.update_tag(tag, remove_flow=True)
    assert e.value.status == 409


def test_tagging_by_name_finds_global_tags(sf, setup):
    act = sf.get_activity(setup["act"])
    assert act["tags"] == ["Devslice"]
    assert act["states"] == {"Devslice": "Planificada"}
    # no se ha creado una etiqueta de proyecto con el mismo nombre
    assert [(t["name"], t["scope"]) for t in sf.list_tags(setup["pid"])] == [("Devslice", "global")]


# ── Estados ───────────────────────────────────────────────────────────────

def test_set_flow_state_follows_transitions(sf, setup):
    r = sf.set_flow_state("devslice", "en desarrollo", activity_id=setup["act"], note="arranco")
    assert (r["tag"], r["flow"], r["state"]) == ("Devslice", "Devslice", "En desarrollo")
    assert r["next"] == ["En verificación"]
    assert r["activity"]["states"] == {"Devslice": "En desarrollo"}
    with pytest.raises(JKanbanError) as e:
        sf.set_flow_state("Devslice", "Terminada", activity_id=setup["act"])
    assert e.value.status == 409 and "En verificación" in str(e.value)


def test_plans_have_states_too(sf, setup):
    plan = sf.tag_plan(setup["plan"], add=["Devslice"])
    assert plan["states"] == {"Devslice": "Planificada"}
    r = sf.set_flow_state("Devslice", "En desarrollo", plan_id=setup["plan"])
    assert r["plan"]["states"] == {"Devslice": "En desarrollo"}
    assert sf.get_activity(setup["act"])["states"] == {"Devslice": "Planificada"}


def test_flow_history(sf, setup):
    act = setup["act"]
    sf.set_flow_state("Devslice", "En desarrollo", activity_id=act, note="arranco")
    sf.tag_activity(act, remove=["Devslice"])
    hist = sf.get_flow_history("devslice", activity_id=act)
    assert [(h["from"], h["to"], h["note"]) for h in hist] == [
        (None, "Planificada", None), ("Planificada", "En desarrollo", "arranco"), ("En desarrollo", None, None)]
    assert all(h["by"] == EMAIL and h["at"] for h in hist)


@pytest.mark.parametrize("kwargs,status", [
    ({"tag": "Devslice", "to": "En desarrollo"}, 422),                                   # sin elemento
    ({"tag": "Devslice", "to": "En desarrollo", "plan_id": 1, "activity_id": 1}, 422),   # los dos
    ({"tag": "Otra", "to": "En desarrollo", "activity_id": "act"}, 404),                 # no la tiene
    ({"tag": "Devslice", "to": "Nada", "activity_id": "act"}, 404),                      # estado
])
def test_set_flow_state_errors(sf, setup, kwargs, status):
    kwargs = {k: setup["act"] if v == "act" else v for k, v in kwargs.items()}
    with pytest.raises(JKanbanError) as e:
        sf.set_flow_state(**kwargs)
    assert e.value.status == status


def test_set_flow_state_on_tag_without_flow(sf, setup):
    sf.tag_activity(setup["act"], add=["Docs"])
    with pytest.raises(JKanbanError) as e:
        sf.set_flow_state("Docs", "X", activity_id=setup["act"])
    assert e.value.status == 422


def test_member_can_change_states(sf, setup, person):
    sf.add_member(setup["pid"], "ana@test.com")
    r = person.set_flow_state("Devslice", "En desarrollo", activity_id=setup["act"])
    assert r["state"] == "En desarrollo"
    assert person.get_flow_history("Devslice", activity_id=setup["act"])[-1]["by"] == "ana@test.com"


# ── Consultas ─────────────────────────────────────────────────────────────

def test_queries_show_and_filter_states(sf, setup):
    other = sf.create_activity(setup["plan"], "Registro", tags=["Devslice"])["id"]
    sf.create_activity(setup["plan"], "Sin flujo")
    sf.set_flow_state("Devslice", "En desarrollo", activity_id=other)
    sf.tag_plan(setup["plan"], add=["Devslice"])

    tree = sf.get_project(setup["pid"])
    assert tree["plans"][0]["states"] == {"Devslice": "Planificada"}
    assert [a["states"] for a in tree["plans"][0]["activities"]] == [
        {"Devslice": "Planificada"}, {"Devslice": "En desarrollo"}, {}]

    found = sf.find_activities(states={"devslice": "EN DESARROLLO"})
    assert [a["title"] for a in found["activities"]] == ["Registro"]
    assert sf.find_activities(states={"Devslice": "Terminada"})["total"] == 0

    (row,) = sf.overview()["projects"]
    assert row["flow_states"] == {"Devslice": {
        "Planificada": {"plans": 1, "activities": 1},
        "En desarrollo": {"plans": 0, "activities": 1},
    }}
