/**
 * Zustand store for analytics dashboard state management.
 */
import { create } from 'zustand';
import type {
  HealthReport,
  ComplexityReport,
  DependencyRiskReport,
  HotspotReport,
  DNAScorecard,
  AnalyticsTab,
} from '../types/analytics';

interface AnalyticsState {
  // Active tab
  activeTab: AnalyticsTab;
  setActiveTab: (tab: AnalyticsTab) => void;

  // Health report
  healthReport: HealthReport | null;
  setHealthReport: (report: HealthReport | null) => void;

  // Complexity report
  complexityReport: ComplexityReport | null;
  setComplexityReport: (report: ComplexityReport | null) => void;

  // Risk report
  riskReport: DependencyRiskReport | null;
  setRiskReport: (report: DependencyRiskReport | null) => void;

  // Hotspot report
  hotspotReport: HotspotReport | null;
  setHotspotReport: (report: HotspotReport | null) => void;

  // Scorecard
  scorecard: DNAScorecard | null;
  setScorecard: (scorecard: DNAScorecard | null) => void;

  // Loading
  isLoading: boolean;
  setLoading: (loading: boolean) => void;
  error: string | null;
  setError: (error: string | null) => void;

  // Clear all
  clearAnalytics: () => void;
}

export const useAnalyticsStore = create<AnalyticsState>((set) => ({
  activeTab: 'scorecard',
  setActiveTab: (tab) => set({ activeTab: tab }),

  healthReport: null,
  setHealthReport: (report) => set({ healthReport: report }),

  complexityReport: null,
  setComplexityReport: (report) => set({ complexityReport: report }),

  riskReport: null,
  setRiskReport: (report) => set({ riskReport: report }),

  hotspotReport: null,
  setHotspotReport: (report) => set({ hotspotReport: report }),

  scorecard: null,
  setScorecard: (scorecard) => set({ scorecard }),

  isLoading: false,
  setLoading: (loading) => set({ isLoading: loading }),
  error: null,
  setError: (error) => set({ error }),

  clearAnalytics: () =>
    set({
      healthReport: null,
      complexityReport: null,
      riskReport: null,
      hotspotReport: null,
      scorecard: null,
      error: null,
    }),
}));
