from .conftest import register


def test_register_login_and_me(client):
    register(client, "bob", "password1", "EGP")
    resp = client.post("/api/auth/login", json={"username": "bob", "password": "password1"})
    assert resp.status_code == 200
    headers = {"Authorization": f"Bearer {resp.get_json()['access_token']}"}
    me = client.get("/api/auth/me", headers=headers).get_json()
    assert me["username"] == "bob" and me["base_currency"] == "EGP"


def test_duplicate_username_and_bad_login(client):
    register(client, "bob")
    assert client.post("/api/auth/register", json={"username": "bob", "password": "xxxxxx"}).status_code == 409
    assert client.post("/api/auth/login", json={"username": "bob", "password": "wrong!"}).status_code == 401


def test_protected_routes_require_token(client):
    resp = client.get("/api/wealth")
    assert resp.status_code == 401
    assert "error" in resp.get_json()


def test_update_base_currency(client, auth):
    resp = client.patch("/api/auth/me", headers=auth, json={"base_currency": "eur"})
    assert resp.get_json()["base_currency"] == "EUR"
