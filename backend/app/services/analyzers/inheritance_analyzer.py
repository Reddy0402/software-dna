"""
Inheritance Analyzer
====================
Discovers EXTENDS and IMPLEMENTS relationships from class/interface metadata.
  - Python: class with `bases` in meta_data → EXTENDS for each base class
  - Java/C#/TypeScript: class implementing interface → IMPLEMENTS
  - General: any entity with base/superclass info in meta_data → EXTENDS
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

logger = logging.getLogger("app.services.analyzers.inheritance")


@register_analyzer
class InheritanceAnalyzer(BaseAnalyzer):
    """Produces EXTENDS and IMPLEMENTS edges from inheritance metadata."""

    # Entity types that indicate an interface rather than a class
    INTERFACE_TYPES = {"interface"}

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

        # Index interface entities by name for fast lookup
        interface_names = set()
        for e in entities:
            if e.entity_type in self.INTERFACE_TYPES:
                interface_names.add(e.name)

        for entity in entities:
            if entity.entity_type not in ("class", "struct"):
                continue

            meta = entity.meta_data or {}
            bases = meta.get("bases", [])
            implements_list = meta.get("implements", [])
            source_file = file_path_map.get(entity.file_id, "")

            # Process base classes / superclasses
            for base_name in bases:
                if not base_name:
                    continue

                target_id = self._resolve_base(
                    base_name, entity, fqn_lookup, entities
                )

                # Determine if this is EXTENDS or IMPLEMENTS
                # If the base name matches a known interface, use IMPLEMENTS
                if base_name in interface_names:
                    rel_type = RelationshipType.IMPLEMENTS
                else:
                    rel_type = RelationshipType.EXTENDS

                records.append(DependencyRecord(
                    repository_id=entity.repository_id,
                    source_entity_id=entity.id,
                    target_entity_id=target_id,
                    relationship_type=rel_type,
                    confidence=1.0 if target_id else 0.7,
                    source_file=source_file,
                    line_number=entity.start_line,
                    target_fqn=base_name,
                    meta_data={
                        "child_class": entity.name,
                        "base_class": base_name,
                        "resolved": target_id is not None,
                    },
                ))

            # Process explicit implements list (Java/C#/TypeScript)
            for iface_name in implements_list:
                if not iface_name:
                    continue

                target_id = self._resolve_base(
                    iface_name, entity, fqn_lookup, entities
                )

                records.append(DependencyRecord(
                    repository_id=entity.repository_id,
                    source_entity_id=entity.id,
                    target_entity_id=target_id,
                    relationship_type=RelationshipType.IMPLEMENTS,
                    confidence=1.0 if target_id else 0.7,
                    source_file=source_file,
                    line_number=entity.start_line,
                    target_fqn=iface_name,
                    meta_data={
                        "child_class": entity.name,
                        "interface": iface_name,
                        "resolved": target_id is not None,
                    },
                ))

        logger.info(
            f"InheritanceAnalyzer produced {len(records)} EXTENDS/IMPLEMENTS records"
        )
        return records

    @staticmethod
    def _resolve_base(
        base_name: str,
        source_entity,
        fqn_lookup: Dict[str, uuid.UUID],
        entities: list,
    ) -> uuid.UUID | None:
        """
        Attempt to resolve a base class / interface name to an entity UUID.
        Searches by FQN, then by simple name matching.
        """
        # Direct FQN match
        if base_name in fqn_lookup:
            return fqn_lookup[base_name]

        # Try with module prefix from source entity
        parts = source_entity.fully_qualified_name.rsplit(".", 1)
        if len(parts) > 1:
            module_prefix = parts[0]
            candidate_fqn = f"{module_prefix}.{base_name}"
            if candidate_fqn in fqn_lookup:
                return fqn_lookup[candidate_fqn]

        # Simple name match across all entities
        for e in entities:
            if (e.name == base_name
                    and e.entity_type in ("class", "interface", "struct")
                    and e.id != source_entity.id):
                return e.id

        return None
