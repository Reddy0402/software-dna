/**
 * HotspotTable — Ranked hotspot table with heat-gradient row coloring.
 * Score breakdown columns. Click-to-navigate to graph explorer.
 */
import type { HotspotReport, Hotspot } from '../../types/analytics';
import { useGraphStore } from '../../store/graphStore';

interface HotspotTableProps {
  report: HotspotReport;
}

function heatColor(score: number): string {
  // From cool blue (low) → amber → red (high)
  if (score >= 0.8) return 'rgba(248, 113, 113, 0.15)';
  if (score >= 0.6) return 'rgba(251, 191, 36, 0.12)';
  if (score >= 0.4) return 'rgba(251, 191, 36, 0.08)';
  if (score >= 0.2) return 'rgba(96, 165, 250, 0.08)';
  return 'transparent';
}

function scoreBar(score: number, color: string) {
  return (
    <div className="hotspot-score-bar">
      <div
        className="hotspot-score-bar__fill"
        style={{ width: `${Math.min(score * 100, 100)}%`, backgroundColor: color }}
      />
      <span className="hotspot-score-bar__label">{(score * 100).toFixed(0)}</span>
    </div>
  );
}

export default function HotspotTable({ report }: HotspotTableProps) {
  const { setViewMode, setHighlightedNodeIds, setSelectedNodeId } = useGraphStore();

  const handleNavigate = (hotspot: Hotspot) => {
    setHighlightedNodeIds(new Set([hotspot.entity_id]));
    setSelectedNodeId(hotspot.entity_id);
    setViewMode('explorer');
  };

  return (
    <div className="hotspot-table">
      <div className="hotspot-table__header">
        <h3 className="hotspot-table__title">
          Code Hotspots
          <span className="hotspot-table__count">({report.total_hotspots})</span>
        </h3>
        <span className="hotspot-table__analyzed">
          {report.total_analyzed} entities analyzed
        </span>
      </div>

      <div className="hotspot-table__scroll">
        <table className="analytics-table analytics-table--hotspot">
          <thead>
            <tr>
              <th>#</th>
              <th>Entity</th>
              <th>Type</th>
              <th>Composite</th>
              <th>Centrality</th>
              <th>Coupling</th>
              <th>Complexity</th>
              <th>Connectivity</th>
              <th>File</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {report.hotspots.map((h, idx) => (
              <tr
                key={h.entity_id}
                className="analytics-table__row"
                style={{ backgroundColor: heatColor(h.composite_score) }}
              >
                <td className="hotspot-rank">{idx + 1}</td>
                <td className="analytics-table__name" title={h.fqn}>
                  {h.entity_name}
                </td>
                <td>
                  <span className="entity-type-chip">{h.entity_type}</span>
                </td>
                <td>{scoreBar(h.composite_score, '#a78bfa')}</td>
                <td>{scoreBar(h.sub_scores.centrality, '#818cf8')}</td>
                <td>{scoreBar(h.sub_scores.coupling, '#f472b6')}</td>
                <td>{scoreBar(h.sub_scores.complexity, '#fbbf24')}</td>
                <td>{scoreBar(h.sub_scores.connectivity, '#34d399')}</td>
                <td className="analytics-table__path" title={h.file_path}>
                  {h.file_path.split('/').pop() || h.file_path}
                </td>
                <td>
                  <button
                    className="analytics-nav-btn"
                    onClick={() => handleNavigate(h)}
                    title="View in Graph Explorer"
                  >
                    🔍
                  </button>
                </td>
              </tr>
            ))}
            {report.hotspots.length === 0 && (
              <tr>
                <td colSpan={10} className="analytics-table__empty">
                  No significant hotspots detected 🌿
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {report.future_dimensions.length > 0 && (
        <div className="hotspot-table__future">
          <span>📌 Future dimensions: </span>
          {report.future_dimensions.join(', ')}
        </div>
      )}
    </div>
  );
}
