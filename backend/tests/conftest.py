"""Pytest configuration and fixtures for KrishiRate API tests.

Sets KRISHI_DATABASE_URL to a temporary SQLite file *before* any
backend.app module is imported, so the app uses an isolated test database.
"""

import os
import tempfile

os.environ["KRISHI_DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.gettempdir(), "krishirate_test.db"
)

from fastapi.testclient import TestClient  # noqa: E402

from backend.app.database import SessionLocal, create_tables, engine  # noqa: E402
from backend.app.main import app  # noqa: E402
from backend.app.models import Alert, Price  # noqa: E402


def pytest_configure():
    create_tables()


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def session():
    """SQLAlchemy session bound to the test database; cleans tables after."""
    session = SessionLocal()
    yield session
    session.query(Alert).delete()
    session.query(Price).delete()
    session.commit()
    session.close()


@pytest.fixture
def client():
    """FastAPI TestClient against the test database."""
    return TestClient(app)
