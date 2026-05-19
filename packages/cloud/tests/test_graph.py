"""Tests for Neo4j graph memory integration.

These tests mock the Neo4j driver to avoid requiring a live Neo4j instance.
They verify:
- Graph DB initialization (mocked)
- Entity/relationship storage
- Graph query functions (mocked)
- Graceful degradation when Neo4j is unavailable
- Graph endpoint responses
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime, timezone


# ─── Graph DB Module Tests ─────────────────────────────────────────


class TestGraphDbInit:
    """Test Neo4j driver initialization."""

    @pytest.mark.asyncio
    async def test_init_skips_when_no_password(self):
        """Should skip init when NEO4J_PASSWORD is empty."""
        from agentrecall_cloud import graph_db

        # Reset state
        graph_db._initialized = False
        graph_db._driver = None
        graph_db._available = False

        with patch("agentrecall_cloud.graph_db.config") as mock_config:
            mock_config.neo4j_uri = "bolt://localhost:7687"
            mock_config.neo4j_user = "neo4j"
            mock_config.neo4j_password = ""

            await graph_db.init_graph_db()

            assert graph_db._driver is None
            assert graph_db._initialized is True
            assert graph_db._available is False

    @pytest.mark.asyncio
    async def test_init_skips_when_no_uri(self):
        """Should skip init when NEO4J_URI is empty."""
        from agentrecall_cloud import graph_db

        graph_db._initialized = False
        graph_db._driver = None
        graph_db._available = False

        with patch("agentrecall_cloud.graph_db.config") as mock_config:
            mock_config.neo4j_uri = ""
            mock_config.neo4j_user = "neo4j"
            mock_config.neo4j_password = "test"

            await graph_db.init_graph_db()

            assert graph_db._driver is None
            assert graph_db._initialized is True
            assert graph_db._available is False

    @pytest.mark.asyncio
    async def test_init_connects_when_configured(self):
        """Should create driver when properly configured."""
        from agentrecall_cloud import graph_db

        graph_db._initialized = False
        graph_db._driver = None
        graph_db._available = False

        class MockAsyncCtx:
            def __init__(self, val):
                self.val = val
            async def __aenter__(self):
                return self.val
            async def __aexit__(self, *a):
                pass

        class MockResult:
            def __init__(self, records=None):
                self._records = records or []
            def data(self):
                return self._records

        class MockSession:
            def __init__(self):
                self.run_calls = []
            async def run(self, query, **kwargs):
                self.run_calls.append(query)
                return MockResult()

        class MockDriver:
            def __init__(self):
                self.session_instance = MockSession()
                self.verify_called = False
            async def verify_connectivity(self):
                self.verify_called = True
            def session(self):
                return MockAsyncCtx(self.session_instance)

        mock_driver = MockDriver()

        with patch("agentrecall_cloud.graph_db.config") as mock_config:
            mock_config.neo4j_uri = "bolt://localhost:7687"
            mock_config.neo4j_user = "neo4j"
            mock_config.neo4j_password = "testpass"

            with patch("agentrecall_cloud.graph_db.AsyncGraphDatabase") as mock_ndb:
                mock_ndb.driver.return_value = mock_driver

                await graph_db.init_graph_db()

                assert graph_db._driver is mock_driver
                assert graph_db._available is True
                assert mock_driver.verify_called is True

    @pytest.mark.asyncio
    async def test_init_handles_connection_failure(self):
        """Should gracefully handle connection failure."""
        from agentrecall_cloud import graph_db
        from neo4j.exceptions import ServiceUnavailable

        graph_db._initialized = False
        graph_db._driver = None
        graph_db._available = False

        with patch("agentrecall_cloud.graph_db.config") as mock_config:
            mock_config.neo4j_uri = "bolt://localhost:7687"
            mock_config.neo4j_user = "neo4j"
            mock_config.neo4j_password = "testpass"

            with patch("agentrecall_cloud.graph_db.AsyncGraphDatabase") as mock_ndb:
                mock_ndb.driver.return_value.verify_connectivity.side_effect = (
                    ServiceUnavailable("Connection refused")
                )

                await graph_db.init_graph_db()

                assert graph_db._driver is None
                assert graph_db._initialized is True


class TestGraphDbDegradation:
    """Test graceful degradation when Neo4j is unavailable."""

    @pytest.mark.asyncio
    async def test_get_entities_returns_empty(self):
        """Should return empty list when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        result = await graph_db.get_entities("test-agent")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_entity_neighbors_returns_empty(self):
        """Should return empty result when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        result = await graph_db.get_entity_neighbors("test-agent", "Entity1")
        assert result == {"entity": None, "neighbors": []}

    @pytest.mark.asyncio
    async def test_get_relationships_returns_empty(self):
        """Should return empty list when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        result = await graph_db.get_relationships("test-agent")
        assert result == []

    @pytest.mark.asyncio
    async def test_find_shortest_path_returns_empty(self):
        """Should return empty result when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        result = await graph_db.find_shortest_path("test-agent", "A", "B")
        assert result == {"path": [], "length": 0}

    @pytest.mark.asyncio
    async def test_get_graph_stats_returns_zeros(self):
        """Should return zero stats when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        result = await graph_db.get_graph_stats("test-agent")
        assert result["total_entities"] == 0
        assert result["total_relationships"] == 0
        assert result["total_memories_in_graph"] == 0

    @pytest.mark.asyncio
    async def test_get_graph_context_returns_empty(self):
        """Should return empty list when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        result = await graph_db.get_graph_context("test-agent", "test query")
        assert result == []

    @pytest.mark.asyncio
    async def test_sync_memory_skips_when_unavailable(self):
        """Should silently skip sync when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        # Should not raise
        await graph_db.sync_memory_to_graph(
            memory_id=1,
            content="test content",
            agent_id="test-agent",
            entities=[{"name": "Entity1", "type": "person"}],
            relationships=[],
        )


class TestGraphDbSync:
    """Test syncing data to the graph."""

    @pytest.mark.asyncio
    async def test_sync_memory_to_graph(self):
        """Should write entities and relationships to Neo4j."""
        from agentrecall_cloud import graph_db

        mock_session = AsyncMock()
        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        graph_db._driver = mock_driver

        await graph_db.sync_memory_to_graph(
            memory_id=42,
            content="Alice works at Acme Corp",
            agent_id="agent-123",
            entities=[
                {"name": "Alice", "type": "person"},
                {"name": "Acme Corp", "type": "organization"},
            ],
            relationships=[
                {"source": "Alice", "target": "Acme Corp", "type": "works_at"},
            ],
            summary="Alice at Acme",
        )

        # Should have run multiple queries (memory + 2 entities + 2 links + 1 rel)
        assert mock_session.run.call_count >= 5


class TestGraphDbQueries:
    """Test graph query functions with mocked driver."""

    def _make_mock_session_with_data(self, records: list[dict]):
        """Helper to create a mock session that returns records."""
        mock_session = AsyncMock()

        mock_result = AsyncMock()
        mock_result.data.return_value = records
        mock_session.run.return_value = mock_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        return mock_driver

    @pytest.mark.asyncio
    async def test_get_entities_with_results(self):
        """Should return formatted entity list."""
        from agentrecall_cloud import graph_db

        records = [
            {
                "name": "Alice",
                "type": "person",
                "first_seen": "2024-01-01T00:00:00Z",
                "last_seen": "2024-01-02T00:00:00Z",
                "memory_count": 3,
            }
        ]
        graph_db._driver = self._make_mock_session_with_data(records)

        result = await graph_db.get_entities("agent-123")

        assert len(result) == 1
        assert result[0]["name"] == "Alice"
        assert result[0]["type"] == "person"
        assert result[0]["memory_count"] == 3

    @pytest.mark.asyncio
    async def test_get_entities_filtered_by_type(self):
        """Should filter by entity type."""
        from agentrecall_cloud import graph_db

        graph_db._driver = self._make_mock_session_with_data([])

        await graph_db.get_entities("agent-123", entity_type="person", limit=10)

        # Verify the query was called with entity_type parameter
        session = graph_db._driver.session.return_value.__aenter__.return_value
        session.run.assert_called()
        call_args = session.run.call_args
        assert "entity_type" in call_args.kwargs or "person" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_entity_neighbors_with_results(self):
        """Should return entity with neighbors."""
        from agentrecall_cloud import graph_db

        mock_session = AsyncMock()

        # First call: get the entity
        entity_result = AsyncMock()
        entity_result.single.return_value = {
            "name": "Alice",
            "type": "person",
            "first_seen": "2024-01-01",
            "last_seen": "2024-01-02",
            "memory_count": 2,
        }

        # Second call: get neighbors
        neighbor_result = AsyncMock()
        neighbor_result.data.return_value = [
            {
                "name": "Acme Corp",
                "type": "organization",
                "relationship_type": "WORKS_AT",
                "strength": 1.0,
                "distance": 1,
            }
        ]

        mock_session.run.side_effect = [entity_result, neighbor_result]

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        graph_db._driver = mock_driver

        result = await graph_db.get_entity_neighbors("agent-123", "Alice", depth=1)

        assert result["entity"] is not None
        assert result["entity"]["name"] == "Alice"
        assert len(result["neighbors"]) == 1
        assert result["neighbors"][0]["name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_get_entity_not_found(self):
        """Should return empty when entity not found."""
        from agentrecall_cloud import graph_db

        mock_session = AsyncMock()
        entity_result = AsyncMock()
        entity_result.single.return_value = None
        mock_session.run.return_value = entity_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        graph_db._driver = mock_driver

        result = await graph_db.get_entity_neighbors("agent-123", "NonExistent")

        assert result["entity"] is None
        assert result["neighbors"] == []

    @pytest.mark.asyncio
    async def test_find_shortest_path_with_result(self):
        """Should return path between entities."""
        from agentrecall_cloud import graph_db

        mock_session = AsyncMock()
        path_result = AsyncMock()
        path_result.single.return_value = {
            "entities": [
                {"name": "Alice", "type": "person"},
                {"name": "Acme Corp", "type": "organization"},
            ],
            "relationships": [{"relationship_type": "WORKS_AT"}],
            "path_length": 1,
        }
        mock_session.run.return_value = path_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        graph_db._driver = mock_driver

        result = await graph_db.find_shortest_path("agent-123", "Alice", "Acme Corp")

        assert result["length"] == 1
        assert len(result["path"]) == 2
        assert result["path"][0]["entity"]["name"] == "Alice"
        assert result["path"][0]["relationship"]["relationship_type"] == "WORKS_AT"
        assert result["path"][1]["entity"]["name"] == "Acme Corp"

    @pytest.mark.asyncio
    async def test_find_shortest_path_no_result(self):
        """Should return empty when no path found."""
        from agentrecall_cloud import graph_db

        mock_session = AsyncMock()
        path_result = AsyncMock()
        path_result.single.return_value = None
        mock_session.run.return_value = path_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        graph_db._driver = mock_driver

        result = await graph_db.find_shortest_path("agent-123", "Alice", "NonExistent")

        assert result == {"path": [], "length": 0}

    @pytest.mark.asyncio
    async def test_get_graph_stats(self):
        """Should return aggregated stats."""
        from agentrecall_cloud import graph_db

        mock_session = AsyncMock()

        ent_result = AsyncMock()
        ent_result.single.return_value = {"total": 5}

        rel_result = AsyncMock()
        rel_result.single.return_value = {"total": 8}

        mem_result = AsyncMock()
        mem_result.single.return_value = {"total": 10}

        type_result = AsyncMock()
        type_result.data.return_value = [
            {"type": "person", "cnt": 3},
            {"type": "organization", "cnt": 2},
        ]

        top_result = AsyncMock()
        top_result.data.return_value = [
            {"name": "Alice", "connections": 4},
            {"name": "Bob", "connections": 2},
        ]

        mock_session.run.side_effect = [
            ent_result, rel_result, mem_result, type_result, top_result
        ]

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        graph_db._driver = mock_driver

        result = await graph_db.get_graph_stats("agent-123")

        assert result["total_entities"] == 5
        assert result["total_relationships"] == 8
        assert result["total_memories_in_graph"] == 10
        assert result["entity_types"] == {"person": 3, "organization": 2}
        assert len(result["top_entities"]) == 2
        assert result["top_entities"][0]["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_get_graph_context(self):
        """Should find relevant entities from query text."""
        from agentrecall_cloud import graph_db

        mock_session = AsyncMock()
        ctx_result = AsyncMock()
        ctx_result.data.return_value = [
            {
                "name": "Alice",
                "type": "person",
                "first_seen": "2024-01-01",
                "last_seen": "2024-01-02",
                "memories": [{"memory_id": 1, "summary": "Alice works at Acme"}],
                "connected_entities": [
                    {"name": "Acme Corp", "type": "organization", "relationship": "WORKS_AT"}
                ],
            }
        ]
        mock_session.run.return_value = ctx_result

        mock_driver = MagicMock()
        mock_driver.session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_driver.session.return_value.__aexit__ = AsyncMock(return_value=False)

        graph_db._driver = mock_driver

        result = await graph_db.get_graph_context("agent-123", "Tell me about Alice")

        assert len(result) == 1
        assert result[0]["entity"]["name"] == "Alice"
        assert len(result[0]["memories"]) == 1


class TestGraphDbClose:
    """Test graph DB cleanup."""

    @pytest.mark.asyncio
    async def test_close_cleans_up(self):
        """Should close driver and reset state."""
        from agentrecall_cloud import graph_db

        mock_driver = AsyncMock()
        graph_db._driver = mock_driver
        graph_db._available = True

        await graph_db.close_graph_db()

        mock_driver.close.assert_called_once()
        assert graph_db._driver is None
        assert graph_db._available is False

    @pytest.mark.asyncio
    async def test_close_handles_no_driver(self):
        """Should handle close when driver is None."""
        from agentrecall_cloud import graph_db

        graph_db._driver = None
        # Should not raise
        await graph_db.close_graph_db()
