from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient


def test_import_repository_endpoint_success(client: TestClient):
    payload = {"url": "https://github.com/Reddy0402/software-dna"}

    # Mock the return values for the database object
    mock_repo = MagicMock()
    mock_repo.id = "12345678-1234-5678-1234-567812345678"
    mock_repo.name = "software-dna"
    mock_repo.url = payload["url"]
    mock_repo.owner = "Reddy0402"
    mock_repo.clone_status = "completed"
    mock_repo.parser_status = "pending"
    mock_repo.graph_status = "pending"
    mock_repo.local_path = "/dummy/path"
    mock_repo.default_branch = "main"
    mock_repo.size_bytes = 1024
    mock_repo.latest_commit_hash = "abcdef"
    mock_repo.total_files = 10
    mock_repo.last_error = None
    
    # Standard values for mock dates
    import datetime
    mock_repo.created_at = datetime.datetime(2026, 7, 14, 10, 0, 0)
    mock_repo.updated_at = datetime.datetime(2026, 7, 14, 10, 0, 0)

    with patch(
        "app.services.repository.RepositoryService.create_pending_record"
    ) as mock_create, patch(
        "app.services.repository.RepositoryService.import_repository"
    ) as mock_import:
        mock_create.return_value = mock_repo
        mock_import.return_value = mock_repo

        response = client.post("/api/v1/repositories/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["url"] == payload["url"]
        assert data["clone_status"] == "completed"
        assert data["id"] == "12345678-1234-5678-1234-567812345678"


def test_import_repository_endpoint_invalid_url(client: TestClient):
    # This should fail validation at the Pydantic schema level (returns 422)
    payload = {"url": "https://gitlab.com/some/repo"}
    response = client.post("/api/v1/repositories/", json=payload)

    assert response.status_code == 422
    assert "detail" in response.json()
