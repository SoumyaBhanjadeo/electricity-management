import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing")
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.database import Base, get_db
from app.models import User
from app.security import get_password_hash, create_access_token
from app.main import app

TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db_session():
    session = TestingSessionLocal()
    yield session
    session.close()

@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def admin_user(db_session):
    user = User(
        email="admin_test@gmail.com",
        username="admin_test",
        password=get_password_hash("AdminPass123"),
        role="admin",
        is_active=True,
        created_on=date.today(),
        updated_on=date.today()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def surveyor_user(db_session):
    user = User(
        email="surveyor_test@gmail.com",
        username="surveyor_test",
        password=get_password_hash("SurveyorPass123"),
        role="surveyor",
        is_active=True,
        created_on=date.today(),
        updated_on=date.today()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@pytest.fixture
def admin_token(admin_user):
    return create_access_token({"sub": admin_user.username, "role": admin_user.role, "id": admin_user.id})

@pytest.fixture
def surveyor_token(surveyor_user):
    return create_access_token({"sub": surveyor_user.username, "role": surveyor_user.role, "id": surveyor_user.id})