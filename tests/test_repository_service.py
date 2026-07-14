import pytest
import os
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.services.repository import RepositoryService
from app.models.repository import Repository
from app.core.exceptions import RepositoryImportError


def test_create_pending_record(db_session: Session):
    url = "https://github.com/Reddy0402/software-dna"
    repo = RepositoryService.create_pending_record(db_session, url)
    
    assert repo.id is not None
    assert repo.url == url
    assert repo.name == "software-dna"
    assert repo.owner == "Reddy0402"
    assert repo.clone_status == "pending"
    assert repo.parser_status == "pending"
    assert repo.graph_status == "pending"

    # Verify duplicate url creations generate unique IDs
    repo2 = RepositoryService.create_pending_record(db_session, url)
    assert repo.id != repo2.id


def test_create_pending_record_invalid_url(db_session: Session):
    with pytest.raises(RepositoryImportError):
        RepositoryService.create_pending_record(db_session, "https://invalid-url.com")


@patch("app.utils.git.GitUtility.clone_repository")
@patch("app.utils.git.GitUtility.get_repository_metadata")
def test_import_repository_success(mock_get_metadata, mock_clone, db_session: Session):
    url = "https://github.com/Reddy0402/software-dna"
    repo = RepositoryService.create_pending_record(db_session, url)
    
    mock_clone.return_value = MagicMock()
    mock_get_metadata.return_value = {
        "default_branch": "main",
        "latest_commit_hash": "1234567890abcdef",
        "size_bytes": 5000,
        "total_files": 42
    }

    with patch("os.path.abspath") as mock_abspath:
        mock_abspath.return_value = "/dummy/workspace/path"
        
        imported_repo = RepositoryService.import_repository(db_session, repo.id)
        
        assert imported_repo.clone_status == "completed"
        assert imported_repo.default_branch == "main"
        assert imported_repo.latest_commit_hash == "1234567890abcdef"
        assert imported_repo.size_bytes == 5000
        assert imported_repo.total_files == 42
        assert imported_repo.local_path == "/dummy/workspace/path"
        assert imported_repo.last_error is None


@patch("app.utils.git.GitUtility.clone_repository")
def test_import_repository_failure(mock_clone, db_session: Session):
    url = "https://github.com/Reddy0402/software-dna"
    repo = RepositoryService.create_pending_record(db_session, url)
    
    mock_clone.side_effect = Exception("Cloning timed out after 300 seconds")

    with patch("shutil.rmtree") as mock_rmtree, patch("os.path.exists") as mock_exists:
        mock_exists.return_value = True
        
        with pytest.raises(RepositoryImportError):
            RepositoryService.import_repository(db_session, repo.id)
            
        # Refetch record to verify status is marked failed and error logged
        db_session.expire_all()
        updated_repo = db_session.query(Repository).filter(Repository.id == repo.id).first()
        assert updated_repo.clone_status == "failed"
        assert "Cloning timed out" in updated_repo.last_error
        mock_rmtree.assert_called()
