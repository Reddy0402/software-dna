"""
Dependency Rules — Dependency Risk Analyzer
=============================================
Rules that traverse dependency data to identify architectural risks.
Each result includes severity, affected entities, explanation, and
suggested remediation.
"""
from typing import Any, Dict, List

from app.services.analytics_engine import AnalyticsContext, AnalyticsRule
from app.services.analytics import register_rule


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def _make_risk(
    risk_type: str,
    severity: str,
    entities: List[Dict[str, Any]],
    explanation: str,
    remediation: str,
) -> Dict[str, Any]:
    """Build a standardized risk record."""
    return {
        "risk_type": risk_type,
        "severity": severity,
        "affected_entities": entities,
        "explanation": explanation,
        "remediation": remediation,
    }


def _entity_info(entity) -> Dict[str, Any]:
    """Extract minimal info dict from a CodeEntity."""
    return {
        "entity_id": str(entity.id),
        "entity_name": entity.name,
        "entity_type": entity.entity_type,
        "fqn": entity.fully_qualified_name,
    }


# ---------------------------------------------------------------
# Rules
# ---------------------------------------------------------------

@register_rule
class CircularDependencyRule(AnalyticsRule):
    rule_id = "risk.circular_dependencies"
    category = "risk"
    display_name = "Circular Dependencies"
    description = "Detects dependency cycles in the graph."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        risks: List[Dict[str, Any]] = []

        for cycle in ctx.graph_cycles:
            cycle_entities = cycle.get("entities", [])
            entity_names = []
            entity_infos = []

            for node in cycle_entities:
                if isinstance(node, dict):
                    entity_names.append(node.get("name", "unknown"))
                    entity_infos.append({
                        "entity_id": node.get("id", ""),
                        "entity_name": node.get("name", "unknown"),
                        "entity_type": node.get("entity_type", "unknown"),
                        "fqn": node.get("fully_qualified_name", ""),
                    })
                else:
                    entity_names.append(str(node))

            cycle_len = cycle.get("cycle_length", len(entity_names))
            severity = "critical" if cycle_len >= 3 else "warning"

            risks.append(_make_risk(
                risk_type="circular_dependency",
                severity=severity,
                entities=entity_infos,
                explanation=(
                    f"Circular dependency of length {cycle_len} detected: "
                    f"{' → '.join(entity_names[:6])}"
                    + ("..." if len(entity_names) > 6 else "")
                ),
                remediation=(
                    "Break the cycle by introducing an interface or abstraction layer. "
                    "Consider the Dependency Inversion Principle to decouple these components."
                ),
            ))

        return {
            "risks": risks,
            "total": len(risks),
            "critical_count": sum(1 for r in risks if r["severity"] == "critical"),
            "warning_count": sum(1 for r in risks if r["severity"] == "warning"),
        }


@register_rule
class UnstableModuleRule(AnalyticsRule):
    rule_id = "risk.unstable_modules"
    category = "risk"
    display_name = "Unstable Modules"
    description = "Files/modules with high instability (Ce / (Ca + Ce) > 0.8)."

    INSTABILITY_THRESHOLD = 0.8

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        risks: List[Dict[str, Any]] = []

        for file_id, file_entities in ctx.entities_by_file.items():
            entity_ids = {e.id for e in file_entities}
            ca = sum(len(ctx.deps_by_target.get(eid, [])) for eid in entity_ids)
            ce = sum(len(ctx.deps_by_source.get(eid, [])) for eid in entity_ids)
            total = ca + ce

            if total < 3:  # Skip trivially small modules
                continue

            instability = ce / total if total > 0 else 0.0

            if instability < self.INSTABILITY_THRESHOLD:
                continue

            f = ctx.files_by_id.get(file_id)
            severity = "critical" if instability > 0.9 else "warning"

            risks.append(_make_risk(
                risk_type="unstable_module",
                severity=severity,
                entities=[{
                    "entity_id": str(file_id),
                    "entity_name": f.filename if f else "",
                    "entity_type": "file",
                    "fqn": f.relative_path if f else "",
                    "instability": round(instability, 3),
                    "afferent": ca,
                    "efferent": ce,
                }],
                explanation=(
                    f"'{f.relative_path if f else file_id}' has instability "
                    f"{instability:.2f} (Ce={ce}, Ca={ca}). "
                    f"High instability means the module depends on many others "
                    f"but few depend on it, making it fragile to change."
                ),
                remediation=(
                    "Reduce outgoing dependencies by extracting shared logic "
                    "into stable core modules. Apply the Stable Dependencies Principle."
                ),
            ))

        risks.sort(key=lambda r: r["affected_entities"][0].get("instability", 0), reverse=True)
        return {
            "risks": risks,
            "total": len(risks),
            "critical_count": sum(1 for r in risks if r["severity"] == "critical"),
            "warning_count": sum(1 for r in risks if r["severity"] == "warning"),
        }


@register_rule
class HighCouplingRule(AnalyticsRule):
    rule_id = "risk.high_coupling"
    category = "risk"
    display_name = "Highly Coupled Components"
    description = "Entities with excessive fan-out (outgoing dependencies)."

    FAN_OUT_THRESHOLD = 15

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        risks: List[Dict[str, Any]] = []

        for e in ctx.entities:
            fan_out = len(ctx.deps_by_source.get(e.id, []))
            if fan_out < self.FAN_OUT_THRESHOLD:
                continue

            severity = "critical" if fan_out >= self.FAN_OUT_THRESHOLD * 2 else "warning"
            f = ctx.files_by_id.get(e.file_id)

            risks.append(_make_risk(
                risk_type="high_coupling",
                severity=severity,
                entities=[{
                    **_entity_info(e),
                    "fan_out": fan_out,
                    "file_path": f.relative_path if f else "",
                }],
                explanation=(
                    f"'{e.name}' has {fan_out} outgoing dependencies "
                    f"(threshold: {self.FAN_OUT_THRESHOLD}). "
                    f"Changes to its dependencies will likely require changes here."
                ),
                remediation=(
                    "Apply the Single Responsibility Principle. Split this component "
                    "into smaller, focused modules with fewer dependencies."
                ),
            ))

        risks.sort(key=lambda r: r["affected_entities"][0].get("fan_out", 0), reverse=True)
        return {
            "risks": risks,
            "total": len(risks),
            "critical_count": sum(1 for r in risks if r["severity"] == "critical"),
            "warning_count": sum(1 for r in risks if r["severity"] == "warning"),
        }


@register_rule
class BottleneckRule(AnalyticsRule):
    rule_id = "risk.bottlenecks"
    category = "risk"
    display_name = "Architectural Bottlenecks"
    description = "Entities with extremely high fan-in (many dependents)."

    FAN_IN_THRESHOLD = 15

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        risks: List[Dict[str, Any]] = []

        for e in ctx.entities:
            fan_in = len(ctx.deps_by_target.get(e.id, []))
            if fan_in < self.FAN_IN_THRESHOLD:
                continue

            severity = "critical" if fan_in >= self.FAN_IN_THRESHOLD * 2 else "warning"
            f = ctx.files_by_id.get(e.file_id)

            risks.append(_make_risk(
                risk_type="bottleneck",
                severity=severity,
                entities=[{
                    **_entity_info(e),
                    "fan_in": fan_in,
                    "file_path": f.relative_path if f else "",
                }],
                explanation=(
                    f"'{e.name}' is depended upon by {fan_in} other entities "
                    f"(threshold: {self.FAN_IN_THRESHOLD}). "
                    f"Any change to this component has a blast radius of {fan_in} dependents."
                ),
                remediation=(
                    "Consider extracting a stable interface or abstraction. "
                    "Ensure this component is well-tested given its high impact."
                ),
            ))

        risks.sort(key=lambda r: r["affected_entities"][0].get("fan_in", 0), reverse=True)
        return {
            "risks": risks,
            "total": len(risks),
            "critical_count": sum(1 for r in risks if r["severity"] == "critical"),
            "warning_count": sum(1 for r in risks if r["severity"] == "warning"),
        }


@register_rule
class DependencyHubRule(AnalyticsRule):
    rule_id = "risk.dependency_hubs"
    category = "risk"
    display_name = "Dependency Hubs"
    description = "Entities with total degree above threshold."

    DEGREE_THRESHOLD = 20

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        risks: List[Dict[str, Any]] = []

        for e in ctx.entities:
            fan_in = len(ctx.deps_by_target.get(e.id, []))
            fan_out = len(ctx.deps_by_source.get(e.id, []))
            total = fan_in + fan_out

            if total < self.DEGREE_THRESHOLD:
                continue

            severity = "critical" if total >= self.DEGREE_THRESHOLD * 2 else "warning"
            f = ctx.files_by_id.get(e.file_id)

            risks.append(_make_risk(
                risk_type="dependency_hub",
                severity=severity,
                entities=[{
                    **_entity_info(e),
                    "fan_in": fan_in,
                    "fan_out": fan_out,
                    "total_degree": total,
                    "file_path": f.relative_path if f else "",
                }],
                explanation=(
                    f"'{e.name}' is a dependency hub with total degree {total} "
                    f"(in={fan_in}, out={fan_out}; threshold: {self.DEGREE_THRESHOLD})."
                ),
                remediation=(
                    "Decompose this hub into smaller components. "
                    "Consider the Facade pattern to reduce direct dependencies."
                ),
            ))

        risks.sort(key=lambda r: r["affected_entities"][0].get("total_degree", 0), reverse=True)
        return {
            "risks": risks,
            "total": len(risks),
            "critical_count": sum(1 for r in risks if r["severity"] == "critical"),
            "warning_count": sum(1 for r in risks if r["severity"] == "warning"),
        }


@register_rule
class IsolatedModuleRule(AnalyticsRule):
    rule_id = "risk.isolated_modules"
    category = "risk"
    display_name = "Isolated Modules"
    description = "Entities with zero incoming or outgoing connections."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        risks: List[Dict[str, Any]] = []
        # Exclude imports and trivial types
        skip_types = {"import"}

        for e in ctx.entities:
            if e.entity_type in skip_types:
                continue

            fan_in = len(ctx.deps_by_target.get(e.id, []))
            fan_out = len(ctx.deps_by_source.get(e.id, []))

            if fan_in + fan_out > 0:
                continue

            f = ctx.files_by_id.get(e.file_id)
            risks.append(_make_risk(
                risk_type="isolated_module",
                severity="info",
                entities=[{
                    **_entity_info(e),
                    "file_path": f.relative_path if f else "",
                }],
                explanation=(
                    f"'{e.name}' ({e.entity_type}) has no dependency connections. "
                    f"It may be dead code or missing dependency links."
                ),
                remediation=(
                    "Verify this component is used. If it's dead code, remove it. "
                    "If dependencies are missing, check the extraction configuration."
                ),
            ))

        return {
            "risks": risks,
            "total": len(risks),
            "info_count": len(risks),
        }


@register_rule
class OrphanedFileRule(AnalyticsRule):
    rule_id = "risk.orphaned_files"
    category = "risk"
    display_name = "Orphaned Files"
    description = "Files with no extracted entities or entities with no relationships."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        risks: List[Dict[str, Any]] = []

        for f in ctx.files:
            file_entities = ctx.entities_by_file.get(f.id, [])

            if len(file_entities) == 0:
                risks.append(_make_risk(
                    risk_type="orphaned_file",
                    severity="info",
                    entities=[{
                        "entity_id": str(f.id),
                        "entity_name": f.filename,
                        "entity_type": "file",
                        "fqn": f.relative_path,
                    }],
                    explanation=(
                        f"'{f.relative_path}' has no extracted code entities. "
                        f"It may be a configuration file, data file, or parsing failed."
                    ),
                    remediation=(
                        "Check if this file should be analyzed. If the parser doesn't "
                        "support its language, consider adding support."
                    ),
                ))

        return {
            "risks": risks,
            "total": len(risks),
            "info_count": len(risks),
        }
