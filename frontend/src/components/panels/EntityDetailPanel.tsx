/**
 * Entity Detail Panel — slide-in side panel showing full entity information.
 */
import { useGraphStore } from '../../store/graphStore';
import { Badge } from '../common/Common';
import { getEntityColor } from '../../utils/colors';

export default function EntityDetailPanel() {
  const {
    isDetailPanelOpen,
    setDetailPanelOpen,
    selectedEntityDetail,
    setSelectedNodeId,
    setSelectedEntityDetail,
  } = useGraphStore();

  if (!isDetailPanelOpen || !selectedEntityDetail) return null;

  const { entity, file, outgoing_relationships, incoming_relationships, outgoing_count, incoming_count } =
    selectedEntityDetail;
  const colors = getEntityColor(entity.entity_type);

  const handleClose = () => {
    setDetailPanelOpen(false);
    setSelectedNodeId(null);
    setSelectedEntityDetail(null);
  };

  return (
    <div className={`detail-panel glass-panel ${isDetailPanelOpen ? 'detail-panel--open' : ''}`}>
      <div className="detail-panel__header" style={{ borderBottomColor: colors.primary }}>
        <div className="detail-panel__title-row">
          <span className="detail-panel__icon" style={{ background: colors.gradient }}>
            {colors.icon}
          </span>
          <h3 className="detail-panel__name">{entity.name}</h3>
        </div>
        <button className="detail-panel__close" onClick={handleClose}>
          ✕
        </button>
      </div>

      <div className="detail-panel__body">
        {/* Type & Language */}
        <div className="detail-panel__row">
          <Badge label={entity.entity_type} color={colors.primary} />
          {entity.language && <Badge label={entity.language} color="#60a5fa" small />}
          {entity.visibility && <Badge label={entity.visibility} color="#94a3b8" small />}
        </div>

        {/* FQN */}
        {entity.fully_qualified_name && (
          <div className="detail-panel__section">
            <div className="detail-panel__label">Fully Qualified Name</div>
            <div className="detail-panel__value detail-panel__value--mono">
              {entity.fully_qualified_name}
            </div>
          </div>
        )}

        {/* File Context */}
        {file && (
          <div className="detail-panel__section">
            <div className="detail-panel__label">📄 File</div>
            <div className="detail-panel__value detail-panel__value--mono">
              {file.relative_path}
            </div>
            <div className="detail-panel__meta">
              {file.language} · {(file.size_bytes / 1024).toFixed(1)} KB
            </div>
          </div>
        )}

        {/* Source Location */}
        {entity.start_line != null && (
          <div className="detail-panel__section">
            <div className="detail-panel__label">📍 Source Location</div>
            <div className="detail-panel__value">
              Lines {entity.start_line} – {entity.end_line}
            </div>
          </div>
        )}

        {/* Outgoing Relationships */}
        <div className="detail-panel__section">
          <div className="detail-panel__label">
            ➡ Outgoing ({outgoing_count})
          </div>
          <div className="detail-panel__rel-list">
            {outgoing_relationships.length === 0 && (
              <div className="detail-panel__empty">No outgoing relationships</div>
            )}
            {outgoing_relationships.slice(0, 20).map((rel, i) => (
              <div key={i} className="detail-panel__rel-item">
                <Badge
                  label={rel.relationship_type}
                  color={getEntityColor(rel.target?.entity_type || 'unknown').primary}
                  small
                />
                <span className="detail-panel__rel-target">
                  {rel.target?.name || 'unknown'}
                </span>
              </div>
            ))}
            {outgoing_count > 20 && (
              <div className="detail-panel__more">
                +{outgoing_count - 20} more
              </div>
            )}
          </div>
        </div>

        {/* Incoming Relationships */}
        <div className="detail-panel__section">
          <div className="detail-panel__label">
            ⬅ Incoming ({incoming_count})
          </div>
          <div className="detail-panel__rel-list">
            {incoming_relationships.length === 0 && (
              <div className="detail-panel__empty">No incoming relationships</div>
            )}
            {incoming_relationships.slice(0, 20).map((rel, i) => (
              <div key={i} className="detail-panel__rel-item">
                <Badge
                  label={rel.relationship_type}
                  color={getEntityColor(rel.source?.entity_type || 'unknown').primary}
                  small
                />
                <span className="detail-panel__rel-target">
                  {rel.source?.name || 'unknown'}
                </span>
              </div>
            ))}
            {incoming_count > 20 && (
              <div className="detail-panel__more">
                +{incoming_count - 20} more
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
