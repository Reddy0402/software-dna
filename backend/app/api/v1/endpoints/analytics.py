"""
Analytics API Endpoints
========================
Comprehensive REST API for software intelligence data.
Mounted at /api/v1/analytics.
"""
import uuid
import math
import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.repository import Repository
from app.services.analytics_engine import AnalyticsEngine
from app.schemas.analytics import (
    HealthReport,
    ComplexityReport,
    ComplexityIssue,
    DependencyRiskReport,
    DependencyRisk,
    RiskEntity,
    HotspotReport,
    Hotspot,
    HotspotSubScores,
    ArchitectureSummary,
    FileCoupling,
    MetricDistribution,
    DistributionBucket,
    DNAScorecard,
    ScorecardHighlight,
)
from app.core.exceptions import AnalyticsError

logger = logging.getLogger("app.api.v1.endpoints.analytics")

router = APIRouter()


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _get_repository_or_404(db: Session, repository_id: uuid.UUID) -> Repository:
    repo = db.query(Repository).filter(Repository.id == repository_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return repo


def _paginate(items: list, page: int, page_size: int) -> tuple:
    """Apply pagination and return (page_items, total, total_pages)."""
    total = len(items)
    total_pages = max(1, math.ceil(total / page_size))
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total, total_pages


def _build_context(db: Session, repository_id: uuid.UUID):
    """Build analytics context, raising 500 on failure."""
    try:
        return AnalyticsEngine.build_context(db, repository_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to build analytics context: {e}")
        raise HTTPException(status_code=500, detail=f"Analytics engine error: {str(e)}")


# --------------------------------------------------------------------------
# Health Report
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/health",
    response_model=HealthReport,
    summary="Get repository health report",
    description="Returns comprehensive health metrics including composite score and sub-metrics.",
)
def get_health_report(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Compute and return the full health report."""
    _get_repository_or_404(db, repository_id)
    ctx = _build_context(db, repository_id)

    try:
        results = AnalyticsEngine.run_category(ctx, "health")
        aggregated = AnalyticsEngine.aggregate_results(results)
        health_data = aggregated.get("health", {})

        # Extract data from each rule
        score_data = health_data.get("health.overall_score", {}).get("data", {})
        struct_data = health_data.get("health.structural_counts", {}).get("data", {})
        density_data = health_data.get("health.graph_density", {}).get("data", {})
        inh_data = health_data.get("health.inheritance_depth", {}).get("data", {})
        size_data = health_data.get("health.size_metrics", {}).get("data", {})
        coupling_data = health_data.get("health.coupling_cohesion", {}).get("data", {})
        fan_data = health_data.get("health.fan_in_fan_out", {}).get("data", {})
        cycle_data = health_data.get("health.dependency_cycles", {}).get("data", {})

        return HealthReport(
            repository_id=str(repository_id),
            overall_score=score_data.get("overall_score", 0),
            grade=score_data.get("grade", "F"),
            sub_scores=score_data.get("sub_scores", {}),
            weights=score_data.get("weights", {}),
            structural_counts=struct_data,
            graph_density=density_data,
            inheritance=inh_data,
            size_metrics=size_data,
            coupling=coupling_data,
            fan_metrics=fan_data,
            cycle_info=cycle_data,
        )
    except Exception as e:
        logger.error(f"Health report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Complexity Report
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/complexity",
    response_model=ComplexityReport,
    summary="Get complexity issues",
    description="Returns ranked complexity issues with filtering and pagination.",
)
def get_complexity_report(
    repository_id: uuid.UUID,
    severity: Optional[str] = Query(default=None, description="Filter by severity: critical, warning"),
    entity_type: Optional[str] = Query(default=None, description="Filter by entity type"),
    issue_type: Optional[str] = Query(default=None, description="Filter by issue type"),
    sort_by: str = Query(default="metric_value", description="Sort field"),
    sort_order: str = Query(default="desc", regex="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Compute and return complexity analysis."""
    _get_repository_or_404(db, repository_id)
    ctx = _build_context(db, repository_id)

    try:
        results = AnalyticsEngine.run_category(ctx, "complexity")
        aggregated = AnalyticsEngine.aggregate_results(results)
        complexity_data = aggregated.get("complexity", {})

        # Collect all issues from all complexity rules
        all_issues: List[dict] = []
        by_category: dict = {}
        for rule_id, rule_result in complexity_data.items():
            data = rule_result.get("data", {})
            issues = data.get("issues", [])
            # For duplicate structures, flatten the grouped format
            if rule_id == "complexity.duplicate_structures":
                for group in issues:
                    for entity in group.get("entities", []):
                        all_issues.append({
                            "entity_id": entity.get("entity_id", ""),
                            "entity_name": entity.get("entity_name", ""),
                            "entity_type": entity.get("entity_type", ""),
                            "fqn": entity.get("fqn", ""),
                            "file_path": entity.get("file_path", ""),
                            "issue_type": "duplicate_structure",
                            "severity": group.get("severity", "warning"),
                            "metric_value": group.get("duplicate_count", 0),
                            "threshold": 2,
                            "description": group.get("description", ""),
                        })
            else:
                all_issues.extend(issues)

            category_name = rule_id.split(".")[-1]
            by_category[category_name] = data.get("total", 0)

        # Apply filters
        if severity:
            all_issues = [i for i in all_issues if i.get("severity") == severity]
        if entity_type:
            all_issues = [i for i in all_issues if i.get("entity_type") == entity_type]
        if issue_type:
            all_issues = [i for i in all_issues if i.get("issue_type") == issue_type]

        # Sort
        reverse = sort_order == "desc"
        all_issues.sort(key=lambda x: x.get(sort_by, 0), reverse=reverse)

        # Paginate
        page_items, total, total_pages = _paginate(all_issues, page, page_size)

        return ComplexityReport(
            repository_id=str(repository_id),
            issues=[ComplexityIssue(**i) for i in page_items],
            total=total,
            critical_count=sum(1 for i in all_issues if i.get("severity") == "critical"),
            warning_count=sum(1 for i in all_issues if i.get("severity") == "warning"),
            by_category=by_category,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Complexity report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Dependency Risk Report
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/risks",
    response_model=DependencyRiskReport,
    summary="Get dependency risk report",
    description="Returns dependency risks categorized by type and severity.",
)
def get_risk_report(
    repository_id: uuid.UUID,
    risk_type: Optional[str] = Query(default=None, description="Filter by risk type"),
    severity: Optional[str] = Query(default=None, description="Filter by severity"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Compute and return dependency risk analysis."""
    _get_repository_or_404(db, repository_id)
    ctx = _build_context(db, repository_id)

    try:
        results = AnalyticsEngine.run_category(ctx, "risk")
        aggregated = AnalyticsEngine.aggregate_results(results)
        risk_data = aggregated.get("risk", {})

        # Collect all risks
        all_risks: List[dict] = []
        by_type: dict = {}
        for rule_id, rule_result in risk_data.items():
            data = rule_result.get("data", {})
            risks = data.get("risks", [])
            all_risks.extend(risks)
            risk_category = rule_id.split(".")[-1]
            by_type[risk_category] = data.get("total", 0)

        # Apply filters
        if risk_type:
            all_risks = [r for r in all_risks if r.get("risk_type") == risk_type]
        if severity:
            all_risks = [r for r in all_risks if r.get("severity") == severity]

        # Sort by severity
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        all_risks.sort(key=lambda r: severity_order.get(r.get("severity", "info"), 3))

        # Paginate
        page_items, total, total_pages = _paginate(all_risks, page, page_size)

        # Convert to response models
        risk_models = []
        for r in page_items:
            entities = [RiskEntity(**e) for e in r.get("affected_entities", [])]
            risk_models.append(DependencyRisk(
                risk_type=r.get("risk_type", ""),
                severity=r.get("severity", "info"),
                affected_entities=entities,
                explanation=r.get("explanation", ""),
                remediation=r.get("remediation", ""),
            ))

        return DependencyRiskReport(
            repository_id=str(repository_id),
            risks=risk_models,
            total=total,
            critical_count=sum(1 for r in all_risks if r.get("severity") == "critical"),
            warning_count=sum(1 for r in all_risks if r.get("severity") == "warning"),
            info_count=sum(1 for r in all_risks if r.get("severity") == "info"),
            by_type=by_type,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Risk report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Hotspot Report
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/hotspots",
    response_model=HotspotReport,
    summary="Get hotspot analysis",
    description="Returns ranked code hotspots based on structural characteristics.",
)
def get_hotspot_report(
    repository_id: uuid.UUID,
    category: Optional[str] = Query(
        default=None,
        description="Hotspot category: centrality, coupling, complexity, connectivity, composite",
    ),
    top_n: int = Query(default=30, ge=1, le=100, description="Number of top hotspots"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Compute and return hotspot rankings."""
    _get_repository_or_404(db, repository_id)
    ctx = _build_context(db, repository_id)

    try:
        results = AnalyticsEngine.run_category(ctx, "hotspot")
        aggregated = AnalyticsEngine.aggregate_results(results)
        hotspot_data = aggregated.get("hotspot", {})

        # Use composite by default, or specific category
        target_rule = f"hotspot.{category}" if category else "hotspot.composite"
        rule_data = hotspot_data.get(target_rule, {}).get("data", {})

        if not rule_data and category:
            # Fall back to composite
            rule_data = hotspot_data.get("hotspot.composite", {}).get("data", {})

        raw_hotspots = rule_data.get("hotspots", [])[:top_n]

        # Build response
        hotspot_models = []
        for h in raw_hotspots:
            sub_scores_raw = h.get("sub_scores", {})
            hotspot_models.append(Hotspot(
                entity_id=h.get("entity_id", ""),
                entity_name=h.get("entity_name", ""),
                entity_type=h.get("entity_type", ""),
                fqn=h.get("fqn", ""),
                file_path=h.get("file_path", ""),
                composite_score=h.get("composite_score", h.get("centrality_score",
                    h.get("coupling_score", h.get("complexity_score",
                    h.get("connectivity_score", 0))))),
                sub_scores=HotspotSubScores(**sub_scores_raw) if isinstance(sub_scores_raw, dict) else HotspotSubScores(),
            ))

        # Paginate
        page_items, total, total_pages = _paginate(hotspot_models, page, page_size)

        return HotspotReport(
            repository_id=str(repository_id),
            hotspots=page_items,
            total_analyzed=rule_data.get("total_analyzed", 0),
            total_hotspots=rule_data.get("total_hotspots", 0),
            weights=rule_data.get("weights", {}),
            future_dimensions=rule_data.get("future_dimensions", []),
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
    except Exception as e:
        logger.error(f"Hotspot report failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Architecture Summary
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/architecture",
    response_model=ArchitectureSummary,
    summary="Get architecture summary",
    description="Returns architecture overview: type distributions, coupling analysis.",
)
def get_architecture_summary(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Compute architecture summary."""
    _get_repository_or_404(db, repository_id)
    ctx = _build_context(db, repository_id)

    try:
        # Entity type distribution
        entity_dist = {etype: len(elist) for etype, elist in ctx.entities_by_type.items()}

        # Relationship type distribution
        rel_dist = {rtype: len(rlist) for rtype, rlist in ctx.deps_by_type.items()}

        # Language distribution
        lang_dist: dict = {}
        for f in ctx.files:
            lang_dist[f.language] = lang_dist.get(f.language, 0) + 1

        # Run coupling rule for file-level metrics
        from app.services.analytics.health_rules import CouplingCohesionRule
        coupling_data = CouplingCohesionRule().compute(ctx)

        most_coupled = [
            FileCoupling(
                file_id=m["file_id"],
                file_path=m["file_path"],
                afferent_coupling=m["afferent_coupling"],
                efferent_coupling=m["efferent_coupling"],
                instability=m["instability"],
            )
            for m in coupling_data.get("most_coupled_files", [])
        ]

        return ArchitectureSummary(
            repository_id=str(repository_id),
            total_files=len(ctx.files),
            total_entities=len(ctx.entities),
            entity_type_distribution=entity_dist,
            relationship_type_distribution=rel_dist,
            language_distribution=lang_dist,
            most_coupled_files=most_coupled,
            avg_instability=coupling_data.get("avg_instability", 0),
            dependency_cycles=len(ctx.graph_cycles),
        )
    except Exception as e:
        logger.error(f"Architecture summary failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# Metric Distribution
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/distributions/{metric}",
    response_model=MetricDistribution,
    summary="Get metric distribution",
    description="Returns histogram data for a specific metric. Supported: line_count, fan_in, fan_out, total_degree, instability.",
)
def get_metric_distribution(
    repository_id: uuid.UUID,
    metric: str,
    buckets: int = Query(default=10, ge=3, le=50, description="Number of histogram buckets"),
    db: Session = Depends(get_db),
):
    """Compute and return metric distribution."""
    _get_repository_or_404(db, repository_id)
    ctx = _build_context(db, repository_id)

    supported_metrics = {"line_count", "fan_in", "fan_out", "total_degree", "instability"}
    if metric not in supported_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported metric: {metric}. Supported: {', '.join(sorted(supported_metrics))}",
        )

    try:
        values: List[float] = []

        if metric == "line_count":
            for e in ctx.entities:
                if e.start_line is not None and e.end_line is not None:
                    values.append(max(e.end_line - e.start_line + 1, 1))
        elif metric == "fan_in":
            for e in ctx.entities:
                values.append(len(ctx.deps_by_target.get(e.id, [])))
        elif metric == "fan_out":
            for e in ctx.entities:
                values.append(len(ctx.deps_by_source.get(e.id, [])))
        elif metric == "total_degree":
            for e in ctx.entities:
                fi = len(ctx.deps_by_target.get(e.id, []))
                fo = len(ctx.deps_by_source.get(e.id, []))
                values.append(fi + fo)
        elif metric == "instability":
            for file_id, file_entities in ctx.entities_by_file.items():
                eids = {e.id for e in file_entities}
                ca = sum(len(ctx.deps_by_target.get(eid, [])) for eid in eids)
                ce = sum(len(ctx.deps_by_source.get(eid, [])) for eid in eids)
                total = ca + ce
                values.append(ce / total if total > 0 else 0.0)

        if not values:
            return MetricDistribution(
                repository_id=str(repository_id),
                metric_name=metric,
                total_entities=0,
            )

        min_val = min(values)
        max_val = max(values)
        avg_val = sum(values) / len(values)
        sorted_vals = sorted(values)
        median_val = sorted_vals[len(sorted_vals) // 2]

        # Build histogram buckets
        bucket_width = (max_val - min_val) / buckets if max_val > min_val else 1.0
        histogram: List[DistributionBucket] = []
        for i in range(buckets):
            start = min_val + i * bucket_width
            end = start + bucket_width
            count = sum(1 for v in values if start <= v < end or (i == buckets - 1 and v == end))
            histogram.append(DistributionBucket(
                range_start=round(start, 2),
                range_end=round(end, 2),
                count=count,
            ))

        return MetricDistribution(
            repository_id=str(repository_id),
            metric_name=metric,
            buckets=histogram,
            total_entities=len(values),
            min_value=round(min_val, 2),
            max_value=round(max_val, 2),
            avg_value=round(avg_val, 2),
            median_value=round(median_val, 2),
        )
    except Exception as e:
        logger.error(f"Distribution calculation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --------------------------------------------------------------------------
# DNA Scorecard
# --------------------------------------------------------------------------

@router.get(
    "/repositories/{repository_id}/scorecard",
    response_model=DNAScorecard,
    summary="Get Software DNA scorecard",
    description="Returns a consolidated single-page scorecard summarizing all analytics.",
)
def get_dna_scorecard(
    repository_id: uuid.UUID,
    db: Session = Depends(get_db),
):
    """Produce the consolidated DNA scorecard."""
    repo = _get_repository_or_404(db, repository_id)
    ctx = _build_context(db, repository_id)

    try:
        # Run all analytics
        all_results = AnalyticsEngine.run_all(ctx)
        aggregated = AnalyticsEngine.aggregate_results(all_results)

        # Health
        health = aggregated.get("health", {})
        score_data = health.get("health.overall_score", {}).get("data", {})
        struct_data = health.get("health.structural_counts", {}).get("data", {})

        # Complexity
        complexity = aggregated.get("complexity", {})
        complexity_summary: dict = {}
        total_critical = 0
        total_warning = 0
        for rule_id, rule_result in complexity.items():
            data = rule_result.get("data", {})
            total_critical += data.get("critical_count", 0)
            total_warning += data.get("warning_count", 0)
        complexity_summary = {"critical": total_critical, "warning": total_warning}

        # Risk
        risk = aggregated.get("risk", {})
        risk_critical = 0
        risk_warning = 0
        risk_info = 0
        for rule_id, rule_result in risk.items():
            data = rule_result.get("data", {})
            risk_critical += data.get("critical_count", 0)
            risk_warning += data.get("warning_count", 0)
            risk_info += data.get("info_count", 0)
        risk_summary = {"critical": risk_critical, "warning": risk_warning, "info": risk_info}

        # Hotspots (top 5)
        hotspot = aggregated.get("hotspot", {})
        composite = hotspot.get("hotspot.composite", {}).get("data", {})
        top_hotspots_raw = composite.get("hotspots", [])[:5]
        top_hotspots = [
            Hotspot(
                entity_id=h.get("entity_id", ""),
                entity_name=h.get("entity_name", ""),
                entity_type=h.get("entity_type", ""),
                fqn=h.get("fqn", ""),
                file_path=h.get("file_path", ""),
                composite_score=h.get("composite_score", 0),
                sub_scores=HotspotSubScores(**h.get("sub_scores", {})),
            )
            for h in top_hotspots_raw
        ]

        # Build highlights
        highlights: List[ScorecardHighlight] = []

        overall_score = score_data.get("overall_score", 0)
        grade = score_data.get("grade", "F")

        highlights.append(ScorecardHighlight(
            category="health",
            title="Overall Health",
            value=f"{overall_score}/100 ({grade})",
            severity="success" if overall_score >= 80 else "warning" if overall_score >= 60 else "critical",
            description="Composite health score based on size, coupling, connectivity, cycles, and inheritance.",
        ))

        if total_critical > 0:
            highlights.append(ScorecardHighlight(
                category="complexity",
                title="Critical Complexity Issues",
                value=str(total_critical),
                severity="critical",
                description="Code entities exceeding critical thresholds for size or complexity.",
            ))

        if risk_critical > 0:
            highlights.append(ScorecardHighlight(
                category="risk",
                title="Critical Risks",
                value=str(risk_critical),
                severity="critical",
                description="Architectural risks requiring immediate attention.",
            ))

        cycle_data = health.get("health.dependency_cycles", {}).get("data", {})
        cycle_count = cycle_data.get("total_cycles", 0)
        if cycle_count > 0:
            highlights.append(ScorecardHighlight(
                category="risk",
                title="Dependency Cycles",
                value=str(cycle_count),
                severity="warning",
                description="Circular dependencies detected in the codebase.",
            ))

        density_data = health.get("health.graph_density", {}).get("data", {})
        connectivity = density_data.get("connectivity_ratio", 0)
        if connectivity < 0.5:
            highlights.append(ScorecardHighlight(
                category="health",
                title="Low Connectivity",
                value=f"{connectivity:.0%}",
                severity="warning",
                description="Many entities have no dependency connections.",
            ))

        return DNAScorecard(
            repository_id=str(repository_id),
            repository_name=repo.name,
            overall_score=overall_score,
            grade=grade,
            total_files=struct_data.get("total_files", len(ctx.files)),
            total_entities=struct_data.get("total_entities", len(ctx.entities)),
            total_dependencies=struct_data.get("total_dependencies", len(ctx.dependencies)),
            health_sub_scores=score_data.get("sub_scores", {}),
            complexity_summary=complexity_summary,
            risk_summary=risk_summary,
            top_hotspots=top_hotspots,
            highlights=highlights,
        )
    except Exception as e:
        logger.error(f"Scorecard generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
