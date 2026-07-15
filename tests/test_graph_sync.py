import uuid
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from app.models.repository import Repository
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency
from app.database.neo4j_connection import Neo4jConnection, get_neo4j_connection
from app.services.graph_sync import GraphSyncService
from app.services.graph_query import GraphQueryService
from app.core.exceptions import GraphSyncError


@pytest.fixture
def mock_neo4j_conn():
    """Fixture providing a mocked Neo4jConnection."""
    mock_conn = MagicMock(spec=Neo4jConnection)
    mock_conn.is_available = True
    # Store queries executed for assertion
    mock_conn.queries = []

    def mock_write(query, params=None):
        mock_conn.queries.append((query, params))
        # Return a dummy summary dictionary
        return {
            "nodes_created": 1,
            "relationships_created": 1,
            "nodes_deleted": 0,
            "relationships_deleted": 0,
            "properties_set": 1
        }

    def mock_query(query, params=None):
        mock_conn.queries.append((query, params))
        # Provide default query return values depending on query content
        if "detect_circular_dependencies" in query or "cycles" in query or "cycle" in query:
            return [{"cycle": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}, {"id": "1", "name": "A"}]}]
        if "shortestPath" in query:
            return [{
                "nodes": [{"id": "1", "name": "A"}, {"id": "2", "name": "B"}],
                "edges": [{"id": "rel1", "source_id": "1", "target_id": "2", "type": "CALLS"}]
            }]
        if "dependencies_out" in query:
            return [{
                "entity": {"id": "1", "name": "A", "labels": ["Class"]},
                "dependencies_out": [{"relationship": "CALLS", "target": {"id": "2", "name": "B", "labels": ["Method"]}}],
                "dependencies_in": [{"relationship": "IMPORTS", "source": {"id": "3", "name": "C", "labels": ["Class"]}}]
            }]
        if "depth" in query or "depth_query" in query or "path =" in query:
            return [{
                "nodes": [{"id": "1", "name": "A", "labels": ["Class"]}, {"id": "2", "name": "B", "labels": ["Method"]}],
                "edges": [{"id": "rel1", "source_id": "1", "target_id": "2", "type": "CALLS", "confidence": 1.0, "source_file": "main.py", "line_number": 10}]
            }]
        if "labels(e)" in query:
            # node counts
            return [{"label": "Class", "count": 2}, {"label": "Method", "count": 1}]
        if "type(rel)" in query:
            # edge counts
            return [{"type": "CALLS", "count": 1}, {"type": "CONTAINS", "count": 2}]
        return []

    mock_conn.execute_write.side_effect = mock_write
    mock_conn.execute_query.side_effect = mock_query
    return mock_conn


# Helper functions to build entities in SQLite db_session

def create_db_repo(db, name="test-repo"):
    repo = Repository(
        id=uuid.uuid4(),
        name=name,
        url=f"https://github.com/test/{name}",
        clone_status="completed",
        parser_status="completed",
        graph_status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(repo)
    db.commit()
    db.refresh(repo)
    return repo


def create_db_file(db, repo_id, path="main.py"):
    f = File(
        id=uuid.uuid4(),
        repository_id=repo_id,
        absolute_path=f"/workspace/{path}",
        relative_path=path,
        filename=path.split("/")[-1],
        extension=path.split(".")[-1],
        language="Python",
        depth=path.count("/"),
        size_bytes=150,
        last_modified=datetime.utcnow()
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def create_db_entity(db, repo_id, file_id, name, entity_type, fqn):
    e = CodeEntity(
        id=uuid.uuid4(),
        repository_id=repo_id,
        file_id=file_id,
        entity_type=entity_type,
        name=name,
        fully_qualified_name=fqn,
        start_line=1,
        end_line=20,
        visibility="public",
        language="Python",
        meta_data={}
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return e


def create_db_dependency(db, repo_id, source_id, target_id, rel_type, file_path):
    dep = Dependency(
        id=uuid.uuid4(),
        repository_id=repo_id,
        source_entity_id=source_id,
        target_entity_id=target_id,
        relationship_type=rel_type,
        confidence=1.0,
        source_file=file_path,
        line_number=10
    )
    db.add(dep)
    db.commit()
    db.refresh(dep)
    return dep


# ============================================================================
# Tests: Neo4j Connection Manager
# ============================================================================

class TestNeo4jConnection:
    """Tests the driver wrappers and availability fallback logic."""

    @patch("neo4j.GraphDatabase.driver")
    def test_connection_success(self, mock_driver_fn):
        mock_driver = MagicMock()
        mock_driver_fn.return_value = mock_driver

        conn = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        success = conn.connect()

        assert success is True
        assert conn.is_available is True
        mock_driver.verify_connectivity.assert_called_once()

    @patch("neo4j.GraphDatabase.driver")
    def test_connection_failure_fallback(self, mock_driver_fn):
        mock_driver_fn.side_effect = Exception("Connection refused")

        conn = Neo4jConnection("bolt://localhost:7687", "neo4j", "password")
        success = conn.connect()

        assert success is False
        assert conn.is_available is False

    def test_singleton_accessor(self):
        conn = get_neo4j_connection()
        assert isinstance(conn, Neo4jConnection)


# ============================================================================
# Tests: Graph Synchronization Service
# ============================================================================

class TestGraphSyncService:
    """Tests the full synchronization workflow, Cypher generation, and state updates."""

    @patch("app.services.graph_sync.get_neo4j_connection")
    def test_sync_repository_flow(self, mock_get_connection, db_session, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn

        # Set up DB entities
        repo = create_db_repo(db_session)
        file = create_db_file(db_session, repo.id)
        e1 = create_db_entity(db_session, repo.id, file.id, "ClassA", "class", "module.ClassA")
        e2 = create_db_entity(db_session, repo.id, file.id, "funcB", "function", "module.funcB")
        create_db_dependency(db_session, repo.id, e1.id, e2.id, "CALLS", "main.py")

        # Run Sync
        res = GraphSyncService.sync_repository(db_session, repo.id)

        assert res["status"] == "completed"
        assert res["files_synced"] == 1
        assert res["entities_synced"] == 2
        assert res["dependencies_synced"] == 1

        # Check DB status update
        db_session.refresh(repo)
        assert repo.graph_status == "completed"
        assert repo.last_error is None

        # Verify mock connection executed expected queries
        queries = [q[0] for q in mock_neo4j_conn.queries]
        # Must have cleared existing data
        assert any("DETACH DELETE" in q for q in queries)
        # Must have merged Repository node
        assert any("MERGE (r:Repository" in q for q in queries)
        # Must have merged File nodes
        assert any("MERGE (f:File" in q for q in queries)
        # Must have merged Class and Function nodes
        assert any("SET e :Class" in q for q in queries)
        assert any("SET e :Function" in q for q in queries)
        # Must have created structural relationships (BELONGS_TO, DEFINED_IN)
        assert any("BELONGS_TO" in q for q in queries)
        assert any("DEFINED_IN" in q for q in queries)
        # Must have created dependency relationships
        assert any("-[r:CALLS]->" in q for q in queries)

    @patch("app.services.graph_sync.get_neo4j_connection")
    def test_sync_failure_state(self, mock_get_connection, db_session, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn
        # Simulate an exception in executing write
        mock_neo4j_conn.execute_write.side_effect = Exception("Cypher query error")

        repo = create_db_repo(db_session)
        file = create_db_file(db_session, repo.id)

        with pytest.raises(GraphSyncError):
            GraphSyncService.sync_repository(db_session, repo.id)

        db_session.refresh(repo)
        assert repo.graph_status == "failed"
        assert "Cypher query error" in repo.last_error

    @patch("app.services.graph_sync.get_neo4j_connection")
    def test_sync_no_connection_error(self, mock_get_connection, db_session, mock_neo4j_conn):
        mock_neo4j_conn.is_available = False
        mock_get_connection.return_value = mock_neo4j_conn

        repo = create_db_repo(db_session)

        with pytest.raises(GraphSyncError):
            GraphSyncService.sync_repository(db_session, repo.id)

        db_session.refresh(repo)
        assert repo.graph_status == "failed"
        assert "unavailable" in repo.last_error


# ============================================================================
# Tests: Graph Query Service
# ============================================================================

class TestGraphQueryService:
    """Tests read-only Cypher operations, traversals, chain queries, pathfinding, cycle detection."""

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_get_entity_dependencies(self, mock_get_connection, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn

        entity_id = uuid.uuid4()
        res = GraphQueryService.get_entity_dependencies(entity_id)

        assert res["entity"]["id"] == "1"
        assert len(res["dependencies_out"]) == 1
        assert res["dependencies_out"][0]["relationship"] == "CALLS"
        assert len(res["dependencies_in"]) == 1
        assert res["dependencies_in"][0]["source"]["name"] == "C"

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_get_dependency_chain(self, mock_get_connection, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn

        entity_id = uuid.uuid4()
        res = GraphQueryService.get_dependency_chain(entity_id, depth=3)

        assert len(res["nodes"]) == 2
        assert len(res["edges"]) == 1
        assert res["edges"][0]["type"] == "CALLS"
        assert res["edges"][0]["confidence"] == 1.0

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_get_repository_graph_summary(self, mock_get_connection, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn

        repo_id = uuid.uuid4()
        res = GraphQueryService.get_repository_graph_summary(repo_id)

        assert res["total_nodes"] == 3
        assert res["total_edges"] == 3
        assert res["nodes_by_label"]["Class"] == 2
        assert res["edges_by_type"]["CALLS"] == 1
        assert res["edges_by_type"]["CONTAINS"] == 2

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_find_shortest_path(self, mock_get_connection, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn

        source_id = uuid.uuid4()
        target_id = uuid.uuid4()
        res = GraphQueryService.find_shortest_path(source_id, target_id)

        assert res["path_found"] is True
        assert len(res["nodes"]) == 2
        assert len(res["edges"]) == 1

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_detect_circular_dependencies(self, mock_get_connection, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn

        repo_id = uuid.uuid4()
        res = GraphQueryService.detect_circular_dependencies(repo_id)

        assert len(res) == 1
        assert res[0]["cycle_length"] == 2
        assert res[0]["entities"][0]["name"] == "A"


# ============================================================================
# Tests: REST API Endpoints
# ============================================================================

class TestAPIEndpoints:
    """Verifies graph synchronization and query API routing and response serialization."""

    @patch("app.services.graph_sync.get_neo4j_connection")
    def test_sync_endpoint(self, mock_get_connection, client, db_session, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn
        repo = create_db_repo(db_session)

        response = client.post(f"/api/v1/repositories/{repo.id}/graph/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["repository_id"] == str(repo.id)

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_summary_endpoint(self, mock_get_connection, client, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn
        repo_id = uuid.uuid4()

        response = client.get(f"/api/v1/repositories/{repo_id}/graph/summary")
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] == 3
        assert data["repository_id"] == str(repo_id)

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_dependencies_endpoint(self, mock_get_connection, client, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn
        repo_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        response = client.get(f"/api/v1/repositories/{repo_id}/graph/entity/{entity_id}/dependencies")
        assert response.status_code == 200
        data = response.json()
        assert data["entity"]["name"] == "A"
        assert len(data["dependencies_out"]) == 1

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_chain_endpoint(self, mock_get_connection, client, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn
        repo_id = uuid.uuid4()
        entity_id = uuid.uuid4()

        response = client.get(f"/api/v1/repositories/{repo_id}/graph/entity/{entity_id}/chain", params={"depth": 3})
        assert response.status_code == 200
        data = response.json()
        assert len(data["nodes"]) == 2
        assert len(data["edges"]) == 1

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_path_endpoint(self, mock_get_connection, client, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn
        repo_id = uuid.uuid4()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        response = client.get(
            f"/api/v1/repositories/{repo_id}/graph/path",
            params={"source_id": str(source_id), "target_id": str(target_id)}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["path_found"] is True
        assert len(data["nodes"]) == 2

    @patch("app.services.graph_query.get_neo4j_connection")
    def test_cycles_endpoint(self, mock_get_connection, client, mock_neo4j_conn):
        mock_get_connection.return_value = mock_neo4j_conn
        repo_id = uuid.uuid4()

        response = client.get(f"/api/v1/repositories/{repo_id}/graph/cycles")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["cycle_length"] == 2
