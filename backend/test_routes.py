import pytest
import io
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
    response = client.post("/api/v1/register", json={"username": "testuser123", "email": "test@test.com", "password": "1234"})
    assert response.status_code == 200


def test_login(client):
    client.post("/api/v1/register", json={"username": "testuser123", "email": "test@test.com", "password": "1234"})
    response = client.post("/api/v1/login", data={"username": "testuser123", "password": "1234"})
    assert response.status_code == 200


def test_register_duplicate(client):
    client.post("/api/v1/register", json={"username": "dupuser", "email": "dup@test.com", "password": "1234"})
    response = client.post("/api/v1/register", json={"username": "dupuser", "email": "dup2@test.com", "password": "1234"})
    assert response.status_code == 400


def test_login_wrong_password(client):
    client.post("/api/v1/register", json={"username": "testuser123", "email": "test@test.com", "password": "1234"})
    response = client.post("/api/v1/login", data={"username": "testuser123", "password": "wrong"})
    assert response.status_code == 401


def test_refresh_token(client):
    client.post("/api/v1/register", json={"username": "refreshuser", "email": "refresh@test.com", "password": "1234"})
    login_response = client.post("/api/v1/login", data={"username": "refreshuser", "password": "1234"})
    refresh_token = login_response.json()["refresh_token"]
    response = client.post(f"/api/v1/refresh?refresh_token={refresh_token}")
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout(client):
    client.post("/api/v1/register", json={"username": "logoutuser", "email": "logout@test.com", "password": "1234"})
    login_response = client.post("/api/v1/login", data={"username": "logoutuser", "password": "1234"})
    access_token = login_response.json()["access_token"]
    response = client.post("/api/v1/logout", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200


def test_token_revoked_after_logout(client):
    client.post("/api/v1/register", json={"username": "revokeuser", "email": "revoke@test.com", "password": "1234"})
    login_response = client.post("/api/v1/login", data={"username": "revokeuser", "password": "1234"})
    access_token = login_response.json()["access_token"]
    client.post("/api/v1/logout", headers={"Authorization": f"Bearer {access_token}"})
    response = client.get("/api/v1/profile", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401


def test_admin_access_denied(client):
    client.post("/api/v1/register", json={"username": "normaluser", "email": "normal@test.com", "password": "1234"})
    from backend.security import create_access_token
    access_token = create_access_token({"sub": "normaluser"})
    response = client.patch("/api/v1/admin/users/1/make-admin", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403


def test_delete_user_permission_denied(client):
    client.post("/api/v1/register", json={"username": "normaluser2", "email": "normal2@test.com", "password": "1234"})
    from backend.security import create_access_token
    access_token = create_access_token({"sub": "normaluser2"})
    response = client.delete("/api/v1/users/1", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403


def test_profile_unauthorized(client):
    response = client.get("/api/v1/profile")
    assert response.status_code == 401

def test_get_sessions(client):
    client.post("/api/v1/register", json={"username": "sessionuser", "email": "session@test.com", "password": "1234"})
    from backend.security import create_access_token
    access_token = create_access_token({"sub": "sessionuser"})
    response = client.get("/api/v1/sessions", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_delete_session(client):
    client.post("/api/v1/register", json={"username": "sessionuser2", "email": "session2@test.com", "password": "1234"})
    from backend.security import create_access_token
    access_token = create_access_token({"sub": "sessionuser2"})
    response = client.delete("/api/v1/sessions/9999", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 404


def test_get_session_unauthorized(client):
    response = client.get("/api/v1/sessions")
    assert response.status_code == 401


def test_register_sends_email(client):
    response = client.post("/api/v1/register", json={"username": "emailuser", "email": "email@test.com", "password": "1234"})
    assert response.status_code == 200
    assert response.json()["message"] == "User registered successfully"


def test_upload_file(client):
    client.post("/api/v1/register", json={"username": "uploaduser", "email": "upload@test.com", "password": "1234"})
    from backend.security import create_access_token
    access_token = create_access_token({"sub": "uploaduser"})
    fake_file = io.BytesIO(b"fake image content")
    response = client.post("/api/v1/upload", headers={"Authorization": f"Bearer {access_token}"}, files={"file": ("test.jpg", fake_file, "image/jpeg")})
    assert response.status_code == 200


def test_soft_delete_user(client):
    client.post("/api/v1/register", json={"username": "deleteuser", "email": "delete@test.com", "password": "1234"})
    from backend.security import create_access_token
    from backend.models import User

    db = TestingSessionLocal()
    user = db.query(User).filter(User.username == "deleteuser").first()
    user.role = "admin"
    db.commit()
    user_id = user.id
    db.close()

    admin_token = create_access_token({"sub": "deleteuser"})
    response = client.delete(f"/api/v1/users/{user_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert response.status_code == 200