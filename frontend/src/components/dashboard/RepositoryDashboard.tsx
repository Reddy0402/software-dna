/**
 * Repository Dashboard — displays available repositories with graph status.
 */
import { useGraphStore } from '../../store/graphStore';
import { useRepositories } from '../../hooks/useGraphHooks';
import { LoadingSpinner, ErrorBanner } from '../common/Common';
import { getEntityColor } from '../../utils/colors';

export default function RepositoryDashboard() {
  const {
    repositories,
    setSelectedRepoId,
    setViewMode,
    isLoading,
    error,
    setError,
  } = useGraphStore();
  useRepositories();

  const handleOpenRepo = (repoId: string) => {
    setSelectedRepoId(repoId);
    setViewMode('explorer');
  };

  if (isLoading && repositories.length === 0) {
    return (
      <div className="dashboard">
        <LoadingSpinner message="Loading repositories..." />
      </div>
    );
  }

  return (
    <div className="dashboard">
      <div className="dashboard__header">
        <div className="dashboard__title-group">
          <h1 className="dashboard__title">
            <span className="dashboard__logo">🧬</span>
            Software DNA Explorer
          </h1>
          <p className="dashboard__subtitle">
            Explore software architecture through interactive graph visualization
          </p>
        </div>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {repositories.length === 0 && !isLoading && (
        <div className="dashboard__empty">
          <div className="dashboard__empty-icon">📂</div>
          <h3>No repositories found</h3>
          <p>Import a repository to get started with graph visualization.</p>
        </div>
      )}

      <div className="dashboard__grid">
        {repositories.map((repo) => {
          const statusColor =
            repo.graph_status === 'completed'
              ? '#34d399'
              : repo.graph_status === 'syncing'
                ? '#fbbf24'
                : repo.graph_status === 'failed'
                  ? '#f87171'
                  : '#94a3b8';

          const nodeEntries = Object.entries(repo.nodes_by_label || {});

          return (
            <button
              key={repo.id}
              className="repo-card glass-panel"
              onClick={() => handleOpenRepo(repo.id)}
              disabled={repo.graph_status !== 'completed'}
            >
              <div className="repo-card__header">
                <h3 className="repo-card__name">{repo.name}</h3>
                <span
                  className="repo-card__status"
                  style={{ color: statusColor, borderColor: statusColor }}
                >
                  {repo.graph_status}
                </span>
              </div>

              <div className="repo-card__url">{repo.url}</div>

              {repo.owner && (
                <div className="repo-card__owner">by {repo.owner}</div>
              )}

              <div className="repo-card__stats">
                <div className="repo-card__stat">
                  <span className="repo-card__stat-value">{repo.total_nodes}</span>
                  <span className="repo-card__stat-label">Nodes</span>
                </div>
                <div className="repo-card__stat">
                  <span className="repo-card__stat-value">{repo.total_edges}</span>
                  <span className="repo-card__stat-label">Edges</span>
                </div>
                <div className="repo-card__stat">
                  <span className="repo-card__stat-value">{repo.total_files ?? 0}</span>
                  <span className="repo-card__stat-label">Files</span>
                </div>
              </div>

              {nodeEntries.length > 0 && (
                <div className="repo-card__types">
                  {nodeEntries.slice(0, 5).map(([type, count]) => {
                    const color = getEntityColor(type.toLowerCase()).primary;
                    return (
                      <span
                        key={type}
                        className="repo-card__type-chip"
                        style={{ color, borderColor: color }}
                      >
                        {type}: {count}
                      </span>
                    );
                  })}
                </div>
              )}

              {repo.graph_status === 'completed' && (
                <div className="repo-card__cta-row">
                  <span className="repo-card__cta">Open Explorer →</span>
                  <span
                    className="repo-card__cta repo-card__cta--analytics"
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedRepoId(repo.id);
                      setViewMode('analytics');
                    }}
                  >
                    📊 Analytics
                  </span>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
