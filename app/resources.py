import socket

from flask import request
from flask_jwt_extended import jwt_required
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Blacklist
from app.schemas import blacklist_create_schema, blacklist_schema
from app.version import VERSION


class PingResource(Resource):
    """Health check sin autenticación. Muestra la versión y la instancia que
    respondió, útil para validar las estrategias de despliegue."""

    def get(self):
        return {"status": "ok", "version": VERSION, "host": socket.gethostname()}, 200


class BlacklistListResource(Resource):
    @jwt_required()
    def post(self):
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return {"msg": "El cuerpo de la solicitud debe ser un objeto JSON"}, 400

        try:
            data = blacklist_create_schema.load(payload)
        except ValidationError as err:
            return {"msg": "Datos inválidos", "errors": err.messages}, 400

        entry = Blacklist(
            email=data["email"],
            app_uuid=data["app_uuid"],
            blocked_reason=data["blocked_reason"],
            request_ip=request.remote_addr,
        )
        db.session.add(entry)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            return {"msg": "El email ya se encuentra en la lista negra global"}, 409

        return {
            "msg": "Email agregado a la lista negra global",
            "blacklist": blacklist_schema.dump(entry),
        }, 201


class BlacklistResource(Resource):
    @jwt_required()
    def get(self, email):
        email = email.strip().lower()
        entry = db.session.execute(
            db.select(Blacklist).filter_by(email=email)
        ).scalar_one_or_none()

        return {
            "email": email,
            "is_blacklisted": entry is not None,
            "blocked_reason": entry.blocked_reason if entry else None,
        }, 200
