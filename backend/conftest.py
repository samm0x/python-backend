import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def reset_limiter():
    from backend.server import app
    app.state.limiter._storage.reset()
    yield