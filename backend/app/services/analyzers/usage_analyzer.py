"""
Usage Analyzer
==============
Discovers USES relationships from type references and parameter types.
  - Function/method with typed parameters referencing a class/interface → USES
  - Decorator usage → USES
  - Return type annotations → USES
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

logger = logging.getLogger("app.services.analyzers.usage")


@register_analyzer
class UsageAnalyzer(BaseAnalyzer):
    """Produces USES edges from type annotations, decorators, and parameter types."""

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

        # Build class/interface name → entity id lookup
        type_name_map: Dict[str, uuid.UUID] = {}
        for e in entities:
            if e.entity_type in ("class", "interface", "struct"):
                type_name_map[e.name] = e.id
                type_name_map[e.fully_qualified_name] = e.id

        for entity in entities:
            meta = entity.meta_data or {}
            source_file = file_path_map.get(entity.file_id, "")

            # --- Decorator usage ---
            decorators = meta.get("decorators", [])
            for decorator_name in decorators:
                if not decorator_name:
                    continue

                target_id = self._resolve_type(
                    decorator_name, fqn_lookup, type_name_map
                )

                records.append(DependencyRecord(
                    repository_id=entity.repository_id,
                    source_entity_id=entity.id,
                    target_entity_id=target_id,
                    relationship_type=RelationshipType.USES,
                    confidence=0.8 if target_id else 0.4,
                    source_file=source_file,
                    line_number=entity.start_line,
                    target_fqn=decorator_name,
                    meta_data={
                        "usage_type": "decorator",
                        "decorator": decorator_name,
                        "resolved": target_id is not None,
                    },
                ))

            # --- Return type usage ---
            return_type = meta.get("return_type")
            if return_type and entity.entity_type in ("function", "method"):
                target_id = self._resolve_type(
                    return_type, fqn_lookup, type_name_map
                )
                if target_id and target_id != entity.id:
                    records.append(DependencyRecord(
                        repository_id=entity.repository_id,
                        source_entity_id=entity.id,
                        target_entity_id=target_id,
                        relationship_type=RelationshipType.USES,
                        confidence=0.8,
                        source_file=source_file,
                        line_number=entity.start_line,
                        target_fqn=return_type,
                        meta_data={
                            "usage_type": "return_type",
                            "type_name": return_type,
                        },
                    ))

            # --- Parameter type usage ---
            param_types = meta.get("parameter_types", [])
            for ptype in param_types:
                if not ptype:
                    continue
                target_id = self._resolve_type(
                    ptype, fqn_lookup, type_name_map
                )
                if target_id and target_id != entity.id:
                    records.append(DependencyRecord(
                        repository_id=entity.repository_id,
                        source_entity_id=entity.id,
                        target_entity_id=target_id,
                        relationship_type=RelationshipType.USES,
                        confidence=0.8,
                        source_file=source_file,
                        line_number=entity.start_line,
                        target_fqn=ptype,
                        meta_data={
                            "usage_type": "parameter_type",
                            "type_name": ptype,
                        },
                    ))

        logger.info(
            f"UsageAnalyzer produced {len(records)} USES records"
        )
        return records

    @staticmethod
    def _resolve_type(
        type_name: str,
        fqn_lookup: Dict[str, uuid.UUID],
        type_name_map: Dict[str, uuid.UUID],
    ) -> uuid.UUID | None:
        """Resolve a type/decorator name to an entity UUID."""
        # Strip decorator syntax (e.g. "@staticmethod" → "staticmethod")
        clean = type_name.lstrip("@").strip()

        # Strip call parens (e.g. "property()" → "property")
        if "(" in clean:
            clean = clean.split("(")[0].strip()

        if clean in fqn_lookup:
            return fqn_lookup[clean]
        if clean in type_name_map:
            return type_name_map[clean]
        return None
