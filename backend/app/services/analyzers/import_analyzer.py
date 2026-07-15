"""
Import Analyzer
===============
Discovers IMPORTS and DEPENDS_ON relationships from import-type CodeEntity records.
  - An import entity in file A referencing module/file B → IMPORTS
  - File-level DEPENDS_ON when an import resolves to another file in the repo
Handles cross-file resolution, aliased imports, and unresolved external packages.
"""
import logging
import os
import uuid
from typing import List, Dict, Optional

from app.services.analyzers import (
    BaseAnalyzer,
    DependencyRecord,
    RelationshipType,
    register_analyzer,
)

logger = logging.getLogger("app.services.analyzers.import_analyzer")


@register_analyzer
class ImportAnalyzer(BaseAnalyzer):
    """Produces IMPORTS and DEPENDS_ON edges from import-type entities."""

    def analyze(
        self,
        entities: list,
        files: list,
        entity_lookup: Dict[uuid.UUID, object],
        fqn_lookup: Dict[str, uuid.UUID],
    ) -> List[DependencyRecord]:
        records: List[DependencyRecord] = []

        # Build lookups
        file_path_map: Dict[uuid.UUID, str] = {
            f.id: f.relative_path for f in files
        }
        # Map relative path (without extension) → file id for cross-file resolution
        file_module_map: Dict[str, uuid.UUID] = {}
        for f in files:
            # e.g. "utils/helpers.py" → "utils/helpers" and "utils.helpers"
            base = os.path.splitext(f.relative_path)[0]
            file_module_map[base] = f.id
            # Also store the dot-notation variant
            dot_variant = base.replace("/", ".").replace("\\", ".")
            file_module_map[dot_variant] = f.id

        # Collect all import entities
        import_entities = [e for e in entities if e.entity_type == "import"]

        for imp in import_entities:
            source_file = file_path_map.get(imp.file_id, "")
            raw_import = self._extract_import_target(imp)

            # Try to resolve the import to a known entity in the repository
            target_entity_id = self._resolve_import(
                raw_import, fqn_lookup, file_module_map, entity_lookup
            )

            # IMPORTS relationship: import entity → target entity
            records.append(DependencyRecord(
                repository_id=imp.repository_id,
                source_entity_id=imp.id,
                target_entity_id=target_entity_id,
                relationship_type=RelationshipType.IMPORTS,
                confidence=1.0 if target_entity_id else 0.5,
                source_file=source_file,
                line_number=imp.start_line,
                target_fqn=raw_import,
                meta_data={
                    "raw_import": imp.name,
                    "resolved": target_entity_id is not None,
                },
            ))

            # DEPENDS_ON relationship: source file → target file (file-level)
            if target_entity_id:
                target = entity_lookup.get(target_entity_id)
                if target and target.file_id != imp.file_id:
                    # Find any top-level entity from the source file to anchor the edge
                    source_file_entities = [
                        e for e in entities
                        if e.file_id == imp.file_id and e.parent_id is None
                        and e.entity_type != "import"
                    ]
                    source_anchor_id = (
                        source_file_entities[0].id if source_file_entities else imp.id
                    )
                    records.append(DependencyRecord(
                        repository_id=imp.repository_id,
                        source_entity_id=source_anchor_id,
                        target_entity_id=target_entity_id,
                        relationship_type=RelationshipType.DEPENDS_ON,
                        confidence=0.9,
                        source_file=source_file,
                        line_number=imp.start_line,
                        target_fqn=raw_import,
                        meta_data={"via_import": imp.name},
                    ))

        logger.info(
            f"ImportAnalyzer produced {len(records)} IMPORTS/DEPENDS_ON records"
        )
        return records

    @staticmethod
    def _extract_import_target(entity) -> str:
        """Extract the import target string from the entity metadata or name."""
        meta = entity.meta_data or {}

        # Use raw_import from metadata if available
        raw = meta.get("raw_import", entity.name)

        # Normalize: strip leading 'from ', 'import ', keywords
        target = raw.strip()
        for prefix in ("from ", "import ", "using ", "#include "):
            if target.lower().startswith(prefix):
                target = target[len(prefix):].strip()

        # For 'from X import Y', extract X
        if " import " in target:
            target = target.split(" import ")[0].strip()

        # Strip quotes and angle brackets (for C/C++ includes)
        target = target.strip("\"'<>;")

        return target

    @staticmethod
    def _resolve_import(
        target: str,
        fqn_lookup: Dict[str, uuid.UUID],
        file_module_map: Dict[str, uuid.UUID],
        entity_lookup: Dict[uuid.UUID, object],
    ) -> Optional[uuid.UUID]:
        """
        Attempt to resolve an import target to an entity UUID.
        Tries FQN lookup first, then file-module path matching.
        """
        # Direct FQN match
        if target in fqn_lookup:
            return fqn_lookup[target]

        # Try module path → file → first entity in that file
        if target in file_module_map:
            target_file_id = file_module_map[target]
            # Find first non-import entity in target file
            for eid, entity in entity_lookup.items():
                if (entity.file_id == target_file_id
                        and entity.parent_id is None
                        and entity.entity_type != "import"):
                    return eid
            # Fallback: any entity in that file
            for eid, entity in entity_lookup.items():
                if entity.file_id == target_file_id:
                    return eid

        # Try partial matching (e.g. "os.path" might match "os.path.join")
        for fqn, eid in fqn_lookup.items():
            if fqn.startswith(target + ".") or fqn.endswith("." + target):
                return eid

        return None
