from unittest.mock import patch
from fastapi.testclient import TestClient


def test_scan_repository_endpoint_success(client: TestClient):
    repo_id = "12345678-1234-5678-1234-567812345678"
    mock_summary = {
        "repository_id": repo_id,
        "total_files_scanned": 150,
        "supported_files_found": 88,
        "language_distribution": {"Python": 50, "TypeScript": 38}
    }

    with patch("app.services.scanner.ScannerService.scan_repository") as mock_scan:
        mock_scan.return_value = mock_summary
        
        response = client.post(f"/api/v1/repositories/{repo_id}/scan")
        
        assert response.status_code == 200
        data = response.json()
        assert data["repository_id"] == repo_id
        assert data["total_files_scanned"] == 150
        assert data["supported_files_found"] == 88
        assert data["language_distribution"] == {"Python": 50, "TypeScript": 38}


def test_scan_repository_endpoint_failure(client: TestClient):
    repo_id = "12345678-1234-5678-1234-567812345678"
    
    with patch("app.services.scanner.ScannerService.scan_repository") as mock_scan:
        from app.core.exceptions import RepositoryImportError
        mock_scan.side_effect = RepositoryImportError("Repository clone is not completed")
        
        response = client.post(f"/api/v1/repositories/{repo_id}/scan")
        
        assert response.status_code == 400
        assert "detail" in response.json()
        assert "Scan failed" in response.json()["detail"]
