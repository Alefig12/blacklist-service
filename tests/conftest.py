import pytest
from flask_jwt_extended import create_access_token

from app import create_app
from app.extensions import db


@pytest.fixture
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
            "JWT_SECRET_KEY": "test-secret-de-al-menos-32-caracteres",
        }
    )
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app):
    with app.app_context():
        token = create_access_token(identity="blacklist-client", expires_delta=False)
    return {"Authorization": f"Bearer {token}"}
