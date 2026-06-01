from fastapi.testclient import TestClient
from backend.server import app

client = TestClient(app)

def test_register():
    response = client.post("/register",json={
        "username": "testuser123",
        "password": "1234"

    })
    assert response.status_code == 200

def test_login():
    response = client.post("/login",json={
        "username" : "testuser123",
        "password" : "1234"
    })
    assert response.status_code == 200

def test_register_duplicate():
    client.post("/register", json={"username": "dupuser", "password": "1234"})
    response = client.post("/register", json={"username": "dupuser", "password": "1234"})
    assert response.status_code == 400

def test_login_wrong_password():
    response = client.post("/login", json={"username": "testuser123", "password": "wrong"})
    assert response.status_code == 401

