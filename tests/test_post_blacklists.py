"""POST /blacklists: agregar un email a la lista negra global."""

from app.extensions import db
from app.models import Blacklist


def test_post_adds_email(client, auth_headers, valid_body):
    body = valid_body()
    response = client.post("/blacklists", json=body, headers=auth_headers)

    assert response.status_code == 201
    data = response.get_json()["blacklist"]
    assert data["email"] == "cliente@example.com"
    assert data["app_uuid"] == body["app_uuid"]
    assert data["blocked_reason"] == "Spam"
    assert data["request_ip"]
    assert data["created_at"]


def test_post_persists_entry(client, auth_headers, valid_body, app):
    body = valid_body()
    client.post("/blacklists", json=body, headers=auth_headers)

    with app.app_context():
        entry = db.session.execute(db.select(Blacklist)).scalar_one()
        assert entry.email == "cliente@example.com"
        assert str(entry.app_uuid) == body["app_uuid"]


def test_post_stores_client_ip_behind_load_balancer(client, auth_headers, valid_body, app):
    # nginx agrega la IP del ALB al final del X-Forwarded-For que armó el ALB.
    headers = {**auth_headers, "X-Forwarded-For": "181.50.10.20, 172.31.5.9"}
    client.post("/blacklists", json=valid_body(), headers=headers)

    with app.app_context():
        entry = db.session.execute(db.select(Blacklist)).scalar_one()
        assert entry.request_ip == "181.50.10.20"


def test_post_normalizes_email(client, auth_headers, valid_body):
    response = client.post(
        "/blacklists", json=valid_body(email="  Cliente@Example.COM "), headers=auth_headers
    )
    assert response.status_code == 201
    assert response.get_json()["blacklist"]["email"] == "cliente@example.com"


def test_post_reason_is_optional(client, auth_headers, valid_body):
    body = valid_body()
    del body["blocked_reason"]
    response = client.post("/blacklists", json=body, headers=auth_headers)

    assert response.status_code == 201
    assert response.get_json()["blacklist"]["blocked_reason"] is None


def test_post_reason_of_255_characters_is_accepted(client, auth_headers, valid_body):
    response = client.post(
        "/blacklists", json=valid_body(blocked_reason="x" * 255), headers=auth_headers
    )
    assert response.status_code == 201


def test_post_reason_longer_than_255_returns_400(client, auth_headers, valid_body):
    response = client.post(
        "/blacklists", json=valid_body(blocked_reason="x" * 256), headers=auth_headers
    )
    assert response.status_code == 400
    assert "blocked_reason" in response.get_json()["errors"]


def test_post_duplicate_email_returns_409(client, auth_headers, valid_body):
    client.post("/blacklists", json=valid_body(), headers=auth_headers)
    response = client.post("/blacklists", json=valid_body(), headers=auth_headers)
    assert response.status_code == 409


def test_post_invalid_email_returns_400(client, auth_headers, valid_body):
    response = client.post("/blacklists", json=valid_body(email="no-es-email"), headers=auth_headers)
    assert response.status_code == 400
    assert "email" in response.get_json()["errors"]


def test_post_requires_app_uuid(client, auth_headers, valid_body):
    body = valid_body()
    del body["app_uuid"]
    response = client.post("/blacklists", json=body, headers=auth_headers)
    assert response.status_code == 400
    assert "app_uuid" in response.get_json()["errors"]


def test_post_invalid_app_uuid_returns_400(client, auth_headers, valid_body):
    response = client.post("/blacklists", json=valid_body(app_uuid="123"), headers=auth_headers)
    assert response.status_code == 400
    assert "app_uuid" in response.get_json()["errors"]


def test_post_without_json_body_returns_400(client, auth_headers):
    response = client.post("/blacklists", data="texto", headers=auth_headers)
    assert response.status_code == 400


def test_post_without_token_returns_401(client, valid_body):
    response = client.post("/blacklists", json=valid_body())
    assert response.status_code == 401


def test_post_with_invalid_token_returns_401(client, valid_body):
    response = client.post(
        "/blacklists", json=valid_body(), headers={"Authorization": "Bearer token-falso"}
    )
    assert response.status_code == 401
