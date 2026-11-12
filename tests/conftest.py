import pytest
from sqlalchemy.orm import Session

from app import create_app
from app.extensions import db
from config import TestConfig

pytestmark = pytest.mark.schema

@pytest.fixture(scope="session")
def app():
    application = create_app(TestConfig)

    uri = application.config["SQLALCHEMY_DATABASE_URI"]
    if "test" not in uri:
        raise RuntimeError(
            f"Refusing to run tests against a non-test database: {uri}. Check TEST_DATABASE_URL."
        )

    with application.app_context():
        db.create_all()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    """A database session whose work is rolled back after each test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()

