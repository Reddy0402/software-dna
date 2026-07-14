import os
import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.config import settings
from app.models.repository import Repository
from app.models.file import File
from app.utils.detector import LanguageDetector
from app.core.exceptions import RepositoryImportError

logger = logging.getLogger("app.services.scanner")


class ScannerService:
    @staticmethod
    def scan_repository(db: Session, repository_id: uuid.UUID) -> dict:
        """
        Recursively scans a repository's workspace directory, ignores unwanted folders/files,
        detects file languages, collects metadata, and persists a manifest in the DB.
        """
        # Retrieve repository record
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise RepositoryImportError(f"Repository record with ID {repository_id} not found")

        if repo.clone_status != "completed":
            raise RepositoryImportError(
                f"Repository clone is not completed (current status: {repo.clone_status})"
            )

        workspace_path = repo.local_path
        if not workspace_path or not os.path.exists(workspace_path):
            raise RepositoryImportError(
                f"Local repository workspace path does not exist: '{workspace_path}'"
            )

        logger.info(f"[{repository_id}] Starting filesystem scan at '{workspace_path}'...")

        # Delete existing File entries to ensure a clean re-scan manifest
        try:
            db.query(File).filter(File.repository_id == repository_id).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"[{repository_id}] Failed to clear old scan records: {str(e)}")
            raise RepositoryImportError(f"Database error clearing old files: {str(e)}")

        ignored_dirs = {d.lower() for d in settings.IGNORED_DIRECTORIES}
        
        file_mappings = []
        total_files_scanned = 0
        supported_files_found = 0
        language_distribution = {}

        # Traverse directory recursively
        for root, dirs, filenames in os.walk(workspace_path):
            # Prune directory search list in-place to prevent os.walk from entering ignored directories
            dirs[:] = [d for d in dirs if d.lower() not in ignored_dirs]

            for filename in filenames:
                total_files_scanned += 1
                file_abs_path = os.path.abspath(os.path.join(root, filename))

                # Skip symbolic links to prevent circular loops
                if os.path.islink(file_abs_path):
                    continue

                # Detect if the file is supported
                language = LanguageDetector.detect_language(filename)
                if not language:
                    continue

                supported_files_found += 1
                language_distribution[language] = language_distribution.get(language, 0) + 1

                # Gather file statistics and metadata
                try:
                    relative_path = os.path.relpath(file_abs_path, workspace_path).replace("\\", "/")
                    depth = relative_path.count("/")
                    
                    stat_info = os.stat(file_abs_path)
                    size_bytes = stat_info.st_size
                    last_modified = datetime.fromtimestamp(stat_info.st_mtime, tz=timezone.utc).replace(tzinfo=None)
                    
                    _, ext_with_dot = os.path.splitext(filename.lower())
                    extension = ext_with_dot.lstrip(".")

                    file_mappings.append({
                        "id": uuid.uuid4(),
                        "repository_id": repository_id,
                        "absolute_path": file_abs_path,
                        "relative_path": relative_path,
                        "filename": filename,
                        "extension": extension,
                        "language": language,
                        "depth": depth,
                        "size_bytes": size_bytes,
                        "last_modified": last_modified
                    })
                except OSError as e:
                    logger.warning(
                        f"[{repository_id}] Failed to read stats for file '{file_abs_path}': {str(e)}"
                    )
                    continue

        # Bulk insert records for optimized database insertion performance
        if file_mappings:
            try:
                db.bulk_insert_mappings(File, file_mappings)
                db.commit()
                logger.info(f"[{repository_id}] Successfully scanned and saved {len(file_mappings)} file records.")
            except Exception as e:
                db.rollback()
                logger.error(f"[{repository_id}] Failed to bulk-insert scan results: {str(e)}")
                raise RepositoryImportError(f"Database error during bulk file insert: {str(e)}")
        else:
            logger.info(f"[{repository_id}] Scan completed. No supported files discovered.")

        return {
            "repository_id": repository_id,
            "total_files_scanned": total_files_scanned,
            "supported_files_found": supported_files_found,
            "language_distribution": language_distribution
        }
