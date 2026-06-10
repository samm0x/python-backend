import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend.database import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_TEST_DATABASE_URI = "sqlite:///test_temp.db"
engine = create_engine(SQLALCHEMY_TEST_DATABASE_URI)
TestingSessionLocal = sessionmaker(bind=engine)


@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_register(client):
    response = client.post("/api/v1/register", json={
        "username": "testuser123",
        "password": "1234"
    })
    assert response.status_code == 200


def test_login(client):
    client.post("/api/v1/register", json={"username": "testuser123", "password": "1234"})
    response = client.post("/api/v1/login", data={"username": "testuser123", "password": "1234"})
    assert response.status_code == 200


def test_register_duplicate(client):
    client.post("/api/v1/register", json={"username": "dupuser", "password": "1234"})
    response = client.post("/api/v1/register", json={"username": "dupuser", "password": "1234"})
    assert response.status_code == 400


def test_login_wrong_password(client):
    client.post("/api/v1/register", json={"username": "testuser123", "password": "1234"})
    response = client.post("/api/v1/login", data={"username": "testuser123", "password": "wrong"})
    assert response.status_code == 401

def test_refresh_token(client):
    client.post("/api/v1/register", json={"username": "refreshuser", "password": "1234"})
    login_response = client.post("/api/v1/login", data={"username": "refreshuser", "password": "1234"})
    refresh_token = login_response.json()["refresh_token"]

    response = client.post(f"/api/v1/refresh?refresh_token={refresh_token}")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout(client):
    client.post("/api/v1/register", json={"username": "logoutuser", "password": "1234"})
    login_response = client.post("/api/v1/login", data={"username": "logoutuser", "password": "1234"})
    access_token = login_response.json()["access_token"]

    response = client.post("/api/v1/logout", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code == 200


def test_token_revoked_after_logout(client):
    client.post("/api/v1/register", json={"username": "revokeuser", "password": "1234"})
    login_response = client.post("/api/v1/login", data={"username": "revokeuser", "password": "1234"})
    access_token = login_response.json()["access_token"]

    client.post("/api/v1/logout", headers={"Authorization": f"Bearer {access_token}"})

    response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401


def test_admin_access_denied(client):
    client.post("/api/v1/register", json={"username": "admintest", "password": "1234"})

    # مستقیم توکن میسازیم بدون login
    from backend.security import create_access_token
    access_token = create_access_token({"sub": "admintest"})

    response = client.patch("/api/v1/admin/users/1/make-admin", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code == 403


def test_delete_user_permission_denied(client):
    client.post("/api/v1/register", json={"username": "deletetest", "password": "1234"})

    from backend.security import create_access_token
    access_token = create_access_token({"sub": "deletetest"})

    response = client.delete("/api/v1/users/1", headers={
        "Authorization": f"Bearer {access_token}"
    })
    assert response.status_code == 403

def test_profile_unauthorized(client):
    response = client.get("/api/v1/profile")
    assert response.status_code == 401