"""Plot-id → builder registry.

An Experiment Type declares its **Plot Set** as ids (see
:mod:`pysurvanalysis.experiment_types.base`); this module is the only place
that knows what an id draws. Keeping the mapping here means a type can be
imported — and validated — without matplotlib, and adding a figure to a type is
one tuple entry rather than a pipeline edit.

Every builder takes the :class:`~pysurvanalysis.pipeline.AnalysisResult` and
returns a matplotlib Figure. When the slice cannot support a figure — too few
treatments for a forest plot, a Focus that is not a 2×2 — the builder raises
:class:`~pysurvanalysis.domain.focus.NotApplicable` with the reason, and the
run records it where the reader will see it: one fewer figure is a fact to
state, not a gap to leave.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from . import plotting
from .experiment_types.base import ALL_PLOT_DEFS


@dataclass(frozen=True)
class PlotBuilder:
    id: str
    label: str
    filename: str
    build: Callable
    caption: str = ""


def _time_label(result) -> str:
    exp = getattr(result, "experiment", None)
    if exp is not None:
        return exp.type.resolve_time_label(exp.config)
    return "Age (hours)"


def _focus_levels(result) -> dict[str, list]:
    """The run's varying factors and their levels, in display order — what a
    figure crossing factors draws. Raises NotApplicable unless the Focus
    varies two or more factors and populates two or more treatments."""
    from .domain.focus import FACTORIAL_PLOT, NotApplicable

    focus, shape = getattr(result, "focus", None), getattr(result, "focus_shape", None)
    if focus is None or shape is None:
        raise NotApplicable("no Focus to cross")
    ok, reason = shape.admits(FACTORIAL_PLOT)
    if not ok:
        raise NotApplicable(reason)
    return {f: list(focus.factors[f]) for f in focus.varying_factors}


def _km(result):
    return plotting.plot_km_curves(result.lifetables)


def _km_risk(result):
    return plotting.plot_km_with_risk_table(result.lifetables)


def _forest(result):
    if result.hazard_ratios is None or len(result.hazard_ratios) == 0:
        from .domain.focus import NotApplicable

        raise NotApplicable("fewer than two treatments to compare")
    return plotting.plot_hazard_ratio_forest(result.hazard_ratios)


def _faceted(result):
    return plotting.plot_km_faceted(
        result.lifetables, _focus_levels(result), time_label=_time_label(result),
    )


def _interaction(result):
    return plotting.plot_lifespan_interaction(
        result.individual_data, _focus_levels(result), time_label=_time_label(result),
    )


_BUILDERS: dict[str, tuple[str, Callable]] = {
    "km_curves":             ("kaplan_meier.png", _km),
    "km_risk_table":         ("km_with_risk_table.png", _km_risk),
    "nelson_aalen":          ("nelson_aalen.png",
                              lambda r: plotting.plot_nelson_aalen(r.lifetables)),
    "log_log":               ("log_log_diagnostic.png",
                              lambda r: plotting.plot_log_log(r.lifetables)),
    "cumulative_events":     ("cumulative_events.png",
                              lambda r: plotting.plot_cumulative_events(r.lifetables)),
    "hazard":                ("hazard_rate.png",
                              lambda r: plotting.plot_hazard(r.lifetables)),
    "smoothed_hazard":       ("smoothed_hazard.png",
                              lambda r: plotting.plot_smoothed_hazard(r.lifetables)),
    "mortality":             ("mortality_qx.png",
                              lambda r: plotting.plot_mortality(r.lifetables)),
    "number_at_risk":        ("number_at_risk.png",
                              lambda r: plotting.plot_number_at_risk(r.lifetables)),
    "survival_distribution": ("survival_distribution.png",
                              lambda r: plotting.plot_survival_distribution(
                                  r.individual_data)),
    "hazard_ratio_forest":   ("hazard_ratio_forest.png", _forest),
    "km_faceted":            ("km_faceted.png", _faceted),
    "interaction_lifespan":  ("interaction_lifespan.png", _interaction),
}

PLOTS: dict[str, PlotBuilder] = {
    d.id: PlotBuilder(d.id, d.label, _BUILDERS[d.id][0], _BUILDERS[d.id][1], d.caption)
    for d in ALL_PLOT_DEFS if d.id in _BUILDERS
}


def available() -> list[str]:
    """Every known plot id, in the order the general battery reports them."""
    return [d.id for d in ALL_PLOT_DEFS if d.id in PLOTS]


def get(plot_id: str) -> PlotBuilder:
    try:
        return PLOTS[plot_id]
    except KeyError:
        raise KeyError(
            f"Unknown plot id {plot_id!r}. Known ids: {', '.join(available())}."
        ) from None


def build(plot_id: str, result):
    """Build one figure; raises NotApplicable when the slice cannot support it."""
    return get(plot_id).build(result)
