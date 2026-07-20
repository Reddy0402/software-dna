/**
 * AnalyticsDashboard — Main analytics view with tabbed navigation.
 */
import { useAnalyticsStore } from '../../store/analyticsStore';
import { useGraphStore } from '../../store/graphStore';
import {
  useScorecard,
  useHealthReport,
  useComplexityReport,
  useRiskReport,
  useHotspotReport,
} from '../../hooks/useAnalyticsHooks';
import type { AnalyticsTab } from '../../types/analytics';
import HealthScoreCard from './HealthScoreCard';
import ComplexityTable from './ComplexityTable';
import RiskCards from './RiskCards';
import HotspotTable from './HotspotTable';
import MiniChart from './MiniChart';
import { LoadingSpinner, ErrorBanner } from '../common/Common';

const TABS: { key: AnalyticsTab; label: string; icon: string }[] = [
  { key: 'scorecard', label: 'Scorecard', icon: '🧬' },
  { key: 'health', label: 'Health', icon: '💚' },
  { key: 'complexity', label: 'Complexity', icon: '📊' },
  { key: 'risks', label: 'Risks', icon: '⚠️' },
  { key: 'hotspots', label: 'Hotspots', icon: '🔥' },
];

function ScorecardView() {
  const scorecard = useAnalyticsStore((s) => s.scorecard);
  useScorecard();

  if (!scorecard) return <LoadingSpinner message="Loading scorecard..." />;

  const subScoreEntries = Object.entries(scorecard.health_sub_scores);

  return (
    <div className="scorecard-view">
      {/* Top summary */}
      <div className="scorecard-view__hero glass-panel">
        <div className="scorecard-view__score-ring">
          <div
            className="scorecard-view__score-number"
            style={{
              color: scorecard.overall_score >= 80 ? '#34d399' :
                     scorecard.overall_score >= 60 ? '#fbbf24' : '#f87171',
            }}
          >
            {Math.round(scorecard.overall_score)}
          </div>
          <div className="scorecard-view__grade">Grade {scorecard.grade}</div>
        </div>
        <div className="scorecard-view__meta">
          <h2 className="scorecard-view__repo-name">🧬 {scorecard.repository_name}</h2>
          <div className="scorecard-view__stats-row">
            <div className="scorecard-view__stat">
              <span className="scorecard-view__stat-val">{scorecard.total_files}</span>
              <span className="scorecard-view__stat-lbl">Files</span>
            </div>
            <div className="scorecard-view__stat">
              <span className="scorecard-view__stat-val">{scorecard.total_entities}</span>
              <span className="scorecard-view__stat-lbl">Entities</span>
            </div>
            <div className="scorecard-view__stat">
              <span className="scorecard-view__stat-val">{scorecard.total_dependencies}</span>
              <span className="scorecard-view__stat-lbl">Dependencies</span>
            </div>
          </div>
        </div>
      </div>

      {/* Highlights */}
      {scorecard.highlights.length > 0 && (
        <div className="scorecard-view__highlights">
          {scorecard.highlights.map((h, i) => {
            const color =
              h.severity === 'critical' ? '#f87171' :
              h.severity === 'warning' ? '#fbbf24' :
              h.severity === 'success' ? '#34d399' : '#60a5fa';
            return (
              <div
                key={i}
                className="highlight-card glass-panel"
                style={{ borderLeftColor: color }}
              >
                <div className="highlight-card__value" style={{ color }}>{h.value}</div>
                <div className="highlight-card__title">{h.title}</div>
                <div className="highlight-card__desc">{h.description}</div>
              </div>
            );
          })}
        </div>
      )}

      {/* Charts row */}
      <div className="scorecard-view__charts">
        {subScoreEntries.length > 0 && (
          <div className="glass-panel scorecard-view__chart-card">
            <MiniChart
              type="bar"
              title="Health Sub-Scores"
              data={subScoreEntries.map(([k, v]) => ({
                label: k.replace(/_/g, ' ').slice(0, 8),
                value: Math.round(v),
              }))}
              width={300}
              height={180}
            />
          </div>
        )}

        <div className="glass-panel scorecard-view__chart-card">
          <MiniChart
            type="doughnut"
            title="Issue Summary"
            data={[
              { label: 'Critical', value: (scorecard.complexity_summary.critical ?? 0) + (scorecard.risk_summary.critical ?? 0), color: '#f87171' },
              { label: 'Warning', value: (scorecard.complexity_summary.warning ?? 0) + (scorecard.risk_summary.warning ?? 0), color: '#fbbf24' },
              { label: 'Info', value: scorecard.risk_summary.info ?? 0, color: '#60a5fa' },
            ].filter((d) => d.value > 0)}
            width={180}
            height={180}
          />
        </div>

        {scorecard.top_hotspots.length > 0 && (
          <div className="glass-panel scorecard-view__chart-card">
            <MiniChart
              type="horizontal-bar"
              title="Top Hotspots"
              data={scorecard.top_hotspots.slice(0, 5).map((h) => ({
                label: h.entity_name,
                value: Math.round(h.composite_score * 100),
              }))}
              width={300}
              height={180}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function HealthView() {
  const report = useAnalyticsStore((s) => s.healthReport);
  useHealthReport();

  if (!report) return <LoadingSpinner message="Computing health metrics..." />;
  return <HealthScoreCard report={report} />;
}

function ComplexityView() {
  const report = useAnalyticsStore((s) => s.complexityReport);
  useComplexityReport();

  if (!report) return <LoadingSpinner message="Analyzing complexity..." />;
  return <ComplexityTable report={report} />;
}

function RisksView() {
  const report = useAnalyticsStore((s) => s.riskReport);
  useRiskReport();

  if (!report) return <LoadingSpinner message="Detecting risks..." />;
  return <RiskCards report={report} />;
}

function HotspotsView() {
  const report = useAnalyticsStore((s) => s.hotspotReport);
  useHotspotReport();

  if (!report) return <LoadingSpinner message="Identifying hotspots..." />;
  return <HotspotTable report={report} />;
}

export default function AnalyticsDashboard() {
  const { activeTab, setActiveTab, isLoading, error, setError } = useAnalyticsStore();
  const { setViewMode, selectedRepoId, repositories, setSelectedRepoId, clearGraph } =
    useGraphStore();
  const { clearAnalytics } = useAnalyticsStore();

  const selectedRepo = repositories.find((r) => r.id === selectedRepoId);

  const handleBack = () => {
    clearAnalytics();
    clearGraph();
    setSelectedRepoId(null);
    setViewMode('dashboard');
  };

  const handleSwitchToExplorer = () => {
    setViewMode('explorer');
  };

  return (
    <div className="analytics-dashboard">
      {/* Header */}
      <header className="analytics-dashboard__header glass-panel">
        <div className="analytics-dashboard__header-left">
          <button className="explorer__back-btn" onClick={handleBack}>
            ← Back
          </button>
          <div className="analytics-dashboard__repo-info">
            <span className="analytics-dashboard__repo-name">
              📊 {selectedRepo?.name || 'Repository'} — Analytics
            </span>
          </div>
        </div>
        <div className="analytics-dashboard__header-right">
          <button className="toolbar-btn" onClick={handleSwitchToExplorer}>
            🧬 Graph Explorer
          </button>
        </div>
      </header>

      {error && (
        <div className="analytics-dashboard__error">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {/* Tab bar */}
      <nav className="analytics-tabs">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            className={`analytics-tab ${activeTab === tab.key ? 'analytics-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            <span className="analytics-tab__icon">{tab.icon}</span>
            <span className="analytics-tab__label">{tab.label}</span>
          </button>
        ))}
      </nav>

      {/* Tab content */}
      <div className="analytics-dashboard__content">
        {isLoading && <div className="analytics-dashboard__loading-overlay" />}
        {activeTab === 'scorecard' && <ScorecardView />}
        {activeTab === 'health' && <HealthView />}
        {activeTab === 'complexity' && <ComplexityView />}
        {activeTab === 'risks' && <RisksView />}
        {activeTab === 'hotspots' && <HotspotsView />}
      </div>
    </div>
  );
}
