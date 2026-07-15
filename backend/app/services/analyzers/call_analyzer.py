"""
Call Analyzer
=============
Discovers CALLS and REFERENCES relationships by analyzing function/method entities.
  - Method defined inside a class that calls another method → CALLS
  - Function calling another function in the same or different file → CALLS
  - Entity referencing another entity name in its metadata → REFERENCES
  - Recursive function calls (self-referencing) → CALLS with recursive flag
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

logger = logging.getLogger("app.services.analyzers.call")


@register_analyzer
class CallAnalyzer(BaseAnalyzer):
    """Produces CALLS and REFERENCES edges from function/method metadata."""

    def analyze(
        self,
        entities: list,
        files: list,
        entity_lookup: Dict[uuid.UUID, object],
        fqn_lookup: Dict[str, uuid.UUID],
    ) -> List[DependencyRecord]:
        records: List[DependencyRecord] = []

        file_path_map: Dict[uuid.UUID, str] = {
            f.id: f.relative_path for f in files
        }

        # Build a name → [entity] lookup for call resolution
        name_entity_map: Dict[str, List] = {}
        for e in entities:
            if e.entity_type in ("function", "method", "constructor"):
                name_entity_map.setdefault(e.name, []).append(e)

        # Analyze callable entities for call relationships
        callable_entities = [
            e for e in entities
            if e.entity_type in ("function", "method", "constructor")
        ]

        for entity in callable_entities:
            source_file = file_path_map.get(entity.file_id, "")
            meta = entity.meta_data or {}
            calls_list = meta.get("calls", [])
            references_list = meta.get("references", [])

            # Process explicit call references from metadata
            for call_target in calls_list:
                target_id = self._resolve_call(
                    call_target, entity, fqn_lookup, name_entity_map
                )
                is_recursive = (target_id == entity.id)

                records.append(DependencyRecord(
                    repository_id=entity.repository_id,
                    source_entity_id=entity.id,
                    target_entity_id=target_id,
                    relationship_type=RelationshipType.CALLS,
                    confidence=0.9 if target_id else 0.5,
                    source_file=source_file,
                    line_number=entity.start_line,
                    target_fqn=call_target,
                    meta_data={
                        "caller": entity.name,
                        "callee": call_target,
                        "recursive": is_recursive,
                        "resolved": target_id is not None,
                    },
                ))

            # Process explicit references from metadata
            for ref_target in references_list:
                target_id = self._resolve_reference(
                    ref_target, entity, fqn_lookup, entities
                )

                records.append(DependencyRecord(
                    repository_id=entity.repository_id,
                    source_entity_id=entity.id,
                    target_entity_id=target_id,
                    relationship_type=RelationshipType.REFERENCES,
                    confidence=0.7 if target_id else 0.4,
                    source_file=source_file,
                    line_number=entity.start_line,
                    target_fqn=ref_target,
                    meta_data={
                        "referrer": entity.name,
                        "referenced": ref_target,
                        "resolved": target_id is not None,
                    },
                ))

            # Infer method → method calls within the same class scope
            if entity.entity_type == "method" and entity.parent_id:
                sibling_methods = [
                    e for e in entities
                    if e.parent_id == entity.parent_id
                    and e.entity_type == "method"
                    and e.id != entity.id
                ]
                # Check parameters for potential references to sibling method names
                params = meta.get("parameters", [])
                for sibling in sibling_methods:
                    # Heuristic: if a method's metadata references a sibling name
                    if sibling.name in str(meta.get("calls", [])):
                        records.append(DependencyRecord(
                            repository_id=entity.repository_id,
                            source_entity_id=entity.id,
                            target_entity_id=sibling.id,
                            relationship_type=RelationshipType.CALLS,
                            confidence=0.8,
                            source_file=source_file,
                            line_number=entity.start_line,
                            target_fqn=sibling.fully_qualified_name,
                            meta_data={
                                "caller": entity.name,
                                "callee": sibling.name,
                                "inferred": True,
                            },
                        ))

        logger.info(
            f"CallAnalyzer produced {len(records)} CALLS/REFERENCES records"
        )
        return records

    @staticmethod
    def _resolve_call(
        target_name: str,
        source_entity,
        fqn_lookup: Dict[str, uuid.UUID],
        name_entity_map: Dict[str, List],
    ) -> uuid.UUID | None:
        """Resolve a call target to an entity UUID."""
        # FQN match
        if target_name in fqn_lookup:
            return fqn_lookup[target_name]

        # Simple name match — prefer same-file entities
        candidates = name_entity_map.get(target_name, [])
        if candidates:
            # Prefer same file
            for c in candidates:
                if c.file_id == source_entity.file_id:
                    return c.id
            return candidates[0].id

        return None

    @staticmethod
    def _resolve_reference(
        target_name: str,
        source_entity,
        fqn_lookup: Dict[str, uuid.UUID],
        entities: list,
    ) -> uuid.UUID | None:
        """Resolve a reference target to an entity UUID."""
        if target_name in fqn_lookup:
            return fqn_lookup[target_name]

        # Name match across all entities
        for e in entities:
            if e.name == target_name and e.id != source_entity.id:
                return e.id

        return None
