import io
import re

import pytest

import app as app_module


class FakeCursor:
    def __init__(self, state, dictionary=False):
        self.state = state
        self.dictionary = dictionary
        self.result = None

    def execute(self, query, params=None):
        params = params or ()
        lowered = query.lower()
        self.state["queries"].append((query, params))

        if "select username, password, role from users where username" in lowered:
            username = params[0]
            self.result = self.state["users"].get(username)
        elif "insert into users" in lowered:
            username, password = params
            if username in self.state["users"]:
                raise app_module.MySQLError("duplicate")
            self.state["users"][username] = {"username": username, "password": password, "role": "user"}
            self.result = None
        elif "select id, name, email, course, year from students where id" in lowered:
            student_id = params[0]
            self.result = next((student for student in self.state["students"] if student["id"] == student_id), None)
        elif "select id, name, email, course, year from students" in lowered:
            self.result = list(self.state["students"])
        elif "select username, role from users" in lowered:
            self.result = [{"username": user["username"], "role": user["role"]} for user in self.state["users"].values()]
        elif "insert into students" in lowered:
            name, email, course, year = params
            self.state["students"].append(
                {"id": len(self.state["students"]) + 1, "name": name, "email": email, "course": course, "year": year}
            )
            self.result = None
        elif "update users set role" in lowered:
            role, username = params
            if username in self.state["users"]:
                self.state["users"][username]["role"] = role
            self.result = None
        elif "delete from students" in lowered:
            student_id = params[0]
            self.state["students"] = [student for student in self.state["students"] if student["id"] != student_id]
            self.result = None
        elif "update students set" in lowered:
            name, email, course, year, student_id = params
            for student in self.state["students"]:
                if student["id"] == student_id:
                    student.update({"name": name, "email": email, "course": course, "year": year})
            self.result = None
        else:
            self.result = None

    def fetchone(self):
        if isinstance(self.result, list):
            return self.result[0] if self.result else None
        return self.result

    def fetchall(self):
        if isinstance(self.result, list):
            return self.result
        return []

    def close(self):
        pass


class FakeConnection:
    def __init__(self, state):
        self.state = state

    def cursor(self, dictionary=False):
        return FakeCursor(self.state, dictionary=dictionary)

    def commit(self):
        pass

    def close(self):
        pass


@pytest.fixture()
def client(tmp_path, monkeypatch):
    state = {
        "queries": [],
        "users": {
            "admin": {
                "username": "admin",
                "password": app_module.hash_password("Admin@123"),
                "role": "admin",
            },
            "student": {
                "username": "student",
                "password": app_module.hash_password("Student@123"),
                "role": "user",
            },
        },
        "students": [
            {
                "id": 1,
                "name": "Asha Mehta",
                "email": "asha.mehta@example.edu",
                "course": "Information Security",
                "year": 3,
            }
        ],
    }
    monkeypatch.setattr(app_module, "get_db_connection", lambda include_database=True: FakeConnection(state))
    app_module.LOGIN_ATTEMPTS.clear()
    app_module.app.config.update(
        TESTING=True,
        UPLOAD_FOLDER=str(tmp_path / "uploads"),
        AUDIT_LOG_PATH=str(tmp_path / "audit.log"),
        RATE_LIMIT_ENABLED=False,
        RATELIMIT_ENABLED=False,
    )
    with app_module.app.test_client() as test_client:
        test_client.state = state
        yield test_client


def csrf_token(client, path="/login"):
    response = client.get(path)
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match, response.data.decode("utf-8", errors="ignore")
    return match.group(1).decode("utf-8")


def login(client, username="admin", password="Admin@123"):
    token = csrf_token(client)
    return client.post(
        "/login",
        data={"username": username, "password": password, "csrf_token": token},
        follow_redirects=False,
    )


def test_home_redirects_to_login(client):
    response = client.get("/")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Student Management Login" in response.data


def test_valid_login_redirects_to_dashboard(client):
    response = login(client)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_sql_injection_login_payload_is_rejected(client):
    response = client.post(
        "/login",
        data={
            "username": "admin' --",
            "password": "anything",
            "csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_login_query_uses_parameters(client):
    login(client)
    assert any("WHERE username = %s" in query and params == ("admin",) for query, params in client.state["queries"])


def test_registration_cannot_choose_admin_role(client):
    response = client.post(
        "/register",
        data={
            "username": "newuser",
            "password": "Strong@123",
            "role": "admin",
            "csrf_token": csrf_token(client, "/register"),
        },
        follow_redirects=False,
    )
    assert response.status_code == 302

    login_response = client.post(
        "/login",
        data={
            "username": "newuser",
            "password": "Strong@123",
            "csrf_token": csrf_token(client),
        },
        follow_redirects=True,
    )
    assert b"Role: user" in login_response.data


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_non_admin_cannot_open_admin_panel(client):
    login(client, "student", "Student@123")
    response = client.get("/admin")
    assert response.status_code == 403


def test_admin_can_add_student(client):
    login(client)
    response = client.post(
        "/student/add",
        data={
            "name": "Nia Shah",
            "email": "nia.shah@example.edu",
            "course": "Cloud Security",
            "year": "3",
            "csrf_token": csrf_token(client, "/student/add"),
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Nia Shah" in response.data


def test_upload_rejects_unsafe_extension(client):
    login(client)
    response = client.post(
        "/upload",
        data={
            "csrf_token": csrf_token(client, "/upload"),
            "file": (io.BytesIO(b"bad"), "shell.php"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert b"File type not allowed" in response.data


def test_post_without_csrf_token_is_rejected(client):
    response = client.post("/login", data={"username": "admin", "password": "Admin@123"})
    assert response.status_code == 400
    assert b"Invalid request token" in response.data


def test_security_headers_are_set(client):
    response = client.get("/login")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "same-origin"
