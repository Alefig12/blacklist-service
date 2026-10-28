"""GET /blacklists/<email>: consultar si un email está en la lista negra global."""


def test_get_blacklisted_email(client, auth_headers, valid_body):
    client.post("/blacklists", json=valid_body(), headers=auth_headers)
    response = client.get("/blacklists/cliente@example.com", headers=auth_headers)

    assert response.status_code == 200
    assert response.get_json() == {
        "email": "cliente@example.com",
        "is_blacklisted": True,
        "blocked_reason": "Spam",
    }


def test_get_blacklisted_email_without_reason(client, auth_headers, valid_body):
    body = valid_body()
    del body["blocked_reason"]
    client.post("/blacklists", json=body, headers=auth_headers)

    data = client.get("/blacklists/cliente@example.com", headers=auth_headers).get_json()
    assert data["is_blacklisted"] is True
    assert data["blocked_reason"] is None


def test_get_is_case_insensitive(client, auth_headers, valid_body):
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


def test_get_with_invalid_token_returns_401(client):
    response = client.get(
        "/blacklists/cliente@example.com", headers={"Authorization": "Bearer token-falso"}
    )
    assert response.status_code == 401
