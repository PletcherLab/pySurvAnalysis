"""Experiment Types — a description of the **data source**.

An Experiment Type says what kind of file an experiment reads and how: the
expected input shape, the time unit and axis label, the censoring policy, the
default quality criteria and the report sections, plus the actions it
contributes to the Hub and the script registry (ADR-0002). It deliberately
says nothing about the experimental *design*: one data file may hold several
designs, so which analyses and figures apply is decided by the active
**Focus Shape** (ADR-0011). The 2×2 figures, for instance, are not a type's
Plot Set — they are added to any run whose Focus is a populated 2×2.

A type also declares its **Analysis Set** — the optional analyses a run may
perform — and a run leaves out whichever of either set the config's ``omit:``
block names (ADR-0012).

A type declares its Plot Set as plain ids; :mod:`pysurvanalysis.plot_registry`
maps those ids to builders, so this module stays free of matplotlib and can be
imported by config validation and tests without the analysis stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class PlotDef:
    """One entry in a Plot Set: a registry id plus how to present it.

    ``requires`` names the Requirement the figure needs from its Focus
    (``"comparison"``, ``"factorial_plot"``): a figure whose requirement is
    not *relevant* to the Focus is not part of its Plot Set at all; one that
    is relevant but not computable from the data is Not Applicable.
    """

    id: str
    label: str
    caption: str = ""
    requires: str | None = None
    #: Analysis ids the figure draws from. Leaving one out of a run leaves
    #: the figure out too — a forest with no hazard ratios has nothing to plot.
    needs: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnalysisDef:
    """One entry in an **Analysis Set**: an optional analysis a run performs.

    The survivorship core — lifetables, summaries, median and mean survival —
    is not in it: every figure and every report section stands on that core,
    so it always runs. ``requires`` works as it does for a :class:`PlotDef`.
    """

    id: str
    label: str
    caption: str = ""
    requires: str | None = None


#: Every optional analysis, in report order. The ids are what the config's
#: ``omit: analyses:`` names.
ALL_ANALYSIS_DEFS: tuple[AnalysisDef, ...] = (
    AnalysisDef("logrank_pairwise", "Log-rank pairwise",
                "Mantel-Cox log-rank test for every treatment pair.",
                requires="comparison"),
    AnalysisDef("logrank_omnibus", "Log-rank omnibus",
                "K-sample log-rank test across all treatments.",
                requires="comparison"),
    AnalysisDef("gehan_wilcoxon", "Gehan-Wilcoxon pairwise",
                "Wilcoxon-weighted log-rank for every pair — weights early "
                "deaths more heavily.",
                requires="comparison"),
    AnalysisDef("hazard_ratios", "Pairwise hazard ratios",
                "A Cox hazard ratio with 95% CI for every pair; the "
                "hazard-ratio forest draws these.",
                requires="comparison"),
    AnalysisDef("parametric_aft", "Parametric AFT models",
                "Weibull, log-normal and log-logistic accelerated-failure-time "
                "fits."),
    AnalysisDef("interaction", "Interaction analyses",
                "The Factorial Battery: the Cox factorial model (main effects "
                "vs pairwise interactions, LR test, Schoenfeld PH check) and "
                "its RMST companion, relative to the Focus's Reference Levels.",
                requires="factorial_model"),
)


@dataclass(frozen=True)
class ReportSection:
    """One section of a type's report: a title and the block-builder key."""

    key: str
    title: str


class ExperimentType:
    """Base class for an Experiment Type (a data source)."""

    key: str = "base"
    label: str = "Experiment"
    description: str = ""

    #: Default ``global:`` values a scaffolded config starts from.
    default_global: dict[str, Any] = {
        "time_unit": "hours",
        "time_label": "Age (hours)",
        "assume_censored": True,
    }

    #: The base Plot Set — what every Focus gets. Shape-gated figures are
    #: added by :meth:`plot_set_for`.
    plot_set: tuple[PlotDef, ...] = ()

    #: The optional analyses a run may perform; :meth:`analysis_set_for`
    #: keeps those relevant to a Focus.
    analysis_set: tuple[AnalysisDef, ...] = ALL_ANALYSIS_DEFS

    #: The one figure that states a Focus's primary result when its shape
    #: names no other; leads the report and is the Plot Editor's default.
    headline_plot_id: str | None = None

    #: Keys of pooled actions this type re-exports into its registry.
    action_keys: tuple[str, ...] = ()

    # ── identity ───────────────────────────────────────────────────────────

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<ExperimentType {self.key}>"

    # ── configuration ──────────────────────────────────────────────────────

    def scaffold_config(self, minimal: bool = False) -> dict:
        """A fresh ``survival_config.yaml`` body for this type.

        ``minimal=True`` omits everything a Project's ``defaults:`` already
        supplies. A member scaffolded from a Project must stay minimal, or it
        freezes today's defaults into its own config and later edits to the
        Project stop reaching it.
        """
        cfg: dict[str, Any] = {} if minimal else {"global": dict(self.default_global)}
        return {"experiment_type": self.key, **cfg}

    def owned_keys(self) -> set[str]:
        """``global:`` keys this type defines defaults for."""
        return set(self.default_global)

    def validate_config(self, config: dict) -> list[str]:
        """Return a list of human-readable problems with *config* (empty = ok)."""
        problems: list[str] = []
        g = config.get("global") or {}
        if not isinstance(g, dict):
            return ["`global:` must be a mapping."]
        unit = g.get("time_unit")
        if unit is not None and not isinstance(unit, str):
            problems.append("`global.time_unit` must be a string (e.g. days).")
        ac = g.get("assume_censored")
        if ac is not None and not isinstance(ac, bool):
            problems.append("`global.assume_censored` must be true or false.")
        return problems

    # ── presentation ───────────────────────────────────────────────────────

    def resolve_time_label(self, config: dict) -> str:
        g = config.get("global") or {}
        label = g.get("time_label")
        if label:
            return str(label)
        unit = g.get("time_unit") or self.default_global.get("time_unit", "hours")
        return f"Age ({unit})"

    def resolve_assume_censored(self, config: dict) -> bool:
        g = config.get("global") or {}
        value = g.get("assume_censored")
        if value is None:
            value = self.default_global.get("assume_censored", True)
        return bool(value)

    def plot_ids(self) -> tuple[str, ...]:
        """The base Plot Set's ids, in order."""
        return tuple(p.id for p in self.plot_set)

    def plot_set_for(self, shape=None) -> tuple[PlotDef, ...]:
        """The Plot Set a run under a Focus of *shape* produces: the base set
        plus every shape-gated figure the shape admits.

        The Plot Set is a property of the run — type plus Focus — not of the
        directory.
        """
        if shape is None:
            return tuple(self.plot_set)
        out = [p for p in self.plot_set if shape.relevant(p.requires)[0]]
        for plot in SHAPE_GATED_PLOT_DEFS:
            if plot not in out and plot not in self.plot_set \
                    and shape.relevant(plot.requires)[0]:
                out.append(plot)
        return tuple(out)

    def analysis_set_for(self, shape=None) -> tuple[AnalysisDef, ...]:
        """The optional analyses a run under a Focus of *shape* is offered:
        those whose Requirement the Focus's definition makes relevant. A
        one-factor Focus is not offered the interaction analyses at all."""
        if shape is None:
            return tuple(self.analysis_set)
        return tuple(a for a in self.analysis_set if shape.relevant(a.requires)[0])

    def plots_not_offered(self, shape) -> tuple[PlotDef, ...]:
        """Figures this type draws that a Focus of *shape* is not offered —
        what the Hub names in its quiet "not offered" line."""
        offered = self.plot_set_for(shape)
        return tuple(p for p in (*self.plot_set, *SHAPE_GATED_PLOT_DEFS)
                     if p not in offered)

    def headline_for(self, shape=None) -> str | None:
        """The Headline Figure for a Focus of *shape*: the faceted KM when the
        Focus crosses factors and the data can draw it, the type's own
        headline otherwise."""
        if shape is not None and shape.admits("factorial_plot")[0]:
            return "km_faceted"
        return self.headline_plot_id

    def report_title(self, experiment_name: str) -> str:
        return f"{experiment_name} — Survival Analysis"

    def report_intro(self) -> str | None:
        return None

    def report_sections(self) -> tuple[ReportSection, ...]:
        """Ordered sections the report builder walks for this type."""
        return (
            ReportSection("focus", "Focus"),
            ReportSection("summary", "Experiment summary"),
            ReportSection("figures", "Figures"),
            ReportSection("interaction", "Factorial analysis"),
            ReportSection("lifespan", "Lifespan statistics"),
            ReportSection("tests", "Statistical tests"),
        )

    def ai_summary_prompt(self) -> str:
        return (
            "Summarize this survival analysis for a research audience. Describe "
            "what was measured, the survival differences between treatments, and "
            "which statistical comparisons reached significance. Summarize only "
            "the numbers given to you — never compute, infer, or speculate "
            "beyond them."
        )

    # ── contributed actions ────────────────────────────────────────────────

    def extra_actions(self) -> tuple:
        """Type Actions defined by this type (beyond the shared pool)."""
        return ()


#: Every plot id the general battery knows, in report order. A type's base
#: Plot Set names a subset; the shape-gated ones are added per Focus.
ALL_PLOT_DEFS: tuple[PlotDef, ...] = (
    PlotDef("km_curves", "Kaplan-Meier curves", "Survivorship by treatment."),
    PlotDef("km_risk_table", "KM curves with at-risk table",
            "Survivorship with the number at risk beneath the axis."),
    PlotDef("nelson_aalen", "Nelson-Aalen cumulative hazard",
            "Cumulative hazard by treatment."),
    PlotDef("log_log", "Log-log diagnostic",
            "Parallel lines support the proportional-hazards assumption.",
            requires="comparison"),
    PlotDef("cumulative_events", "Cumulative deaths", "Cumulative event counts."),
    PlotDef("hazard", "Hazard rate", "Interval hazard rate."),
    PlotDef("smoothed_hazard", "Smoothed hazard", "Kernel-smoothed hazard rate."),
    PlotDef("mortality", "Mortality (qx)", "Interval mortality probability."),
    PlotDef("number_at_risk", "Number at risk", "Individuals at risk over time."),
    PlotDef("survival_distribution", "Lifespan distribution",
            "Distribution of individual lifespans by treatment."),
    PlotDef("hazard_ratio_forest", "Hazard-ratio forest",
            "Pairwise hazard ratios with 95% confidence intervals.",
            requires="comparison", needs=("hazard_ratios",)),
    PlotDef("km_faceted", "Faceted Kaplan-Meier",
            "One panel per level of the first varying factor, curves coloured "
            "by the others.",
            requires="factorial_plot"),
    PlotDef("interaction_lifespan", "Lifespan interaction plot",
            "Median lifespan by factor level; non-parallel lines indicate interaction.",
            requires="factorial_plot"),
)

#: The figures a Focus earns by crossing factors — never in a type's base
#: Plot Set, added to a run's when the Focus makes them relevant.
SHAPE_GATED_PLOT_DEFS: tuple[PlotDef, ...] = tuple(
    p for p in ALL_PLOT_DEFS if p.requires == "factorial_plot")
