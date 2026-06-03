from __future__ import annotations

import hashlib
import os
import sqlite3
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import streamlit as st


APP_TITLE = "Organizador académico y personal"
DB_PATH = Path(__file__).with_name("organizador.db")
ENERGY_LEVELS = ["Alta", "Media", "Baja"]
EVALUATION_TYPES = [
    "Prueba",
    "Certamen",
    "Control",
    "Laboratorio",
    "Informe",
    "Tarea",
    "Examen",
    "Otro",
]
EVALUATION_STATES = ["Pendiente", "Rendida", "Reprogramada", "Cancelada"]
EXERCISE_STATES = ["No realizado", "Realizado con dificultad", "Comprendido y resuelto"]
ACTIVITY_TYPES = ["Fija", "Flexible"]
DAYS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS profiles (
                user_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL DEFAULT '',
                university TEXT NOT NULL DEFAULT '',
                sct_hours REAL NOT NULL DEFAULT 27,
                usual_sleep REAL NOT NULL DEFAULT 7,
                needed_sleep REAL NOT NULL DEFAULT 8,
                energy_morning TEXT NOT NULL DEFAULT 'Media',
                energy_afternoon TEXT NOT NULL DEFAULT 'Media',
                energy_night TEXT NOT NULL DEFAULT 'Media',
                setup_complete INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS semesters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                semester_id INTEGER,
                name TEXT NOT NULL,
                sct REAL NOT NULL DEFAULT 0,
                theory_hours REAL NOT NULL DEFAULT 0,
                lab_hours REAL NOT NULL DEFAULT 0,
                target_grade REAL NOT NULL DEFAULT 5.0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (semester_id) REFERENCES semesters(id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS personal_responsibilities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                hours_week REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS personal_goals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                frequency TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                date TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 0,
                state TEXT NOT NULL DEFAULT 'Pendiente',
                grade REAL,
                content TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS exercise_guides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                total INTEGER NOT NULL DEFAULT 0,
                understood INTEGER NOT NULL DEFAULT 0,
                difficult INTEGER NOT NULL DEFAULT 0,
                pending INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS study_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                subject_id INTEGER NOT NULL,
                minutes INTEGER NOT NULL,
                method TEXT NOT NULL,
                session_date TEXT NOT NULL,
                productivity TEXT,
                comprehension TEXT,
                difficulty TEXT,
                concentration TEXT,
                notes TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                day TEXT NOT NULL,
                start_hour INTEGER NOT NULL,
                end_hour INTEGER NOT NULL,
                type TEXT NOT NULL,
                category TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS weekly_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                review_date TEXT NOT NULL,
                went_well TEXT NOT NULL,
                difficult TEXT NOT NULL,
                improve TEXT NOT NULL,
                feeling TEXT NOT NULL,
                realistic TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );
            """
        )


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt, _ = stored.split("$", 1)
    return hash_password(password, salt) == stored


def fetch_all(query: str, params: tuple = ()) -> list[sqlite3.Row]:
    with connect() as conn:
        return conn.execute(query, params).fetchall()


def fetch_one(query: str, params: tuple = ()) -> sqlite3.Row | None:
    with connect() as conn:
        return conn.execute(query, params).fetchone()


def execute(query: str, params: tuple = ()) -> None:
    with connect() as conn:
        conn.execute(query, params)


def create_user(email: str, password: str) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (email, password_hash, created_at) VALUES (?, ?, ?)",
            (email.strip().lower(), hash_password(password), now),
        )
        user_id = cur.lastrowid
        conn.execute("INSERT INTO profiles (user_id) VALUES (?)", (user_id,))
        conn.execute(
            "INSERT INTO semesters (user_id, name, active, created_at) VALUES (?, ?, 1, ?)",
            (user_id, f"Semestre {date.today().year}", now),
        )
        return int(user_id)


def authenticate(email: str, password: str) -> int | None:
    row = fetch_one("SELECT id, password_hash FROM users WHERE email = ?", (email.strip().lower(),))
    if row and verify_password(password, row["password_hash"]):
        return int(row["id"])
    return None


def active_semester_id(user_id: int) -> int:
    row = fetch_one("SELECT id FROM semesters WHERE user_id = ? AND active = 1 ORDER BY id DESC", (user_id,))
    if row:
        return int(row["id"])
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO semesters (user_id, name, active, created_at) VALUES (?, ?, 1, ?)",
            (user_id, f"Semestre {date.today().year}", now),
        )
        return int(cur.lastrowid)


def subjects(user_id: int) -> list[sqlite3.Row]:
    return fetch_all(
        "SELECT * FROM subjects WHERE user_id = ? AND semester_id = ? ORDER BY name",
        (user_id, active_semester_id(user_id)),
    )


def subject_options(user_id: int) -> dict[str, int]:
    return {row["name"]: int(row["id"]) for row in subjects(user_id)}


def grade_average(subject_id: int) -> float | None:
    rows = fetch_all(
        "SELECT grade, weight FROM evaluations WHERE subject_id = ? AND state = 'Rendida' AND grade IS NOT NULL",
        (subject_id,),
    )
    total_weight = sum(float(row["weight"]) for row in rows)
    if not rows:
        return None
    if total_weight <= 0:
        return sum(float(row["grade"]) for row in rows) / len(rows)
    return sum(float(row["grade"]) * float(row["weight"]) for row in rows) / total_weight


def subject_progress(subject_id: int) -> tuple[int, int, int]:
    row = fetch_one(
        """
        SELECT
            COALESCE(SUM(understood), 0) AS understood,
            COALESCE(SUM(difficult), 0) AS difficult,
            COALESCE(SUM(pending), 0) AS pending
        FROM exercise_guides
        WHERE subject_id = ?
        """,
        (subject_id,),
    )
    return int(row["understood"]), int(row["difficult"]), int(row["pending"])


def setup_progress(user_id: int) -> tuple[int, list[str]]:
    profile = fetch_one("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    checks = [
        ("Perfil personal", bool(profile and profile["name"] and profile["university"])),
        ("Energía diaria", bool(profile and profile["energy_morning"] and profile["energy_afternoon"] and profile["energy_night"])),
        ("Asignaturas", len(subjects(user_id)) > 0),
        ("Horario o responsabilidades", bool(fetch_one("SELECT id FROM activities WHERE user_id = ? LIMIT 1", (user_id,))) or bool(fetch_one("SELECT id FROM personal_responsibilities WHERE user_id = ? LIMIT 1", (user_id,)))),
    ]
    completed = sum(1 for _, ok in checks if ok)
    return int(completed / len(checks) * 100), [label for label, ok in checks if not ok]


def recommendation(user_id: int) -> tuple[str, str, str]:
    subj_rows = subjects(user_id)
    if not subj_rows:
        return (
            "Agrega tus asignaturas",
            "El sistema necesita conocer tus ramos para ayudarte a ordenar prioridades.",
            "Después podrá sugerir bloques de estudio más realistas.",
        )

    upcoming = fetch_all(
        """
        SELECT e.*, s.name AS subject_name, s.target_grade
        FROM evaluations e
        JOIN subjects s ON s.id = e.subject_id
        WHERE e.user_id = ? AND e.state IN ('Pendiente', 'Reprogramada')
        ORDER BY date(e.date) ASC
        """,
        (user_id,),
    )
    today = date.today()
    if upcoming:
        ev = upcoming[0]
        days = max((date.fromisoformat(ev["date"]) - today).days, 0)
        understood, difficult, pending = subject_progress(int(ev["subject_id"]))
        if days <= 3:
            return (
                f"Dedica un bloque breve a {ev['subject_name']}",
                f"{ev['name']} está a {days} día(s) y aún hay {pending} ejercicio(s) pendientes.",
                "Un repaso enfocado puede bajar la carga mental sin sacrificar descanso.",
            )
        if pending + difficult > understood:
            return (
                f"Trabaja ejercicios de {ev['subject_name']}",
                "La próxima evaluación se acerca y conviene priorizar comprensión, no solo acumular horas.",
                "Resolver menos ejercicios, pero entenderlos bien, mejora la preparación para problemas nuevos.",
            )

    at_risk = []
    for subj in subj_rows:
        avg = grade_average(int(subj["id"]))
        understood, difficult, pending = subject_progress(int(subj["id"]))
        score = 0
        if avg is not None and avg < float(subj["target_grade"]):
            score += 3
        score += min(pending // 5, 3)
        score += min(difficult // 4, 2)
        at_risk.append((score, subj, avg))
    at_risk.sort(key=lambda item: item[0], reverse=True)
    if at_risk and at_risk[0][0] > 0:
        _, subj, avg = at_risk[0]
        average_text = "sin promedio registrado" if avg is None else f"promedio actual {avg:.1f}"
        return (
            f"Revisa el avance de {subj['name']}",
            f"Tu meta es {subj['target_grade']:.1f} y el ramo aparece con {average_text}.",
            "Una sesión corta con ejercicios comprendidos deja mejor evidencia para decidir el próximo paso.",
        )

    return (
        "Protege un bloque de recuperación",
        "No hay una urgencia académica fuerte registrada en este momento.",
        "Mantener descanso y vida personal ayuda a sostener el rendimiento durante el semestre.",
    )


def risk_label(subject: sqlite3.Row) -> str:
    avg = grade_average(int(subject["id"]))
    understood, difficult, pending = subject_progress(int(subject["id"]))
    score = 0
    if avg is not None and avg < float(subject["target_grade"]):
        score += 2
    if pending > understood:
        score += 1
    if difficult > understood:
        score += 1
    if score >= 3:
        return "Prioridad alta"
    if score >= 1:
        return "Prioridad media"
    return "Prioridad baja"


def auth_view() -> None:
    st.title(APP_TITLE)
    st.caption("Una guía para organizar estudio, responsabilidades, descanso y bienestar.")
    login_tab, register_tab = st.tabs(["Iniciar sesión", "Crear cuenta"])

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Correo electrónico", key="login_email")
            password = st.text_input("Contraseña", type="password", key="login_password")
            submit = st.form_submit_button("Entrar", use_container_width=True)
        if submit:
            user_id = authenticate(email, password)
            if user_id:
                st.session_state.user_id = user_id
                st.rerun()
            st.error("Correo o contraseña incorrectos.")

    with register_tab:
        with st.form("register_form"):
            email = st.text_input("Correo electrónico", key="register_email")
            password = st.text_input("Contraseña", type="password", key="register_password")
            password_2 = st.text_input("Repetir contraseña", type="password")
            submit = st.form_submit_button("Crear cuenta", use_container_width=True)
        if submit:
            if not email or len(password) < 6:
                st.warning("Usa un correo y una contraseña de al menos 6 caracteres.")
            elif password != password_2:
                st.warning("Las contraseñas no coinciden.")
            else:
                try:
                    st.session_state.user_id = create_user(email, password)
                    st.success("Cuenta creada. Vamos a configurar tu espacio.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Ese correo ya está registrado.")


def sidebar(user_id: int) -> str:
    profile = fetch_one("SELECT name FROM profiles WHERE user_id = ?", (user_id,))
    st.sidebar.title(APP_TITLE)
    st.sidebar.caption(f"Hola, {profile['name'] or 'estudiante'}")
    page = st.sidebar.radio(
        "Navegación",
        [
            "Dashboard",
            "Configuración inicial",
            "Asignaturas",
            "Horario",
            "Evaluaciones",
            "Ejercicios",
            "Estudio y reflexión",
            "Metas personales",
            "Revisión semanal",
            "Estadísticas",
            "Semestres",
        ],
    )
    if st.sidebar.button("Cerrar sesión", use_container_width=True):
        st.session_state.clear()
        st.rerun()
    return page


def setup_view(user_id: int) -> None:
    progress, missing = setup_progress(user_id)
    st.header("Configuración inicial")
    st.progress(progress / 100, text=f"{progress}% completado")
    if missing:
        st.info("Falta completar: " + ", ".join(missing))
    else:
        st.success("La configuración base está completa. Puedes ajustarla cuando quieras.")
        execute("UPDATE profiles SET setup_complete = 1 WHERE user_id = ?", (user_id,))

    profile = fetch_one("SELECT * FROM profiles WHERE user_id = ?", (user_id,))
    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nombre", value=profile["name"])
            university = st.text_input("Universidad", value=profile["university"] or "ULS")
            sct_hours = st.number_input("Horas por SCT", min_value=1.0, max_value=60.0, value=float(profile["sct_hours"]), step=0.5)
        with col2:
            usual_sleep = st.number_input("Horas de sueño habituales", min_value=0.0, max_value=14.0, value=float(profile["usual_sleep"]), step=0.5)
            needed_sleep = st.number_input("Horas necesarias para sentirte descansado", min_value=0.0, max_value=14.0, value=float(profile["needed_sleep"]), step=0.5)
        e1, e2, e3 = st.columns(3)
        with e1:
            morning = st.selectbox("Energía en la mañana", ENERGY_LEVELS, index=ENERGY_LEVELS.index(profile["energy_morning"]))
        with e2:
            afternoon = st.selectbox("Energía en la tarde", ENERGY_LEVELS, index=ENERGY_LEVELS.index(profile["energy_afternoon"]))
        with e3:
            night = st.selectbox("Energía en la noche", ENERGY_LEVELS, index=ENERGY_LEVELS.index(profile["energy_night"]))
        if st.form_submit_button("Guardar perfil", use_container_width=True):
            execute(
                """
                UPDATE profiles
                SET name = ?, university = ?, sct_hours = ?, usual_sleep = ?, needed_sleep = ?,
                    energy_morning = ?, energy_afternoon = ?, energy_night = ?
                WHERE user_id = ?
                """,
                (name, university, sct_hours, usual_sleep, needed_sleep, morning, afternoon, night, user_id),
            )
            st.success("Perfil guardado.")
            st.rerun()


def dashboard_view(user_id: int) -> None:
    progress, missing = setup_progress(user_id)
    st.header("Dashboard principal")
    if progress < 100:
        st.info("Completa la configuración inicial para recibir recomendaciones más precisas.")
        st.progress(progress / 100, text=f"{progress}% completado")

    upcoming = fetch_one(
        """
        SELECT e.name, e.date, s.name AS subject_name
        FROM evaluations e JOIN subjects s ON s.id = e.subject_id
        WHERE e.user_id = ? AND e.state IN ('Pendiente', 'Reprogramada')
        ORDER BY date(e.date) ASC
        LIMIT 1
        """,
        (user_id,),
    )
    col1, col2, col3 = st.columns(3)
    with col1:
        if upcoming:
            days = max((date.fromisoformat(upcoming["date"]) - date.today()).days, 0)
            st.metric("Próxima evaluación", upcoming["name"], f"{days} día(s)")
            st.caption(upcoming["subject_name"])
        else:
            st.metric("Próxima evaluación", "Sin pendientes")
            st.caption("Agrega evaluaciones para anticiparte.")
    with col2:
        minutes = fetch_one("SELECT COALESCE(SUM(minutes), 0) AS total FROM study_sessions WHERE user_id = ?", (user_id,))["total"]
        st.metric("Estudio registrado", f"{minutes / 60:.1f} h")
        st.caption("Todas las sesiones cuentan en una misma base.")
    with col3:
        completed = fetch_one("SELECT COALESCE(SUM(understood), 0) AS total FROM exercise_guides WHERE user_id = ?", (user_id,))["total"]
        st.metric("Ejercicios comprendidos", int(completed))
        st.caption("Comprender pesa más que acumular horas.")

    what, why, benefit = recommendation(user_id)
    st.subheader("Recomendación principal del día")
    st.write(f"**Qué hacer:** {what}")
    st.write(f"**Por qué hacerlo:** {why}")
    st.write(f"**Beneficio posible:** {benefit}")

    st.subheader("Progreso por asignatura")
    rows = subjects(user_id)
    if not rows:
        st.warning("Aún no hay asignaturas registradas.")
    for subj in rows:
        understood, difficult, pending = subject_progress(int(subj["id"]))
        total = max(understood + difficult + pending, 1)
        st.write(f"**{subj['name']}** · {risk_label(subj)}")
        st.progress(understood / total, text=f"{understood} comprendidos · {difficult} en proceso · {pending} pendientes")


def subjects_view(user_id: int) -> None:
    st.header("Asignaturas")
    default_subjects = ["Cálculo III", "Física II", "Programación", "Álgebra", "Química", "Estadística"]
    with st.form("subject_form"):
        col1, col2 = st.columns(2)
        with col1:
            preset = st.selectbox("Asignatura frecuente", ["Crear nueva"] + default_subjects)
            custom = st.text_input("Nombre de asignatura", value="" if preset != "Crear nueva" else "")
            sct = st.number_input("SCT", min_value=0.0, max_value=30.0, value=5.0, step=0.5)
        with col2:
            theory = st.number_input("Horas de teoría semanales", min_value=0.0, max_value=30.0, value=3.0, step=0.5)
            lab = st.number_input("Horas de laboratorio semanales", min_value=0.0, max_value=30.0, value=0.0, step=0.5)
            target = st.number_input("Nota objetivo", min_value=1.0, max_value=7.0, value=5.0, step=0.1)
        if st.form_submit_button("Agregar asignatura", use_container_width=True):
            name = custom.strip() or preset
            if name == "Crear nueva":
                st.warning("Escribe el nombre de la asignatura.")
            else:
                execute(
                    """
                    INSERT INTO subjects (user_id, semester_id, name, sct, theory_hours, lab_hours, target_grade)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, active_semester_id(user_id), name, sct, theory, lab, target),
                )
                st.success("Asignatura agregada.")
                st.rerun()

    rows = subjects(user_id)
    for subj in rows:
        avg = grade_average(int(subj["id"]))
        average_text = "Sin promedio" if avg is None else f"Promedio {avg:.1f}"
        with st.expander(f"{subj['name']} · Meta {subj['target_grade']:.1f} · {average_text}"):
            st.write(f"SCT: {subj['sct']} · Teoría: {subj['theory_hours']} h · Laboratorio: {subj['lab_hours']} h")
            if st.button("Eliminar asignatura", key=f"delete_subject_{subj['id']}"):
                execute("DELETE FROM subjects WHERE id = ? AND user_id = ?", (subj["id"], user_id))
                st.rerun()


def schedule_view(user_id: int) -> None:
    st.header("Constructor visual de horario")
    with st.form("activity_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            title = st.text_input("Actividad")
            day = st.selectbox("Día", DAYS)
        with col2:
            start = st.number_input("Hora de inicio", min_value=0, max_value=23, value=8)
            end = st.number_input("Hora de término", min_value=1, max_value=24, value=9)
        with col3:
            act_type = st.selectbox("Tipo", ACTIVITY_TYPES)
            category = st.text_input("Categoría", value="Estudio")
        if st.form_submit_button("Agregar actividad", use_container_width=True):
            if title and end > start:
                execute(
                    "INSERT INTO activities (user_id, title, day, start_hour, end_hour, type, category) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (user_id, title, day, int(start), int(end), act_type, category),
                )
                st.success("Actividad agregada.")
                st.rerun()
            else:
                st.warning("Revisa el nombre y las horas de la actividad.")

    rows = fetch_all("SELECT * FROM activities WHERE user_id = ? ORDER BY start_hour", (user_id,))
    grid = {hour: {day: "" for day in DAYS} for hour in range(24)}
    for row in rows:
        for hour in range(int(row["start_hour"]), int(row["end_hour"])):
            grid[hour][row["day"]] = f"{row['title']} ({row['type']})"
    st.dataframe(
        [{"Hora": f"{hour:02d}:00", **grid[hour]} for hour in range(24)],
        use_container_width=True,
        hide_index=True,
    )
    for row in rows:
        with st.expander(f"{row['day']} {row['start_hour']}:00-{row['end_hour']}:00 · {row['title']}"):
            st.write(f"Tipo: {row['type']} · Categoría: {row['category']}")
            if st.button("Eliminar actividad", key=f"delete_activity_{row['id']}"):
                execute("DELETE FROM activities WHERE id = ? AND user_id = ?", (row["id"], user_id))
                st.rerun()


def evaluations_view(user_id: int) -> None:
    st.header("Evaluaciones")
    options = subject_options(user_id)
    if not options:
        st.warning("Primero agrega una asignatura.")
        return
    with st.form("evaluation_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject_name = st.selectbox("Asignatura", list(options.keys()))
            name = st.text_input("Nombre")
            ev_type = st.selectbox("Tipo", EVALUATION_TYPES)
            ev_date = st.date_input("Fecha", value=date.today() + timedelta(days=7))
        with col2:
            weight = st.number_input("Ponderación", min_value=0.0, max_value=100.0, value=20.0, step=1.0)
            state = st.selectbox("Estado", EVALUATION_STATES)
            grade = st.number_input("Nota", min_value=0.0, max_value=7.0, value=0.0, step=0.1)
            content = st.text_area("Contenido evaluado (opcional)")
        if st.form_submit_button("Guardar evaluación", use_container_width=True):
            execute(
                """
                INSERT INTO evaluations (user_id, subject_id, name, type, date, weight, state, grade, content)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, options[subject_name], name, ev_type, ev_date.isoformat(), weight, state, None if grade == 0 else grade, content),
            )
            st.success("Evaluación guardada.")
            st.rerun()

    rows = fetch_all(
        """
        SELECT e.*, s.name AS subject_name
        FROM evaluations e JOIN subjects s ON s.id = e.subject_id
        WHERE e.user_id = ?
        ORDER BY date(e.date) ASC
        """,
        (user_id,),
    )
    for ev in rows:
        with st.expander(f"{ev['date']} · {ev['subject_name']} · {ev['name']} · {ev['state']}"):
            st.write(f"Tipo: {ev['type']} · Ponderación: {ev['weight']}%")
            if ev["grade"] is not None:
                st.write(f"Nota: {ev['grade']:.1f}")
            if ev["content"]:
                st.write(ev["content"])
            c1, c2 = st.columns(2)
            with c1:
                new_state = st.selectbox("Cambiar estado", EVALUATION_STATES, index=EVALUATION_STATES.index(ev["state"]), key=f"state_{ev['id']}")
            with c2:
                new_grade = st.number_input("Actualizar nota", min_value=0.0, max_value=7.0, value=float(ev["grade"] or 0), step=0.1, key=f"grade_{ev['id']}")
            if st.button("Guardar cambios", key=f"save_eval_{ev['id']}"):
                execute(
                    "UPDATE evaluations SET state = ?, grade = ? WHERE id = ? AND user_id = ?",
                    (new_state, None if new_grade == 0 else new_grade, ev["id"], user_id),
                )
                st.rerun()


def exercises_view(user_id: int) -> None:
    st.header("Sistema de ejercicios")
    options = subject_options(user_id)
    if not options:
        st.warning("Primero agrega una asignatura.")
        return
    with st.form("guide_form"):
        subject_name = st.selectbox("Asignatura", list(options.keys()))
        name = st.text_input("Nombre de guía")
        total = st.number_input("Cantidad total de ejercicios", min_value=0, max_value=500, value=20)
        understood = st.number_input("Comprendidos y resueltos", min_value=0, max_value=500, value=0)
        difficult = st.number_input("Realizados con dificultad", min_value=0, max_value=500, value=0)
        if st.form_submit_button("Guardar guía", use_container_width=True):
            pending = max(int(total) - int(understood) - int(difficult), 0)
            execute(
                """
                INSERT INTO exercise_guides (user_id, subject_id, name, total, understood, difficult, pending)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, options[subject_name], name, int(total), int(understood), int(difficult), pending),
            )
            st.success("Guía guardada.")
            st.rerun()

    rows = fetch_all(
        """
        SELECT g.*, s.name AS subject_name
        FROM exercise_guides g JOIN subjects s ON s.id = g.subject_id
        WHERE g.user_id = ?
        ORDER BY s.name, g.name
        """,
        (user_id,),
    )
    for guide in rows:
        total = max(int(guide["total"]), 1)
        st.write(f"**{guide['subject_name']} · {guide['name']}**")
        st.progress(int(guide["understood"]) / total, text=f"{guide['understood']} comprendidos · {guide['difficult']} en proceso · {guide['pending']} pendientes")


def study_view(user_id: int) -> None:
    st.header("Registro de estudio y reflexión")
    options = subject_options(user_id)
    if not options:
        st.warning("Primero agrega una asignatura.")
        return

    if "timer_start" not in st.session_state:
        st.session_state.timer_start = None
    timer_col1, timer_col2, timer_col3 = st.columns(3)
    with timer_col1:
        if st.button("Iniciar temporizador", use_container_width=True):
            st.session_state.timer_start = time.time()
    with timer_col2:
        if st.button("Pausar", use_container_width=True):
            st.session_state.timer_start = None
    with timer_col3:
        elapsed = 0
        if st.session_state.timer_start:
            elapsed = int((time.time() - st.session_state.timer_start) / 60)
        st.metric("Minutos actuales", elapsed)

    with st.form("study_form"):
        col1, col2 = st.columns(2)
        with col1:
            subject_name = st.selectbox("Asignatura", list(options.keys()))
            method = st.selectbox("Método", ["Ingreso manual", "Temporizador", "Estudio-descanso"])
            hours = st.number_input("Horas", min_value=0, max_value=12, value=0)
            minutes = st.number_input("Minutos", min_value=0, max_value=59, value=max(elapsed, 0))
            session_date = st.date_input("Fecha", value=date.today())
        with col2:
            productivity = st.selectbox("Productividad", ["Muy productiva", "Productiva", "Normal", "Difícil"])
            comprehension = st.selectbox("Comprensión", ["Sí", "Parcialmente", "No"])
            difficulty = st.selectbox("Dificultad", ["Fácil", "Media", "Difícil"])
            concentration = st.selectbox("Concentración", ["Sí", "Parcialmente", "No"])
            notes = st.text_area("Reflexión breve")
        if st.form_submit_button("Guardar sesión", use_container_width=True):
            total_minutes = int(hours) * 60 + int(minutes)
            if total_minutes <= 0:
                st.warning("Registra al menos un minuto.")
            else:
                execute(
                    """
                    INSERT INTO study_sessions
                    (user_id, subject_id, minutes, method, session_date, productivity, comprehension, difficulty, concentration, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, options[subject_name], total_minutes, method, session_date.isoformat(), productivity, comprehension, difficulty, concentration, notes),
                )
                st.session_state.timer_start = None
                st.success("Sesión guardada. Esta información sirve para conocerte mejor, no para juzgarte.")
                st.rerun()

    rows = fetch_all(
        """
        SELECT ss.*, s.name AS subject_name
        FROM study_sessions ss JOIN subjects s ON s.id = ss.subject_id
        WHERE ss.user_id = ?
        ORDER BY date(ss.session_date) DESC, ss.id DESC
        LIMIT 20
        """,
        (user_id,),
    )
    for session in rows:
        st.write(f"{session['session_date']} · **{session['subject_name']}** · {session['minutes'] / 60:.1f} h · {session['productivity']}")


def personal_goals_view(user_id: int) -> None:
    st.header("Responsabilidades y metas personales")
    with st.form("responsibility_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            name = st.text_input("Responsabilidad")
        with col2:
            category = st.selectbox("Categoría", ["Trabajo", "Deporte", "Voluntariado", "Emprendimiento", "Familia", "Traslados", "Personal", "Otra"])
        with col3:
            hours_week = st.number_input("Horas semanales", min_value=0.0, max_value=80.0, value=2.0, step=0.5)
        if st.form_submit_button("Agregar responsabilidad", use_container_width=True) and name:
            execute(
                "INSERT INTO personal_responsibilities (user_id, name, category, hours_week) VALUES (?, ?, ?, ?)",
                (user_id, name, category, hours_week),
            )
            st.rerun()

    with st.form("goal_form"):
        goal = st.text_input("Meta personal")
        frequency = st.text_input("Frecuencia", value="Semanal")
        if st.form_submit_button("Agregar meta", use_container_width=True) and goal:
            execute("INSERT INTO personal_goals (user_id, name, frequency) VALUES (?, ?, ?)", (user_id, goal, frequency))
            st.rerun()

    st.subheader("Registrado")
    resp = fetch_all("SELECT * FROM personal_responsibilities WHERE user_id = ? ORDER BY category, name", (user_id,))
    goals = fetch_all("SELECT * FROM personal_goals WHERE user_id = ? ORDER BY active DESC, name", (user_id,))
    for row in resp:
        st.write(f"**{row['category']}** · {row['name']} · {row['hours_week']} h/semana")
    for row in goals:
        st.write(f"Meta: **{row['name']}** · {row['frequency']}")


def weekly_review_view(user_id: int) -> None:
    st.header("Revisión semanal")
    with st.form("weekly_review_form"):
        went_well = st.text_area("¿Qué salió bien esta semana?")
        difficult = st.text_area("¿Qué fue difícil?")
        improve = st.text_area("¿Qué quieres mejorar la próxima semana?")
        feeling = st.text_input("¿Cómo te sentiste esta semana?")
        realistic = st.selectbox("¿Tu planificación fue realista?", ["Sí", "Parcialmente", "No"])
        if st.form_submit_button("Guardar revisión", use_container_width=True):
            execute(
                """
                INSERT INTO weekly_reviews (user_id, review_date, went_well, difficult, improve, feeling, realistic)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, date.today().isoformat(), went_well, difficult, improve, feeling, realistic),
            )
            st.success("Revisión guardada. Servirá para ajustar futuras recomendaciones.")
            st.rerun()

    rows = fetch_all("SELECT * FROM weekly_reviews WHERE user_id = ? ORDER BY date(review_date) DESC", (user_id,))
    for row in rows:
        with st.expander(f"{row['review_date']} · Plan realista: {row['realistic']}"):
            st.write(f"**Salió bien:** {row['went_well']}")
            st.write(f"**Fue difícil:** {row['difficult']}")
            st.write(f"**Mejorar:** {row['improve']}")
            st.write(f"**Cómo te sentiste:** {row['feeling']}")


def stats_view(user_id: int) -> None:
    st.header("Estadísticas")
    study_by_subject = fetch_all(
        """
        SELECT s.name, COALESCE(SUM(ss.minutes), 0) AS minutes
        FROM subjects s
        LEFT JOIN study_sessions ss ON ss.subject_id = s.id
        WHERE s.user_id = ?
        GROUP BY s.id
        ORDER BY minutes DESC
        """,
        (user_id,),
    )
    if study_by_subject:
        st.subheader("Horas por asignatura")
        st.bar_chart({row["name"]: row["minutes"] / 60 for row in study_by_subject})

    st.subheader("Lo que aprendí de mí este semestre")
    sessions = fetch_all("SELECT * FROM study_sessions WHERE user_id = ?", (user_id,))
    reviews = fetch_all("SELECT * FROM weekly_reviews WHERE user_id = ?", (user_id,))
    if sessions:
        productive = {}
        for row in sessions:
            productive[row["productivity"]] = productive.get(row["productivity"], 0) + 1
        top = max(productive, key=productive.get)
        st.write(f"Tu registro más frecuente de productividad fue: **{top}**.")
        understood = sum(1 for row in sessions if row["comprehension"] == "Sí")
        st.write(f"En {understood} sesión(es) indicaste comprensión completa.")
    if reviews:
        st.write("Tus revisiones semanales ya están dejando evidencia para ajustar el plan con más criterio.")
    if not sessions and not reviews:
        st.info("Cuando registres sesiones y revisiones, aquí aparecerán patrones personales.")


def semesters_view(user_id: int) -> None:
    st.header("Historial de semestres")
    with st.form("semester_form"):
        name = st.text_input("Nuevo semestre", value=f"Semestre {date.today().year}")
        if st.form_submit_button("Crear nuevo semestre", use_container_width=True):
            with connect() as conn:
                conn.execute("UPDATE semesters SET active = 0 WHERE user_id = ?", (user_id,))
                conn.execute(
                    "INSERT INTO semesters (user_id, name, active, created_at) VALUES (?, ?, 1, ?)",
                    (user_id, name, datetime.now().isoformat(timespec="seconds")),
                )
            st.success("Nuevo semestre creado. El historial anterior se mantiene.")
            st.rerun()
    rows = fetch_all("SELECT * FROM semesters WHERE user_id = ? ORDER BY id DESC", (user_id,))
    for row in rows:
        marker = "Activo" if row["active"] else "Histórico"
        st.write(f"**{row['name']}** · {marker} · creado el {row['created_at'][:10]}")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, page_icon="OK", layout="wide")
    init_db()
    st.markdown(
        """
        <style>
        .stApp { background: #f7f8fb; }
        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e6e8ee;
            border-radius: 8px;
            padding: 14px 16px;
        }
        section[data-testid="stSidebar"] { background: #ffffff; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if "user_id" not in st.session_state:
        auth_view()
        return

    user_id = int(st.session_state.user_id)
    page = sidebar(user_id)
    views = {
        "Dashboard": dashboard_view,
        "Configuración inicial": setup_view,
        "Asignaturas": subjects_view,
        "Horario": schedule_view,
        "Evaluaciones": evaluations_view,
        "Ejercicios": exercises_view,
        "Estudio y reflexión": study_view,
        "Metas personales": personal_goals_view,
        "Revisión semanal": weekly_review_view,
        "Estadísticas": stats_view,
        "Semestres": semesters_view,
    }
    views[page](user_id)


if __name__ == "__main__":
    main()

