/**
 * Statistics Panel — displays graph analytics and metrics.
 */
import { useGraphStore } from '../../store/graphStore';
import { StatCard } from '../common/Common';
import { getEntityColor, getRelationshipColor } from '../../utils/colors';

export default function StatisticsPanel() {
  const { isStatsPanelOpen, setStatsPanelOpen, statistics } = useGraphStore();

  if (!isStatsPanelOpen || !statistics) return null;

  const nodeEntries = Object.entries(statistics.nodes_by_type);
  const edgeEntries = Object.entries(statistics.edges_by_type);
  const langEntries = Object.entries(statistics.languages);

  return (
    <div className="stats-panel glass-panel">
      <div className="stats-panel__header">
        <h3>📊 Graph Statistics</h3>
        <button className="stats-panel__close" onClick={() => setStatsPanelOpen(false)}>
          ✕
        </button>
      </div>

      <div className="stats-panel__body">
        {/* Summary cards */}
        <div className="stats-panel__cards">
          <StatCard title="Total Nodes" value={statistics.total_nodes} color="#818cf8" />
          <StatCard title="Total Edges" value={statistics.total_edges} color="#34d399" />
          <StatCard title="Files" value={statistics.total_files} color="#fbbf24" />
          <StatCard title="Entities" value={statistics.total_entities} color="#f472b6" />
          <StatCard
            title="Graph Density"
            value={statistics.density.toFixed(4)}
            color="#60a5fa"
          />
          <StatCard
            title="Avg Degree"
            value={statistics.avg_degree.toFixed(1)}
            color="#a78bfa"
          />
        </div>

        {/* Node type distribution */}
        {nodeEntries.length > 0 && (
          <div className="stats-panel__section">
            <div className="stats-panel__label">Node Types</div>
            <div className="stats-panel__bars">
              {nodeEntries.map(([type, count]) => {
                const max = Math.max(...nodeEntries.map(([, c]) => c));
                const color = getEntityColor(type.toLowerCase()).primary;
                return (
                  <div key={type} className="stats-bar">
                    <div className="stats-bar__label">
                      <span style={{ color }}>{type}</span>
                      <span>{count}</span>
                    </div>
                    <div className="stats-bar__track">
                      <div
                        className="stats-bar__fill"
                        style={{
                          width: `${(count / max) * 100}%`,
                          background: color,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Edge type distribution */}
        {edgeEntries.length > 0 && (
          <div className="stats-panel__section">
            <div className="stats-panel__label">Relationship Types</div>
            <div className="stats-panel__bars">
              {edgeEntries.map(([type, count]) => {
                const max = Math.max(...edgeEntries.map(([, c]) => c));
                const color = getRelationshipColor(type);
                return (
                  <div key={type} className="stats-bar">
                    <div className="stats-bar__label">
                      <span style={{ color }}>{type}</span>
                      <span>{count}</span>
                    </div>
                    <div className="stats-bar__track">
                      <div
                        className="stats-bar__fill"
                        style={{
                          width: `${(count / max) * 100}%`,
                          background: color,
                        }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Language distribution */}
        {langEntries.length > 0 && (
          <div className="stats-panel__section">
            <div className="stats-panel__label">Languages</div>
            <div className="stats-panel__lang-chips">
              {langEntries.map(([lang, count]) => (
                <span key={lang} className="stats-lang-chip">
                  {lang}: {count}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Complexity */}
        <div className="stats-panel__section">
          <div className="stats-panel__label">Complexity</div>
          <div className="stats-panel__complexity">
            <div>Types Used: {statistics.complexity.types_used}</div>
            <div>Relationship Types: {statistics.complexity.relationship_types_used}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
