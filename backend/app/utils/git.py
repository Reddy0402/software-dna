import os
import re
import shutil
import logging
from typing import Tuple, Optional
import git
from app.core.exceptions import InvalidRepositoryURLError, GitCloneError

logger = logging.getLogger("app.utils.git")


class GitUtility:
    # Pattern to match standard GitHub HTTP(S) URLs
    # Example matches:
    # - https://github.com/owner/repo
    # - http://github.com/owner/repo.git
    # - https://www.github.com/owner/repo/
    GITHUB_URL_PATTERN = re.compile(
        r"^https?://(?:www\.)?github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$"
    )

    @classmethod
    def validate_github_url(cls, url: str) -> bool:
        """
        Validates if the provided URL is a valid GitHub repository URL.
        """
        if not url:
            return False
        return bool(cls.GITHUB_URL_PATTERN.match(url.strip()))

    @classmethod
    def extract_owner_and_name(cls, url: str) -> Tuple[str, str]:
        """
        Extracts the repository owner and repository name from a GitHub URL.
        Raises InvalidRepositoryURLError if the URL is invalid.
        """
        if not url:
            raise InvalidRepositoryURLError("Repository URL is empty")
            
        match = cls.GITHUB_URL_PATTERN.match(url.strip())
        if not match:
            raise InvalidRepositoryURLError(f"Invalid GitHub repository URL: '{url}'")
            
        owner, repo_name = match.groups()
        return owner, repo_name

    @classmethod
    def clone_repository(
        cls,
        repo_url: str,
        dest_path: str,
        timeout: int = 300,
        git_executable: Optional[str] = None
    ) -> git.Repo:
        """
        Clones a remote repository to a local path using GitPython.
        Cleans up and removes destination path if clone fails.
        """
        # Validate URL format
        if not cls.validate_github_url(repo_url):
            raise InvalidRepositoryURLError(f"Invalid GitHub repository URL: '{repo_url}'")

        # Prepare workspace directory
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        if os.path.exists(dest_path):
            shutil.rmtree(dest_path, ignore_errors=True)

        logger.info(f"Cloning repository '{repo_url}' to '{dest_path}' with timeout {timeout}s...")
        try:
            # Set git executable if provided
            if git_executable:
                git.refresh(git_executable)

            git_cmd = git.cmd.Git()
            # Perform git clone with timeout limit
            git_cmd.clone(repo_url, dest_path, kill_after_timeout=timeout)
            
            repo = git.Repo(dest_path)
            logger.info(f"Successfully cloned repository '{repo_url}' to '{dest_path}'")
            return repo
        except git.exc.GitCommandError as e:
            logger.error(f"GitCommandError during clone of '{repo_url}': {str(e)}")
            # Cleanup on failure
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path, ignore_errors=True)
            raise GitCloneError(f"Git clone operation failed: {e.stderr or str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during clone of '{repo_url}': {str(e)}")
            # Cleanup on failure
            if os.path.exists(dest_path):
                shutil.rmtree(dest_path, ignore_errors=True)
            raise GitCloneError(f"Failed to clone repository: {str(e)}")

    @classmethod
    def get_repository_metadata(cls, repo: git.Repo, dest_path: str) -> dict:
        """
        Walks the cloned repository to extract metadata:
        - Default branch
        - Latest commit hash
        - Repository size on disk (excluding .git)
        - Total number of files (excluding .git)
        """
        # 1. Default branch
        try:
            default_branch = repo.active_branch.name
        except Exception:
            # Detached head or other issue, check remote origin HEAD
            default_branch = None
            try:
                for ref in repo.remotes.origin.refs:
                    if ref.name == 'origin/HEAD':
                        default_branch = ref.ref.name.split('/')[-1]
                        break
            except Exception:
                pass
            if not default_branch:
                default_branch = "main"

        # 2. Latest commit hash
        try:
            latest_commit_hash = repo.head.commit.hexsha
        except Exception as e:
            logger.warning(f"Could not retrieve latest commit hash: {str(e)}")
            latest_commit_hash = None

        # 3 & 4. Size and file count (excluding .git folder)
        size_bytes = 0
        total_files = 0
        
        for root, dirs, files in os.walk(dest_path):
            # Prune .git folder
            if '.git' in dirs:
                dirs.remove('.git')
            
            for file in files:
                filepath = os.path.join(root, file)
                try:
                    # check if the path exists (handle broken symlinks)
                    if os.path.exists(filepath) and not os.path.islink(filepath):
                        size_bytes += os.path.getsize(filepath)
                        total_files += 1
                except OSError as e:
                    logger.warning(f"Error reading file details for size: {filepath}. Error: {str(e)}")
                    
        return {
            "default_branch": default_branch,
            "latest_commit_hash": latest_commit_hash,
            "size_bytes": size_bytes,
            "total_files": total_files
        }
