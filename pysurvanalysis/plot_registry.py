"""Plot-id → builder registry.

An Experiment Type declares its **Plot Set** as ids (see
:mod:`pysurvanalysis.experiment_types.base`); this module is the only place
that knows what an id draws. Keeping the mapping here means a type can be
imported — and validated — without matplotlib, and adding a figure to a type is
one tuple entry rather than a pipeline edit.

Every builder takes the :class:`~pysurvanalysis.pipeline.AnalysisResult` and
returns a matplotlib Figure, drawn with the run's time label and its Focus's
order, display names and colours (:func:`figure_options`). When the slice
cannot support a figure — too few treatments for a forest plot, a Focus that
does not cross two factors — the builder raises
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


def figure_options(experiment=None, focus=None) -> dict:
    """The keywords every :mod:`plotting` figure takes from its context: the
    Experiment Type's time label, and the Focus's colours and display names.

    One function so the Plot Set, the Defined Plots and the script actions
    (``figure_options(ctx.experiment, ctx.focus)``) draw a Focus the same
    way. With no experiment the label is the direct-mode default.
    """
    if experiment is not None:
        time_label = experiment.type.resolve_time_label(experiment.config)
    else:
        time_label = "Age (hours)"
    return {
        "time_label": time_label,
        "colours": dict(getattr(focus, "colours", None) or {}),
        "display_names": dict(getattr(focus, "display_names", None) or {}),
    }


def _options(result) -> dict:
    return figure_options(getattr(result, "experiment", None),
                          getattr(result, "focus", None))


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
    return plotting.plot_km_curves(result.lifetables, **_options(result))


def _km_risk(result):
    return plotting.plot_km_with_risk_table(result.lifetables, **_options(result))


def _forest(result):
    if result.hazard_ratios is None or len(result.hazard_ratios) == 0:
        from .domain.focus import NotApplicable

        raise NotApplicable("fewer than two treatments to compare")
    return plotting.plot_hazard_ratio_forest(
        result.hazard_ratios, display_names=_options(result)["display_names"])


def _faceted(result):
    return plotting.plot_km_faceted(
        result.lifetables, _focus_levels(result), **_options(result))


def _interaction(result):
    return plotting.plot_lifespan_interaction(
        result.individual_data, _focus_levels(result), **_options(result))


def _smoothed(result):
    ## The shared bandwidth, named rather than left to the default, so the
    ## Plot Set figure is visibly the one the Publication Figure and the
    ## script action also draw.
    return plotting.plot_smoothed_hazard(
        result.lifetables, sigma=plotting.SMOOTHED_HAZARD_SIGMA, **_options(result))


def _lifetable_figure(draw: Callable) -> Callable:
    return lambda result: draw(result.lifetables, **_options(result))


_BUILDERS: dict[str, tuple[str, Callable]] = {
    "km_curves":             ("kaplan_meier.png", _km),
    "km_risk_table":         ("km_with_risk_table.png", _km_risk),
    "nelson_aalen":          ("nelson_aalen.png",
                              _lifetable_figure(plotting.plot_nelson_aalen)),
    "log_log":               ("log_log_diagnostic.png",
                              _lifetable_figure(plotting.plot_log_log)),
    "cumulative_events":     ("cumulative_events.png",
                              _lifetable_figure(plotting.plot_cumulative_events)),
    "hazard":                ("hazard_rate.png",
                              _lifetable_figure(plotting.plot_hazard)),
    "smoothed_hazard":       ("smoothed_hazard.png", _smoothed),
    "mortality":             ("mortality_qx.png",
                              _lifetable_figure(plotting.plot_mortality)),
    "number_at_risk":        ("number_at_risk.png",
                              _lifetable_figure(plotting.plot_number_at_risk)),
    "survival_distribution": ("survival_distribution.png",
                              lambda r: plotting.plot_survival_distribution(
                                  r.individual_data, **_options(r))),
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
