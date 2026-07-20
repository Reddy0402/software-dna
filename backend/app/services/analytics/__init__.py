"""
Analytics Rule Registry & Package Init
=======================================
Central registry for all analytics rules. Rules auto-register
via the @register_rule decorator.
"""
from typing import List, Type, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from app.services.analytics_engine import AnalyticsRule

# Global rule registry
_RULE_REGISTRY: Dict[str, Type["AnalyticsRule"]] = {}


def register_rule(cls: Type["AnalyticsRule"]) -> Type["AnalyticsRule"]:
    """Class decorator that registers an analytics rule."""
    _RULE_REGISTRY[cls.rule_id] = cls
    return cls


def get_all_rule_classes() -> List[Type["AnalyticsRule"]]:
    """Return all registered rule classes."""
    return list(_RULE_REGISTRY.values())


def get_rule_classes_by_category(category: str) -> List[Type["AnalyticsRule"]]:
    """Return rule classes matching the given category."""
    return [r for r in _RULE_REGISTRY.values() if r.category == category]


# Import rule modules to trigger registration
# These must be imported AFTER the registry is defined
from app.services.analytics import health_rules as _health  # noqa: F401, E402
from app.services.analytics import complexity_rules as _complexity  # noqa: F401, E402
from app.services.analytics import dependency_rules as _deps  # noqa: F401, E402
from app.services.analytics import hotspot_rules as _hotspots  # noqa: F401, E402
