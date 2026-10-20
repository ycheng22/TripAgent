from fastapi.testclient import TestClient

from app.main import app


def test_ping_is_database_free_liveness_response() -> None:
    response = TestClient(app).get("/ping")

    assert response.status_code == 200
    assert response.json()["status"] == "pong"
    assert "version" in response.json()
