import pytest
from unittest.mock import MagicMock, patch
import git
from app.utils.git import GitUtility
from app.core.exceptions import InvalidRepositoryURLError, GitCloneError


def test_validate_github_url():
    # Valid URLs
    assert GitUtility.validate_github_url("https://github.com/owner/repo") is True
    assert GitUtility.validate_github_url("http://github.com/owner/repo.git") is True
    assert GitUtility.validate_github_url("https://www.github.com/owner/repo/") is True
    
    # Invalid URLs
    assert GitUtility.validate_github_url("https://github.com/owner") is False
    assert GitUtility.validate_github_url("https://gitlab.com/owner/repo") is False
    assert GitUtility.validate_github_url("") is False
    assert GitUtility.validate_github_url("invalid-url") is False


def test_extract_owner_and_name():
    owner, name = GitUtility.extract_owner_and_name("https://github.com/owner/repo")
    assert owner == "owner"
    assert name == "repo"

    owner, name = GitUtility.extract_owner_and_name("https://github.com/another-owner/some-repo.git/")
    assert owner == "another-owner"
    assert name == "some-repo"

    with pytest.raises(InvalidRepositoryURLError):
        GitUtility.extract_owner_and_name("https://github.com/owner")


@patch("git.cmd.Git")
@patch("git.Repo")
def test_clone_repository_success(mock_repo_class, mock_git_class):
    mock_git_instance = mock_git_class.return_value
    mock_git_instance.clone = MagicMock()
    
    mock_repo_instance = MagicMock()
    mock_repo_class.return_value = mock_repo_instance

    with patch("os.makedirs") as mock_makedirs, patch("os.path.exists") as mock_exists, patch("shutil.rmtree") as mock_rmtree:
        mock_exists.return_value = False
        repo = GitUtility.clone_repository("https://github.com/owner/repo", "/dummy/path")
        
        assert repo == mock_repo_instance
        mock_git_instance.clone.assert_called_once_with("https://github.com/owner/repo", "/dummy/path", kill_after_timeout=300)


@patch("git.cmd.Git")
def test_clone_repository_failure(mock_git_class):
    mock_git_instance = mock_git_class.return_value
    mock_git_instance.clone.side_effect = git.exc.GitCommandError("clone", 128, "Error")

    with patch("os.makedirs"), patch("os.path.exists") as mock_exists, patch("shutil.rmtree") as mock_rmtree:
        mock_exists.return_value = True
        with pytest.raises(GitCloneError):
            GitUtility.clone_repository("https://github.com/owner/repo", "/dummy/path")
        
        # Verify cleanup was triggered
        mock_rmtree.assert_called_with("/dummy/path", ignore_errors=True)


def test_get_repository_metadata():
    mock_repo = MagicMock()
    mock_repo.active_branch.name = "main"
    mock_repo.head.commit.hexsha = "abcdef123456"

    with patch("os.walk") as mock_walk, patch("os.path.exists") as mock_exists, patch("os.path.getsize") as mock_getsize, patch("os.path.islink") as mock_islink:
        mock_walk.return_value = [
            ("/path/to/repo", ["subdir", ".git"], ["file1.py", "file2.md"]),
            ("/path/to/repo/subdir", [], ["file3.go"])
        ]
        mock_exists.return_value = True
        mock_islink.return_value = False
        mock_getsize.return_value = 100
        
        metadata = GitUtility.get_repository_metadata(mock_repo, "/path/to/repo")
        
        assert metadata["default_branch"] == "main"
        assert metadata["latest_commit_hash"] == "abcdef123456"
        assert metadata["size_bytes"] == 300  # 3 files * 100 bytes
        assert metadata["total_files"] == 3
