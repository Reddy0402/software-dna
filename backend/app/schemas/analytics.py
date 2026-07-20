"""
Pydantic response schemas for the Analytics API.
These models define the contract between backend and frontend for all
software intelligence data.
"""
import uuid
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


# ---------------------------------------------------------------
# Health Report
# ---------------------------------------------------------------

class HealthSubScore(BaseModel):
    name: str
    score: float
    weight: float = 0.0

class HealthReport(BaseModel):
    """Full repository health report with composite score."""
    repository_id: str
    overall_score: float = 0.0
    grade: str = "F"
    sub_scores: Dict[str, float] = {}
    weights: Dict[str, float] = {}
    structural_counts: Dict[str, Any] = {}
    graph_density: Dict[str, Any] = {}
    inheritance: Dict[str, Any] = {}
    size_metrics: Dict[str, Any] = {}
    coupling: Dict[str, Any] = {}
    fan_metrics: Dict[str, Any] = {}
    cycle_info: Dict[str, Any] = {}


# ---------------------------------------------------------------
# Complexity Report
# ---------------------------------------------------------------

class ComplexityIssue(BaseModel):
    """A single complexity issue detected in the codebase."""
    entity_id: str
    entity_name: str
    entity_type: str
    fqn: str = ""
    file_path: str = ""
    issue_type: str
    severity: str  # critical, warning, info
    metric_value: float = 0.0
    threshold: float = 0.0
    description: str = ""

class ComplexityReport(BaseModel):
    """Ranked list of complexity issues with summary."""
    repository_id: str
    issues: List[ComplexityIssue] = []
    total: int = 0
    critical_count: int = 0
    warning_count: int = 0
    by_category: Dict[str, int] = {}
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# ---------------------------------------------------------------
# Dependency Risk Report
# ---------------------------------------------------------------

class RiskEntity(BaseModel):
    """Minimal entity reference in a risk record."""
    entity_id: str
    entity_name: str
    entity_type: str
    fqn: str = ""
    file_path: str = ""

    model_config = ConfigDict(extra="allow")

class DependencyRisk(BaseModel):
    """A single dependency risk issue."""
    risk_type: str
    severity: str  # critical, warning, info
    affected_entities: List[RiskEntity] = []
    explanation: str = ""
    remediation: str = ""

class DependencyRiskReport(BaseModel):
    """Categorized dependency risk report."""
    repository_id: str
    risks: List[DependencyRisk] = []
    total: int = 0
    critical_count: int = 0
    warning_count: int = 0
    info_count: int = 0
    by_type: Dict[str, int] = {}
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# ---------------------------------------------------------------
# Hotspot Report
# ---------------------------------------------------------------

class HotspotSubScores(BaseModel):
    """Individual dimension scores contributing to a hotspot."""
    centrality: float = 0.0
    coupling: float = 0.0
    complexity: float = 0.0
    connectivity: float = 0.0

    model_config = ConfigDict(extra="allow")

class Hotspot(BaseModel):
    """A single code hotspot."""
    entity_id: str
    entity_name: str
    entity_type: str
    fqn: str = ""
    file_path: str = ""
    composite_score: float = 0.0
    sub_scores: HotspotSubScores = HotspotSubScores()

class HotspotReport(BaseModel):
    """Ranked hotspot analysis report."""
    repository_id: str
    hotspots: List[Hotspot] = []
    total_analyzed: int = 0
    total_hotspots: int = 0
    weights: Dict[str, float] = {}
    future_dimensions: List[str] = []
    page: int = 1
    page_size: int = 50
    total_pages: int = 1


# ---------------------------------------------------------------
# Architecture Summary
# ---------------------------------------------------------------

class FileCoupling(BaseModel):
    """Coupling metrics for a single file."""
    file_id: str
    file_path: str
    afferent_coupling: int = 0
    efferent_coupling: int = 0
    instability: float = 0.0

class ArchitectureSummary(BaseModel):
    """Architecture overview: coupling matrix, type distribution."""
    repository_id: str
    total_files: int = 0
    total_entities: int = 0
    entity_type_distribution: Dict[str, int] = {}
    relationship_type_distribution: Dict[str, int] = {}
    language_distribution: Dict[str, int] = {}
    most_coupled_files: List[FileCoupling] = []
    avg_instability: float = 0.0
    dependency_cycles: int = 0


# ---------------------------------------------------------------
# Metric Distribution
# ---------------------------------------------------------------

class DistributionBucket(BaseModel):
    """Single bucket in a metric histogram."""
    range_start: float
    range_end: float
    count: int = 0

class MetricDistribution(BaseModel):
    """Histogram data for a metric across entities."""
    repository_id: str
    metric_name: str
    buckets: List[DistributionBucket] = []
    total_entities: int = 0
    min_value: float = 0.0
    max_value: float = 0.0
    avg_value: float = 0.0
    median_value: float = 0.0


# ---------------------------------------------------------------
# DNA Scorecard
# ---------------------------------------------------------------

class ScorecardHighlight(BaseModel):
    """A single highlight / insight on the scorecard."""
    category: str
    title: str
    value: str
    severity: str = "info"  # info, warning, critical, success
    description: str = ""

class DNAScorecard(BaseModel):
    """Consolidated Software DNA scorecard."""
    repository_id: str
    repository_name: str = ""
    overall_score: float = 0.0
    grade: str = "F"
    total_files: int = 0
    total_entities: int = 0
    total_dependencies: int = 0
    health_sub_scores: Dict[str, float] = {}
    complexity_summary: Dict[str, int] = {}
    risk_summary: Dict[str, int] = {}
    top_hotspots: List[Hotspot] = []
    highlights: List[ScorecardHighlight] = []
