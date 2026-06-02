import pytest
from fastapi.testclient import TestClient
from backend.server import app
from backend.database import get_db , Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


SOLALCHMY_TEST_DATABASE_URI = "sqlite:///test_temp.db"
engine = create_engine(SOLALCHMY_TEST_DATABASE_URI)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client (db):
    def override_get_db():
        yield db
    app.dependency_overrides[get_db]=override_get_db
    return TestClient(app)


def test_login(client):
    client.post("/register", json={
        "username": "testuser123",
        "password": "1234"
    })
    response = client.post("/login", json={
        "username": "testuser123",
        "password": "1234"
    })
    assert response.status_code == 200


def test_register_duplicate(client):
    client.post("/register", json={"username": "dupuser", "password": "1234"})
    response = client.post("/register", json={"username": "dupuser", "password": "1234"})
    assert response.status_code == 400

# def test_login_wrong_password(client):
#     response = client.post("/login", json={"username": "testuser123", "password": "wrong"})
#     assert response.status_code == 400


