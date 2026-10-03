"""Standard Lifespan — the general case, and the only Experiment Type.

A DLife census workbook of chambers scored to death: assumed censoring on, the
full survivorship battery, demographic-rate figures included because a lifespan
cohort dies slowly enough for them to mean something. Every analysis the app can
do is reachable from it; the **Factorial Battery** is offered whenever the
active Focus varies two or more factors, gated by Focus Shape rather than by
type (ADR-0011, which retired the Interaction Experiment type).
"""

from __future__ import annotations

from .base import ALL_PLOT_DEFS, ExperimentType, PlotDef, ReportSection

_BY_ID = {p.id: p for p in ALL_PLOT_DEFS}


class StandardLifespanType(ExperimentType):
    key = "standard_lifespan"
    label = "Standard Lifespan"
    description = (
        "A census-scored lifespan cohort (DLife workbook): chambers of "
        "individuals scored to death, with unaccounted individuals treated as "
        "censored."
    )

    default_global = {
        "time_unit": "days",
        "time_label": "Age (days)",
        "assume_censored": True,
        "min_n_per_chamber": 5,
    }

    ## Every series figure the app draws is here, the raw hazard and the
    ## cumulative deaths included: a figure outside the Plot Set had no
    ## checkbox, and an `omit:` naming it was accepted and meant nothing.
    plot_set = (
        _BY_ID["km_risk_table"],
        _BY_ID["km_curves"],
        _BY_ID["cumulative_events"],
        _BY_ID["survival_distribution"],
        _BY_ID["mortality"],
        _BY_ID["hazard"],
        _BY_ID["smoothed_hazard"],
        _BY_ID["nelson_aalen"],
        _BY_ID["number_at_risk"],
        _BY_ID["hazard_ratio_forest"],
        _BY_ID["log_log"],
    )
    headline_plot_id = "km_risk_table"

    action_keys = (
        "km_curves", "nelson_aalen", "hazard_plot", "mortality", "forest_plot",
        "log_rank_pairwise", "log_rank_omnibus", "gehan_wilcoxon",
        "parametric_aft", "cox_ph", "rmst",
        # The Factorial Battery — offered to a Focus varying two or more
        # factors, Not Applicable where the populated cells cannot support
        # it (the Action declares the requirement).
        "faceted_km", "interaction_plot", "cox_interaction", "rmst_interaction",
    )

    def report_intro(self) -> str | None:
        return (
            "Survivorship of a census-scored lifespan cohort. Curves are "
            "Kaplan-Meier estimates over individuals; individuals unaccounted "
            "for at the final census are right-censored unless that policy is "
            "switched off in the experiment's configuration."
        )

    def validate_config(self, config: dict) -> list[str]:
        problems = super().validate_config(config)
        g = config.get("global") or {}
        min_n = g.get("min_n_per_chamber")
        if min_n is not None:
            if not isinstance(min_n, int) or isinstance(min_n, bool) or min_n < 0:
                problems.append(
                    "`global.min_n_per_chamber` must be a non-negative integer "
                    "(0 turns the check off)."
                )
        return problems

    def report_sections(self) -> tuple[ReportSection, ...]:
        return (
            ReportSection("focus", "Focus"),
            ReportSection("summary", "Experiment summary"),
            ReportSection("figures", "Survivorship figures"),
            ReportSection("interaction", "Factorial analysis"),
            ReportSection("lifespan", "Lifespan statistics"),
            ReportSection("tests", "Survival comparisons"),
            ReportSection("quality", "Data quality"),
        )

    def ai_summary_prompt(self) -> str:
        return (
            "Summarize this lifespan experiment for a research audience. State "
            "the median and mean lifespan per treatment, describe how the "
            "survival curves differ, and report which log-rank comparisons "
            "reached significance. If a factorial model is given, state the "
            "main effect of each factor and whether the interaction term was "
            "significant; its coefficients are relative to each factor's "
            "reference level. Summarize only the numbers given to you — never "
            "compute, infer, or speculate beyond them."
        )
