"""NEXORA application factory."""
import os

import psycopg
from flask import Blueprint, Flask, current_app, jsonify
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.routing import IntegerConverter

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
MAX_ID = 2**31 - 1  # ids are 32-bit integers in Postgres


class IdConverter(IntegerConverter):
    """`<int:...>` accepts plain ASCII ids only. Anything else becomes 0, which no
    row has, so every lookup answers its normal 404 instead of a 500.

    Refused: ids Postgres cannot hold, leading zeros and non-ASCII digits (one
    record, one URL). Mapping instead of rejecting, because werkzeug would
    answer 405 for a rejected PATCH id.
    """

    def to_python(self, value: str) -> int:
        plain = value.isascii() and len(value) <= 10 and not value.startswith("0")
        number = int(value) if plain else 0
        return number if number <= MAX_ID else 0


def _json_http_error(exc: HTTPException):
    """Every HTTP error (404, 405, 413, ...) answers in the API's JSON shape."""
    response = exc.get_response()
    message = "Not found." if exc.code == 404 else f"{exc.name}."
    response.data = jsonify(error=message).data
    response.content_type = "application/json"
    return response


def _json_server_error(exc: Exception):
    """Anything unexpected answers in the API's JSON shape, with no details."""
    app = current_app
    app.logger.exception("Unhandled error", exc_info=exc)
    return jsonify(error="Internal error."), 500


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    _check_required_settings(app)
    proxies = str(app.config["TRUSTED_PROXIES"])
    if not proxies.isdecimal():
        raise RuntimeError("TRUSTED_PROXIES must be 0 or a positive whole number.")
    if int(proxies):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=int(proxies))

    app.url_map.converters["int"] = IdConverter
    app.register_error_handler(HTTPException, _json_http_error)
    app.register_error_handler(Exception, _json_server_error)
    db.init_app(app)
    migrate.init_app(app, db)

    # Import models so Alembic's autogenerate can see every table.
    from app.admin import routes as admin_routes  # noqa: F401

    # Importing the routes attaches them to auth_bp.
    from app.auth import routes  # noqa: F401

    # The ledger and history routes import from the savings routes, so they come after.
    from app.ledger import routes as ledger_routes  # noqa: F401
    from app.members import routes as members_routes  # noqa: F401
    from app.models import (  # noqa: F401
        audit,
        ledger,
        membership,
        refresh_token,
        sacco,
        savings,
        user,
    )
    from app.saccos import routes as saccos_routes  # noqa: F401
    from app.savings import accounts as savings_accounts  # noqa: F401
    from app.savings import history as savings_history  # noqa: F401
    from app.savings import routes as savings_routes  # noqa: F401
    init_limiter(app)

    for blueprint in BLUEPRINTS:
        prefix = f"{API_PREFIX}{blueprint.url_prefix}"
        app.register_blueprint(blueprint, url_prefix=prefix)

    _register_health(app)

    return app


def _register_health(app):
    @app.get("/api/health")
    def health():
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            return jsonify({"status": "error", "database": "not_configured"}), 503

        try:
            # libpq does not understand SQLAlchemy's driver suffix, and .env.example
            # tells everyone to use postgresql+psycopg://. Strip it before connecting.
            dsn = make_url(database_url).set(drivername="postgresql")
            dsn_text = dsn.render_as_string(hide_password=False)
            with psycopg.connect(dsn_text) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()

            return jsonify({"status": "healthy", "database": "connected"}), 200

        except (psycopg.Error, ArgumentError):
            return jsonify({"status": "error", "database": "disconnected"}), 503


def _check_required_settings(app):
    required = ("SECRET_KEY", "SQLALCHEMY_DATABASE_URI")
    missing = [name for name in required if not app.config.get(name)]
    if missing:
        raise RuntimeError(
            f"Missing settings: {', '.join(missing)}. "
            "Set them in your .env file or shell."
        )
