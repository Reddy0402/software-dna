"""
Containment Analyzer
====================
Discovers CONTAINS and DEFINES relationships from parent-child CodeEntity nesting.
  - File CONTAINS top-level entities (classes, functions, imports)
  - Class/Interface CONTAINS its methods, inner classes
  - Namespace CONTAINS its children
  - Parent entity DEFINES each direct child entity
"""
import logging
import uuid
from typing import List, Dict

from app.services.analyzers import (
    BaseAnalyzer,
    DependencyRecord,
    RelationshipType,
    register_analyzer,
)

logger = logging.getLogger("app.services.analyzers.containment")


@register_analyzer
class ContainmentAnalyzer(BaseAnalyzer):
    """Produces CONTAINS and DEFINES edges from the entity parent-child hierarchy."""

    def analyze(
        self,
        entities: list,
        files: list,
        entity_lookup: Dict[uuid.UUID, object],
        fqn_lookup: Dict[str, uuid.UUID],
    ) -> List[DependencyRecord]:
        records: List[DependencyRecord] = []

        # Build a file-id → relative_path lookup
        file_path_map: Dict[uuid.UUID, str] = {
            f.id: f.relative_path for f in files
        }

        for entity in entities:
            source_file = file_path_map.get(entity.file_id, "")

            # --- CONTAINS: parent → child ---
            if entity.parent_id is not None:
                parent = entity_lookup.get(entity.parent_id)
                if parent:
                    records.append(DependencyRecord(
                        repository_id=entity.repository_id,
                        source_entity_id=entity.parent_id,
                        target_entity_id=entity.id,
                        relationship_type=RelationshipType.CONTAINS,
                        confidence=1.0,
                        source_file=source_file,
                        line_number=entity.start_line,
                        target_fqn=entity.fully_qualified_name,
                        meta_data={
                            "parent_type": parent.entity_type,
                            "child_type": entity.entity_type,
                        },
                    ))

            # --- DEFINES: parent defines child (structural ownership) ---
            if entity.parent_id is not None:
                parent = entity_lookup.get(entity.parent_id)
                if parent:
                    records.append(DependencyRecord(
                        repository_id=entity.repository_id,
                        source_entity_id=entity.parent_id,
                        target_entity_id=entity.id,
                        relationship_type=RelationshipType.DEFINES,
                        confidence=1.0,
                        source_file=source_file,
                        line_number=entity.start_line,
                        target_fqn=entity.fully_qualified_name,
                        meta_data={
                            "parent_type": parent.entity_type,
                            "child_type": entity.entity_type,
                        },
                    ))

        logger.info(
            f"ContainmentAnalyzer produced {len(records)} CONTAINS/DEFINES records"
        )
        return records
