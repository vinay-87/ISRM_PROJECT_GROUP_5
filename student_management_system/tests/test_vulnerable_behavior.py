import io

import pytest

import app as app_module


class FakeCursor:
    def __init__(self, state, dictionary=False):
        self.state = state
        self.dictionary = dictionary
        self.result = None

    def execute(self, query):
        self.state["queries"].append(query)
        lowered = query.lower()
        if "select username, role from users" in lowered and "admin' --" in query:
            self.result = {"username": "admin", "role": "admin"}
        elif "select username, role from users" in lowered and "student" in query and "Student@123" in query:
            self.result = {"username": "student", "role": "user"}
        elif "select username, role from users" in lowered and "attacker" in query and "weak" in query:
            self.result = self.state["users"].get("attacker")
        elif "select id, name, email, course, year from students" in lowered:
            self.result = self.state["students"]
        elif "select username, role from users" in lowered:
            self.result = list(self.state["users"].values())
        elif "insert into users" in lowered and "attacker" in query:
            self.state["users"]["attacker"] = {"username": "attacker", "role": "admin"}
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
            "admin": {"username": "admin", "role": "admin"},
            "student": {"username": "student", "role": "user"},
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
    monkeypatch.setattr(app_module, "UPLOAD_FOLDER", str(tmp_path / "uploads"))
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as test_client:
        test_client.state = state
        yield test_client


def login(client, username="admin", password="Admin@123"):
    return client.post("/login", data={"username": username, "password": password})


def test_sql_query_is_built_with_user_input(client):
    login(client, "admin' --", "wrong-password")
    assert any("admin' --" in query for query in client.state["queries"])


def test_sql_injection_bypass_is_present(client):
    response = client.post(
        "/login",
        data={"username": "admin' --", "password": "wrong-password"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")


def test_user_can_self_register_as_admin(client):
    response = client.post(
        "/register",
        data={"username": "attacker", "password": "weak", "role": "admin"},
        follow_redirects=False,
    )
    assert response.status_code == 302

    login_response = client.post(
        "/login",
        data={"username": "attacker", "password": "weak"},
        follow_redirects=True,
    )
    assert b"Role: admin" in login_response.data


def test_admin_panel_has_missing_access_control(client):
    login(client, "student", "Student@123")
    response = client.get("/admin")
    assert response.status_code == 200
    assert b"User Accounts" in response.data


def test_unsafe_upload_accepts_script_extension(client):
    response = client.post(
        "/upload",
        data={"file": (io.BytesIO(b"<?php echo 'demo'; ?>"), "shell.php")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    assert b"shell.php uploaded successfully" in response.data
