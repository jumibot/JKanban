"""La prioridad de una tarea debe ser del proyecto de la tarea (PriorityNotInProject -> 422)."""
import pytest


@pytest.fixture
def setup(client, auth):
    _, h = auth
    p1 = client.post("/projects/", json={"name": "P1"}, headers=h).json()["id"]
    p2 = client.post("/projects/", json={"name": "P2"}, headers=h).json()["id"]
    g1 = client.post("/groups/", json={"name": "G1", "project_id": p1}, headers=h).json()["id"]
    g2 = client.post("/groups/", json={"name": "G2", "project_id": p2}, headers=h).json()["id"]
    own = client.post(f"/projects/{p1}/priorities/", json={"name": "Alta"}, headers=h).json()["id"]
    foreign = client.post(f"/projects/{p2}/priorities/", json={"name": "Ajena"}, headers=h).json()["id"]
    return {"h": h, "g1": g1, "g2": g2, "own": own, "foreign": foreign}


class TestCreate:
    def test_own_priority_is_accepted(self, client, setup):
        r = client.post("/tasks/", json={"group_id": setup["g1"], "title": "T",
                                         "priority_id": setup["own"]}, headers=setup["h"])
        assert r.status_code == 201
        assert r.json()["priority"]["id"] == setup["own"]

    def test_foreign_priority_returns_422(self, client, setup):
        r = client.post("/tasks/", json={"group_id": setup["g1"], "title": "T",
                                         "priority_id": setup["foreign"]}, headers=setup["h"])
        assert r.status_code == 422
        assert "does not belong" in r.json()["detail"]
        assert client.get(f"/groups/{setup['g1']}/tasks", headers=setup["h"]).json() == []

    def test_unknown_priority_still_returns_404(self, client, setup):
        r = client.post("/tasks/", json={"group_id": setup["g1"], "title": "T",
                                         "priority_id": 999}, headers=setup["h"])
        assert r.status_code == 404


class TestUpdate:
    @pytest.fixture
    def task(self, client, setup):
        return client.post("/tasks/", json={"group_id": setup["g1"], "title": "T"},
                           headers=setup["h"]).json()["id"]

    def test_own_priority_is_accepted(self, client, setup, task):
        r = client.patch(f"/tasks/{task}", json={"priority_id": setup["own"]}, headers=setup["h"])
        assert r.status_code == 200
        assert r.json()["priority"]["id"] == setup["own"]

    def test_foreign_priority_returns_422_and_nothing_changes(self, client, setup, task):
        r = client.patch(f"/tasks/{task}", json={"priority_id": setup["foreign"], "title": "Nuevo"},
                         headers=setup["h"])
        assert r.status_code == 422
        t = client.get(f"/tasks/{task}", headers=setup["h"]).json()
        assert (t["priority"], t["title"]) == (None, "T")

    def test_priority_can_be_cleared(self, client, setup, task):
        client.patch(f"/tasks/{task}", json={"priority_id": setup["own"]}, headers=setup["h"])
        r = client.patch(f"/tasks/{task}", json={"priority_id": None}, headers=setup["h"])
        assert r.status_code == 200
        assert r.json()["priority"] is None

    def test_other_fields_unaffected(self, client, setup, task):
        r = client.patch(f"/tasks/{task}", json={"title": "Otro"}, headers=setup["h"])
        assert r.status_code == 200
