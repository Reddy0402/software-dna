"""
Dependency Extraction Service
==============================
Orchestrates the full dependency extraction pipeline for a repository:
  1. Retrieve metadata (CodeEntities + Files) from PostgreSQL
  2. Run all registered analyzers to infer relationships
  3. Validate and deduplicate discovered dependencies
  4. Persist to PostgreSQL for later Neo4j synchronization
"""
import uuid
import logging
from typing import List, Dict, Tuple

from sqlalchemy.orm import Session

from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency
from app.models.repository import Repository
from app.core.exceptions import DependencyExtractionError
from app.services.analyzers import (
    DependencyRecord,
    RelationshipType,
    get_all_analyzers,
)

logger = logging.getLogger("app.services.dependency_extractor")


class DependencyExtractionService:
    """
    Main service that coordinates the dependency extraction pipeline.
    Stateless — all state flows through method parameters.
    """

    @staticmethod
    def extract_dependencies(db: Session, repository_id: uuid.UUID) -> Dict:
        """
        Full extraction pipeline entry point.

        Args:
            db:             SQLAlchemy session.
            repository_id:  UUID of the repository to analyze.

        Returns:
            Dict with extraction statistics.

        Raises:
            DependencyExtractionError on any pipeline failure.
        """
        logger.info(f"[{repository_id}] Starting dependency extraction pipeline...")

        # Verify repository exists
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise DependencyExtractionError(
                f"Repository with ID {repository_id} not found"
            )

        # Step 1: Retrieve metadata
        entities, files = DependencyExtractionService._retrieve_metadata(
            db, repository_id
        )

        if not entities:
            logger.info(
                f"[{repository_id}] No code entities found. Nothing to extract."
            )
            return {
                "repository_id": repository_id,
                "total_dependencies": 0,
                "by_relationship_type": {},
                "avg_confidence": 0.0,
                "unresolved_count": 0,
            }

        # Step 2: Infer relationships
        raw_records = DependencyExtractionService._infer_relationships(
            entities, files
        )

        # Step 3: Validate and deduplicate
        validated_records = DependencyExtractionService._validate_dependencies(
            raw_records
        )

        # Step 4: Persist
        DependencyExtractionService._persist_dependencies(
            db, repository_id, validated_records
        )

        # Compute statistics
        stats = DependencyExtractionService._compute_stats(
            repository_id, validated_records
        )

        logger.info(
            f"[{repository_id}] Dependency extraction complete. "
            f"Total: {stats['total_dependencies']}, "
            f"Unresolved: {stats['unresolved_count']}"
        )

        return stats

    @staticmethod
    def _retrieve_metadata(
        db: Session, repository_id: uuid.UUID
    ) -> Tuple[List[CodeEntity], List[File]]:
        """
        Step 1: Fetch all CodeEntity and File records for the repository.
        """
        logger.info(f"[{repository_id}] Step 1: Retrieving metadata...")

        try:
            entities = (
                db.query(CodeEntity)
                .filter(CodeEntity.repository_id == repository_id)
                .all()
            )
            files = (
                db.query(File)
                .filter(File.repository_id == repository_id)
                .all()
            )
        except Exception as e:
            logger.error(
                f"[{repository_id}] Failed to retrieve metadata: {str(e)}"
            )
            raise DependencyExtractionError(
                f"Database error retrieving metadata: {str(e)}"
            )

        logger.info(
            f"[{repository_id}] Retrieved {len(entities)} entities "
            f"and {len(files)} files."
        )
        return entities, files

    @staticmethod
    def _infer_relationships(
        entities: List[CodeEntity], files: List[File]
    ) -> List[DependencyRecord]:
        """
        Step 2: Run all registered analyzers against the entity/file dataset.
        """
        logger.info("Step 2: Running dependency analyzers...")

        # Build lookups shared across all analyzers
        entity_lookup: Dict[uuid.UUID, CodeEntity] = {
            e.id: e for e in entities
        }
        fqn_lookup: Dict[str, uuid.UUID] = {
            e.fully_qualified_name: e.id for e in entities
        }

        all_records: List[DependencyRecord] = []
        analyzers = get_all_analyzers()

        for analyzer in analyzers:
            analyzer_name = type(analyzer).__name__
            try:
                records = analyzer.analyze(
                    entities=entities,
                    files=files,
                    entity_lookup=entity_lookup,
                    fqn_lookup=fqn_lookup,
                )
                all_records.extend(records)
                logger.info(
                    f"  {analyzer_name}: produced {len(records)} records"
                )
            except Exception as e:
                logger.error(
                    f"  {analyzer_name} failed: {str(e)}", exc_info=True
                )
                # Continue with other analyzers — don't let one failure
                # stop the entire pipeline
                continue

        logger.info(
            f"Step 2 complete. Total raw records: {len(all_records)}"
        )
        return all_records

    @staticmethod
    def _validate_dependencies(
        records: List[DependencyRecord],
    ) -> List[DependencyRecord]:
        """
        Step 3: Deduplicate and validate dependency records.
        - Remove exact duplicates (same source, target, type, fqn)
        - Validate relationship_type is known
        - Clamp confidence to [0.0, 1.0]
        """
        logger.info(f"Step 3: Validating {len(records)} raw records...")

        seen_keys = set()
        validated: List[DependencyRecord] = []

        for record in records:
            # Validate relationship type
            if record.relationship_type not in RelationshipType.ALL:
                logger.warning(
                    f"  Skipping record with unknown relationship type: "
                    f"{record.relationship_type}"
                )
                continue

            # Clamp confidence
            record.confidence = max(0.0, min(1.0, record.confidence))

            # Deduplicate
            key = record.unique_key()
            if key in seen_keys:
                continue
            seen_keys.add(key)

            validated.append(record)

        logger.info(
            f"Step 3 complete. {len(records)} → {len(validated)} "
            f"after deduplication/validation"
        )
        return validated

    @staticmethod
    def _persist_dependencies(
        db: Session,
        repository_id: uuid.UUID,
        records: List[DependencyRecord],
    ) -> None:
        """
        Step 4: Clear old dependencies and bulk-insert validated records.
        """
        logger.info(
            f"[{repository_id}] Step 4: Persisting {len(records)} dependencies..."
        )

        # Clear existing dependencies for this repository
        try:
            db.query(Dependency).filter(
                Dependency.repository_id == repository_id
            ).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(
                f"[{repository_id}] Failed to clear old dependencies: {str(e)}"
            )
            raise DependencyExtractionError(
                f"Database error clearing old dependencies: {str(e)}"
            )

        if not records:
            logger.info(
                f"[{repository_id}] No dependencies to persist."
            )
            return

        # Build bulk insert mappings
        mappings = []
        for record in records:
            mappings.append({
                "id": uuid.uuid4(),
                "repository_id": record.repository_id,
                "source_entity_id": record.source_entity_id,
                "target_entity_id": record.target_entity_id,
                "relationship_type": record.relationship_type,
                "confidence": record.confidence,
                "source_file": record.source_file,
                "line_number": record.line_number,
                "target_fqn": record.target_fqn,
                "meta_data": record.meta_data,
            })

        try:
            db.bulk_insert_mappings(Dependency, mappings)
            db.commit()
            logger.info(
                f"[{repository_id}] Successfully persisted "
                f"{len(mappings)} dependency records."
            )
        except Exception as e:
            db.rollback()
            logger.error(
                f"[{repository_id}] Failed to persist dependencies: {str(e)}"
            )
            raise DependencyExtractionError(
                f"Database error persisting dependencies: {str(e)}"
            )

    @staticmethod
    def _compute_stats(
        repository_id: uuid.UUID,
        records: List[DependencyRecord],
    ) -> Dict:
        """Compute summary statistics from the validated records."""
        by_type: Dict[str, int] = {}
        total_confidence = 0.0
        unresolved = 0

        for r in records:
            by_type[r.relationship_type] = by_type.get(r.relationship_type, 0) + 1
            total_confidence += r.confidence
            if r.target_entity_id is None:
                unresolved += 1

        total = len(records)
        return {
            "repository_id": repository_id,
            "total_dependencies": total,
            "by_relationship_type": by_type,
            "avg_confidence": round(total_confidence / total, 3) if total > 0 else 0.0,
            "unresolved_count": unresolved,
        }
