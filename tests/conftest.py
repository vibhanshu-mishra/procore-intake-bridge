import os
from collections.abc import Generator

os.environ["APP_DATABASE_URL"] = "sqlite://"
os.environ["APP_PROCORE_MODE"] = "fixture"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_session
from app.main import app
from app.models import (  # noqa: F401
    DMSAConnection,
    IntakeAttachment,
    IntakeRecord,
    SyncProfile,
    SyncRun,
)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as session:
        yield session


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_session():
        yield db_session

    app.dependency_overrides[get_session] = override_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def connection(db_session: Session) -> DMSAConnection:
    value = DMSAConnection(
        name="Synthetic contractor",
        procore_company_id="company-test",
        permitted_project_ids=["project-1001"],
        enabled_tools=["rfis", "submittals"],
        secret_name="secret/test-placeholder",
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value


@pytest.fixture
def sync_profile(db_session: Session, connection: DMSAConnection) -> SyncProfile:
    value = SyncProfile(
        connection_id=connection.id,
        procore_project_id="project-1001",
        name="Synthetic project polling",
        enabled=True,
        sync_rfis=True,
        sync_submittals=True,
        polling_interval_minutes=30,
        mode="mock",
    )
    db_session.add(value)
    db_session.commit()
    db_session.refresh(value)
    return value
