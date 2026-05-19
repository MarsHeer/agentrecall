"""Integration tests for the AgentRecall Cloud API endpoints.

These tests run against the live server (localhost:8700).
Start the server first: systemctl start agentrecall-cloud
"""

import httpx
import pytest

BASE = "http://localhost:8700"
client = httpx.Client(base_url=BASE, timeout=10.0)

TEST_EMAIL = "pytest@test.com"
TEST_PASSWORD = "pytestpass123"


# ─── Fixtures ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def token():
    """Signup and return JWT token."""
    r = client.post("/v1/auth/signup", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD,
    })
    if r.status_code == 200:
        return r.json()["token"]
    # Already exists — login
    r = client.post("/v1/auth/login", json={
        "email": TEST_EMAIL, "password": TEST_PASSWORD,
    })
    assert r.status_code == 200
    return r.json()["token"]


@pytest.fixture(scope="module")
def headers(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def agent_id(headers):
    """Get or create default agent, return its ID."""
    r = client.get("/v1/agents", headers=headers)
    agents = r.json()
    if agents:
        return agents[0]["id"]
    r = client.post("/v1/agents", json={"name": "pytest-agent"}, headers=headers)
    return r.json()["id"]


# ─── Health ────────────────────────────────────────────────────────

class TestHealth:
    def test_health(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ─── Auth ──────────────────────────────────────────────────────────

class TestAuth:
    def test_signup(self, token):
        assert token
        assert len(token) > 20

    def test_login_wrong_password(self):
        r = client.post("/v1/auth/login", json={
            "email": TEST_EMAIL, "password": "wrongpassword",
        })
        assert r.status_code == 401

    def test_me(self, headers):
        r = client.get("/v1/auth/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["email"] == TEST_EMAIL

    def test_me_no_auth(self):
        r = client.get("/v1/auth/me")
        assert r.status_code == 401


# ─── Agents ────────────────────────────────────────────────────────

class TestAgents:
    def test_create_agent(self, headers):
        r = client.post("/v1/agents", json={"name": "new-agent"}, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["name"] == "new-agent"
        assert "id" in data

    def test_list_agents(self, headers):
        r = client.get("/v1/agents", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    def test_get_single_agent(self, headers, agent_id):
        r = client.get(f"/v1/agents/{agent_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == agent_id

    def test_rename_agent(self, headers, agent_id):
        r = client.put(f"/v1/agents/{agent_id}", json={"name": "renamed"}, headers=headers)
        assert r.status_code == 200
        assert r.json()["name"] == "renamed"
        # Rename back
        client.put(f"/v1/agents/{agent_id}", json={"name": "pytest-agent"}, headers=headers)

    def test_delete_agent(self, headers):
        r = client.post("/v1/agents", json={"name": "to-delete"}, headers=headers)
        agent_id = r.json()["id"]
        r = client.delete(f"/v1/agents/{agent_id}", headers=headers)
        assert r.status_code == 200

    def test_count_memories(self, headers, agent_id):
        r = client.get(f"/v1/agents/{agent_id}/count", headers=headers)
        assert r.status_code == 200
        assert "count" in r.json()


# ─── Memories ──────────────────────────────────────────────────────

class TestMemories:
    def test_store_memory(self, headers, agent_id):
        r = client.post("/v1/memories", json={
            "content": "Test memory content",
            "agent_id": agent_id,
            "category": "fact",
        }, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["content"] == "Test memory content"
        assert data["category"] == "fact"

    def test_list_memories(self, headers):
        r = client.get("/v1/memories?limit=10", headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_get_memory(self, headers, agent_id):
        r = client.post("/v1/memories", json={
            "content": "Gettable memory",
            "agent_id": agent_id,
        }, headers=headers)
        mem_id = r.json()["id"]
        r = client.get(f"/v1/memories/{mem_id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["content"] == "Gettable memory"

    def test_update_memory(self, headers, agent_id):
        r = client.post("/v1/memories", json={
            "content": "Original content",
            "agent_id": agent_id,
        }, headers=headers)
        mem_id = r.json()["id"]
        r = client.put(f"/v1/memories/{mem_id}", json={
            "content": "Updated content",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["content"] == "Updated content"

    def test_skip_unskip_memory(self, headers, agent_id):
        r = client.post("/v1/memories", json={
            "content": "Skippable memory",
            "agent_id": agent_id,
        }, headers=headers)
        mem_id = r.json()["id"]
        # Skip
        r = client.post(f"/v1/memories/{mem_id}/skip", headers=headers)
        assert r.status_code == 200
        assert "skipped" in r.json()["message"]
        # Unskip
        r = client.delete(f"/v1/memories/{mem_id}/skip", headers=headers)
        assert r.status_code == 200
        assert "unskipped" in r.json()["message"]

    def test_recall(self, headers, agent_id):
        client.post("/v1/memories", json={
            "content": "Marco likes espresso coffee",
            "agent_id": agent_id,
            "category": "preference",
        }, headers=headers)
        r = client.get("/v1/memories/recall", params={
            "query": "coffee", "agent_id": agent_id, "limit": 5,
        }, headers=headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_delete_memory(self, headers, agent_id):
        r = client.post("/v1/memories", json={
            "content": "Delete me",
            "agent_id": agent_id,
        }, headers=headers)
        mem_id = r.json()["id"]
        r = client.delete(f"/v1/memories/{mem_id}", headers=headers)
        assert r.status_code == 200
        # Verify gone
        r = client.get(f"/v1/memories/{mem_id}", headers=headers)
        assert r.status_code == 404


# ─── API Keys ──────────────────────────────────────────────────────

class TestApiKeys:
    def test_create_list_delete(self, headers):
        # Create
        r = client.post("/v1/api-keys", json={"name": "test-key"}, headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "full_key" in data
        assert data["full_key"].startswith("ark_")
        key_id = data["id"]
        # List
        r = client.get("/v1/api-keys", headers=headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1
        # Delete
        r = client.delete(f"/v1/api-keys/{key_id}", headers=headers)
        assert r.status_code == 200


# ─── Usage ─────────────────────────────────────────────────────────

class TestUsage:
    def test_get_usage(self, headers):
        r = client.get("/v1/usage", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "api_calls_today" in data
        assert "plan" in data


# ─── Billing ───────────────────────────────────────────────────────

class TestBilling:
    def test_checkout_no_stripe(self, headers):
        """Without Stripe keys, should return graceful fallback."""
        r = client.post("/v1/billing/checkout", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "url" in data

    def test_subscription(self, headers):
        r = client.get("/v1/billing/subscription", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["plan"] == "free"
        assert data["status"] == "active"


# ─── Cross-endpoint: API key auth for memories ─────────────────────

class TestApiKeyAuth:
    def test_full_flow(self, headers, agent_id):
        """Full flow: create API key, use it for memories."""
        # Create API key
        r = client.post("/v1/api-keys", json={"name": "sdk-test"}, headers=headers)
        full_key = r.json()["full_key"]
        api_headers = {"Authorization": f"Bearer {full_key}"}

        # Remember via API key
        r = client.post("/v1/memories", json={
            "content": "Agent prefers dark mode",
            "agent_id": agent_id,
            "category": "preference",
        }, headers=api_headers)
        assert r.status_code == 200

        # Recall via API key
        r = client.get("/v1/memories/recall", params={
            "query": "dark mode", "agent_id": agent_id,
        }, headers=api_headers)
        assert r.status_code == 200
        assert len(r.json()) >= 1

        # Cleanup: revoke the key
        keys = client.get("/v1/api-keys", headers=headers).json()
        sdk_key = next((k for k in keys if k["name"] == "sdk-test"), None)
        if sdk_key:
            client.delete(f"/v1/api-keys/{sdk_key['id']}", headers=headers)
