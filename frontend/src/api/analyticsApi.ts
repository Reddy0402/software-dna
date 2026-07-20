/**
 * API client for the Analytics backend.
 * All calls target /api/v1/analytics/* endpoints.
 */
import axios from 'axios';
import type {
  HealthReport,
  ComplexityReport,
  DependencyRiskReport,
  HotspotReport,
  ArchitectureSummary,
  MetricDistribution,
  DNAScorecard,
} from '../types/analytics';

const api = axios.create({
  baseURL: '/api/v1/analytics',
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
});

// ---- Health ----

export async function fetchHealthReport(repoId: string): Promise<HealthReport> {
  const { data } = await api.get<HealthReport>(`/repositories/${repoId}/health`);
  return data;
}

// ---- Complexity ----

export async function fetchComplexityReport(
  repoId: string,
  params?: {
    severity?: string;
    entity_type?: string;
    issue_type?: string;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    page?: number;
    page_size?: number;
  },
): Promise<ComplexityReport> {
  const { data } = await api.get<ComplexityReport>(
    `/repositories/${repoId}/complexity`,
    { params },
  );
  return data;
}

// ---- Risk ----

export async function fetchRiskReport(
  repoId: string,
  params?: {
    risk_type?: string;
    severity?: string;
    page?: number;
    page_size?: number;
  },
): Promise<DependencyRiskReport> {
  const { data } = await api.get<DependencyRiskReport>(
    `/repositories/${repoId}/risks`,
    { params },
  );
  return data;
}

// ---- Hotspots ----

export async function fetchHotspotReport(
  repoId: string,
  params?: {
    category?: string;
    top_n?: number;
    page?: number;
    page_size?: number;
  },
): Promise<HotspotReport> {
  const { data } = await api.get<HotspotReport>(
    `/repositories/${repoId}/hotspots`,
    { params },
  );
  return data;
}

// ---- Architecture ----

export async function fetchArchitectureSummary(
  repoId: string,
): Promise<ArchitectureSummary> {
  const { data } = await api.get<ArchitectureSummary>(
    `/repositories/${repoId}/architecture`,
  );
  return data;
}

// ---- Distribution ----

export async function fetchMetricDistribution(
  repoId: string,
  metric: string,
  buckets?: number,
): Promise<MetricDistribution> {
  const { data } = await api.get<MetricDistribution>(
    `/repositories/${repoId}/distributions/${metric}`,
    { params: { buckets } },
  );
  return data;
}

// ---- Scorecard ----

export async function fetchDNAScorecard(repoId: string): Promise<DNAScorecard> {
  const { data } = await api.get<DNAScorecard>(
    `/repositories/${repoId}/scorecard`,
  );
  return data;
}
