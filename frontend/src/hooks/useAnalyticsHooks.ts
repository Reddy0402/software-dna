/**
 * React hooks for fetching analytics data.
 */
import { useEffect } from 'react';
import { useGraphStore } from '../store/graphStore';
import { useAnalyticsStore } from '../store/analyticsStore';
import {
  fetchHealthReport,
  fetchComplexityReport,
  fetchRiskReport,
  fetchHotspotReport,
  fetchDNAScorecard,
} from '../api/analyticsApi';

/**
 * Fetch the DNA scorecard when a repo is selected.
 */
export function useScorecard() {
  const repoId = useGraphStore((s) => s.selectedRepoId);
  const { setScorecard, setLoading, setError } = useAnalyticsStore();

  useEffect(() => {
    if (!repoId) return;
    let cancelled = false;
    setLoading(true);
    fetchDNAScorecard(repoId)
      .then((data) => {
        if (!cancelled) setScorecard(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [repoId, setScorecard, setLoading, setError]);
}

/**
 * Fetch health report when health tab is active.
 */
export function useHealthReport() {
  const repoId = useGraphStore((s) => s.selectedRepoId);
  const activeTab = useAnalyticsStore((s) => s.activeTab);
  const { setHealthReport, setLoading, setError } = useAnalyticsStore();

  useEffect(() => {
    if (!repoId || activeTab !== 'health') return;
    let cancelled = false;
    setLoading(true);
    fetchHealthReport(repoId)
      .then((data) => {
        if (!cancelled) setHealthReport(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [repoId, activeTab, setHealthReport, setLoading, setError]);
}

/**
 * Fetch complexity report when complexity tab is active.
 */
export function useComplexityReport() {
  const repoId = useGraphStore((s) => s.selectedRepoId);
  const activeTab = useAnalyticsStore((s) => s.activeTab);
  const { setComplexityReport, setLoading, setError } = useAnalyticsStore();

  useEffect(() => {
    if (!repoId || activeTab !== 'complexity') return;
    let cancelled = false;
    setLoading(true);
    fetchComplexityReport(repoId)
      .then((data) => {
        if (!cancelled) setComplexityReport(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [repoId, activeTab, setComplexityReport, setLoading, setError]);
}

/**
 * Fetch risk report when risks tab is active.
 */
export function useRiskReport() {
  const repoId = useGraphStore((s) => s.selectedRepoId);
  const activeTab = useAnalyticsStore((s) => s.activeTab);
  const { setRiskReport, setLoading, setError } = useAnalyticsStore();

  useEffect(() => {
    if (!repoId || activeTab !== 'risks') return;
    let cancelled = false;
    setLoading(true);
    fetchRiskReport(repoId)
      .then((data) => {
        if (!cancelled) setRiskReport(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [repoId, activeTab, setRiskReport, setLoading, setError]);
}

/**
 * Fetch hotspot report when hotspots tab is active.
 */
export function useHotspotReport() {
  const repoId = useGraphStore((s) => s.selectedRepoId);
  const activeTab = useAnalyticsStore((s) => s.activeTab);
  const { setHotspotReport, setLoading, setError } = useAnalyticsStore();

  useEffect(() => {
    if (!repoId || activeTab !== 'hotspots') return;
    let cancelled = false;
    setLoading(true);
    fetchHotspotReport(repoId)
      .then((data) => {
        if (!cancelled) setHotspotReport(data);
      })
      .catch((e) => {
        if (!cancelled) setError(e?.response?.data?.detail || e.message);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [repoId, activeTab, setHotspotReport, setLoading, setError]);
}
