from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)

def test_root_endpoint():
    """Verify that root welcome path returns correctly."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"

def test_health_ready_endpoint():
    """Verify that readiness probe returns correctly."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"

@patch("api.routes.health._check_database", new_callable=AsyncMock)
@patch("api.routes.health._check_redis", new_callable=AsyncMock)
@patch("api.routes.health._check_qdrant", new_callable=AsyncMock)
def test_health_check_endpoint(mock_qdrant, mock_redis, mock_db):
    """Verify that liveness probe returns correctly based on service status."""
    # Mock all checks to return success
    mock_db.return_value = {"status": "ok", "latency_ms": None}
    mock_redis.return_value = {"status": "ok"}
    mock_qdrant.return_value = {"status": "ok"}

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@patch("api.routes.health._check_database", new_callable=AsyncMock)
@patch("api.routes.health._check_redis", new_callable=AsyncMock)
@patch("api.routes.health._check_qdrant", new_callable=AsyncMock)
def test_health_check_endpoint_degraded(mock_qdrant, mock_redis, mock_db):
    """Verify health returns 503 degraded status when services fail."""
    mock_db.return_value = {"status": "error", "detail": "Connection refused"}
    mock_redis.return_value = {"status": "ok"}
    mock_qdrant.return_value = {"status": "ok"}

    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["status"] == "degraded"

@pytest.mark.asyncio
async def test_chat_endpoint_success():
    """Verify POST /api/chat triggers LangGraph and returns ChatResponse successfully."""
    # Mock AshaSwarm.run to stream a mock string
    async def mock_run(*args, **kwargs):
        words = ["Hello", "this", "is", "a", "mock", "response."]
        for w in words:
            yield w + " "

    with patch("api.routes.chat.AshaSwarm") as MockSwarm:
        mock_instance = MagicMock()
        mock_instance.run = mock_run
        mock_instance.state = {
            "current_intent": "chitchat"
        }
        MockSwarm.return_value = mock_instance

        payload = {
            "session_id": "test_session_123",
            "message": "Hi, I have a query.",
            "device_type": "web"
        }
        
        response = client.post("/api/chat", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test_session_123"
        assert "mock response" in data["response_text"]
        assert data["intent_detected"] == "chitchat"
        assert data["status"] == "success"
