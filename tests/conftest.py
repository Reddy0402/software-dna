import os
import sys
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the backend directory to sys.path so 'app' can be imported
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend"))
)

# Set environment overrides for configuration
os.environ["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
from app.config import settings

# Override settings directly to ensure it points to SQLite in-memory db
settings.SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

from app.database.base_class import Base
from app.api.deps import get_db
from app.main import app

# Create a test engine and session factory
test_engine = create_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    connect_args={"check_same_thread": False},
)
TestingSessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    """
    Creates the database tables for the session.
    """
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session() -> Generator:
    """
    Provides a database session for tests, clearing tables afterward.
    """
    session = TestingSessionLocal()
    yield session
    session.close()

    # Clear all records from tables to isolate tests
    with test_engine.connect() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())
        connection.commit()


@pytest.fixture
def client(db_session) -> Generator[TestClient, None, None]:
    """
    Provides a TestClient with overridden get_db dependency.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
