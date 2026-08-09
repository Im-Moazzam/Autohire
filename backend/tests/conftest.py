from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.db import SessionLocal
from app.main import app
from app.models.recruiter import Recruiter


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    yield session
    session.query(Recruiter).delete()
    session.commit()
    session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    yield TestClient(app)
    app.dependency_overrides.pop(get_db, None)
