from datetime import datetime, timezone

from app.extensions import db


class Blacklist(db.Model):
    __tablename__ = "blacklist"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(320), unique=True, nullable=False)
    app_uuid = db.Column(db.Uuid, nullable=False)
    blocked_reason = db.Column(db.String(255), nullable=True)
    request_ip = db.Column(db.String(45), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
