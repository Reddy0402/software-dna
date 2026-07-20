/**
 * RiskCards — Severity-colored cards for dependency risks.
 * Expandable details showing affected entities with graph navigation links.
 */
import { useState } from 'react';
import type { DependencyRiskReport, DependencyRisk } from '../../types/analytics';
import { useGraphStore } from '../../store/graphStore';

interface RiskCardsProps {
  report: DependencyRiskReport;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f87171',
  warning: '#fbbf24',
  info: '#60a5fa',
};

const SEVERITY_BG: Record<string, string> = {
  critical: 'rgba(248, 113, 113, 0.08)',
  warning: 'rgba(251, 191, 36, 0.08)',
  info: 'rgba(96, 165, 250, 0.08)',
};

const RISK_ICONS: Record<string, string> = {
  circular_dependency: '🔄',
  unstable_module: '⚠️',
  high_coupling: '🕸️',
  bottleneck: '🚧',
  dependency_hub: '🎯',
  isolated_module: '🏝️',
  orphaned_file: '📂',
};

function RiskCard({ risk }: { risk: DependencyRisk }) {
  const [expanded, setExpanded] = useState(false);
  const { setViewMode, setHighlightedNodeIds, setSelectedNodeId } = useGraphStore();

  const color = SEVERITY_COLORS[risk.severity] || '#94a3b8';
  const bg = SEVERITY_BG[risk.severity] || 'transparent';
  const icon = RISK_ICONS[risk.risk_type] || '⚡';

  const handleNavigate = (entityId: string) => {
    const ids = risk.affected_entities.map((e) => e.entity_id);
    setHighlightedNodeIds(new Set(ids));
    setSelectedNodeId(entityId);
    setViewMode('explorer');
  };

  return (
    <div
      className="risk-card"
      style={{ borderLeftColor: color, backgroundColor: bg }}
    >
      <div className="risk-card__header" onClick={() => setExpanded(!expanded)}>
        <div className="risk-card__title-row">
          <span className="risk-card__icon">{icon}</span>
          <span className="risk-card__type">
            {risk.risk_type.replace(/_/g, ' ')}
          </span>
          <span
            className="severity-badge"
            style={{ color, borderColor: color }}
          >
            {risk.severity}
          </span>
        </div>
        <div className="risk-card__explanation">{risk.explanation}</div>
        <button className="risk-card__expand-btn">
          {expanded ? '▲ Less' : '▼ Details'}
        </button>
      </div>

      {expanded && (
        <div className="risk-card__details">
          <div className="risk-card__remediation">
            <strong>💡 Remediation:</strong> {risk.remediation}
          </div>
          {risk.affected_entities.length > 0 && (
            <div className="risk-card__entities">
              <strong>Affected entities:</strong>
              <ul className="risk-card__entity-list">
                {risk.affected_entities.map((e, i) => (
                  <li key={`${e.entity_id}-${i}`}>
                    <span className="entity-type-chip">{e.entity_type}</span>
                    <span className="risk-card__entity-name">{e.entity_name}</span>
                    {e.fqn && (
                      <span className="risk-card__entity-fqn">{e.fqn}</span>
                    )}
                    <button
                      className="analytics-nav-btn"
                      onClick={() => handleNavigate(e.entity_id)}
                      title="View in Graph Explorer"
                    >
                      🔍
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RiskCards({ report }: RiskCardsProps) {
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  let filtered = report.risks;
  if (filterSeverity !== 'all') {
    filtered = filtered.filter((r) => r.severity === filterSeverity);
  }

  return (
    <div className="risk-cards">
      <div className="risk-cards__header">
        <h3 className="risk-cards__title">
          Dependency Risks
          <span className="risk-cards__count">({report.total})</span>
        </h3>
        <div className="risk-cards__badges">
          <span className="severity-badge severity-badge--critical">
            {report.critical_count} critical
          </span>
          <span className="severity-badge severity-badge--warning">
            {report.warning_count} warning
          </span>
          <span className="severity-badge severity-badge--info">
            {report.info_count} info
          </span>
        </div>
      </div>

      <div className="risk-cards__filters">
        <select
          className="analytics-select"
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
        </select>
      </div>

      <div className="risk-cards__list">
        {filtered.map((risk, idx) => (
          <RiskCard key={`${risk.risk_type}-${idx}`} risk={risk} />
        ))}
        {filtered.length === 0 && (
          <div className="risk-cards__empty">
            No dependency risks detected — clean architecture! ✨
          </div>
        )}
      </div>
    </div>
  );
}
