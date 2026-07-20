/**
 * Custom node component for the graph visualization.
 * Renders entity nodes with type-specific styling, icons, and glow effects.
 */
import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';

interface EntityNodeData {
  label: string;
  entityType: string;
  fqn: string;
  language: string;
  icon: string;
  color: string;
  gradient: string;
  borderColor: string;
  glowColor: string;
  bgColor: string;
  isHighlighted: boolean;
  isSelected: boolean;
  [key: string]: unknown;
}

function EntityNode({ data, selected }: NodeProps) {
  const d = data as unknown as EntityNodeData;
  const isActive = d.isHighlighted || d.isSelected || selected;

  return (
    <div
      className={`entity-node ${isActive ? 'entity-node--active' : ''}`}
      style={{
        borderColor: d.borderColor,
        background: d.bgColor,
        boxShadow: isActive
          ? `0 0 20px ${d.glowColor}, 0 0 40px ${d.glowColor}`
          : `0 2px 8px rgba(0,0,0,0.3)`,
        transform: isActive ? 'scale(1.05)' : 'scale(1)',
      }}
    >
      <Handle type="target" position={Position.Top} className="entity-handle" />

      <div className="entity-node__header">
        <span className="entity-node__icon" style={{ background: d.gradient }}>
          {d.icon}
        </span>
        <span
          className="entity-node__type-badge"
          style={{ color: d.color, borderColor: d.color }}
        >
          {d.entityType}
        </span>
        {d.language && (
          <span className="entity-node__lang">{d.language}</span>
        )}
      </div>

      <div className="entity-node__name" title={d.fqn || d.label}>
        {d.label}
      </div>

      {d.fqn && d.fqn !== d.label && (
        <div className="entity-node__fqn" title={d.fqn}>
          {d.fqn}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} className="entity-handle" />
    </div>
  );
}

export default memo(EntityNode);
