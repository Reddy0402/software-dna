/**
 * ComplexityTable — Sortable, filterable table of complexity issues.
 * Supports click-to-navigate to graph explorer.
 */
import { useState } from 'react';
import type { ComplexityReport, ComplexityIssue } from '../../types/analytics';
import { useGraphStore } from '../../store/graphStore';

interface ComplexityTableProps {
  report: ComplexityReport;
}

const SEVERITY_COLORS: Record<string, string> = {
  critical: '#f87171',
  warning: '#fbbf24',
  info: '#60a5fa',
};

const ISSUE_LABELS: Record<string, string> = {
  large_file: '📄 Large File',
  oversized_class: '🏗️ Oversized Class',
  long_method: '📏 Long Method',
  high_parameters: '🔢 High Params',
  dependency_concentration: '🕸️ Dep. Concentration',
  duplicate_structure: '♻️ Duplicate Structure',
};

export default function ComplexityTable({ report }: ComplexityTableProps) {
  const { setSelectedRepoId, setViewMode, setHighlightedNodeIds, setSelectedNodeId } = useGraphStore();
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterType, setFilterType] = useState<string>('all');
  const [sortField, setSortField] = useState<'metric_value' | 'severity'>('metric_value');
  const [sortAsc, setSortAsc] = useState(false);

  let filtered = report.issues;

  if (filterSeverity !== 'all') {
    filtered = filtered.filter((i) => i.severity === filterSeverity);
  }
  if (filterType !== 'all') {
    filtered = filtered.filter((i) => i.issue_type === filterType);
  }

  const sorted = [...filtered].sort((a, b) => {
    if (sortField === 'severity') {
      const order: Record<string, number> = { critical: 0, warning: 1, info: 2 };
      const diff = (order[a.severity] ?? 3) - (order[b.severity] ?? 3);
      return sortAsc ? diff : -diff;
    }
    return sortAsc
      ? a.metric_value - b.metric_value
      : b.metric_value - a.metric_value;
  });

  const handleSort = (field: 'metric_value' | 'severity') => {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(false); }
  };

  const handleNavigate = (issue: ComplexityIssue) => {
    setHighlightedNodeIds(new Set([issue.entity_id]));
    setSelectedNodeId(issue.entity_id);
    setViewMode('explorer');
  };

  const issueTypes = [...new Set(report.issues.map((i) => i.issue_type))];

  return (
    <div className="complexity-table">
      <div className="complexity-table__header">
        <h3 className="complexity-table__title">
          Complexity Issues
          <span className="complexity-table__count">({report.total})</span>
        </h3>
        <div className="complexity-table__badges">
          <span className="severity-badge severity-badge--critical">
            {report.critical_count} critical
          </span>
          <span className="severity-badge severity-badge--warning">
            {report.warning_count} warning
          </span>
        </div>
      </div>

      <div className="complexity-table__filters">
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
        <select
          className="analytics-select"
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
        >
          <option value="all">All Types</option>
          {issueTypes.map((t) => (
            <option key={t} value={t}>{ISSUE_LABELS[t] || t}</option>
          ))}
        </select>
      </div>

      <div className="complexity-table__scroll">
        <table className="analytics-table">
          <thead>
            <tr>
              <th>Entity</th>
              <th>Type</th>
              <th>Issue</th>
              <th
                className="sortable"
                onClick={() => handleSort('severity')}
              >
                Severity {sortField === 'severity' ? (sortAsc ? '↑' : '↓') : ''}
              </th>
              <th
                className="sortable"
                onClick={() => handleSort('metric_value')}
              >
                Value {sortField === 'metric_value' ? (sortAsc ? '↑' : '↓') : ''}
              </th>
              <th>File</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((issue, idx) => (
              <tr key={`${issue.entity_id}-${idx}`} className="analytics-table__row">
                <td className="analytics-table__name" title={issue.fqn}>
                  {issue.entity_name}
                </td>
                <td>
                  <span className="entity-type-chip">{issue.entity_type}</span>
                </td>
                <td>{ISSUE_LABELS[issue.issue_type] || issue.issue_type}</td>
                <td>
                  <span
                    className="severity-dot"
                    style={{ backgroundColor: SEVERITY_COLORS[issue.severity] }}
                  />
                  {issue.severity}
                </td>
                <td className="analytics-table__value">{issue.metric_value}</td>
                <td className="analytics-table__path" title={issue.file_path}>
                  {issue.file_path.split('/').pop() || issue.file_path}
                </td>
                <td>
                  <button
                    className="analytics-nav-btn"
                    onClick={() => handleNavigate(issue)}
                    title="View in Graph Explorer"
                  >
                    🔍
                  </button>
                </td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={7} className="analytics-table__empty">
                  No complexity issues found — great code health! 🎉
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
