"""
Complexity Rules — Complexity Analysis Module
==============================================
Rules that identify code smells related to size, structure, and dependency
concentration. Each issue is ranked by severity.
"""
from typing import Any, Dict, List

from app.services.analytics_engine import AnalyticsContext, AnalyticsRule
from app.services.analytics import register_rule


# ---------------------------------------------------------------
# Severity helpers
# ---------------------------------------------------------------

def _severity(value: float, warning_threshold: float, critical_threshold: float) -> str:
    if value >= critical_threshold:
        return "critical"
    if value >= warning_threshold:
        return "warning"
    return "info"


def _entity_line_count(entity) -> int:
    if entity.start_line is not None and entity.end_line is not None:
        return max(entity.end_line - entity.start_line + 1, 1)
    return 0


# ---------------------------------------------------------------
# Rules
# ---------------------------------------------------------------

@register_rule
class LargeFileRule(AnalyticsRule):
    rule_id = "complexity.large_files"
    category = "complexity"
    display_name = "Large Files"
    description = "Files exceeding a configurable line threshold."

    WARNING_THRESHOLD = 300
    CRITICAL_THRESHOLD = 500

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        for f in ctx.files:
            # Estimate file size from entities or size_bytes
            file_entities = ctx.entities_by_file.get(f.id, [])
            if not file_entities:
                continue

            max_line = max(
                (e.end_line for e in file_entities if e.end_line is not None),
                default=0,
            )
            if max_line <= 0:
                continue

            sev = _severity(max_line, self.WARNING_THRESHOLD, self.CRITICAL_THRESHOLD)
            if sev == "info":
                continue

            issues.append({
                "entity_id": str(f.id),
                "entity_name": f.filename,
                "entity_type": "file",
                "file_path": f.relative_path,
                "metric_value": max_line,
                "threshold": self.WARNING_THRESHOLD,
                "severity": sev,
                "issue_type": "large_file",
                "description": f"File has ~{max_line} lines (threshold: {self.WARNING_THRESHOLD})",
            })

        issues.sort(key=lambda x: x["metric_value"], reverse=True)
        return {
            "issues": issues,
            "total": len(issues),
            "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
        }


@register_rule
class OversizedClassRule(AnalyticsRule):
    rule_id = "complexity.oversized_classes"
    category = "complexity"
    display_name = "Oversized Classes"
    description = "Classes exceeding the line threshold."

    WARNING_THRESHOLD = 200
    CRITICAL_THRESHOLD = 400

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        classes = ctx.entities_by_type.get("class", [])

        for e in classes:
            lc = _entity_line_count(e)
            if lc == 0:
                continue

            sev = _severity(lc, self.WARNING_THRESHOLD, self.CRITICAL_THRESHOLD)
            if sev == "info":
                continue

            f = ctx.files_by_id.get(e.file_id)
            issues.append({
                "entity_id": str(e.id),
                "entity_name": e.name,
                "entity_type": "class",
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "metric_value": lc,
                "threshold": self.WARNING_THRESHOLD,
                "severity": sev,
                "issue_type": "oversized_class",
                "description": f"Class '{e.name}' has {lc} lines (threshold: {self.WARNING_THRESHOLD})",
            })

        issues.sort(key=lambda x: x["metric_value"], reverse=True)
        return {
            "issues": issues,
            "total": len(issues),
            "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
        }


@register_rule
class LongMethodRule(AnalyticsRule):
    rule_id = "complexity.long_methods"
    category = "complexity"
    display_name = "Long Methods"
    description = "Methods/functions exceeding the line threshold."

    WARNING_THRESHOLD = 30
    CRITICAL_THRESHOLD = 60

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        callable_types = ("method", "function", "constructor")

        for e in ctx.entities:
            if e.entity_type not in callable_types:
                continue

            lc = _entity_line_count(e)
            if lc == 0:
                continue

            sev = _severity(lc, self.WARNING_THRESHOLD, self.CRITICAL_THRESHOLD)
            if sev == "info":
                continue

            f = ctx.files_by_id.get(e.file_id)
            issues.append({
                "entity_id": str(e.id),
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "metric_value": lc,
                "threshold": self.WARNING_THRESHOLD,
                "severity": sev,
                "issue_type": "long_method",
                "description": f"'{e.name}' has {lc} lines (threshold: {self.WARNING_THRESHOLD})",
            })

        issues.sort(key=lambda x: x["metric_value"], reverse=True)
        return {
            "issues": issues,
            "total": len(issues),
            "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
        }


@register_rule
class HighParameterCountRule(AnalyticsRule):
    rule_id = "complexity.high_parameters"
    category = "complexity"
    display_name = "High Parameter Count"
    description = "Functions/methods with excessive parameter counts."

    WARNING_THRESHOLD = 4
    CRITICAL_THRESHOLD = 7

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        callable_types = ("method", "function", "constructor")

        for e in ctx.entities:
            if e.entity_type not in callable_types:
                continue

            # Parameter count from meta_data
            meta = e.meta_data or {}
            param_count = 0
            if "parameters" in meta:
                params = meta["parameters"]
                if isinstance(params, list):
                    param_count = len(params)
                elif isinstance(params, int):
                    param_count = params
            elif "param_count" in meta:
                param_count = meta["param_count"]

            if param_count == 0:
                continue

            sev = _severity(param_count, self.WARNING_THRESHOLD, self.CRITICAL_THRESHOLD)
            if sev == "info":
                continue

            f = ctx.files_by_id.get(e.file_id)
            issues.append({
                "entity_id": str(e.id),
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "metric_value": param_count,
                "threshold": self.WARNING_THRESHOLD,
                "severity": sev,
                "issue_type": "high_parameters",
                "description": f"'{e.name}' has {param_count} parameters (threshold: {self.WARNING_THRESHOLD})",
            })

        issues.sort(key=lambda x: x["metric_value"], reverse=True)
        return {
            "issues": issues,
            "total": len(issues),
            "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
        }


@register_rule
class DependencyConcentrationRule(AnalyticsRule):
    rule_id = "complexity.dependency_concentration"
    category = "complexity"
    display_name = "Dependency Concentration"
    description = "Entities with disproportionately high dependency count."

    WARNING_THRESHOLD = 10
    CRITICAL_THRESHOLD = 20

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []

        for e in ctx.entities:
            outgoing = len(ctx.deps_by_source.get(e.id, []))
            incoming = len(ctx.deps_by_target.get(e.id, []))
            total = outgoing + incoming

            sev = _severity(total, self.WARNING_THRESHOLD, self.CRITICAL_THRESHOLD)
            if sev == "info":
                continue

            f = ctx.files_by_id.get(e.file_id)
            issues.append({
                "entity_id": str(e.id),
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "metric_value": total,
                "incoming": incoming,
                "outgoing": outgoing,
                "threshold": self.WARNING_THRESHOLD,
                "severity": sev,
                "issue_type": "dependency_concentration",
                "description": (
                    f"'{e.name}' has {total} dependencies "
                    f"({incoming} in, {outgoing} out; threshold: {self.WARNING_THRESHOLD})"
                ),
            })

        issues.sort(key=lambda x: x["metric_value"], reverse=True)
        return {
            "issues": issues,
            "total": len(issues),
            "critical_count": sum(1 for i in issues if i["severity"] == "critical"),
            "warning_count": sum(1 for i in issues if i["severity"] == "warning"),
        }


@register_rule
class DuplicateStructureRule(AnalyticsRule):
    rule_id = "complexity.duplicate_structures"
    category = "complexity"
    display_name = "Duplicate Structures"
    description = "Classes/modules with identical child-entity compositions."

    def compute(self, ctx: AnalyticsContext) -> Dict[str, Any]:
        # Group classes by their child entity signature
        container_types = ("class", "module", "struct", "namespace")
        signatures: Dict[str, List[Dict[str, Any]]] = {}

        for e in ctx.entities:
            if e.entity_type not in container_types:
                continue

            # Build child signature: sorted list of (child_type, child_name)
            children = [
                c for c in ctx.entities
                if c.parent_id == e.id
            ]
            if len(children) < 2:
                continue

            sig = tuple(sorted((c.entity_type, c.name) for c in children))
            sig_key = str(sig)

            f = ctx.files_by_id.get(e.file_id)
            signatures.setdefault(sig_key, []).append({
                "entity_id": str(e.id),
                "entity_name": e.name,
                "entity_type": e.entity_type,
                "fqn": e.fully_qualified_name,
                "file_path": f.relative_path if f else "",
                "child_count": len(children),
            })

        # Filter to only groups with duplicates
        issues: List[Dict[str, Any]] = []
        for sig_key, group in signatures.items():
            if len(group) < 2:
                continue
            issues.append({
                "duplicate_count": len(group),
                "severity": "warning" if len(group) < 4 else "critical",
                "issue_type": "duplicate_structure",
                "entities": group,
                "description": f"{len(group)} entities share identical structural composition",
            })

        issues.sort(key=lambda x: x["duplicate_count"], reverse=True)
        return {
            "issues": issues,
            "total_groups": len(issues),
            "total_duplicated_entities": sum(i["duplicate_count"] for i in issues),
        }
