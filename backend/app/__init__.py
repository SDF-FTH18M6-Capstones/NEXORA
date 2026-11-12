"""NEXORA application factory."""
from flask import Blueprint, Flask
from app.models import user, sacco, membership, savings, ledger, audit 

from app.extensions import db, migrate
from config import Config

# Empty blueprints for Move 1. Routes are added in Moves 3 to 5.
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
saccos_bp = Blueprint("saccos", __name__, url_prefix="/saccos")
savings_bp = Blueprint("savings", __name__, url_prefix="/savings")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

BLUEPRINTS = (auth_bp, saccos_bp, savings_bp, admin_bp)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    _check_required_settings(app)

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic's autogenerate can see every table.
    from app.models import audit, ledger, membership, sacco, savings, user  # noqa: F401

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    return app


def _check_required_settings(app):
    missing = [name for name in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI") if not app.config.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing settings: {', '.join(missing)}. Set them in your .env file or shell."
        )