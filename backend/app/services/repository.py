import os
import uuid
import shutil
import logging
from sqlalchemy.orm import Session
from app.config import settings
from app.models.repository import Repository
from app.utils.git import GitUtility
from app.core.exceptions import RepositoryImportError

logger = logging.getLogger("app.services.repository")


class RepositoryService:
    @staticmethod
    def create_pending_record(db: Session, url: str) -> Repository:
        """
        Validates the URL, extracts owner and name, creates a database record with
        'pending' status and returns the record.
        """
        if not GitUtility.validate_github_url(url):
            raise RepositoryImportError(f"Invalid GitHub repository URL: '{url}'")

        owner, repo_name = GitUtility.extract_owner_and_name(url)
        
        # Create database object in pending status
        db_obj = Repository(
            name=repo_name,
            url=url,
            owner=owner,
            clone_status="pending",
            parser_status="pending",
            graph_status="pending"
        )
        
        try:
            db.add(db_obj)
            db.commit()
            db.refresh(db_obj)
            logger.info(f"Created pending repository record: {db_obj.id} for URL: {url}")
            return db_obj
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to create database record for {url}: {str(e)}")
            raise RepositoryImportError(f"Database insertion failed: {str(e)}")

    @staticmethod
    def import_repository(db: Session, repo_id: uuid.UUID) -> Repository:
        """
        Orchestrates the repository import flow:
        - Updates status to 'cloning'
        - Generates workspace directory
        - Clones repository using GitUtility
        - Collects metadata
        - Updates database and status to 'completed'
        - Cleans up directory and logs error if cloning fails
        """
        # Fetch the repository record
        repo_record = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo_record:
            raise RepositoryImportError(f"Repository record with ID {repo_id} not found")

        # 1. Update status to 'cloning'
        try:
            repo_record.clone_status = "cloning"
            workspace_base = settings.WORKSPACE_BASE_DIR
            dest_path = os.path.abspath(os.path.join(workspace_base, str(repo_id)))
            repo_record.local_path = dest_path
            db.commit()
            db.refresh(repo_record)
            logger.info(f"[{repo_id}] Starting cloning process for '{repo_record.url}'")
        except Exception as e:
            db.rollback()
            logger.error(f"[{repo_id}] Failed to set cloning status: {str(e)}")
            raise RepositoryImportError(f"Database error during status update: {str(e)}")

        try:
            # 2. Perform clone
            git_repo = GitUtility.clone_repository(
                repo_url=repo_record.url,
                dest_path=dest_path,
                timeout=settings.GIT_CLONE_TIMEOUT,
                git_executable=settings.GIT_EXECUTABLE
            )

            # 3. Retrieve metadata
            metadata = GitUtility.get_repository_metadata(git_repo, dest_path)

            # 4. Save metadata and mark complete
            repo_record.default_branch = metadata["default_branch"]
            repo_record.latest_commit_hash = metadata["latest_commit_hash"]
            repo_record.size_bytes = metadata["size_bytes"]
            repo_record.total_files = metadata["total_files"]
            repo_record.clone_status = "completed"
            repo_record.last_error = None
            
            db.commit()
            db.refresh(repo_record)
            logger.info(f"[{repo_id}] Successfully imported repository and saved metadata.")
            return repo_record

        except Exception as e:
            logger.error(f"[{repo_id}] Import failed. Error: {str(e)}")
            
            # Rollback database changes to metadata updates in the current transaction if any
            db.rollback()
            
            # Fetch record again to update status to failed and store the error message
            repo_record = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo_record:
                repo_record.clone_status = "failed"
                repo_record.last_error = str(e)
                try:
                    db.commit()
                    db.refresh(repo_record)
                except Exception as db_err:
                    db.rollback()
                    logger.error(f"[{repo_id}] Failed to save failure status: {str(db_err)}")

            # 5. Clean up filesystem workspace directory
            if os.path.exists(dest_path):
                logger.info(f"[{repo_id}] Cleaning up workspace directory '{dest_path}' due to failure...")
                shutil.rmtree(dest_path, ignore_errors=True)

            raise RepositoryImportError(str(e))
