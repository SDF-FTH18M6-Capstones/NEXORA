"""NEXORA application factory."""
import os

import psycopg
from flask import Blueprint, Flask, jsonify
from werkzeug.middleware.proxy_fix import ProxyFix

from app.auth.limits import init_limiter
from app.extensions import db, migrate
from config import Config

API_PREFIX = "/api/v1"  # the one place the version prefix is set

# Empty blueprints for Move 1. Routes are added in Moves 3 to 5.
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
saccos_bp = Blueprint("saccos", __name__, url_prefix="/saccos")
savings_bp = Blueprint("savings", __name__, url_prefix="/savings")
admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
members_bp = Blueprint("members", __name__, url_prefix="/members")

BLUEPRINTS = (auth_bp, saccos_bp, savings_bp, admin_bp, members_bp)


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
    from app.members import routes as members_routes  # noqa: F401
    # from app.savings import routes as savings_routes  # noqa: F401

    init_limiter(app)

    for blueprint in BLUEPRINTS:
        app.register_blueprint(blueprint, url_prefix=f"{API_PREFIX}{blueprint.url_prefix}")

    _register_health(app)

    return app


def _register_health(app):
    @app.get("/api/health")
    def health():
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            return jsonify({"status": "error", "database": "not_configured"}), 503

        try:
            with psycopg.connect(database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

            return jsonify({"status": "healthy", "database": "connected"}), 200

        except psycopg.Error:
            return jsonify({"status": "error", "database": "disconnected"}), 503


def _check_required_settings(app):
    missing = [name for name in ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI") if not app.config.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing settings: {', '.join(missing)}. Set them in your .env file or shell."
        )