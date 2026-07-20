"""
Tests for the Graph Explorer API endpoints.
Uses FastAPI TestClient with mocked Neo4j and database dependencies.
"""
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.api.deps import get_db
from app.models.repository import Repository


# ---- Fixtures ----

@pytest.fixture
def client():
    """FastAPI test client with overridden DB dependency."""
    mock_db = MagicMock()

    # Create mock repositories
    repo_1 = MagicMock(spec=Repository)
    repo_1.id = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
    repo_1.name = "test-repo"
    repo_1.url = "https://github.com/test/test-repo"
    repo_1.owner = "test"
    repo_1.clone_status = "completed"
    repo_1.parser_status = "completed"
    repo_1.graph_status = "completed"
    repo_1.total_files = 10
    repo_1.created_at = "2026-01-01T00:00:00"
    repo_1.updated_at = "2026-01-01T00:00:00"
    repo_1.last_error = None

    mock_query = MagicMock()
    mock_query.order_by.return_value.all.return_value = [repo_1]
    mock_db.query.return_value = mock_query

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def repo_id():
    return "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


@pytest.fixture
def entity_id():
    return "11111111-2222-3333-4444-555555555555"


# ---- Mock data helpers ----

MOCK_GRAPH_DATA = {
    "nodes": [
        {
            "id": "node-1",
            "label": "MyClass",
            "name": "MyClass",
            "entity_type": "class",
            "fully_qualified_name": "pkg.MyClass",
            "language": "Python",
            "file_path": "src/main.py",
            "start_line": 10,
            "end_line": 50,
            "visibility": "public",
            "metadata": {},
        }
    ],
    "edges": [],
    "total_nodes": 1,
    "total_edges": 0,
    "has_more": False,
}

MOCK_SEARCH_RESULTS = [
    {
        "entity": {
            "id": "node-1",
            "label": "MyClass",
            "name": "MyClass",
            "entity_type": "class",
            "fully_qualified_name": "pkg.MyClass",
            "language": "Python",
            "file_path": "src/main.py",
            "start_line": 10,
            "end_line": 50,
            "visibility": "public",
            "metadata": {},
        },
        "match_field": "exact_name",
    }
]

MOCK_ENTITY_DETAIL = {
    "entity": {
        "id": "node-1",
        "label": "MyClass",
        "name": "MyClass",
        "entity_type": "class",
        "fully_qualified_name": "pkg.MyClass",
        "language": "Python",
        "file_path": "src/main.py",
        "start_line": 10,
        "end_line": 50,
        "visibility": "public",
        "metadata": {},
    },
    "file": {
        "id": "file-1",
        "relative_path": "src/main.py",
        "filename": "main.py",
        "language": "Python",
        "size_bytes": 2048,
    },
    "outgoing_relationships": [],
    "incoming_relationships": [],
    "outgoing_count": 0,
    "incoming_count": 0,
}

MOCK_STATISTICS = {
    "repository_id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    "total_nodes": 15,
    "total_files": 5,
    "total_entities": 10,
    "total_edges": 20,
    "nodes_by_type": {"Class": 3, "Method": 5, "Function": 2},
    "edges_by_type": {"CALLS": 10, "IMPORTS": 5, "EXTENDS": 5},
    "density": 0.0095,
    "avg_degree": 2.67,
    "languages": {"Python": 4, "JavaScript": 1},
    "complexity": {
        "files": 5,
        "entities": 10,
        "relationships": 20,
        "types_used": 3,
        "relationship_types_used": 3,
    },
}

MOCK_HIERARCHY = {
    "repository": {"id": "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee", "name": "test-repo", "url": "https://github.com/test/test-repo"},
    "children": [],
    "total_files": 0,
    "total_entities": 0,
}

MOCK_PATH_DATA = {
    "path_found": True,
    "nodes": [
        {"id": "n1", "label": "A", "name": "A", "entity_type": "class", "fully_qualified_name": "", "language": "", "file_path": "", "start_line": None, "end_line": None, "visibility": "", "metadata": {}},
        {"id": "n2", "label": "B", "name": "B", "entity_type": "class", "fully_qualified_name": "", "language": "", "file_path": "", "start_line": None, "end_line": None, "visibility": "", "metadata": {}},
    ],
    "edges": [
        {"id": "e1", "source": "n1", "target": "n2", "relationship_type": "CALLS", "confidence": 1.0, "source_file": "", "line_number": 0},
    ],
    "length": 1,
}


# ---- Tests ----

class TestRepositoryListing:
    """Tests for GET /api/v1/graph/repositories"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_repository_graph_summary")
    def test_list_repositories(self, mock_summary, client):
        mock_summary.return_value = {
            "total_nodes": 10,
            "total_edges": 20,
            "nodes_by_label": {"Class": 3},
            "edges_by_type": {"CALLS": 10},
        }
        response = client.get("/api/v1/graph/repositories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        repo = data[0]
        assert repo["name"] == "test-repo"
        assert repo["graph_status"] == "completed"


class TestRepositoryGraph:
    """Tests for GET /api/v1/graph/repositories/{id}/graph"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_repository_graph")
    def test_get_full_graph(self, mock_graph, client, repo_id):
        mock_graph.return_value = MOCK_GRAPH_DATA
        response = client.get(f"/api/v1/graph/repositories/{repo_id}/graph")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert data["total_nodes"] == 1
        assert data["has_more"] is False

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_repository_graph")
    def test_graph_with_filters(self, mock_graph, client, repo_id):
        mock_graph.return_value = MOCK_GRAPH_DATA
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph",
            params={"node_types": "Class,Method", "relationship_types": "CALLS", "limit": 50},
        )
        assert response.status_code == 200
        mock_graph.assert_called_once()
        call_kwargs = mock_graph.call_args
        assert call_kwargs[1]["limit"] == 50

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_repository_graph")
    def test_graph_pagination(self, mock_graph, client, repo_id):
        mock_graph.return_value = {**MOCK_GRAPH_DATA, "has_more": True}
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph",
            params={"limit": 10, "offset": 0},
        )
        assert response.status_code == 200
        assert response.json()["has_more"] is True


class TestNeighborExpansion:
    """Tests for GET /api/v1/graph/repositories/{id}/graph/neighbors/{entity_id}"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_node_neighbors")
    def test_expand_neighbors(self, mock_neighbors, client, repo_id, entity_id):
        mock_neighbors.return_value = {"nodes": MOCK_GRAPH_DATA["nodes"], "edges": []}
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/neighbors/{entity_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_node_neighbors")
    def test_expand_with_direction(self, mock_neighbors, client, repo_id, entity_id):
        mock_neighbors.return_value = {"nodes": [], "edges": []}
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/neighbors/{entity_id}",
            params={"direction": "out", "depth": 2},
        )
        assert response.status_code == 200

    def test_expand_invalid_direction(self, client, repo_id, entity_id):
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/neighbors/{entity_id}",
            params={"direction": "invalid"},
        )
        assert response.status_code == 422  # Validation error


class TestSearch:
    """Tests for GET /api/v1/graph/repositories/{id}/graph/search"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.search_entities")
    def test_search_entities(self, mock_search, client, repo_id):
        mock_search.return_value = MOCK_SEARCH_RESULTS
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/search",
            params={"q": "MyClass"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "MyClass"
        assert data["total"] >= 1
        assert data["results"][0]["entity"]["name"] == "MyClass"

    def test_search_missing_query(self, client, repo_id):
        response = client.get(f"/api/v1/graph/repositories/{repo_id}/graph/search")
        assert response.status_code == 422  # Missing required param

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.search_entities")
    def test_search_with_type_filter(self, mock_search, client, repo_id):
        mock_search.return_value = []
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/search",
            params={"q": "test", "entity_types": "Class,Method", "limit": 5},
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0


class TestEntityDetail:
    """Tests for GET /api/v1/graph/repositories/{id}/graph/entity/{entity_id}"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_entity_detail")
    def test_get_entity_detail(self, mock_detail, client, repo_id, entity_id):
        mock_detail.return_value = MOCK_ENTITY_DETAIL
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/entity/{entity_id}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entity"]["name"] == "MyClass"
        assert data["file"]["filename"] == "main.py"
        assert data["outgoing_count"] == 0

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_entity_detail")
    def test_entity_not_found(self, mock_detail, client, repo_id, entity_id):
        mock_detail.return_value = None
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/entity/{entity_id}"
        )
        assert response.status_code == 404


class TestHierarchy:
    """Tests for GET /api/v1/graph/repositories/{id}/graph/hierarchy"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_repository_hierarchy")
    def test_get_hierarchy(self, mock_hierarchy, client, repo_id):
        mock_hierarchy.return_value = MOCK_HIERARCHY
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/hierarchy"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["repository"]["name"] == "test-repo"


class TestDependencyPath:
    """Tests for GET /api/v1/graph/repositories/{id}/graph/path"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_dependency_path")
    def test_find_path(self, mock_path, client, repo_id):
        mock_path.return_value = MOCK_PATH_DATA
        source = "11111111-1111-1111-1111-111111111111"
        target = "22222222-2222-2222-2222-222222222222"
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/path",
            params={"source_id": source, "target_id": target},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["path_found"] is True
        assert data["length"] == 1

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_dependency_path")
    def test_path_not_found(self, mock_path, client, repo_id):
        mock_path.return_value = {"path_found": False, "nodes": [], "edges": [], "length": 0}
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/path",
            params={
                "source_id": "11111111-1111-1111-1111-111111111111",
                "target_id": "22222222-2222-2222-2222-222222222222",
            },
        )
        assert response.status_code == 200
        assert response.json()["path_found"] is False


class TestStatistics:
    """Tests for GET /api/v1/graph/repositories/{id}/graph/statistics"""

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_graph_statistics")
    def test_get_statistics(self, mock_stats, client, repo_id):
        mock_stats.return_value = MOCK_STATISTICS
        response = client.get(
            f"/api/v1/graph/repositories/{repo_id}/graph/statistics"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_nodes"] == 15
        assert data["total_edges"] == 20
        assert data["density"] == 0.0095
        assert "Class" in data["nodes_by_type"]
        assert data["languages"]["Python"] == 4


class TestErrorHandling:
    """Tests for error handling across endpoints."""

    def test_invalid_uuid(self, client):
        response = client.get("/api/v1/graph/repositories/not-a-uuid/graph")
        assert response.status_code == 422

    @patch("app.api.v1.endpoints.graph_explorer.GraphQueryService.get_repository_graph")
    def test_internal_error(self, mock_graph, client, repo_id):
        mock_graph.side_effect = Exception("Database timeout")
        response = client.get(f"/api/v1/graph/repositories/{repo_id}/graph")
        assert response.status_code == 500
        assert "Database timeout" in response.json()["detail"]
