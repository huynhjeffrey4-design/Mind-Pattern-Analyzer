"""
Shared fixtures for all MindPattern backend tests.

Uses SQLite in-memory so tests never touch the real database.
Each test function gets a fresh, isolated database.
"""
import pytest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.models.base import Base
from app.models.user import User
from app.models.checkin import CheckIn
from app.core.database import get_db
from app.core.security import hash_password, create_access_token
from main import app

# StaticPool forces all checkouts to reuse the SAME underlying connection.
# This is essential for SQLite :memory: — each distinct connection gets its
# own empty in-memory database, so without StaticPool the session and the
# create_all call would be talking to different (invisible-to-each-other) DBs.
SQLITE_URL = "sqlite:///:memory:"


@pytest.fixture()
def db_session():
    engine = create_engine(
        SQLITE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture()
def client(db_session):
    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def make_user(db, email, display_name="Test User"):
    user = User(
        email=email,
        hashed_password=hash_password("test-password"),
        display_name=display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(user):
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def alice(db_session):
    return make_user(db_session, "alice@example.com", "Alice")


@pytest.fixture()
def bob(db_session):
    return make_user(db_session, "bob@example.com", "Bob")


@pytest.fixture()
def alice_headers(alice):
    return auth_headers(alice)


@pytest.fixture()
def bob_headers(bob):
    return auth_headers(bob)


def seed_checkins(db, user_id, rows):
    """
    Directly insert CheckIn rows for a user.
    Each row dict must have: mood_rating, stress_level, sleep_hours.
    Optional: exercised, socialized, workload_level, date.
    """
    now = datetime.now(timezone.utc)
    checkins = []
    for i, r in enumerate(rows):
        c = CheckIn(
            user_id=user_id,
            date=r.get("date", f"2026-05-{str(i + 1).zfill(2)}"),
            mood_rating=r["mood_rating"],
            stress_level=r["stress_level"],
            sleep_hours=r["sleep_hours"],
            exercised=r.get("exercised", False),
            socialized=r.get("socialized", False),
            workload_level=r.get("workload_level"),
            created_at=now,
        )
        checkins.append(c)
    db.add_all(checkins)
    db.commit()
    return checkins
