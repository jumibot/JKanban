"""SQLite seed data.

Populates a fresh database with demo content.
Only runs when the users table is empty; safe to call on every startup.

Uses ? placeholders directly because this module is SQLite-specific and
the calls go through SQLiteConnection which leaves ? untouched.
"""
from backend.infrastructure.persistence.sqlite.connection import get_connection


def seed_db() -> None:
    with get_connection() as conn:
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
            return

        # ── Usuarios ──────────────────────────────────────────────────────────
        u_alice = conn.execute(
            "INSERT INTO users (name, email, password_hash, avatar_url, is_admin) VALUES (?,?,?,?,1)",
            ("Alice Martín", "alice@example.com", "pbkdf2$seed$placeholder", "https://i.pravatar.cc/40?img=1"),
        ).lastrowid
        u_bob = conn.execute(
            "INSERT INTO users (name, email, password_hash, avatar_url) VALUES (?,?,?,?)",
            ("Bob Chen", "bob@example.com", "pbkdf2$seed$placeholder", "https://i.pravatar.cc/40?img=3"),
        ).lastrowid
        u_carol = conn.execute(
            "INSERT INTO users (name, email, password_hash, avatar_url) VALUES (?,?,?,?)",
            ("Carol López", "carol@example.com", "pbkdf2$seed$placeholder", "https://i.pravatar.cc/40?img=5"),
        ).lastrowid

        proj_default = conn.execute(
            """INSERT INTO projects (name, description, icon, color, owner_id, leader_id)
               VALUES (?,?,?,?,?,?)""",
            ("Proyecto Principal", "Tablero de tareas general del equipo",
             "rocket_launch", "#3B82F6", u_alice, u_alice),
        ).lastrowid

        conn.executemany(
            "INSERT INTO project_members (project_id, user_id) VALUES (?,?)",
            [(proj_default, u_bob), (proj_default, u_carol)],
        )

        # ── Prioridades ───────────────────────────────────────────────────────
        p_critical = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("Critical", "emergency", "#EF4444", proj_default),
        ).lastrowid
        p_high = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("High", "arrow_upward", "#F97316", proj_default),
        ).lastrowid
        p_normal = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("Normal", "remove", "#3B82F6", proj_default),
        ).lastrowid
        p_low = conn.execute(
            "INSERT INTO priorities (name, icon, color, project_id) VALUES (?,?,?,?)",
            ("Low", "arrow_downward", "#6B7280", proj_default),
        ).lastrowid

        conn.execute("UPDATE projects SET priority_id=? WHERE id=?", (p_normal, proj_default))

        # ── Grupos ────────────────────────────────────────────────────────────
        g_backlog = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("Backlog", "Tareas pendientes de planificación", "#6B7280", proj_default),
        ).lastrowid
        g_progress = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("En Progreso", "Tareas actualmente en desarrollo", "#F59E0B", proj_default),
        ).lastrowid
        g_review = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("En Revisión", "Pendiente de revisión y QA", "#8B5CF6", proj_default),
        ).lastrowid
        g_done = conn.execute(
            "INSERT INTO groups (name, description, color, project_id) VALUES (?,?,?,?)",
            ("Completado", "Tareas finalizadas y entregadas", "#10B981", proj_default),
        ).lastrowid

        # ── Tags ──────────────────────────────────────────────────────────────
        t_backend  = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Backend",       "#3B82F6", proj_default)).lastrowid
        t_frontend = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Frontend",      "#F97316", proj_default)).lastrowid
        t_urgent   = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Urgente",       "#EF4444", proj_default)).lastrowid
        t_docs     = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Documentación", "#8B5CF6", proj_default)).lastrowid
        t_debt     = conn.execute("INSERT INTO tags (name, color, project_id) VALUES (?,?,?)", ("Deuda técnica", "#6B7280", proj_default)).lastrowid

        # ── Tareas ────────────────────────────────────────────────────────────
        tasks_data = [
            (g_backlog,  u_carol, p_normal,   "Diseñar wireframes del dashboard",
             "Crear wireframes de baja fidelidad para las vistas principales",
             0, 4.0, "2024-02-05T09:00:00", "2024-02-09T18:00:00", None, None),
            (g_backlog,  u_bob,   p_high,     "Escribir tests de integración",
             "Cobertura de los endpoints críticos con pytest y TestClient",
             0, 6.0, "2024-02-12T09:00:00", "2024-02-14T18:00:00", None, None),
            (g_backlog,  u_alice, p_low,      "Documentar API con OpenAPI",
             "Revisar y completar descripciones de todos los endpoints",
             0, 2.0, None, None, None, None),
            (g_progress, u_bob,   p_critical, "Implementar autenticación JWT",
             "Login, refresh token y middleware de autenticación",
             0, 8.0, "2024-01-22T09:00:00", "2024-01-29T18:00:00", "2024-01-23T09:00:00", None),
            (g_progress, u_alice, p_high,     "Refactorizar módulo de notificaciones",
             "Extraer lógica de envío a un servicio independiente",
             0, 5.0, "2024-01-24T09:00:00", "2024-01-28T18:00:00", "2024-01-24T10:00:00", None),
            (g_review,   u_carol, p_normal,   "Revisar paleta de colores y tipografía",
             "Validar contraste WCAG AA en todos los componentes",
             0, 2.0, "2024-01-18T09:00:00", "2024-01-19T18:00:00", "2024-01-18T09:00:00", None),
            (g_review,   u_alice, p_high,     "Code review módulo de pagos",
             "Revisar integración con Stripe y manejo de errores",
             0, 3.0, None, None, "2024-01-20T09:00:00", None),
            (g_done,     u_bob,   p_normal,   "Configurar entorno de desarrollo",
             "Docker Compose con PostgreSQL, Redis y hot-reload",
             1, 2.0, "2024-01-10T09:00:00", "2024-01-11T18:00:00", "2024-01-10T09:00:00", "2024-01-11T16:30:00"),
            (g_done,     u_alice, p_low,      "Definir arquitectura del sistema",
             "ADR con decisiones sobre Clean Architecture y stack tecnológico",
             1, 4.0, "2024-01-08T09:00:00", "2024-01-09T18:00:00", "2024-01-08T09:00:00", "2024-01-09T17:00:00"),
        ]

        task_ids = []
        for t in tasks_data:
            tid = conn.execute(
                """INSERT INTO tasks
                       (group_id, user_id, priority_id, title, description, completed,
                        estimated_duration, estimated_start, estimated_end, actual_start, actual_end)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                t,
            ).lastrowid
            task_ids.append(tid)

        conn.executemany(
            "INSERT INTO task_tags (task_id, tag_id) VALUES (?,?)",
            [
                (task_ids[0], t_frontend),
                (task_ids[1], t_backend), (task_ids[1], t_debt),
                (task_ids[2], t_docs),
                (task_ids[3], t_backend), (task_ids[3], t_urgent),
                (task_ids[4], t_backend), (task_ids[4], t_debt),
                (task_ids[5], t_frontend), (task_ids[5], t_docs),
                (task_ids[6], t_backend),
                (task_ids[8], t_docs),
            ],
        )

        conn.executemany(
            "INSERT INTO group_tags (group_id, tag_id) VALUES (?,?)",
            [(g_backlog, t_debt), (g_progress, t_urgent), (g_review, t_docs)],
        )

        conn.executemany(
            "INSERT INTO todo_items (task_id, title, completed, sort_order) VALUES (?,?,?,?)",
            [
                (task_ids[3], "Crear modelo User y migración de BD",  1, 0),
                (task_ids[3], "Implementar endpoint /auth/login",      1, 1),
                (task_ids[3], "Añadir middleware de validación",       0, 2),
                (task_ids[4], "Extraer servicio EmailService",  0, 0),
                (task_ids[4], "Añadir tests unitarios",         0, 1),
                (task_ids[4], "Documentar la interfaz pública", 1, 2),
                (task_ids[0], "Vista de lista de tareas",   0, 0),
                (task_ids[0], "Vista de detalle de tarea",  0, 1),
                (task_ids[0], "Flujo de creación de tarea", 0, 2),
                (task_ids[7], "Crear docker-compose.yml",        1, 0),
                (task_ids[7], "Configurar variables de entorno", 1, 1),
            ],
        )
        conn.commit()
