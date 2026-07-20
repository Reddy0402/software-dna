"""
Health Rules — Repository Health Engine
========================================
Rules that compute high-level quality indicators for a repository.
Each rule produces a focused metric; HealthScoreRule combines them
into a composite 0-100 score.
"""
import math
from typing import Any, Dict, List

from app.services.analytics_engine import AnalyticsContext, AnalyticsRule
from app.services.analytics import register_rule


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _entity_line_count(entity) -> int:
    """Compute line count from start_line/end_line."""
    if entity.start_line is not None and entity.end_line is not None:
        return max(entity.end_line - entity.start_line + 1, 1)
    return 0


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------
# Rules
# ---------------------------------------------------------------

@register_rule
class StructuralCountsRule(AnalyticsRule):
    rule_id = "health.structural_counts"
    category = "health"
    display_name = "Structural Counts"
    description = "Total counts of files, packages, modules, classes, interfaces, methods, functions, imports."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        counts: Dict[str, int] = {}
        for etype, elist in ctx.entities_by_type.items():
            counts[etype] = len(elist)

        return {
            "total_files": len(ctx.files),
            "total_entities": len(ctx.entities),
            "total_dependencies": len(ctx.dependencies),
            "classes": counts.get("class", 0),
            "interfaces": counts.get("interface", 0),
            "methods": counts.get("method", 0),
            "functions": counts.get("function", 0),
            "modules": counts.get("module", 0),
            "imports": counts.get("import", 0),
            "constructors": counts.get("constructor", 0),
            "structs": counts.get("struct", 0),
            "namespaces": counts.get("namespace", 0),
            "entity_type_breakdown": counts,
        }


@register_rule
class GraphDensityRule(AnalyticsRule):
    rule_id = "health.graph_density"
    category = "health"
    display_name = "Graph Density"
    description = "Measures the density and connectivity of the dependency graph."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        n = len(ctx.entities)
        e = len(ctx.dependencies)

        # Density = E / (N * (N - 1)) for directed graph
        max_edges = n * (n - 1) if n > 1 else 1
        density = e / max_edges if max_edges > 0 else 0.0

        # Average degree
        avg_degree = (2 * e) / n if n > 0 else 0.0

        # Connected component estimation via union-find
        connected_entities = set()
        for d in ctx.dependencies:
            connected_entities.add(d.source_entity_id)
            if d.target_entity_id:
                connected_entities.add(d.target_entity_id)

        isolated_count = n - len(connected_entities)

        return {
            "total_nodes": n,
            "total_edges": e,
            "density": round(density, 6),
            "avg_degree": round(avg_degree, 2),
            "max_possible_edges": max_edges,
            "connected_entities": len(connected_entities),
            "isolated_entities": isolated_count,
            "connectivity_ratio": round(len(connected_entities) / n, 4) if n > 0 else 0.0,
        }


@register_rule
class InheritanceDepthRule(AnalyticsRule):
    rule_id = "health.inheritance_depth"
    category = "health"
    display_name = "Inheritance Depth"
    description = "Average depth of EXTENDS chains."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        extends_deps = ctx.deps_by_type.get("EXTENDS", [])

        if not extends_deps:
            return {
                "avg_inheritance_depth": 0.0,
                "max_inheritance_depth": 0,
                "classes_with_inheritance": 0,
                "deepest_chain": [],
            }

        # Build parent map: child -> parent
        parent_map: Dict[Any, Any] = {}
        for d in extends_deps:
            if d.target_entity_id:
                parent_map[d.source_entity_id] = d.target_entity_id

        # Compute depth for each class in the chain
        depths: Dict[Any, int] = {}

        def get_depth(entity_id):
            if entity_id in depths:
                return depths[entity_id]
            if entity_id not in parent_map:
                depths[entity_id] = 1
                return 1
            parent_depth = get_depth(parent_map[entity_id])
            depths[entity_id] = parent_depth + 1
            return depths[entity_id]

        for child_id in parent_map:
            get_depth(child_id)

        if not depths:
            return {
                "avg_inheritance_depth": 0.0,
                "max_inheritance_depth": 0,
                "classes_with_inheritance": 0,
                "deepest_chain": [],
            }

        max_depth = max(depths.values())
        avg_depth = sum(depths.values()) / len(depths)

        # Find deepest chain
        deepest_entity = max(depths, key=depths.get)
        chain = []
        current = deepest_entity
        visited = set()
        while current and current not in visited:
            visited.add(current)
            entity = ctx.entities_by_id.get(current)
            if entity:
                chain.append(entity.name)
            current = parent_map.get(current)

        return {
            "avg_inheritance_depth": round(avg_depth, 2),
            "max_inheritance_depth": max_depth,
            "classes_with_inheritance": len(depths),
            "deepest_chain": chain,
        }


@register_rule
class SizeMetricsRule(AnalyticsRule):
    rule_id = "health.size_metrics"
    category = "health"
    display_name = "Size Metrics"
    description = "Average function/method size and class size in lines."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        method_sizes = []
        function_sizes = []
        class_sizes = []

        for e in ctx.entities:
            lc = _entity_line_count(e)
            if lc == 0:
                continue
            if e.entity_type in ("method", "constructor"):
                method_sizes.append(lc)
            elif e.entity_type == "function":
                function_sizes.append(lc)
            elif e.entity_type == "class":
                class_sizes.append(lc)

        avg_method = sum(method_sizes) / len(method_sizes) if method_sizes else 0.0
        avg_function = sum(function_sizes) / len(function_sizes) if function_sizes else 0.0
        avg_class = sum(class_sizes) / len(class_sizes) if class_sizes else 0.0

        return {
            "avg_method_size": round(avg_method, 1),
            "avg_function_size": round(avg_function, 1),
            "avg_class_size": round(avg_class, 1),
            "max_method_size": max(method_sizes) if method_sizes else 0,
            "max_function_size": max(function_sizes) if function_sizes else 0,
            "max_class_size": max(class_sizes) if class_sizes else 0,
            "total_methods": len(method_sizes),
            "total_functions": len(function_sizes),
            "total_classes": len(class_sizes),
        }


@register_rule
class CouplingCohesionRule(AnalyticsRule):
    rule_id = "health.coupling_cohesion"
    category = "health"
    display_name = "Coupling & Cohesion"
    description = "Afferent/efferent coupling per file, instability index."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        # Compute per-file coupling
        # Afferent (Ca) = incoming deps to entities in this file
        # Efferent (Ce) = outgoing deps from entities in this file
        file_metrics: List[Dict[str, Any]] = []

        for file_id, file_entities in ctx.entities_by_file.items():
            entity_ids = {e.id for e in file_entities}
            ca = 0  # afferent
            ce = 0  # efferent

            for eid in entity_ids:
                # Outgoing
                ce += len(ctx.deps_by_source.get(eid, []))
                # Incoming
                ca += len(ctx.deps_by_target.get(eid, []))

            total = ca + ce
            instability = ce / total if total > 0 else 0.0

            f = ctx.files_by_id.get(file_id)
            file_metrics.append({
                "file_id": str(file_id),
                "file_path": f.relative_path if f else "",
                "afferent_coupling": ca,
                "efferent_coupling": ce,
                "instability": round(instability, 3),
            })

        avg_ca = sum(m["afferent_coupling"] for m in file_metrics) / len(file_metrics) if file_metrics else 0.0
        avg_ce = sum(m["efferent_coupling"] for m in file_metrics) / len(file_metrics) if file_metrics else 0.0
        avg_instability = sum(m["instability"] for m in file_metrics) / len(file_metrics) if file_metrics else 0.0

        return {
            "avg_afferent_coupling": round(avg_ca, 2),
            "avg_efferent_coupling": round(avg_ce, 2),
            "avg_instability": round(avg_instability, 3),
            "total_files_analyzed": len(file_metrics),
            "most_coupled_files": sorted(
                file_metrics,
                key=lambda m: m["afferent_coupling"] + m["efferent_coupling"],
                reverse=True,
            )[:10],
        }


@register_rule
class FanInFanOutRule(AnalyticsRule):
    rule_id = "health.fan_in_fan_out"
    category = "health"
    display_name = "Fan-In / Fan-Out"
    description = "Per-entity incoming (fan-in) and outgoing (fan-out) relationship counts."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        fan_data: List[Dict[str, Any]] = []

        for e in ctx.entities:
            fan_out = len(ctx.deps_by_source.get(e.id, []))
            fan_in = len(ctx.deps_by_target.get(e.id, []))
            fan_data.append({
                "entity_id": str(e.id),
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "fan_in": fan_in,
                "fan_out": fan_out,
                "total_degree": fan_in + fan_out,
            })

        avg_fan_in = sum(d["fan_in"] for d in fan_data) / len(fan_data) if fan_data else 0.0
        avg_fan_out = sum(d["fan_out"] for d in fan_data) / len(fan_data) if fan_data else 0.0

        return {
            "avg_fan_in": round(avg_fan_in, 2),
            "avg_fan_out": round(avg_fan_out, 2),
            "max_fan_in": max((d["fan_in"] for d in fan_data), default=0),
            "max_fan_out": max((d["fan_out"] for d in fan_data), default=0),
            "high_fan_in_entities": sorted(fan_data, key=lambda d: d["fan_in"], reverse=True)[:10],
            "high_fan_out_entities": sorted(fan_data, key=lambda d: d["fan_out"], reverse=True)[:10],
        }


@register_rule
class DependencyCyclesRule(AnalyticsRule):
    rule_id = "health.dependency_cycles"
    category = "health"
    display_name = "Dependency Cycles"
    description = "Counts circular dependencies detected in the graph."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        cycles = ctx.graph_cycles
        return {
            "total_cycles": len(cycles),
            "cycles": [
                {
                    "cycle_length": c.get("cycle_length", 0),
                    "entities": [
                        n.get("name", "unknown") if isinstance(n, dict) else str(n)
                        for n in c.get("entities", [])
                    ],
                }
                for c in cycles[:20]  # Cap display at 20
            ],
        }


@register_rule
class HealthScoreRule(AnalyticsRule):
    rule_id = "health.overall_score"
    category = "health"
    display_name = "Overall Health Score"
    description = "Weighted composite health score (0-100) with letter grade."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        # Sub-scores (each 0-100, higher = healthier)
        scores: Dict[str, float] = {}

        # --- Size balance score ---
        size_rule = SizeMetricsRule()
        size_data = size_rule.compute(ctx)
        avg_method = size_data["avg_method_size"]
        avg_class = size_data["avg_class_size"]
        # Ideal: methods < 30 lines, classes < 200 lines
        method_score = _clamp(100 - max(0, avg_method - 30) * 2)
        class_score = _clamp(100 - max(0, avg_class - 200) * 0.5)
        scores["size_balance"] = (method_score + class_score) / 2

        # --- Coupling score ---
        coupling_rule = CouplingCohesionRule()
        coupling_data = coupling_rule.compute(ctx)
        avg_instability = coupling_data["avg_instability"]
        # Ideal instability is around 0.5 (balanced)
        coupling_score = _clamp(100 - abs(avg_instability - 0.5) * 100)
        scores["coupling_balance"] = coupling_score

        # --- Connectivity score ---
        density_rule = GraphDensityRule()
        density_data = density_rule.compute(ctx)
        connectivity = density_data["connectivity_ratio"]
        # Higher connectivity is generally better (fewer isolated entities)
        scores["connectivity"] = _clamp(connectivity * 100)

        # --- Cycle penalty ---
        cycle_count = len(ctx.graph_cycles)
        scores["cycle_health"] = _clamp(100 - cycle_count * 15)

        # --- Inheritance depth score ---
        inh_rule = InheritanceDepthRule()
        inh_data = inh_rule.compute(ctx)
        max_depth = inh_data["max_inheritance_depth"]
        scores["inheritance_health"] = _clamp(100 - max(0, max_depth - 4) * 20)

        # --- Weighted composite ---
        weights = {
            "size_balance": 0.25,
            "coupling_balance": 0.20,
            "connectivity": 0.20,
            "cycle_health": 0.20,
            "inheritance_health": 0.15,
        }
        overall = sum(scores[k] * weights[k] for k in weights)
        overall = round(_clamp(overall), 1)

        # Grade
        if overall >= 90:
            grade = "A"
        elif overall >= 80:
            grade = "B"
        elif overall >= 65:
            grade = "C"
        elif overall >= 50:
            grade = "D"
        else:
            grade = "F"

        return {
            "overall_score": overall,
            "grade": grade,
            "sub_scores": {k: round(v, 1) for k, v in scores.items()},
            "weights": weights,
        }
