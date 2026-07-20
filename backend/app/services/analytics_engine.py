"""
Analytics Engine — Core Orchestrator
=====================================
Loads repository data into an AnalyticsContext, then runs registered
AnalyticsRule instances to produce metric results.

Architecture:
  AnalyticsContext   – read-only snapshot of repo data (SQL + Neo4j)
  AnalyticsRule      – abstract base; one per metric / check
  RuleResult         – output of a single rule execution
  AnalyticsEngine    – orchestrator: builds context, runs rules, aggregates
"""
import uuid
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.repository import Repository
from app.models.file import File
from app.models.code_entity import CodeEntity
from app.models.dependency import Dependency

logger = logging.getLogger("app.services.analytics_engine")


# ---------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------

@dataclass
class AnalyticsContext:
    """
    Read-only snapshot of all data needed to evaluate analytics rules.
    Built once per analysis run and shared across all rules.
    """
    repository_id: uuid.UUID
    repository_name: str = ""
    repository_url: str = ""

    # SQL data
    files: List[File] = field(default_factory=list)
    entities: List[CodeEntity] = field(default_factory=list)
    dependencies: List[Dependency] = field(default_factory=list)

    # Pre-computed indexes (built by AnalyticsEngine._build_indexes)
    entities_by_type: Dict[str, List[CodeEntity]] = field(default_factory=dict)
    entities_by_file: Dict[uuid.UUID, List[CodeEntity]] = field(default_factory=dict)
    files_by_id: Dict[uuid.UUID, File] = field(default_factory=dict)
    entities_by_id: Dict[uuid.UUID, CodeEntity] = field(default_factory=dict)

    # Dependency indexes
    deps_by_source: Dict[uuid.UUID, List[Dependency]] = field(default_factory=dict)
    deps_by_target: Dict[uuid.UUID, List[Dependency]] = field(default_factory=dict)
    deps_by_type: Dict[str, List[Dependency]] = field(default_factory=dict)

    # Neo4j graph summary (optional, loaded if available)
    neo4j_available: bool = False
    graph_node_count: int = 0
    graph_edge_count: int = 0
    graph_nodes_by_label: Dict[str, int] = field(default_factory=dict)
    graph_edges_by_type: Dict[str, int] = field(default_factory=dict)
    graph_cycles: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RuleResult:
    """Output produced by a single AnalyticsRule execution."""
    rule_id: str
    category: str
    success: bool = True
    error: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0


# ---------------------------------------------------------------
# Abstract base rule
# ---------------------------------------------------------------

class AnalyticsRule(ABC):
    """
    Base class for all analytics rules.

    Subclasses must define:
      - rule_id   (str): unique identifier, e.g. "health.structural_counts"
      - category  (str): grouping key, e.g. "health", "complexity", "risk", "hotspot"
      - compute() : performs the analysis and returns result data
    """
    rule_id: str = ""
    category: str = ""
    display_name: str = ""
    description: str = ""

    @abstractmethod
    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        """
        Execute the rule against the given context.
        Returns a dict of metric data.
        """
        ...


# ---------------------------------------------------------------
# Engine
# ---------------------------------------------------------------

class AnalyticsEngine:
    """
    Orchestrates analytics rule execution for a repository.
    """

    @staticmethod
    def build_context(db: Session, repository_id: uuid.UUID) -> AnalyticsContext:
        """
        Load all repository data from PostgreSQL and optionally Neo4j
        into an AnalyticsContext.
        """
        repo = db.query(Repository).filter(Repository.id == repository_id).first()
        if not repo:
            raise ValueError(f"Repository {repository_id} not found")

        files = db.query(File).filter(File.repository_id == repository_id).all()
        entities = db.query(CodeEntity).filter(CodeEntity.repository_id == repository_id).all()
        dependencies = db.query(Dependency).filter(Dependency.repository_id == repository_id).all()

        ctx = AnalyticsContext(
            repository_id=repository_id,
            repository_name=repo.name,
            repository_url=repo.url,
            files=files,
            entities=entities,
            dependencies=dependencies,
        )

        # Build indexes
        AnalyticsEngine._build_indexes(ctx)

        # Attempt Neo4j enrichment
        AnalyticsEngine._enrich_from_neo4j(ctx)

        logger.info(
            f"[{repository_id}] AnalyticsContext built: "
            f"{len(files)} files, {len(entities)} entities, "
            f"{len(dependencies)} dependencies"
        )
        return ctx

    @staticmethod
    def _build_indexes(ctx: AnalyticsContext) -> None:
        """Pre-compute lookup indexes for fast rule access."""
        for f in ctx.files:
            ctx.files_by_id[f.id] = f

        for e in ctx.entities:
            ctx.entities_by_id[e.id] = e
            ctx.entities_by_type.setdefault(e.entity_type, []).append(e)
            ctx.entities_by_file.setdefault(e.file_id, []).append(e)

        for d in ctx.dependencies:
            ctx.deps_by_source.setdefault(d.source_entity_id, []).append(d)
            if d.target_entity_id:
                ctx.deps_by_target.setdefault(d.target_entity_id, []).append(d)
            ctx.deps_by_type.setdefault(d.relationship_type, []).append(d)

    @staticmethod
    def _enrich_from_neo4j(ctx: AnalyticsContext) -> None:
        """Load graph summary and cycle data from Neo4j if available."""
        try:
            from app.services.graph_query import GraphQueryService

            summary = GraphQueryService.get_repository_graph_summary(ctx.repository_id)
            if summary and not summary.get("error"):
                ctx.neo4j_available = True
                ctx.graph_node_count = summary.get("total_nodes", 0)
                ctx.graph_edge_count = summary.get("total_edges", 0)
                ctx.graph_nodes_by_label = summary.get("nodes_by_label", {})
                ctx.graph_edges_by_type = summary.get("edges_by_type", {})

            # Detect cycles
            cycles = GraphQueryService.detect_circular_dependencies(ctx.repository_id)
            ctx.graph_cycles = cycles or []
        except Exception as e:
            logger.warning(f"Neo4j enrichment skipped: {e}")
            ctx.neo4j_available = False

    @staticmethod
    def run_all(ctx: AnalyticsContext) -> List[RuleResult]:
        """Execute all registered rules and return results."""
        from app.services.analytics import get_all_rule_classes
        return AnalyticsEngine._run_rules(get_all_rule_classes(), ctx)

    @staticmethod
    def run_category(ctx: AnalyticsContext, category: str) -> List[RuleResult]:
        """Execute only rules matching the given category."""
        from app.services.analytics import get_rule_classes_by_category
        return AnalyticsEngine._run_rules(get_rule_classes_by_category(category), ctx)

    @staticmethod
    def _run_rules(rule_classes: list, ctx: AnalyticsContext) -> List[RuleResult]:
        """Instantiate and execute rule classes, collecting results."""
        results: List[RuleResult] = []
        for rule_cls in rule_classes:
            rule = rule_cls()
            start = time.perf_counter()
            try:
                data = rule.compute(ctx)
                elapsed = (time.perf_counter() - start) * 1000
                results.append(RuleResult(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    success=True,
                    data=data,
                    duration_ms=round(elapsed, 2),
                ))
            except Exception as e:
                elapsed = (time.perf_counter() - start) * 1000
                logger.error(f"Rule {rule.rule_id} failed: {e}")
                results.append(RuleResult(
                    rule_id=rule.rule_id,
                    category=rule.category,
                    success=False,
                    error=str(e),
                    duration_ms=round(elapsed, 2),
                ))
        return results

    @staticmethod
    def aggregate_results(results: List[RuleResult]) -> Dict[str, Any]:
        """Group rule results by category into a single dict."""
        grouped: Dict[str, Dict[str, Any]] = {}
        for r in results:
            grouped.setdefault(r.category, {})[r.rule_id] = {
                "success": r.success,
                "data": r.data,
                "error": r.error,
                "duration_ms": r.duration_ms,
            }
        return grouped
