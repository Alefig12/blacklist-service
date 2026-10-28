"""GET /ping: health check que usa el balanceador de Elastic Beanstalk."""


def test_ping_does_not_require_token(client):
    for path in ("/", "/ping"):
        response = client.get(path)
        assert response.status_code == 200
        assert response.get_json()["status"] == "ok"


def test_ping_reports_version_and_host(client):
    data = client.get("/ping").get_json()
    assert data["version"]
    assert data["host"]
