import pytest
from fastapi.testclient import TestClient
from backend.interfaces.dependencies import get_user_use_cases


# ── Helpers ───────────────────────────────────────────────────────────────────

def create_user(client, name="User", email="user@test.com", password="pass1234"):
    return client.post("/users/", json={"name": name, "email": email, "password": password}).json()["id"]


def login(client, email, password="pass1234"):
    r = client.post("/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def make_admin(user_id):
    get_user_use_cases().update(user_id, {"is_admin": True})


def create_project_with_data(client, headers, name="Proyecto"):
    """Creates a project with 1 group, 1 task and returns project_id."""
    pid = client.post("/projects/", json={"name": name}, headers=headers).json()["id"]
    gid = client.post("/groups/", json={"name": "Col", "color": "#3B82F6", "project_id": pid}, headers=headers).json()["id"]
    client.post("/tasks/", json={"group_id": gid, "title": "Task"}, headers=headers)
    return pid


# ── GET /admin/users/{id}/deletion-preview ────────────────────────────────────

class TestDeletionPreview:
    def test_requires_auth(self, client):
        assert client.get("/admin/users/1/deletion-preview").status_code == 401

    def test_requires_admin(self, client, auth):
        _, h = auth
        uid = create_user(client, email="target@test.com")
        assert client.get(f"/admin/users/{uid}/deletion-preview", headers=h).status_code == 403

    def test_not_found_returns_404(self, client, admin_auth):
        _, ha = admin_auth
        assert client.get("/admin/users/9999/deletion-preview", headers=ha).status_code == 404

    def test_user_without_projects(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, email="empty@test.com")
        data = client.get(f"/admin/users/{uid}/deletion-preview", headers=ha).json()
        assert data["user"]["id"] == uid
        assert data["projects"] == []
        assert data["totals"]["projects"] == 0

    def test_user_with_projects(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, name="Owner", email="owner@test.com")
        make_admin(uid)
        h_owner = login(client, "owner@test.com")
        create_project_with_data(client, h_owner, "P1")
        create_project_with_data(client, h_owner, "P2")

        data = client.get(f"/admin/users/{uid}/deletion-preview", headers=ha).json()
        assert data["totals"]["projects"] == 2
        assert data["totals"]["groups"] == 2
        assert data["totals"]["tasks"] == 2
        assert len(data["projects"]) == 2

    def test_project_counts_are_correct(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, name="Owner", email="owner@test.com")
        make_admin(uid)
        h_owner = login(client, "owner@test.com")
        pid = create_project_with_data(client, h_owner, "P")
        # Add a tag and priority
        client.post(f"/projects/{pid}/tags/", json={"name": "T", "color": "#3B82F6"}, headers=h_owner)
        client.post(f"/projects/{pid}/priorities/", json={"name": "High", "icon": "flag", "color": "#EF4444"}, headers=h_owner)

        data = client.get(f"/admin/users/{uid}/deletion-preview", headers=ha).json()
        p = data["projects"][0]
        assert p["groups_count"] == 1
        assert p["tasks_count"] == 1
        assert p["tags_count"] == 1
        assert p["priorities_count"] == 1


# ── DELETE /admin/users/{id}/cascade ─────────────────────────────────────────

class TestCascadeDelete:
    def test_requires_auth(self, client):
        assert client.request("DELETE", "/admin/users/1/cascade",
                              json={"admin_password": "x"}).status_code == 401

    def test_requires_admin(self, client, auth):
        _, h = auth
        uid = create_user(client, email="target@test.com")
        assert client.request("DELETE", f"/admin/users/{uid}/cascade",
                              json={"admin_password": "authpass123"}, headers=h).status_code == 403

    def test_not_found_returns_404(self, client, admin_auth):
        _, ha = admin_auth
        assert client.request("DELETE", "/admin/users/9999/cascade",
                              json={"admin_password": "adminpass123"}, headers=ha).status_code == 404

    def test_wrong_password_returns_403(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, email="target@test.com")
        assert client.request("DELETE", f"/admin/users/{uid}/cascade",
                              json={"admin_password": "wrongpass"}, headers=ha).status_code == 403

    def test_cannot_delete_self(self, client, admin_auth):
        admin, ha = admin_auth
        assert client.request("DELETE", f"/admin/users/{admin['id']}/cascade",
                              json={"admin_password": "adminpass123"}, headers=ha).status_code == 400

    def test_deletes_user_without_projects(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, email="target@test.com")
        assert client.request("DELETE", f"/admin/users/{uid}/cascade",
                              json={"admin_password": "adminpass123"}, headers=ha).status_code == 204
        assert client.get(f"/users/{uid}", headers=ha).status_code == 404

    def test_deletes_user_with_projects_in_cascade(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, name="Owner", email="owner@test.com")
        make_admin(uid)
        h_owner = login(client, "owner@test.com")
        pid = create_project_with_data(client, h_owner, "P")

        assert client.request("DELETE", f"/admin/users/{uid}/cascade",
                              json={"admin_password": "adminpass123"}, headers=ha).status_code == 204

        # User gone
        assert client.get(f"/users/{uid}", headers=ha).status_code == 404
        # Project gone
        assert client.get(f"/projects/{pid}", headers=ha).status_code == 404

    def test_cascade_removes_groups_and_tasks(self, client, admin_auth):
        _, ha = admin_auth
        uid = create_user(client, name="Owner", email="owner@test.com")
        make_admin(uid)
        h_owner = login(client, "owner@test.com")
        pid = create_project_with_data(client, h_owner, "P")
        gid = client.get(f"/projects/{pid}/groups", headers=ha).json()[0]["id"]

        client.request("DELETE", f"/admin/users/{uid}/cascade",
                       json={"admin_password": "adminpass123"}, headers=ha)

        assert client.get(f"/groups/{gid}", headers=ha).status_code == 404
