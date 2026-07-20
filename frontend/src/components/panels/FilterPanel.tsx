/**
 * Filter Panel — toggle node types and relationship types visible on the graph.
 */
import { useGraphStore } from '../../store/graphStore';
import { NODE_TYPE_OPTIONS, RELATIONSHIP_TYPE_OPTIONS, type EntityType, type RelationshipType } from '../../types/graph';
import { getEntityColor, getRelationshipColor } from '../../utils/colors';

export default function FilterPanel() {
  const {
    isFilterPanelOpen,
    setFilterPanelOpen,
    filters,
    setNodeTypeFilter,
    setRelTypeFilter,
    resetFilters,
  } = useGraphStore();

  if (!isFilterPanelOpen) return null;

  const toggleNodeType = (type: EntityType) => {
    const current = filters.nodeTypes;
    if (current.includes(type)) {
      setNodeTypeFilter(current.filter((t) => t !== type));
    } else {
      setNodeTypeFilter([...current, type]);
    }
  };

  const toggleRelType = (type: RelationshipType) => {
    const current = filters.relationshipTypes;
    if (current.includes(type)) {
      setRelTypeFilter(current.filter((t) => t !== type));
    } else {
      setRelTypeFilter([...current, type]);
    }
  };

  return (
    <div className="filter-panel glass-panel">
      <div className="filter-panel__header">
        <h3>Filters</h3>
        <div className="filter-panel__actions">
          <button className="filter-panel__reset" onClick={resetFilters}>
            Reset
          </button>
          <button className="filter-panel__close" onClick={() => setFilterPanelOpen(false)}>
            ✕
          </button>
        </div>
      </div>

      {/* Node type filters */}
      <div className="filter-panel__section">
        <div className="filter-panel__label">Node Types</div>
        <div className="filter-panel__options">
          {NODE_TYPE_OPTIONS.map((type) => {
            const color = getEntityColor(type);
            const isActive = filters.nodeTypes.includes(type);
            return (
              <button
                key={type}
                className={`filter-chip ${isActive ? 'filter-chip--active' : ''}`}
                style={{
                  borderColor: isActive ? color.primary : 'transparent',
                  color: isActive ? color.primary : '#94a3b8',
                  background: isActive ? color.bgOpacity : 'transparent',
                }}
                onClick={() => toggleNodeType(type)}
              >
                <span className="filter-chip__icon">{color.icon}</span>
                {type}
              </button>
            );
          })}
        </div>
      </div>

      {/* Relationship type filters */}
      <div className="filter-panel__section">
        <div className="filter-panel__label">Relationship Types</div>
        <div className="filter-panel__options">
          {RELATIONSHIP_TYPE_OPTIONS.map((type) => {
            const color = getRelationshipColor(type);
            const isActive = filters.relationshipTypes.includes(type);
            return (
              <button
                key={type}
                className={`filter-chip ${isActive ? 'filter-chip--active' : ''}`}
                style={{
                  borderColor: isActive ? color : 'transparent',
                  color: isActive ? color : '#94a3b8',
                }}
                onClick={() => toggleRelType(type)}
              >
                {type}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
