/**
 * TypeScript interfaces matching the backend Analytics API schemas.
 */

// ---- Health Report ----

export interface HealthReport {
  repository_id: string;
  overall_score: number;
  grade: string;
  sub_scores: Record<string, number>;
  weights: Record<string, number>;
  structural_counts: Record<string, unknown>;
  graph_density: Record<string, unknown>;
  inheritance: Record<string, unknown>;
  size_metrics: Record<string, unknown>;
  coupling: Record<string, unknown>;
  fan_metrics: Record<string, unknown>;
  cycle_info: Record<string, unknown>;
}

// ---- Complexity Report ----

export interface ComplexityIssue {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  fqn: string;
  file_path: string;
  issue_type: string;
  severity: 'critical' | 'warning' | 'info';
  metric_value: number;
  threshold: number;
  description: string;
}

export interface ComplexityReport {
  repository_id: string;
  issues: ComplexityIssue[];
  total: number;
  critical_count: number;
  warning_count: number;
  by_category: Record<string, number>;
  page: number;
  page_size: number;
  total_pages: number;
}

// ---- Dependency Risk Report ----

export interface RiskEntity {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  fqn: string;
  file_path: string;
  [key: string]: unknown;
}

export interface DependencyRisk {
  risk_type: string;
  severity: 'critical' | 'warning' | 'info';
  affected_entities: RiskEntity[];
  explanation: string;
  remediation: string;
}

export interface DependencyRiskReport {
  repository_id: string;
  risks: DependencyRisk[];
  total: number;
  critical_count: number;
  warning_count: number;
  info_count: number;
  by_type: Record<string, number>;
  page: number;
  page_size: number;
  total_pages: number;
}

// ---- Hotspot Report ----

export interface HotspotSubScores {
  centrality: number;
  coupling: number;
  complexity: number;
  connectivity: number;
}

export interface Hotspot {
  entity_id: string;
  entity_name: string;
  entity_type: string;
  fqn: string;
  file_path: string;
  composite_score: number;
  sub_scores: HotspotSubScores;
}

export interface HotspotReport {
  repository_id: string;
  hotspots: Hotspot[];
  total_analyzed: number;
  total_hotspots: number;
  weights: Record<string, number>;
  future_dimensions: string[];
  page: number;
  page_size: number;
  total_pages: number;
}

// ---- Architecture Summary ----

export interface FileCoupling {
  file_id: string;
  file_path: string;
  afferent_coupling: number;
  efferent_coupling: number;
  instability: number;
}

export interface ArchitectureSummary {
  repository_id: string;
  total_files: number;
  total_entities: number;
  entity_type_distribution: Record<string, number>;
  relationship_type_distribution: Record<string, number>;
  language_distribution: Record<string, number>;
  most_coupled_files: FileCoupling[];
  avg_instability: number;
  dependency_cycles: number;
}

// ---- Metric Distribution ----

export interface DistributionBucket {
  range_start: number;
  range_end: number;
  count: number;
}

export interface MetricDistribution {
  repository_id: string;
  metric_name: string;
  buckets: DistributionBucket[];
  total_entities: number;
  min_value: number;
  max_value: number;
  avg_value: number;
  median_value: number;
}

// ---- DNA Scorecard ----

export interface ScorecardHighlight {
  category: string;
  title: string;
  value: string;
  severity: 'info' | 'warning' | 'critical' | 'success';
  description: string;
}

export interface DNAScorecard {
  repository_id: string;
  repository_name: string;
  overall_score: number;
  grade: string;
  total_files: number;
  total_entities: number;
  total_dependencies: number;
  health_sub_scores: Record<string, number>;
  complexity_summary: Record<string, number>;
  risk_summary: Record<string, number>;
  top_hotspots: Hotspot[];
  highlights: ScorecardHighlight[];
}

// ---- Analytics Tab ----

export type AnalyticsTab = 'health' | 'complexity' | 'risks' | 'hotspots' | 'scorecard';
