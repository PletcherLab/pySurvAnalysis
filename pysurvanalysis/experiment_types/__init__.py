"""Experiment Type registry.

``experiment_type`` in ``survival_config.yaml`` names one of these by key. There
is one: **Standard Lifespan**, the general case. A config with no key is a
Standard Lifespan, and so is one naming a retired type — ``interaction`` (whose
2×2 analyses are now the Factorial Battery, gated by Focus Shape) or ``custom``
(the absence of a type, which no longer exists as a separate thing). Both
retirements are ADR-0011's.
"""

from __future__ import annotations

from .base import (ALL_PLOT_DEFS, SHAPE_GATED_PLOT_DEFS, ExperimentType, PlotDef,
                   ReportSection)
from .standard import StandardLifespanType

STANDARD = StandardLifespanType()

_TYPES: dict[str, ExperimentType] = {
    StandardLifespanType.key: STANDARD,
}

#: Keys a config may still carry from before ADR-0011. They resolve to the
#: general case; the config is rewritten the next time it is saved.
RETIRED_KEYS: frozenset[str] = frozenset({"interaction", "custom"})


def available_types() -> list[ExperimentType]:
    """Selectable types."""
    return [_TYPES[k] for k in sorted(_TYPES)]


def type_keys() -> list[str]:
    return sorted(_TYPES)


def is_retired(key) -> bool:
    return key is not None and str(key).strip().lower() in RETIRED_KEYS


def get_type(key: str | None) -> ExperimentType:
    """Resolve a type key. ``None``/empty, or a retired key → Standard Lifespan.

    An unknown key is an error rather than a silent fallback: a config naming
    a type this build doesn't have must not be analysed as though it were
    something else.
    """
    if key is None or str(key).strip() == "" or is_retired(key):
        return STANDARD
    try:
        return _TYPES[str(key).strip().lower()]
    except KeyError:
        raise ValueError(
            f"Unknown experiment_type {key!r}. Known types: "
            f"{', '.join(sorted(_TYPES))}, or omit the key."
        ) from None


def type_for_config(config: dict) -> ExperimentType:
    """The Experiment Type a ``survival_config.yaml`` body selects."""
    return get_type((config or {}).get("experiment_type"))


__all__ = [
    "ALL_PLOT_DEFS",
    "ExperimentType",
    "PlotDef",
    "RETIRED_KEYS",
    "ReportSection",
    "SHAPE_GATED_PLOT_DEFS",
    "STANDARD",
    "StandardLifespanType",
    "available_types",
    "get_type",
    "is_retired",
    "type_for_config",
    "type_keys",
]
