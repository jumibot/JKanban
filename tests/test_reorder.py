"""Reordenación de grupos (columnas) y de tareas dentro de un grupo."""


def _project(client, headers) -> int:
    return client.post("/projects/", json={"name": "P"}, headers=headers).json()["id"]


def _groups(client, headers, pid, names):
    return [client.post("/groups/", json={"name": n, "project_id": pid}, headers=headers).json()["id"]
            for n in names]


def _tasks(client, headers, gid, titles):
    return [client.post("/tasks/", json={"group_id": gid, "title": t}, headers=headers).json()["id"]
            for t in titles]


class TestReorderGroups:
    def test_reorder_sets_sort_order(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        a, b, c = _groups(client, h, pid, "ABC")
        r = client.patch("/groups/reorder", json={"project_id": pid, "group_ids": [c, a, b]}, headers=h)
        assert r.status_code == 204
        groups = client.get(f"/projects/{pid}/groups", headers=h).json()
        assert [g["name"] for g in sorted(groups, key=lambda g: g["sort_order"])] == ["C", "A", "B"]

    def test_new_group_goes_last(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        a, b = _groups(client, h, pid, "AB")
        client.patch("/groups/reorder", json={"project_id": pid, "group_ids": [b, a]}, headers=h)
        _groups(client, h, pid, "C")
        groups = client.get(f"/projects/{pid}/groups", headers=h).json()
        assert [g["name"] for g in sorted(groups, key=lambda g: g["sort_order"])] == ["B", "A", "C"]

    def test_foreign_group_is_rejected_and_nothing_changes(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        a, b = _groups(client, h, pid, "AB")
        other = _project(client, h)
        (foreign,) = _groups(client, h, other, "X")
        r = client.patch("/groups/reorder", json={"project_id": pid, "group_ids": [b, foreign, a]}, headers=h)
        assert r.status_code == 404
        assert str(foreign) in r.json()["detail"]
        assert client.get(f"/groups/{foreign}", headers=h).json()["sort_order"] == 0
        groups = client.get(f"/projects/{pid}/groups", headers=h).json()
        assert [g["name"] for g in sorted(groups, key=lambda g: g["sort_order"])] == ["A", "B"]

    def test_cannot_reorder_groups_of_a_project_without_access(self, client, auth, admin_auth):
        """Con acceso a un proyecto propio no se pueden reordenar grupos ajenos."""
        _, h = auth
        _, other = admin_auth
        victim = _project(client, h)
        a, b = _groups(client, h, victim, "AB")
        mine = client.post("/projects/", json={"name": "Mío"}, headers=other).json()["id"]
        r = client.patch("/groups/reorder", json={"project_id": mine, "group_ids": [b, a]}, headers=other)
        assert r.status_code == 404
        groups = client.get(f"/projects/{victim}/groups", headers=h).json()
        assert [g["name"] for g in sorted(groups, key=lambda g: g["sort_order"])] == ["A", "B"]

    def test_unknown_group_returns_404(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        r = client.patch("/groups/reorder", json={"project_id": pid, "group_ids": [999]}, headers=h)
        assert r.status_code == 404

    def test_duplicate_ids_return_422(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        a, b = _groups(client, h, pid, "AB")
        r = client.patch("/groups/reorder", json={"project_id": pid, "group_ids": [a, b, a]}, headers=h)
        assert r.status_code == 422

    def test_requires_auth(self, client):
        r = client.patch("/groups/reorder", json={"project_id": 1, "group_ids": []})
        assert r.status_code == 401

    def test_requires_project_access(self, client, auth, admin_auth):
        _, h = auth
        _, other = admin_auth
        pid = _project(client, h)
        ids = _groups(client, h, pid, "AB")
        r = client.patch("/groups/reorder", json={"project_id": pid, "group_ids": ids[::-1]}, headers=other)
        assert r.status_code in (403, 404)


class TestReorderTasks:
    def test_reorder_sets_sort_order(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        (gid,) = _groups(client, h, pid, "G")
        a, b, c = _tasks(client, h, gid, "ABC")
        r = client.patch(f"/groups/{gid}/tasks/reorder", json={"task_ids": [b, c, a]}, headers=h)
        assert r.status_code == 204
        tasks = client.get(f"/groups/{gid}/tasks", headers=h).json()
        assert [t["title"] for t in sorted(tasks, key=lambda t: t["sort_order"])] == ["B", "C", "A"]

    def test_task_from_another_group_is_rejected_and_nothing_changes(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        g1, g2 = _groups(client, h, pid, ["G1", "G2"])
        a, b = _tasks(client, h, g1, "AB")
        (foreign,) = _tasks(client, h, g2, "X")
        r = client.patch(f"/groups/{g1}/tasks/reorder", json={"task_ids": [b, foreign, a]}, headers=h)
        assert r.status_code == 404
        assert str(foreign) in r.json()["detail"]
        tasks = client.get(f"/groups/{g1}/tasks", headers=h).json()
        assert [t["title"] for t in sorted(tasks, key=lambda t: t["sort_order"])] == ["A", "B"]
        assert client.get(f"/tasks/{foreign}", headers=h).json()["sort_order"] == 0

    def test_cannot_reorder_tasks_of_a_project_without_access(self, client, auth, admin_auth):
        _, h = auth
        _, other = admin_auth
        victim = _project(client, h)
        (vg,) = _groups(client, h, victim, "G")
        a, b = _tasks(client, h, vg, "AB")
        mine = client.post("/projects/", json={"name": "Mío"}, headers=other).json()["id"]
        (my_group,) = _groups(client, other, mine, "M")
        r = client.patch(f"/groups/{my_group}/tasks/reorder", json={"task_ids": [b, a]}, headers=other)
        assert r.status_code == 404
        tasks = client.get(f"/groups/{vg}/tasks", headers=h).json()
        assert [t["title"] for t in sorted(tasks, key=lambda t: t["sort_order"])] == ["A", "B"]

    def test_duplicate_ids_return_422(self, client, auth):
        _, h = auth
        pid = _project(client, h)
        (gid,) = _groups(client, h, pid, "G")
        a, b = _tasks(client, h, gid, "AB")
        r = client.patch(f"/groups/{gid}/tasks/reorder", json={"task_ids": [a, a, b]}, headers=h)
        assert r.status_code == 422

    def test_group_not_found(self, client, auth):
        _, h = auth
        r = client.patch("/groups/999/tasks/reorder", json={"task_ids": []}, headers=h)
        assert r.status_code == 404

    def test_requires_project_access(self, client, auth, admin_auth):
        _, h = auth
        _, other = admin_auth
        pid = _project(client, h)
        (gid,) = _groups(client, h, pid, "G")
        ids = _tasks(client, h, gid, "AB")
        r = client.patch(f"/groups/{gid}/tasks/reorder", json={"task_ids": ids[::-1]}, headers=other)
        assert r.status_code in (403, 404)
