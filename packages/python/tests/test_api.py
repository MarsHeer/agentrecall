from fastapi.testclient import TestClient
from agentrecall.server import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_save_memory():
    response = client.post("/v1/memories", json={
        "agent_id": "api_test",
        "content": "User lives in Marbella"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "api_test"
    assert data["content"] == "User lives in Marbella"
    assert data["category"] == "factual"


def test_recall():
    client.post("/v1/memories", json={
        "agent_id": "api_test2",
        "content": "User has a dog named Poppy"
    })
    response = client.get("/v1/memories/api_test2/recall?q=what+pet+does+user+have")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1


def test_count():
    client.post("/v1/memories", json={
        "agent_id": "api_test3",
        "content": "Fact one"
    })
    response = client.get("/v1/memories/api_test3/count")
    assert response.status_code == 200
    assert response.json()["count"] >= 1


def test_delete():
    resp = client.post("/v1/memories", json={
        "agent_id": "api_test4",
        "content": "Memory to delete"
    })
    memory_id = resp.json()["id"]
    response = client.delete(f"/v1/memories/api_test4/{memory_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True


def test_save_returns_general_for_unmatched():
    """Content that doesn't match any specific category gets 'general'."""
    response = client.post("/v1/memories", json={
        "agent_id": "api_test5",
        "content": "wget downloaded file successfully"
    })
    assert response.status_code == 200
    assert response.json()["category"] == "general"
