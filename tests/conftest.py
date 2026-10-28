import uuid

import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db

APP_UUID = str(uuid.uuid4())


@pytest.fixture
def app():
    # SQLite en memoria: las pruebas no dependen de un motor de base de datos
    # externo, así que corren igual en local y en AWS CodeBuild.
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "test-secret-de-al-menos-32-caracteres",
        }
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()
        db.engine.dispose()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        token = create_access_token(identity="blacklist-client", expires_delta=False)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def valid_body():
    """Cuerpo válido para POST /blacklists; los argumentos reemplazan campos."""

    def build(**overrides):
        body = {"email": "cliente@example.com", "app_uuid": APP_UUID, "blocked_reason": "Spam"}
        body.update(overrides)
        return body

    return build
