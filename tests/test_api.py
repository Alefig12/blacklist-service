import uuid

from app.extensions import db
from app.models import Blacklist

APP_UUID = str(uuid.uuid4())


def valid_body(**overrides):
    body = {"email": "cliente@example.com", "app_uuid": APP_UUID, "blocked_reason": "Spam"}
    body.update(overrides)
    return body


# --- Health check -----------------------------------------------------------

def test_ping_does_not_require_token(client):
    for path in ("/", "/ping"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"
        assert "version" in response.get_json()


# --- POST /blacklists -------------------------------------------------------

def test_post_adds_email(client, auth_headers, app):
    response = client.post("/blacklists", json=valid_body(), headers=auth_headers)

    assert response.status_code == 201
    data = response.get_json()["blacklist"]
    assert data["email"] == "cliente@example.com"
    assert data["app_uuid"] == APP_UUID
    assert data["blocked_reason"] == "Spam"
    assert data["request_ip"]
    assert data["created_at"]


def test_post_stores_client_ip_behind_load_balancer(client, auth_headers, app):
    # nginx agrega la IP del ALB al final del X-Forwarded-For que armó el ALB.
    headers = {**auth_headers, "X-Forwarded-For": "181.50.10.20, 172.31.5.9"}
    client.post("/blacklists", json=valid_body(), headers=headers)

    with app.app_context():
        entry = db.session.execute(db.select(Blacklist)).scalar_one()
        assert entry.request_ip == "181.50.10.20"


def test_post_normalizes_email(client, auth_headers):
    response = client.post(
        "/blacklists", json=valid_body(email="  Cliente@Example.COM "), headers=auth_headers
    )
    assert response.status_code == 201
    assert response.get_json()["blacklist"]["email"] == "cliente@example.com"


def test_post_reason_is_optional(client, auth_headers):
    body = valid_body()
    del body["blocked_reason"]
    response = client.post("/blacklists", json=body, headers=auth_headers)

    assert response.status_code == 201
    assert response.get_json()["blacklist"]["blocked_reason"] is None


def test_post_duplicate_email_returns_409(client, auth_headers):
    client.post("/blacklists", json=valid_body(), headers=auth_headers)
    response = client.post("/blacklists", json=valid_body(), headers=auth_headers)
    assert response.status_code == 409


def test_post_invalid_email_returns_400(client, auth_headers):
    response = client.post("/blacklists", json=valid_body(email="no-es-email"), headers=auth_headers)
    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]


def test_post_requires_app_uuid(client, auth_headers):
    body = valid_body()
    del body["app_uuid"]
    response = client.post("/blacklists", json=body, headers=auth_headers)
    assert response.status_code == 400
    assert "app_uuid" in response.get_json()["errors"]


def test_post_invalid_app_uuid_returns_400(client, auth_headers):
    response = client.post("/blacklists", json=valid_body(app_uuid="123"), headers=auth_headers)
    assert response.status_code == 400
    assert "app_uuid" in response.get_json()["errors"]


def test_post_reason_longer_than_255_returns_400(client, auth_headers):
    response = client.post(
        "/blacklists", json=valid_body(blocked_reason="x" * 256), headers=auth_headers
    )
    assert response.status_code == 400
    assert "blocked_reason" in response.get_json()["errors"]


def test_post_without_json_body_returns_400(client, auth_headers):
    response = client.post("/blacklists", data="texto", headers=auth_headers)
    assert response.status_code == 400


def test_post_without_token_returns_401(client):
    response = client.post("/blacklists", json=valid_body())
    assert response.status_code == 401


def test_post_with_invalid_token_returns_401(client):
    response = client.post(
        "/blacklists", json=valid_body(), headers={"Authorization": "Bearer token-falso"}
    )
    assert response.status_code == 401


# --- GET /blacklists/<email> ------------------------------------------------

def test_get_blacklisted_email(client, auth_headers):
    client.post("/blacklists", json=valid_body(), headers=auth_headers)
    response = client.get("/blacklists/cliente@example.com", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {
        "email": "cliente@example.com",
        "is_blacklisted": True,
        "blocked_reason": "Spam",
    }


def test_get_is_case_insensitive(client, auth_headers):
    client.post("/blacklists", json=valid_body(), headers=auth_headers)
    response = client.get("/blacklists/CLIENTE@example.com", headers=auth_headers)
    assert response.get_json()["is_blacklisted"] is True


def test_get_email_not_in_blacklist(client, auth_headers):
    response = client.get("/blacklists/otro@example.com", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {
        "email": "otro@example.com",
        "is_blacklisted": False,
        "blocked_reason": None,
    }


def test_get_without_token_returns_401(client):
    response = client.get("/blacklists/cliente@example.com")
    assert response.status_code == 401
