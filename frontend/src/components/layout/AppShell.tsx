/**
 * AppShell — main layout composing the header, sidebar, canvas, and panels.
 */
import { ReactFlowProvider } from '@xyflow/react';
import { useGraphStore } from '../../store/graphStore';
import RepositoryDashboard from '../dashboard/RepositoryDashboard';
import GraphCanvas from '../graph/GraphCanvas';
import EntityDetailPanel from '../panels/EntityDetailPanel';
import FilterPanel from '../panels/FilterPanel';
import SearchPanel from '../panels/SearchPanel';
import StatisticsPanel from '../panels/StatisticsPanel';
import AnalyticsDashboard from '../analytics/AnalyticsDashboard';
import { ErrorBanner } from '../common/Common';
import { useGraphStatistics } from '../../hooks/useGraphHooks';

function ExplorerView() {
  const {
    setViewMode,
    setSelectedRepoId,
    clearGraph,
    setFilterPanelOpen,
    setStatsPanelOpen,
    isFilterPanelOpen,
    isStatsPanelOpen,
    error,
    setError,
    repositories,
    selectedRepoId,
  } = useGraphStore();
  useGraphStatistics();

  const selectedRepo = repositories.find((r) => r.id === selectedRepoId);

  const handleBack = () => {
    clearGraph();
    setSelectedRepoId(null);
    setViewMode('dashboard');
  };

  return (
    <div className="explorer">
      {/* Top bar */}
      <header className="explorer__header glass-panel">
        <div className="explorer__header-left">
          <button className="explorer__back-btn" onClick={handleBack}>
            ← Back
          </button>
          <div className="explorer__repo-info">
            <span className="explorer__repo-name">
              🧬 {selectedRepo?.name || 'Repository'}
            </span>
          </div>
        </div>

        <div className="explorer__header-center">
          <SearchPanel />
        </div>

        <div className="explorer__header-right">
          <button
            className="toolbar-btn"
            onClick={() => setViewMode('analytics')}
            title="Analytics Dashboard"
          >
            📊 Analytics
          </button>
          <button
            className={`toolbar-btn ${isFilterPanelOpen ? 'toolbar-btn--active' : ''}`}
            onClick={() => setFilterPanelOpen(!isFilterPanelOpen)}
            title="Filters"
          >
            ⚙ Filters
          </button>
          <button
            className={`toolbar-btn ${isStatsPanelOpen ? 'toolbar-btn--active' : ''}`}
            onClick={() => setStatsPanelOpen(!isStatsPanelOpen)}
            title="Statistics"
          >
            📊 Stats
          </button>
        </div>
      </header>

      {error && (
        <div className="explorer__error">
          <ErrorBanner message={error} onDismiss={() => setError(null)} />
        </div>
      )}

      {/* Main content area */}
      <div className="explorer__body">
        <div className="explorer__canvas">
          <GraphCanvas />
        </div>

        {/* Right-side panels */}
        <EntityDetailPanel />
        <FilterPanel />
        <StatisticsPanel />
      </div>
    </div>
  );
}

export default function AppShell() {
  const { viewMode } = useGraphStore();

  return (
    <div className="app-shell">
      {viewMode === 'dashboard' ? (
        <RepositoryDashboard />
      ) : viewMode === 'analytics' ? (
        <AnalyticsDashboard />
      ) : (
        <ReactFlowProvider>
          <ExplorerView />
        </ReactFlowProvider>
      )}
    </div>
  );
}

