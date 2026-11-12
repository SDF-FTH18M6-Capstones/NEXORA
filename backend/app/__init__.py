"""NEXORA application factory."""
from flask import Blueprint, Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from app.auth.limits import init_limiter
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
    proxies = str(app.config["TRUSTED_PROXIES"])
    if not proxies.isdecimal():
        raise RuntimeError("TRUSTED_PROXIES must be 0 or a positive whole number.")
    if int(proxies):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=int(proxies))

    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic's autogenerate can see every table.
    from app.models import audit, ledger, membership, refresh_token, sacco, savings, user  # noqa: F401

    # Importing the routes attaches them to auth_bp.
    from app.auth import routes  # noqa: F401

    init_limiter(app)

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint)

    return app


def _check_required_settings(app):
    missing = [name for name in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI") if not app.config.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing settings: {', '.join(missing)}. Set them in your .env file or shell."
        )