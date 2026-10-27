"""Flujos y etiquetas globales (docs/flows.md): definición, uso, modificación en
uso, ámbitos y permisos. Todo por la API."""
import pytest

from tests.conftest import make_admin

DEVSLICE = {
    "name": "Devslice",
    "states": [{"name": "Planificada", "color": "#94A3B8"}, {"name": "En desarrollo"},
               {"name": "En verificación"}, {"name": "Terminada"}],
    "initial": "Planificada",
    "transitions": [{"from": "Planificada", "to": "En desarrollo"},
                    {"from": "En desarrollo", "to": "En verificación"},
                    {"from": "En verificación", "to": "En desarrollo"},
                    {"from": "En verificación", "to": "Terminada"}],
}


# ── helpers ───────────────────────────────────────────────────────────────────

def login(client, email, admin=False):
    r = client.post("/users/", json={"name": email.split("@")[0], "email": email, "password": "pass1234"})
    uid = r.json()["id"]
    if admin:
        make_admin(uid)
    token = client.post("/auth/login", json={"email": email, "password": "pass1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, uid


@pytest.fixture
def admin(client):
    return login(client, "sf@x.com", admin=True)[0]


@pytest.fixture
def user(client):
    return login(client, "ana@x.com")


def project(client, h, name="P"):
    return client.post("/projects/", json={"name": name}, headers=h).json()["id"]


def group(client, h, pid, name="G"):
    return client.post("/groups/", json={"name": name, "project_id": pid}, headers=h).json()["id"]


def task(client, h, gid, title="T"):
    return client.post("/tasks/", json={"title": title, "group_id": gid}, headers=h).json()["id"]


def flow(client, h, body=None, pid=None, **overrides):
    body = {**(body or DEVSLICE), **overrides}
    url = f"/projects/{pid}/flows/" if pid else "/flows/"
    return client.post(url, json=body, headers=h)


def state_id(flow_json, name):
    return next(s["id"] for s in flow_json["states"] if s["name"] == name)


def global_tag(client, h, name="Devslice", flow_id=None):
    return client.post("/tags/", json={"name": name, "flow_id": flow_id}, headers=h)


def project_tag(client, h, pid, name="Local", flow_id=None):
    return client.post(f"/projects/{pid}/tags/", json={"name": name, "flow_id": flow_id}, headers=h)


def task_tag(client, h, tid, tag_id):
    return next(t for t in client.get(f"/tasks/{tid}", headers=h).json()["tags"] if t["id"] == tag_id)


def move(client, h, tid, tag_id, sid, note=None, kind="tasks"):
    return client.patch(f"/{kind}/{tid}/tags/{tag_id}/state", json={"state_id": sid, "note": note}, headers=h)


@pytest.fixture
def board(client, admin, user):
    """Global Devslice flow + global tag, and a project of `user` with a task."""
    uh, _ = user
    f = flow(client, admin).json()
    tag = global_tag(client, admin, flow_id=f["id"]).json()
    pid = project(client, uh)
    gid = group(client, uh, pid)
    tid = task(client, uh, gid)
    return {"flow": f, "tag": tag["id"], "pid": pid, "gid": gid, "tid": tid, "h": uh}


# ── 4.1 Definición ────────────────────────────────────────────────────────────

class TestDefinition:
    def test_admin_creates_global_flow(self, client, admin):
        r = flow(client, admin)
        assert r.status_code == 201
        body = r.json()
        assert body["project_id"] is None
        assert [s["name"] for s in body["states"]] == [s["name"] for s in DEVSLICE["states"]]
        assert [s["sort_order"] for s in body["states"]] == [0, 1, 2, 3]
        assert body["initial_state_id"] == state_id(body, "Planificada")
        assert [s["is_initial"] for s in body["states"]] == [True, False, False, False]
        assert body["states"][0]["color"] == "#94A3B8"
        assert body["states"][1]["color"] == "#6B7280"
        pairs = {(t["from_state_id"], t["to_state_id"]) for t in body["transitions"]}
        assert (state_id(body, "En verificación"), state_id(body, "En desarrollo")) in pairs
        assert len(pairs) == 4

    @pytest.mark.parametrize("override,message", [
        ({"states": []}, "at least one state"),
        ({"initial": "Nada"}, "Initial state"),
        ({"states": [{"name": "A"}, {"name": "a"}], "initial": "A", "transitions": []}, "repeated"),
        ({"transitions": [{"from": "Planificada", "to": "Nada"}]}, "unknown state"),
        ({"transitions": [{"from": "Terminada", "to": "Terminada"}]}, "itself"),
        ({"transitions": [{"from": "Terminada", "to": "Planificada"},
                          {"from": "terminada", "to": "planificada"}]}, "repeated"),
    ])
    def test_invalid_definition_returns_422(self, client, admin, override, message):
        r = flow(client, admin, **override)
        assert r.status_code == 422
        assert message in r.json()["detail"]
        assert client.get("/flows/", headers=admin).json() == []

    def test_initial_and_transitions_match_names_ignoring_case(self, client, admin):
        r = flow(client, admin, initial="planificada",
                 transitions=[{"from": "PLANIFICADA", "to": "terminada"}])
        assert r.status_code == 201
        assert r.json()["initial_state_id"] == state_id(r.json(), "Planificada")

    def test_flow_without_transitions_is_valid(self, client, admin):
        assert flow(client, admin, transitions=[]).status_code == 201

    def test_non_admin_cannot_create_global_flow(self, client, user):
        assert flow(client, user[0]).status_code == 403

    def test_unauthenticated_returns_401(self, client):
        assert client.get("/flows/").status_code == 401


# ── Ámbitos: unicidad de nombres y flujos de proyecto ─────────────────────────

class TestScopes:
    def test_global_name_is_unique_ignoring_case(self, client, admin):
        flow(client, admin)
        assert flow(client, admin, name="devslice").status_code == 409

    def test_project_flow_cannot_reuse_a_global_name(self, client, admin, user):
        flow(client, admin)
        pid = project(client, user[0])
        assert flow(client, user[0], pid=pid).status_code == 409

    def test_global_flow_cannot_reuse_a_project_name(self, client, admin, user):
        pid = project(client, user[0])
        assert flow(client, user[0], pid=pid).status_code == 201
        assert flow(client, admin).status_code == 409

    def test_same_name_in_two_projects_is_allowed(self, client, user):
        h = user[0]
        assert flow(client, h, pid=project(client, h, "A")).status_code == 201
        assert flow(client, h, pid=project(client, h, "B")).status_code == 201

    def test_project_list_includes_global_flows_first(self, client, admin, user):
        h = user[0]
        flow(client, admin)
        pid = project(client, h)
        flow(client, h, pid=pid, name="Revisión")
        names = [(f["name"], f["project_id"]) for f in client.get(f"/projects/{pid}/flows/", headers=h).json()]
        assert names == [("Devslice", None), ("Revisión", pid)]
        assert [f["name"] for f in client.get("/flows/", headers=h).json()] == ["Devslice"]

    def test_rename_checks_uniqueness(self, client, admin):
        flow(client, admin)
        other = flow(client, admin, name="Otro").json()
        assert client.patch(f"/flows/{other['id']}", json={"name": "DEVSLICE"}, headers=admin).status_code == 409
        r = client.patch(f"/flows/{other['id']}", json={"name": "Otro bis"}, headers=admin)
        assert r.status_code == 200 and r.json()["name"] == "Otro bis"

    def test_deleting_project_deletes_its_flows(self, client, user):
        h = user[0]
        pid = project(client, h)
        fid = flow(client, h, pid=pid).json()["id"]
        assert client.delete(f"/projects/{pid}", headers=h).status_code == 204
        assert client.get(f"/flows/{fid}", headers=h).status_code == 404


# ── 4.4 Permisos ──────────────────────────────────────────────────────────────

class TestPermissions:
    def test_any_user_sees_global_flows(self, client, admin, user):
        fid = flow(client, admin).json()["id"]
        assert client.get(f"/flows/{fid}", headers=user[0]).status_code == 200

    def test_only_admin_manages_global_flows(self, client, admin, user):
        f = flow(client, admin).json()
        h = user[0]
        sid = state_id(f, "Terminada")
        assert client.patch(f"/flows/{f['id']}", json={"name": "X"}, headers=h).status_code == 403
        assert client.post(f"/flows/{f['id']}/states", json={"name": "X"}, headers=h).status_code == 403
        assert client.patch(f"/flows/{f['id']}/states/{sid}", json={"name": "X"}, headers=h).status_code == 403
        assert client.delete(f"/flows/{f['id']}/states/{sid}", headers=h).status_code == 403
        assert client.post(f"/flows/{f['id']}/transitions",
                           json={"from_state_id": sid, "to_state_id": f["states"][0]["id"]},
                           headers=h).status_code == 403
        assert client.delete(f"/flows/{f['id']}", headers=h).status_code == 403

    def test_project_flows_managed_by_owner_not_by_member(self, client, user):
        h, _ = user
        pid = project(client, h)
        member_h, member_id = login(client, "member@x.com")
        client.post(f"/projects/{pid}/members/{member_id}", headers=h)
        assert flow(client, member_h, pid=pid).status_code == 403
        fid = flow(client, h, pid=pid).json()["id"]
        assert client.get(f"/flows/{fid}", headers=member_h).status_code == 200
        assert client.patch(f"/flows/{fid}", json={"name": "X"}, headers=member_h).status_code == 403
        assert client.patch(f"/flows/{fid}", json={"name": "X"}, headers=h).status_code == 200

    def test_non_member_cannot_see_project_flows(self, client, user):
        h, _ = user
        pid = project(client, h)
        fid = flow(client, h, pid=pid).json()["id"]
        outsider, _ = login(client, "out@x.com")
        assert client.get(f"/flows/{fid}", headers=outsider).status_code == 403
        assert client.get(f"/projects/{pid}/flows/", headers=outsider).status_code == 403

    def test_global_tags_only_admin(self, client, admin, user):
        assert global_tag(client, user[0]).status_code == 403
        tid = global_tag(client, admin).json()["id"]
        assert client.get(f"/tags/{tid}", headers=user[0]).status_code == 200
        assert client.patch(f"/tags/{tid}", json={"name": "X"}, headers=user[0]).status_code == 403
        assert client.delete(f"/tags/{tid}", headers=user[0]).status_code == 403

    def test_non_member_cannot_change_state_or_read_history(self, client, board):
        outsider, _ = login(client, "out@x.com")
        sid = state_id(board["flow"], "En desarrollo")
        client.post(f"/tasks/{board['tid']}/tags/{board['tag']}", headers=board["h"])
        assert move(client, outsider, board["tid"], board["tag"], sid).status_code == 403
        assert client.get(f"/tasks/{board['tid']}/tags/{board['tag']}/history",
                          headers=outsider).status_code == 403


# ── Etiquetas globales y de proyecto ──────────────────────────────────────────

class TestTags:
    def test_global_tag_with_flow(self, client, admin):
        f = flow(client, admin).json()
        r = global_tag(client, admin, flow_id=f["id"])
        assert r.status_code == 201
        assert r.json() == {"id": r.json()["id"], "name": "Devslice", "color": "#6B7280",
                            "project_id": None, "flow": {"id": f["id"], "name": "Devslice"},
                            "state": None}

    def test_global_tag_cannot_use_project_flow(self, client, admin, user):
        pid = project(client, user[0])
        fid = flow(client, user[0], pid=pid, name="Local").json()["id"]
        assert global_tag(client, admin, flow_id=fid).status_code == 422

    def test_project_tag_uses_global_or_own_flows_only(self, client, admin, user):
        h = user[0]
        g = flow(client, admin).json()["id"]
        p1, p2 = project(client, h, "A"), project(client, h, "B")
        own = flow(client, h, pid=p1, name="Local").json()["id"]
        assert project_tag(client, h, p1, "x", g).status_code == 201
        assert project_tag(client, h, p1, "y", own).status_code == 201
        assert project_tag(client, h, p2, "z", own).status_code == 422

    def test_unknown_flow_returns_404(self, client, admin):
        assert global_tag(client, admin, flow_id=999).status_code == 404

    def test_tag_names_unique_across_scopes(self, client, admin, user):
        h = user[0]
        global_tag(client, admin, "Bug")
        pid = project(client, h)
        assert project_tag(client, h, pid, "bug").status_code == 409
        project_tag(client, h, pid, "Docs")
        assert global_tag(client, admin, "DOCS").status_code == 409

    def test_project_tag_list_includes_global_tags(self, client, admin, user):
        h = user[0]
        global_tag(client, admin, "Bug")
        pid = project(client, h)
        project_tag(client, h, pid, "Docs")
        tags = client.get(f"/projects/{pid}/tags/", headers=h).json()
        assert [(t["name"], t["project_id"]) for t in tags] == [("Bug", None), ("Docs", pid)]
        assert [t["name"] for t in client.get("/tags/", headers=h).json()] == ["Bug"]

    def test_global_tag_readable_but_not_editable_from_a_project(self, client, admin, user):
        h = user[0]
        tid = global_tag(client, admin, "Bug").json()["id"]
        pid = project(client, h)
        assert client.get(f"/projects/{pid}/tags/{tid}", headers=h).status_code == 200
        assert client.patch(f"/projects/{pid}/tags/{tid}", json={"name": "X"}, headers=h).status_code == 404
        assert client.delete(f"/projects/{pid}/tags/{tid}", headers=h).status_code == 404

    def test_project_tag_is_not_reachable_as_global(self, client, admin, user):
        pid = project(client, user[0])
        tid = project_tag(client, user[0], pid).json()["id"]
        assert client.get(f"/tags/{tid}", headers=admin).status_code == 404

    def test_admin_updates_and_deletes_global_tag(self, client, admin):
        f = flow(client, admin).json()
        tid = global_tag(client, admin, "Bug").json()["id"]
        r = client.patch(f"/tags/{tid}", json={"color": "#ff0000", "flow_id": f["id"]}, headers=admin)
        assert r.status_code == 200
        assert (r.json()["color"], r.json()["flow"]["id"]) == ("#FF0000", f["id"])
        r = client.patch(f"/tags/{tid}", json={"flow_id": None}, headers=admin)
        assert r.json()["flow"] is None
        assert client.delete(f"/tags/{tid}", headers=admin).status_code == 204
        assert client.get("/tags/", headers=admin).json() == []

    def test_global_tag_works_in_any_project(self, client, board):
        h = board["h"]
        other = task(client, h, group(client, h, project(client, h, "Otro")))
        for tid in (board["tid"], other):
            assert client.post(f"/tasks/{tid}/tags/{board['tag']}", headers=h).status_code == 204

    def test_project_tag_still_limited_to_its_project(self, client, user):
        h = user[0]
        p1, p2 = project(client, h, "A"), project(client, h, "B")
        tag = project_tag(client, h, p1).json()["id"]
        tid = task(client, h, group(client, h, p2))
        assert client.post(f"/tasks/{tid}/tags/{tag}", headers=h).status_code == 422


# ── 4.2 Uso ───────────────────────────────────────────────────────────────────

class TestUse:
    def test_assign_enters_initial_state_and_logs_it(self, client, board):
        h, tid, tag = board["h"], board["tid"], board["tag"]
        assert client.post(f"/tasks/{tid}/tags/{tag}", headers=h).status_code == 204
        t = task_tag(client, h, tid, tag)
        assert t["state"] == {"id": state_id(board["flow"], "Planificada"), "name": "Planificada"}
        assert t["flow"]["name"] == "Devslice"
        (entry,) = client.get(f"/tasks/{tid}/tags/{tag}/history", headers=h).json()
        assert (entry["from_state"], entry["to_state"], entry["task_id"], entry["group_id"]) == \
               (None, "Planificada", tid, None)

    def test_assign_twice_does_not_reset_state_nor_log(self, client, board):
        h, tid, tag = board["h"], board["tid"], board["tag"]
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        move(client, h, tid, tag, state_id(board["flow"], "En desarrollo"))
        assert client.post(f"/tasks/{tid}/tags/{tag}", headers=h).status_code == 204
        assert task_tag(client, h, tid, tag)["state"]["name"] == "En desarrollo"
        assert len(client.get(f"/tasks/{tid}/tags/{tag}/history", headers=h).json()) == 2

    def test_valid_transition_changes_state_and_logs_note(self, client, board, user):
        h, tid, tag = board["h"], board["tid"], board["tag"]
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        r = move(client, h, tid, tag, state_id(board["flow"], "En desarrollo"), note="arranco")
        assert r.status_code == 200
        assert r.json()["state"]["name"] == "En desarrollo"
        assert task_tag(client, h, tid, tag)["state"]["name"] == "En desarrollo"
        last = client.get(f"/tasks/{tid}/tags/{tag}/history", headers=h).json()[-1]
        assert (last["from_state"], last["to_state"], last["note"], last["changed_by"]) == \
               ("Planificada", "En desarrollo", "arranco", user[1])
        assert last["changed_at"] is not None

    def test_invalid_transition_returns_409_with_allowed_targets(self, client, board):
        h, tid, tag = board["h"], board["tid"], board["tag"]
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        r = move(client, h, tid, tag, state_id(board["flow"], "Terminada"))
        assert r.status_code == 409
        assert "'En desarrollo'" in r.json()["detail"]
        assert task_tag(client, h, tid, tag)["state"]["name"] == "Planificada"
        assert len(client.get(f"/tasks/{tid}/tags/{tag}/history", headers=h).json()) == 1

    def test_moving_to_the_same_state_is_not_a_transition(self, client, board):
        h, tid, tag = board["h"], board["tid"], board["tag"]
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        assert move(client, h, tid, tag, state_id(board["flow"], "Planificada")).status_code == 409

    def test_state_of_another_flow_returns_404(self, client, board, admin):
        other = flow(client, admin, name="Otro").json()
        h, tid, tag = board["h"], board["tid"], board["tag"]
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        assert move(client, h, tid, tag, other["states"][1]["id"]).status_code == 404

    def test_tag_without_flow_has_no_state(self, client, board):
        h, tid = board["h"], board["tid"]
        tag = project_tag(client, h, board["pid"]).json()["id"]
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        assert task_tag(client, h, tid, tag)["state"] is None
        assert move(client, h, tid, tag, 1).status_code == 422
        assert client.get(f"/tasks/{tid}/tags/{tag}/history", headers=h).json() == []

    def test_state_change_on_unassigned_tag_returns_404(self, client, board):
        r = move(client, board["h"], board["tid"], board["tag"], state_id(board["flow"], "En desarrollo"))
        assert r.status_code == 404

    def test_unknown_task_or_tag_returns_404(self, client, board):
        h = board["h"]
        assert move(client, h, 999, board["tag"], 1).status_code == 404
        assert move(client, h, board["tid"], 999, 1).status_code == 404
        assert client.get(f"/tasks/999/tags/{board['tag']}/history", headers=h).status_code == 404
        assert client.get(f"/tasks/{board['tid']}/tags/999/history", headers=h).status_code == 404

    def test_unassign_is_allowed_and_logged_and_history_survives(self, client, board):
        h, tid, tag = board["h"], board["tid"], board["tag"]
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        move(client, h, tid, tag, state_id(board["flow"], "En desarrollo"))
        assert client.delete(f"/tasks/{tid}/tags/{tag}", headers=h).status_code == 204
        assert client.get(f"/tasks/{tid}", headers=h).json()["tags"] == []
        hist = client.get(f"/tasks/{tid}/tags/{tag}/history", headers=h).json()
        assert [(e["from_state"], e["to_state"]) for e in hist] == [
            (None, "Planificada"), ("Planificada", "En desarrollo"), ("En desarrollo", None)]
        # re-assigning starts again at the initial state
        client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        assert task_tag(client, h, tid, tag)["state"]["name"] == "Planificada"

    def test_unassign_not_assigned_is_harmless(self, client, board):
        h = board["h"]
        assert client.delete(f"/tasks/{board['tid']}/tags/{board['tag']}", headers=h).status_code == 204
        assert client.get(f"/tasks/{board['tid']}/tags/{board['tag']}/history", headers=h).json() == []

    def test_groups_have_states_too(self, client, board):
        h, gid, tag = board["h"], board["gid"], board["tag"]
        assert client.post(f"/groups/{gid}/tags/{tag}", headers=h).status_code == 204
        r = move(client, h, gid, tag, state_id(board["flow"], "En desarrollo"), kind="groups")
        assert r.status_code == 200
        g = client.get(f"/groups/{gid}", headers=h).json()
        assert g["tags"][0]["state"]["name"] == "En desarrollo"
        hist = client.get(f"/groups/{gid}/tags/{tag}/history", headers=h).json()
        assert [(e["group_id"], e["task_id"], e["to_state"]) for e in hist] == [
            (gid, None, "Planificada"), (gid, None, "En desarrollo")]
        assert move(client, h, gid, tag, state_id(board["flow"], "Planificada"), kind="groups").status_code == 409
        # the task history is separate
        assert client.get(f"/tasks/{board['tid']}/tags/{tag}/history", headers=h).json() == []

    def test_same_tag_has_independent_states_per_item(self, client, board):
        h, tag = board["h"], board["tag"]
        other = task(client, h, board["gid"], "T2")
        for tid in (board["tid"], other):
            client.post(f"/tasks/{tid}/tags/{tag}", headers=h)
        move(client, h, board["tid"], tag, state_id(board["flow"], "En desarrollo"))
        assert task_tag(client, h, board["tid"], tag)["state"]["name"] == "En desarrollo"
        assert task_tag(client, h, other, tag)["state"]["name"] == "Planificada"


# ── 4.3 Modificar un flujo en uso ─────────────────────────────────────────────

class TestModifyInUse:
    @pytest.fixture
    def in_use(self, client, board):
        """The board task is 'En desarrollo'."""
        client.post(f"/tasks/{board['tid']}/tags/{board['tag']}", headers=board["h"])
        move(client, board["h"], board["tid"], board["tag"], state_id(board["flow"], "En desarrollo"))
        return board

    def test_rename_recolor_reorder_and_add_states(self, client, admin, in_use):
        f = in_use["flow"]
        sid = state_id(f, "En desarrollo")
        r = client.patch(f"/flows/{f['id']}/states/{sid}",
                         json={"name": "Desarrollo", "color": "#00ff00", "sort_order": 9}, headers=admin)
        assert r.status_code == 200
        assert r.json()["states"][-1] == {"id": sid, "name": "Desarrollo", "color": "#00FF00",
                                          "sort_order": 9, "is_initial": False}
        r = client.post(f"/flows/{f['id']}/states", json={"name": "Bloqueada"}, headers=admin)
        assert r.status_code == 201
        assert r.json()["states"][-1]["name"] == "Bloqueada"
        # the item shows the new name; the log keeps the old one
        h = in_use["h"]
        assert task_tag(client, h, in_use["tid"], in_use["tag"])["state"]["name"] == "Desarrollo"
        hist = client.get(f"/tasks/{in_use['tid']}/tags/{in_use['tag']}/history", headers=h).json()
        assert hist[-1]["to_state"] == "En desarrollo"

    def test_state_names_stay_unique(self, client, admin, in_use):
        f = in_use["flow"]
        assert client.post(f"/flows/{f['id']}/states", json={"name": "terminada"}, headers=admin).status_code == 422
        sid = state_id(f, "Terminada")
        r = client.patch(f"/flows/{f['id']}/states/{sid}", json={"name": "PLANIFICADA"}, headers=admin)
        assert r.status_code == 422

    def test_deleting_occupied_state_returns_409_with_items(self, client, admin, in_use):
        f = in_use["flow"]
        r = client.delete(f"/flows/{f['id']}/states/{state_id(f, 'En desarrollo')}", headers=admin)
        assert r.status_code == 409
        assert f"[{in_use['tid']}]" in r.json()["detail"]

    def test_deleting_free_state_removes_its_transitions(self, client, admin, in_use):
        f = in_use["flow"]
        sid = state_id(f, "Terminada")
        assert client.delete(f"/flows/{f['id']}/states/{sid}", headers=admin).status_code == 204
        body = client.get(f"/flows/{f['id']}", headers=admin).json()
        assert sid not in [s["id"] for s in body["states"]]
        assert all(sid not in (t["from_state_id"], t["to_state_id"]) for t in body["transitions"])
        assert len(body["transitions"]) == 3

    def test_initial_state_cannot_be_deleted_until_another_is_chosen(self, client, admin, in_use):
        f = in_use["flow"]
        first, last = state_id(f, "Planificada"), state_id(f, "Terminada")
        assert client.delete(f"/flows/{f['id']}/states/{first}", headers=admin).status_code == 422
        assert client.patch(f"/flows/{f['id']}/states/{first}", json={"is_initial": False},
                            headers=admin).status_code == 422
        r = client.patch(f"/flows/{f['id']}/states/{last}", json={"is_initial": True}, headers=admin)
        assert r.json()["initial_state_id"] == last
        assert [s["is_initial"] for s in r.json()["states"]].count(True) == 1
        assert client.delete(f"/flows/{f['id']}/states/{first}", headers=admin).status_code == 204

    def test_new_initial_applies_only_to_future_assignments(self, client, admin, in_use):
        f, h = in_use["flow"], in_use["h"]
        client.patch(f"/flows/{f['id']}/states/{state_id(f, 'Terminada')}", json={"is_initial": True},
                     headers=admin)
        assert task_tag(client, h, in_use["tid"], in_use["tag"])["state"]["name"] == "En desarrollo"
        other = task(client, h, in_use["gid"], "T2")
        client.post(f"/tasks/{other}/tags/{in_use['tag']}", headers=h)
        assert task_tag(client, h, other, in_use["tag"])["state"]["name"] == "Terminada"

    def test_transitions_can_be_added_and_removed_in_use(self, client, admin, in_use):
        f, h = in_use["flow"], in_use["h"]
        dev, ver = state_id(f, "En desarrollo"), state_id(f, "En verificación")
        assert client.delete(f"/flows/{f['id']}/transitions/{dev}/{ver}", headers=admin).status_code == 204
        # the item is left with no way out
        assert move(client, h, in_use["tid"], in_use["tag"], ver).status_code == 409
        r = client.post(f"/flows/{f['id']}/transitions", json={"from_state_id": dev, "to_state_id": ver},
                        headers=admin)
        assert r.status_code == 201
        assert move(client, h, in_use["tid"], in_use["tag"], ver).status_code == 200

    @pytest.mark.parametrize("pair,code", [("same", 422), ("dup", 422), ("foreign", 404)])
    def test_invalid_transitions(self, client, admin, in_use, pair, code):
        f = in_use["flow"]
        dev, ver = state_id(f, "En desarrollo"), state_id(f, "En verificación")
        other = flow(client, admin, name="Otro").json()["states"][0]["id"]
        body = {"same": (dev, dev), "dup": (dev, ver), "foreign": (dev, other)}[pair]
        r = client.post(f"/flows/{f['id']}/transitions",
                        json={"from_state_id": body[0], "to_state_id": body[1]}, headers=admin)
        assert r.status_code == code

    def test_deleting_missing_transition_returns_404(self, client, admin, in_use):
        f = in_use["flow"]
        a, b = state_id(f, "Terminada"), state_id(f, "Planificada")
        assert client.delete(f"/flows/{f['id']}/transitions/{a}/{b}", headers=admin).status_code == 404

    def test_flow_used_by_a_tag_cannot_be_deleted(self, client, admin, in_use):
        fid = in_use["flow"]["id"]
        r = client.delete(f"/flows/{fid}", headers=admin)
        assert r.status_code == 409 and "'Devslice'" in r.json()["detail"]
        unused = flow(client, admin, name="Libre").json()["id"]
        assert client.delete(f"/flows/{unused}", headers=admin).status_code == 204
        assert client.get(f"/flows/{unused}", headers=admin).status_code == 404

    def test_flow_of_an_assigned_tag_cannot_change(self, client, admin, in_use):
        tag = in_use["tag"]
        other = flow(client, admin, name="Otro").json()["id"]
        assert client.patch(f"/tags/{tag}", json={"flow_id": other}, headers=admin).status_code == 409
        assert client.patch(f"/tags/{tag}", json={"flow_id": None}, headers=admin).status_code == 409
        # renaming the tag (same flow) is fine
        assert client.patch(f"/tags/{tag}", json={"name": "Slice", "flow_id": in_use["flow"]["id"]},
                            headers=admin).status_code == 200
        client.delete(f"/tasks/{in_use['tid']}/tags/{tag}", headers=in_use["h"])
        assert client.patch(f"/tags/{tag}", json={"flow_id": other}, headers=admin).status_code == 200

    def test_empty_state_update_returns_422(self, client, admin, in_use):
        f = in_use["flow"]
        assert client.patch(f"/flows/{f['id']}/states/{f['states'][0]['id']}", json={},
                            headers=admin).status_code == 422

    def test_unknown_flow_or_state_returns_404(self, client, admin, in_use):
        f = in_use["flow"]
        assert client.get("/flows/999", headers=admin).status_code == 404
        assert client.patch(f"/flows/{f['id']}/states/999", json={"name": "X"}, headers=admin).status_code == 404
        assert client.delete(f"/flows/{f['id']}/states/999", headers=admin).status_code == 404
