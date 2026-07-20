"""
Hotspot Rules — Code Hotspot Analyzer
======================================
Identifies the most critical areas of a repository based on structural
characteristics. Designed with extension hooks for future Git history
enrichment (commit frequency, churn, developer activity).
"""
from typing import Any, Dict, List

from app.services.analytics_engine import AnalyticsContext, AnalyticsRule
from app.services.analytics import register_rule


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _entity_line_count(entity) -> int:
    if entity.start_line is not None and entity.end_line is not None:
        return max(entity.end_line - entity.start_line + 1, 1)
    return 0


def _normalize_scores(scores: Dict[str, float]) -> Dict[str, float]:
    """Normalize a dict of scores to 0-1 range."""
    if not scores:
        return scores
    max_val = max(scores.values())
    if max_val == 0:
        return {k: 0.0 for k in scores}
    return {k: round(v / max_val, 4) for k, v in scores.items()}


# ---------------------------------------------------------------
# Rules
# ---------------------------------------------------------------

@register_rule
class CentralityHotspotRule(AnalyticsRule):
    rule_id = "hotspot.centrality"
    category = "hotspot"
    display_name = "Dependency Centrality"
    description = "Entities ranked by their centrality in the dependency graph."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        """
        Approximate betweenness centrality using degree centrality
        (fan-in * fan-out as a proxy for path-through potential).
        """
        scores: Dict[str, float] = {}
        entity_map: Dict[str, Dict[str, Any]] = {}

        for e in ctx.entities:
            fan_in = len(ctx.deps_by_target.get(e.id, []))
            fan_out = len(ctx.deps_by_source.get(e.id, []))
            # Proxy for betweenness: how many paths could go through this node
            score = fan_in * fan_out
            eid = str(e.id)
            scores[eid] = score
            f = ctx.files_by_id.get(e.file_id)
            entity_map[eid] = {
                "entity_id": eid,
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "fan_in": fan_in,
                "fan_out": fan_out,
            }

        normalized = _normalize_scores(scores)

        hotspots = []
        for eid, norm_score in normalized.items():
            if norm_score < 0.1:
                continue
            hotspots.append({
                **entity_map[eid],
                "centrality_score": norm_score,
                "raw_score": scores[eid],
            })

        hotspots.sort(key=lambda h: h["centrality_score"], reverse=True)
        return {
            "hotspots": hotspots[:50],
            "total_analyzed": len(ctx.entities),
            "total_hotspots": len(hotspots),
        }


@register_rule
class CouplingHotspotRule(AnalyticsRule):
    rule_id = "hotspot.coupling"
    category = "hotspot"
    display_name = "Coupling Hotspots"
    description = "Entities appearing in the most dependency chains."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        # Score based on total degree weighted by relationship diversity
        scores: Dict[str, float] = {}
        entity_map: Dict[str, Dict[str, Any]] = {}

        for e in ctx.entities:
            outgoing = ctx.deps_by_source.get(e.id, [])
            incoming = ctx.deps_by_target.get(e.id, [])

            # Count unique relationship types
            rel_types = set()
            for d in outgoing:
                rel_types.add(d.relationship_type)
            for d in incoming:
                rel_types.add(d.relationship_type)

            # Score = total_degree * relationship_type_diversity
            total_degree = len(outgoing) + len(incoming)
            type_diversity = len(rel_types)
            score = total_degree * (1 + type_diversity * 0.5)

            eid = str(e.id)
            scores[eid] = score
            f = ctx.files_by_id.get(e.file_id)
            entity_map[eid] = {
                "entity_id": eid,
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "total_degree": total_degree,
                "relationship_types": list(rel_types),
            }

        normalized = _normalize_scores(scores)

        hotspots = []
        for eid, norm_score in normalized.items():
            if norm_score < 0.1:
                continue
            hotspots.append({
                **entity_map[eid],
                "coupling_score": norm_score,
                "raw_score": scores[eid],
            })

        hotspots.sort(key=lambda h: h["coupling_score"], reverse=True)
        return {
            "hotspots": hotspots[:50],
            "total_analyzed": len(ctx.entities),
            "total_hotspots": len(hotspots),
        }


@register_rule
class ComplexityHotspotRule(AnalyticsRule):
    rule_id = "hotspot.complexity"
    category = "hotspot"
    display_name = "Complexity Hotspots"
    description = "Entities with highest combined size + dependency metrics."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        scores: Dict[str, float] = {}
        entity_map: Dict[str, Dict[str, Any]] = {}

        for e in ctx.entities:
            lc = _entity_line_count(e)
            total_deps = (
                len(ctx.deps_by_source.get(e.id, []))
                + len(ctx.deps_by_target.get(e.id, []))
            )

            # Weighted: size contributes 60%, dependencies 40%
            score = lc * 0.6 + total_deps * 10 * 0.4

            eid = str(e.id)
            scores[eid] = score
            f = ctx.files_by_id.get(e.file_id)
            entity_map[eid] = {
                "entity_id": eid,
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "line_count": lc,
                "dependency_count": total_deps,
            }

        normalized = _normalize_scores(scores)

        hotspots = []
        for eid, norm_score in normalized.items():
            if norm_score < 0.1:
                continue
            hotspots.append({
                **entity_map[eid],
                "complexity_score": norm_score,
                "raw_score": round(scores[eid], 2),
            })

        hotspots.sort(key=lambda h: h["complexity_score"], reverse=True)
        return {
            "hotspots": hotspots[:50],
            "total_analyzed": len(ctx.entities),
            "total_hotspots": len(hotspots),
        }


@register_rule
class ConnectivityHotspotRule(AnalyticsRule):
    rule_id = "hotspot.connectivity"
    category = "hotspot"
    display_name = "Connectivity Hotspots"
    description = "Critical connection points whose removal would fragment the graph."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        """
        Approximate articulation point detection using a heuristic:
        entities that bridge otherwise disconnected clusters.
        Score = fan_in * fan_out * unique_file_connections
        """
        scores: Dict[str, float] = {}
        entity_map: Dict[str, Dict[str, Any]] = {}

        for e in ctx.entities:
            outgoing = ctx.deps_by_source.get(e.id, [])
            incoming = ctx.deps_by_target.get(e.id, [])

            # Count unique files this entity connects to
            connected_files = set()
            for d in outgoing:
                if d.target_entity_id:
                    target = ctx.entities_by_id.get(d.target_entity_id)
                    if target:
                        connected_files.add(target.file_id)
            for d in incoming:
                source = ctx.entities_by_id.get(d.source_entity_id)
                if source:
                    connected_files.add(source.file_id)

            unique_files = len(connected_files)
            fan_in = len(incoming)
            fan_out = len(outgoing)

            # Higher score if entity connects many different files
            score = (fan_in + fan_out) * unique_files

            eid = str(e.id)
            scores[eid] = score
            f = ctx.files_by_id.get(e.file_id)
            entity_map[eid] = {
                "entity_id": eid,
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "unique_file_connections": unique_files,
                "fan_in": fan_in,
                "fan_out": fan_out,
            }

        normalized = _normalize_scores(scores)

        hotspots = []
        for eid, norm_score in normalized.items():
            if norm_score < 0.1:
                continue
            hotspots.append({
                **entity_map[eid],
                "connectivity_score": norm_score,
                "raw_score": scores[eid],
            })

        hotspots.sort(key=lambda h: h["connectivity_score"], reverse=True)
        return {
            "hotspots": hotspots[:50],
            "total_analyzed": len(ctx.entities),
            "total_hotspots": len(hotspots),
        }


@register_rule
class CompositeHotspotRule(AnalyticsRule):
    rule_id = "hotspot.composite"
    category = "hotspot"
    display_name = "Composite Hotspots"
    description = "Weighted composite of all hotspot dimensions."

    # Weights for each dimension
    WEIGHTS = {
        "centrality": 0.30,
        "coupling": 0.25,
        "complexity": 0.25,
        "connectivity": 0.20,
        # Future: "churn": 0.0 (placeholder for Git history)
    }

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        # Compute individual hotspot scores
        centrality = CentralityHotspotRule().compute(ctx)
        coupling = CouplingHotspotRule().compute(ctx)
        complexity = ComplexityHotspotRule().compute(ctx)
        connectivity = ConnectivityHotspotRule().compute(ctx)

        # Build per-entity score maps
        score_maps = {
            "centrality": {h["entity_id"]: h.get("centrality_score", 0) for h in centrality["hotspots"]},
            "coupling": {h["entity_id"]: h.get("coupling_score", 0) for h in coupling["hotspots"]},
            "complexity": {h["entity_id"]: h.get("complexity_score", 0) for h in complexity["hotspots"]},
            "connectivity": {h["entity_id"]: h.get("connectivity_score", 0) for h in connectivity["hotspots"]},
        }

        # Collect all entity IDs that appear in any dimension
        all_ids = set()
        for sm in score_maps.values():
            all_ids.update(sm.keys())

        # Compute composite scores
        entity_info: Dict[str, Dict[str, Any]] = {}
        for h_list in [centrality["hotspots"], coupling["hotspots"],
                       complexity["hotspots"], connectivity["hotspots"]]:
            for h in h_list:
                if h["entity_id"] not in entity_info:
                    entity_info[h["entity_id"]] = {
                        "entity_id": h["entity_id"],
                        "entity_name": h["entity_name"],
                        "entity_type": h["entity_type"],
                        "fqn": h.get("fqn", ""),
                        "file_path": h.get("file_path", ""),
                    }

        hotspots = []
        for eid in all_ids:
            sub_scores = {}
            composite = 0.0
            for dim, weight in self.WEIGHTS.items():
                s = score_maps.get(dim, {}).get(eid, 0.0)
                sub_scores[dim] = round(s, 4)
                composite += s * weight

            if composite < 0.05:
                continue

            info = entity_info.get(eid, {"entity_id": eid})
            hotspots.append({
                **info,
                "composite_score": round(composite, 4),
                "sub_scores": sub_scores,
            })

        hotspots.sort(key=lambda h: h["composite_score"], reverse=True)

        return {
            "hotspots": hotspots[:50],
            "total_analyzed": len(ctx.entities),
            "total_hotspots": len(hotspots),
            "weights": self.WEIGHTS,
            "future_dimensions": ["churn", "commit_frequency", "developer_count"],
        }
