"""
Dependency Analyzers Package
============================

Pluggable analyzer classes that inspect CodeEntity metadata to discover
different categories of dependency relationships. Each analyzer produces
a list of DependencyRecord instances — a language-independent intermediate
representation that the DependencyExtractionService persists to PostgreSQL.
"""
import uuid
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict

logger = logging.getLogger("app.services.analyzers")


# ---------------------------------------------------------------------------
# Relationship type constants
# ---------------------------------------------------------------------------
class RelationshipType:
    IMPORTS = "IMPORTS"
    CALLS = "CALLS"
    DEFINES = "DEFINES"
    CONTAINS = "CONTAINS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    REFERENCES = "REFERENCES"

    ALL = [
        IMPORTS, CALLS, DEFINES, CONTAINS, EXTENDS,
        IMPLEMENTS, USES, DEPENDS_ON, REFERENCES
    ]


# ---------------------------------------------------------------------------
# Language-independent intermediate representation
# ---------------------------------------------------------------------------
@dataclass
class DependencyRecord:
    """
    A single dependency edge in language-independent form.
    Produced by analyzers and consumed by the extraction service for persistence.
    """
    repository_id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: Optional[uuid.UUID]
    relationship_type: str
    confidence: float
    source_file: str
    line_number: int
    target_fqn: str
    meta_data: Dict = field(default_factory=dict)

    def unique_key(self) -> str:
        """Generate a deduplication key for this record."""
        return (
            f"{self.source_entity_id}|{self.target_entity_id}|"
            f"{self.relationship_type}|{self.target_fqn}"
        )


# ---------------------------------------------------------------------------
# Base analyzer
# ---------------------------------------------------------------------------
class BaseAnalyzer(ABC):
    """
    Abstract base class for all dependency analyzers.
    Each concrete analyzer inspects a list of CodeEntity records and
    produces DependencyRecord instances for the relationship types it covers.
    """

    @abstractmethod
    def analyze(
        self,
        entities: list,
        files: list,
        entity_lookup: Dict[uuid.UUID, object],
        fqn_lookup: Dict[str, uuid.UUID],
    ) -> List[DependencyRecord]:
        """
        Run the analysis and return discovered dependency records.

        Args:
            entities:       All CodeEntity ORM objects for a repository.
            files:          All File ORM objects for the repository.
            entity_lookup:  Dict mapping entity UUID → CodeEntity object.
            fqn_lookup:     Dict mapping fully_qualified_name → entity UUID.

        Returns:
            List of DependencyRecord instances.
        """
        ...


# ---------------------------------------------------------------------------
# Analyzer registry
# ---------------------------------------------------------------------------
_ANALYZER_REGISTRY: List[type] = []


def register_analyzer(cls: type) -> type:
    """Class decorator that registers an analyzer in the global registry."""
    _ANALYZER_REGISTRY.append(cls)
    return cls


def get_all_analyzers() -> List[BaseAnalyzer]:
    """Instantiate and return all registered analyzers."""
    return [cls() for cls in _ANALYZER_REGISTRY]
