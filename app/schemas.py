from marshmallow import EXCLUDE, fields, pre_load, validate

from app.extensions import ma
from app.models import Blacklist


class BlacklistCreateSchema(ma.Schema):
    """Valida el cuerpo del POST /blacklists."""

    class Meta:
        unknown = EXCLUDE

    email = fields.Email(required=True, validate=validate.Length(max=320))
    app_uuid = fields.UUID(required=True)
    blocked_reason = fields.String(
        load_default=None, allow_none=True, validate=validate.Length(max=255)
    )

    @pre_load
    def normalize_email(self, data, **kwargs):
        if isinstance(data, dict) and isinstance(data.get("email"), str):
            data = {**data, "email": data["email"].strip().lower()}
        return data


class BlacklistSchema(ma.SQLAlchemyAutoSchema):
    """Serializa un registro de la lista negra."""

    class Meta:
        model = Blacklist


blacklist_create_schema = BlacklistCreateSchema()
blacklist_schema = BlacklistSchema()
