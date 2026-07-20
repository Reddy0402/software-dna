/**
 * Entity type → visual configuration mapping.
 * Each entity type has a primary color, gradient, icon, and border style.
 */

export interface EntityColorConfig {
  primary: string;
  gradient: string;
  border: string;
  glow: string;
  icon: string;
  bgOpacity: string;
}

const ENTITY_COLORS: Record<string, EntityColorConfig> = {
  class: {
    primary: '#818cf8',
    gradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    border: '#818cf8',
    glow: 'rgba(129, 140, 248, 0.4)',
    icon: '◆',
    bgOpacity: 'rgba(99, 102, 241, 0.12)',
  },
  interface: {
    primary: '#a78bfa',
    gradient: 'linear-gradient(135deg, #8b5cf6, #a78bfa)',
    border: '#a78bfa',
    glow: 'rgba(167, 139, 250, 0.4)',
    icon: '◇',
    bgOpacity: 'rgba(139, 92, 246, 0.12)',
  },
  function: {
    primary: '#34d399',
    gradient: 'linear-gradient(135deg, #10b981, #34d399)',
    border: '#34d399',
    glow: 'rgba(52, 211, 153, 0.4)',
    icon: 'ƒ',
    bgOpacity: 'rgba(16, 185, 129, 0.12)',
  },
  method: {
    primary: '#2dd4bf',
    gradient: 'linear-gradient(135deg, #14b8a6, #2dd4bf)',
    border: '#2dd4bf',
    glow: 'rgba(45, 212, 191, 0.4)',
    icon: 'λ',
    bgOpacity: 'rgba(20, 184, 166, 0.12)',
  },
  file: {
    primary: '#fbbf24',
    gradient: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    border: '#fbbf24',
    glow: 'rgba(251, 191, 36, 0.4)',
    icon: '📄',
    bgOpacity: 'rgba(245, 158, 11, 0.12)',
  },
  import: {
    primary: '#f472b6',
    gradient: 'linear-gradient(135deg, #ec4899, #f472b6)',
    border: '#f472b6',
    glow: 'rgba(244, 114, 182, 0.4)',
    icon: '↗',
    bgOpacity: 'rgba(236, 72, 153, 0.12)',
  },
  module: {
    primary: '#60a5fa',
    gradient: 'linear-gradient(135deg, #3b82f6, #60a5fa)',
    border: '#60a5fa',
    glow: 'rgba(96, 165, 250, 0.4)',
    icon: '▣',
    bgOpacity: 'rgba(59, 130, 246, 0.12)',
  },
  external: {
    primary: '#94a3b8',
    gradient: 'linear-gradient(135deg, #64748b, #94a3b8)',
    border: '#94a3b8',
    glow: 'rgba(148, 163, 184, 0.3)',
    icon: '⬡',
    bgOpacity: 'rgba(100, 116, 139, 0.12)',
  },
  repository: {
    primary: '#f97316',
    gradient: 'linear-gradient(135deg, #ea580c, #f97316)',
    border: '#f97316',
    glow: 'rgba(249, 115, 22, 0.4)',
    icon: '⊞',
    bgOpacity: 'rgba(234, 88, 12, 0.12)',
  },
  unknown: {
    primary: '#6b7280',
    gradient: 'linear-gradient(135deg, #4b5563, #6b7280)',
    border: '#6b7280',
    glow: 'rgba(107, 114, 128, 0.3)',
    icon: '●',
    bgOpacity: 'rgba(75, 85, 99, 0.12)',
  },
};

export function getEntityColor(entityType: string): EntityColorConfig {
  return ENTITY_COLORS[entityType.toLowerCase()] || ENTITY_COLORS.unknown;
}

/**
 * Relationship type → edge color mapping.
 */
const RELATIONSHIP_COLORS: Record<string, string> = {
  IMPORTS: '#f472b6',
  CALLS: '#34d399',
  EXTENDS: '#818cf8',
  IMPLEMENTS: '#a78bfa',
  USES: '#60a5fa',
  DEPENDS_ON: '#fbbf24',
  REFERENCES: '#94a3b8',
  CONTAINS: '#475569',
  DEFINES: '#475569',
  DEFINED_IN: '#334155',
  BELONGS_TO: '#1e293b',
};

export function getRelationshipColor(relType: string): string {
  return RELATIONSHIP_COLORS[relType] || '#475569';
}

export default ENTITY_COLORS;
