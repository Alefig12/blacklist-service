import logging

from flask import Flask, jsonify
from flask_restful import Api
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.middleware.proxy_fix import ProxyFix

from app.config import load_config
from app.extensions import db, jwt, ma
from app.resources import BlacklistListResource, BlacklistResource, PingResource

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app(config_overrides=None):
    app = Flask(__name__)
    app.json.ensure_ascii = False
    app.config.update(load_config())
    if config_overrides:
        app.config.update(config_overrides)

    if not app.config["SQLALCHEMY_DATABASE_URI"]:
        raise RuntimeError(
            "Falta la configuración de la base de datos: defina DATABASE_URL "
            "o las variables RDS_HOSTNAME, RDS_PORT, RDS_DB_NAME, RDS_USERNAME y RDS_PASSWORD."
        )
    if not app.config["JWT_SECRET_KEY"]:
        raise RuntimeError("Falta la variable de entorno JWT_SECRET_KEY.")

    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("postgresql"):
        app.config.setdefault(
            "SQLALCHEMY_ENGINE_OPTIONS",
            {"pool_pre_ping": True, "connect_args": {"connect_timeout": 5}},
        )

    # La IP real del cliente llega en X-Forwarded-For (ALB -> nginx -> gunicorn).
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=app.config["PROXY_X_FOR"])

    db.init_app(app)
    ma.init_app(app)
    jwt.init_app(app)
    register_jwt_errors()

    api = Api(app)
    api.add_resource(PingResource, "/", "/ping")
    api.add_resource(BlacklistListResource, "/blacklists")
    api.add_resource(BlacklistResource, "/blacklists/<string:email>")

    with app.app_context():
        try:
            db.create_all()
        except SQLAlchemyError:
            # Si la base no está disponible la app igual arranca (el health
            # check en /ping sigue respondiendo) y el error queda en los logs.
            logger.exception("No fue posible crear las tablas en la base de datos")

    return app


def register_jwt_errors():
    @jwt.unauthorized_loader
    def missing_token(reason):
        return jsonify(msg="Token de autorización requerido", detail=reason), 401

    @jwt.invalid_token_loader
    def invalid_token(reason):
        return jsonify(msg="Token de autorización inválido", detail=reason), 401
