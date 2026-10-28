import time

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _login(client: TestClient, username: str, password: str) -> str:
    resp = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200
    return resp.json()["data"]["token"]["access_token"]


class TestRegister:
    def test_register_success(self, client):
        uniq = f"u{int(time.time())}"
        resp = client.post(
            "/api/auth/register",
            json={"username": uniq, "password": "test123456"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        assert resp.json()["data"]["user"]["username"] == uniq
        assert resp.json()["data"]["user"]["role"] == "user"

    def test_register_duplicate(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "seed123456"},
        )
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_register_short_password(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"username": "weakpass", "password": "12"},
        )
        assert resp.status_code == 422

    def test_register_invalid_username_chars(self, client):
        resp = client.post(
            "/api/auth/register",
            json={"username": "bad user!", "password": "test123456"},
        )
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client):
        token = _login(client, "alice", "seed123456")
        assert token.startswith("eyJ")

    def test_login_wrong_password(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "wrongpass"},
        )
        assert resp.status_code == 400
        assert resp.json()["error_code"] == "LOGIN_FAILED"

    def test_login_nonexistent_user(self, client):
        resp = client.post(
            "/api/auth/login",
            json={"username": "ghost", "password": "whatever"},
        )
        assert resp.status_code == 400


class TestGetMe:
    def test_me_without_token(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_with_token(self, client):
        token = _login(client, "alice", "seed123456")
        resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["data"]["user"]["username"] == "alice"
        assert resp.json()["data"]["user"]["role"] == "user"


class TestAdmin:
    def test_admin_without_token(self, client):
        resp = client.get("/api/auth/admin-only")
        assert resp.status_code == 401

    def test_admin_as_normal_user_403(self, client):
        token = _login(client, "alice", "seed123456")
        resp = client.get(
            "/api/auth/admin-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403
        assert resp.json()["error_code"] == "FORBIDDEN"

    def test_admin_as_admin_200(self, client):
        token = _login(client, "admin", "admin123456")
        resp = client.get(
            "/api/auth/admin-only", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["user"]["role"] == "admin"