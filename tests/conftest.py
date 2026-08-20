import pytest
from fastapi.testclient import TestClient

from applytrack.api import create_app
from applytrack.db import build_session_factory, create_db_engine


@pytest.fixture()
def session():
    """An isolated in-memory database session."""
    engine = create_db_engine("sqlite://")
    factory = build_session_factory(engine)
    db = factory()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(tmp_path):
    """A TestClient backed by a temporary file database."""
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def sample_payload():
    return {
        "company": "Shopify",
        "role": "Senior .NET Engineer",
        "location": "Montreal, QC",
        "source": "LinkedIn",
        "salary_min": 120000,
        "salary_max": 160000,
    }
