"""Plotting functions for survival analysis.

All plot functions return a matplotlib Figure so callers can save, embed in
a UI, or display interactively.

Every figure draws its treatments in **display order** — the Focus's order
(``statistics.treatment_order``), never alphabetical — and takes the Focus's
look through two optional keywords: ``colours`` (label → colour) and
``display_names`` (label → legend text). A treatment the Focus gives no
colour takes the cycle by its position in that order, so it keeps one colour
in every figure, a Defined Plot drawing only some of the treatments
included. Every figure with a time axis takes ``time_label`` (None keeps the
function's old default text); callers pass the Experiment Type's resolved
label, so an axis says "Age (days)" when the data is in days.
"""

from __future__ import annotations

from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np
import pandas as pd
from scipy.ndimage import gaussian_filter1d

# Consistent color cycle for treatments
COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
    "#9467bd", "#8c564b", "#e377c2", "#7f7f7f",
    "#bcbd22", "#17becf", "#aec7e8", "#ffbb78",
]

#: The smoothed hazard's Gaussian bandwidth, in lifetable rows. One constant
#: for the Plot Set figure, the Publication Figure and the script action, so
#: the three draw the same estimate unless somebody deliberately asks for
#: another.
SMOOTHED_HAZARD_SIGMA = 3.0

#: Where the at-risk counts are printed by default, as fractions of the last
#: observed age — shared by the matplotlib table and the publication At-Risk
#: Band so the two print the same numbers at the same ages.
RISK_TIME_FRACTIONS = (0.0, 0.25, 0.5, 0.75, 1.0)


def _treatment_order(frame: pd.DataFrame) -> list[str]:
    """The frame's treatments in display order (the Focus's)."""
    from .statistics import treatment_order

    return [str(t) for t in treatment_order(frame)]


def _treatment_colors(treatments: list[str],
                      colours: Optional[dict] = None) -> dict[str, str]:
    """A colour per treatment: the Focus's own where it names one, else the
    cycle by position in *treatments* — the full display order, so a figure
    drawing a subset still gives each treatment the colour it has elsewhere."""
    colours = colours or {}
    return {str(t): colours.get(str(t)) or COLORS[i % len(COLORS)]
            for i, t in enumerate(treatments)}


def _name(label, display_names: Optional[dict]) -> str:
    """The legend text for a curve: the Focus's display name, else the label."""
    return (display_names or {}).get(str(label), str(label))


def _rows(frame: pd.DataFrame, treatment) -> pd.DataFrame:
    """One treatment's rows, compared as text so a categorical, string or
    numeric ``treatment`` column all select the same way."""
    return frame[frame["treatment"].astype(str) == str(treatment)]


def _setup(frame: pd.DataFrame, treatments, colours):
    """``(treatments to draw, colour map)``: the given list in its own order,
    else every treatment in display order; colours from the full order."""
    order = _treatment_order(frame)
    drawn = [str(t) for t in treatments] if treatments is not None else order
    return drawn, _treatment_colors(order + [t for t in drawn if t not in order],
                                    colours)


def default_risk_times(t_max: float) -> list[float]:
    """The default at-risk times: 0, 25, 50, 75 and 100% of the last age."""
    return [float(t_max) * f for f in RISK_TIME_FRACTIONS]


def at_risk_counts(times, n_at_risk, at) -> list[int]:
    """The number at risk at each age in *at*, from one curve's knots.

    At risk at age t means a recorded time of t or later — alive and
    uncensored entering t — which is the n_at_risk of the first knot at or
    after t (the starting group size before the first; 0 after the last).
    Read off the lifetable rather than recomputed, so a table can never
    disagree with the curve above it. *times* must be sorted.
    """
    times = np.asarray(times, dtype=float)
    counts = np.asarray(n_at_risk)
    out: list[int] = []
    for t in at:
        i = int(np.searchsorted(times, float(t), side="left"))
        out.append(int(counts[i]) if i < len(times) else 0)
    return out


def plot_km_curves(
    lifetable: pd.DataFrame,
    title: str = "Kaplan–Meier Survival Curves",
    show_ci: bool = True,
    ax: Optional[plt.Axes] = None,
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot Kaplan-Meier survival curves for all (or selected) treatments.

    Parameters
    ----------
    lifetable : DataFrame from ``lifetable.compute_lifetables()``
    title : plot title
    show_ci : whether to show 95% confidence bands
    ax : optional existing Axes to draw on
    treatments : optional subset of treatments to plot, in the order given
    time_label : x-axis title (None = "Time (hours)")
    colours, display_names : the Focus's per-treatment colours and legend text

    Returns
    -------
    matplotlib Figure
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty:
            continue

        color = colors[treatment]

        # Build step-function coordinates (prepend t=0, lx=1.0)
        times = np.concatenate([[0], grp["time"].values])
        surv = np.concatenate([[1.0], grp["km_lx"].values])

        ax.step(times, surv, where="post", label=_name(treatment, display_names),
                color=color, linewidth=1.5)

        if show_ci:
            ci_lo = np.concatenate([[1.0], grp["km_ci_lo"].values])
            ci_hi = np.concatenate([[1.0], grp["km_ci_hi"].values])
            ax.fill_between(
                times, ci_lo, ci_hi,
                step="post", alpha=0.15, color=color,
            )

        # Add censoring tick marks
        cens = grp[grp["n_censored"] > 0]
        if not cens.empty:
            cens_times = cens["time"].values
            cens_surv = cens["km_lx"].values
            ax.plot(
                cens_times, cens_surv,
                "|", color=color, markersize=8, markeredgewidth=1.5,
            )

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Survival Probability", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_ylim(-0.02, 1.05)
    ax.set_xlim(left=0)
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return fig


def plot_hazard(
    lifetable: pd.DataFrame,
    title: str = "Hazard Rate Over Time",
    ax: Optional[plt.Axes] = None,
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot hazard rate (hx) over time for each treatment."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty:
            continue
        color = colors[treatment]
        ax.plot(
            grp["time"], grp["hx"],
            label=_name(treatment, display_names), color=color, linewidth=1.2,
            marker=".", markersize=3,
        )

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Hazard Rate", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return fig


def plot_mortality(
    lifetable: pd.DataFrame,
    title: str = "Interval Mortality (qx)",
    ax: Optional[plt.Axes] = None,
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot probability of death per interval (qx) over time."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty:
            continue
        color = colors[treatment]
        ax.plot(
            grp["time"], grp["qx"],
            label=_name(treatment, display_names), color=color, linewidth=1.2,
            marker=".", markersize=3,
        )

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Probability of Death (qx)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return fig


def plot_number_at_risk(
    lifetable: pd.DataFrame,
    title: str = "Number at Risk",
    ax: Optional[plt.Axes] = None,
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot the number at risk over time for each treatment."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        # At time 0, n_at_risk equals the first row's value
        n_risk = np.concatenate([[grp["n_at_risk"].iloc[0]], grp["n_at_risk"].values])
        ax.step(times, n_risk, where="post", label=_name(treatment, display_names),
                color=color, linewidth=1.5)

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Number at Risk", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()

    return fig


def plot_km_with_risk_table(
    lifetable: pd.DataFrame,
    title: str = "Kaplan–Meier Curves with Number at Risk",
    show_ci: bool = True,
    treatments: Optional[list[str]] = None,
    risk_times: Optional[list[float]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """KM survival curves with an integrated number-at-risk table below.

    The plot area is divided: upper ~75% for the KM curves, lower ~25% for
    the at-risk table. The table counts exactly as the publication At-Risk
    Band does (:func:`at_risk_counts` — at risk at age t means a recorded
    time of t or later) and, unless *risk_times* names others, at the same
    ages: 0, 25, 50, 75 and 100% of the last observed age.
    """
    treatments, colors = _setup(lifetable, treatments, colours)

    drawn = lifetable[lifetable["treatment"].astype(str).isin(treatments)]
    if risk_times is None:
        risk_times = default_risk_times(drawn["time"].max() if len(drawn) else 0.0)
    risk_times = list(risk_times)

    n_treatments = len(treatments)
    fig = plt.figure(figsize=(12, 7 + 0.35 * n_treatments))
    gs = gridspec.GridSpec(
        2, 1, height_ratios=[3, max(1, n_treatments * 0.35)],
        hspace=0.05,
    )
    ax_km = fig.add_subplot(gs[0])
    ax_risk = fig.add_subplot(gs[1], sharex=ax_km)

    # KM curves
    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        surv = np.concatenate([[1.0], grp["km_lx"].values])
        ax_km.step(times, surv, where="post", label=_name(treatment, display_names),
                   color=color, linewidth=2.0)
        if show_ci:
            ci_lo = np.concatenate([[1.0], grp["km_ci_lo"].values])
            ci_hi = np.concatenate([[1.0], grp["km_ci_hi"].values])
            ax_km.fill_between(times, ci_lo, ci_hi, step="post", alpha=0.12, color=color)
        cens = grp[grp["n_censored"] > 0]
        if not cens.empty:
            ax_km.plot(cens["time"].values, cens["km_lx"].values, "|",
                       color=color, markersize=8, markeredgewidth=1.5)

    ax_km.set_ylabel("Survival Probability", fontsize=12)
    ax_km.set_title(title, fontsize=14)
    ax_km.set_ylim(-0.02, 1.05)
    ax_km.legend(loc="upper right", fontsize=9)
    ax_km.grid(True, alpha=0.25)
    plt.setp(ax_km.get_xticklabels(), visible=False)

    # At-risk table
    ax_risk.set_xlim(ax_km.get_xlim())
    ax_risk.set_yticks(range(n_treatments))
    ax_risk.set_yticklabels([_name(t, display_names) for t in treatments], fontsize=8)
    ax_risk.set_ylim(-0.5, n_treatments - 0.5)

    for row_idx, treatment in enumerate(treatments):
        grp = _rows(lifetable, treatment).sort_values("time")
        color = colors[treatment]
        counts = at_risk_counts(grp["time"], grp["n_at_risk"], risk_times)
        for tp, n_r in zip(risk_times, counts):
            ax_risk.text(tp, row_idx, str(n_r), ha="center", va="center",
                         fontsize=8, color=color, fontweight="bold")

    ax_risk.set_xlabel(time_label or "Time (hours)", fontsize=11)
    ax_risk.set_title("Number at Risk", fontsize=10, pad=2)
    ax_risk.tick_params(axis="y", length=0)
    ax_risk.yaxis.set_ticks_position("left")
    ax_risk.set_facecolor("#f9f9f9")
    ax_risk.grid(False)
    for spine in ax_risk.spines.values():
        spine.set_visible(False)
    ax_risk.spines["bottom"].set_visible(True)

    ## Not tight_layout: it warns "Axes not compatible … results might be
    ## incorrect" over this GridSpec pair and then guesses. The layout is
    ## already hand-tuned (height_ratios + hspace above), so only the outer
    ## margins are left to set.
    fig.subplots_adjust(left=0.10, right=0.97, top=0.93, bottom=0.09)
    return fig


def plot_nelson_aalen(
    lifetable: pd.DataFrame,
    title: str = "Nelson–Aalen Cumulative Hazard",
    show_ci: bool = True,
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot Nelson-Aalen cumulative hazard estimator H(t) for each treatment."""
    fig, ax = plt.subplots(figsize=(10, 6))

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty or "na_H" not in grp.columns:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        na_h = np.concatenate([[0.0], grp["na_H"].values])
        ax.step(times, na_h, where="post", label=_name(treatment, display_names),
                color=color, linewidth=1.8)
        if show_ci and "na_ci_lo" in grp.columns:
            ci_lo = np.concatenate([[0.0], grp["na_ci_lo"].values])
            ci_hi = np.concatenate([[0.0], grp["na_ci_hi"].values])
            ax.fill_between(times, ci_lo, ci_hi, step="post", alpha=0.13, color=color)

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Cumulative Hazard H(t)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def plot_log_log(
    lifetable: pd.DataFrame,
    title: str = "Log(−log S(t)) vs Log(t) — PH Assumption Check",
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot log(-log(S(t))) vs log(t) for proportional hazards assumption check.

    Under PH assumption, curves for different treatments should be parallel.
    Non-parallel lines suggest PH assumption violation. The x axis is
    ``log(<time_label>)`` — the natural log of age in the data's own unit.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty:
            continue
        color = colors[treatment]

        # Filter to positive survival and positive time
        valid = grp[(grp["km_lx"] > 0) & (grp["km_lx"] < 1) & (grp["time"] > 0)]
        if len(valid) < 2:
            continue

        log_t = np.log(valid["time"].values)
        log_neg_log_s = np.log(-np.log(valid["km_lx"].values))

        ax.plot(log_t, log_neg_log_s, label=_name(treatment, display_names),
                color=color, linewidth=1.8, marker=".", markersize=4)

    ax.set_xlabel(f"log({time_label})" if time_label else "log(Time)", fontsize=12)
    ax.set_ylabel("log(−log S(t))", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5, linewidth=0.8)
    fig.tight_layout()
    return fig


def plot_cumulative_events(
    lifetable: pd.DataFrame,
    title: str = "Cumulative Deaths (1 − S(t))",
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot the cumulative probability of death, 1 − S(t), over time.

    The Kaplan-Meier complement, so censoring is accounted for: it estimates
    the fraction of the cohort that would have died by age t, which a raw
    count of deaths cannot (it falls short wherever individuals were
    censored, and grows with group size). The band is the KM band reflected.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment)
        if grp.empty:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        cum_events = np.concatenate([[0.0], 1.0 - grp["km_lx"].values])
        ax.step(times, cum_events, where="post", label=_name(treatment, display_names),
                color=color, linewidth=1.8)
        ci_hi = np.concatenate([[0.0], 1.0 - grp["km_ci_lo"].values])
        ci_lo = np.concatenate([[0.0], 1.0 - grp["km_ci_hi"].values])
        ax.fill_between(times, ci_lo, ci_hi, step="post", alpha=0.12, color=color)

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Cumulative probability of death", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(left=0)
    ax.set_ylim(0, 1.05)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def plot_hazard_ratio_forest(
    hazard_ratios: "pd.DataFrame",
    title: str = "Hazard Ratio Forest Plot",
    reference: Optional[str] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Forest plot of pairwise hazard ratios with 95% CI.

    Parameters
    ----------
    hazard_ratios : DataFrame from ``statistics.pairwise_hazard_ratios()``
    title : plot title
    reference : reference group label (not used directly but shown for context)
    display_names : the Focus's legend text for each treatment, used in the
        row labels
    """
    if len(hazard_ratios) == 0:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No hazard ratio data", ha="center", va="center",
                transform=ax.transAxes)
        return fig

    valid = hazard_ratios.dropna(subset=["hazard_ratio"])
    n = len(valid)

    fig, ax = plt.subplots(figsize=(10, max(4, 1.0 + n * 0.6)))

    y_positions = list(range(n - 1, -1, -1))

    for i, (y, (_, row)) in enumerate(zip(y_positions, valid.iterrows())):
        hr = row["hazard_ratio"]
        lo = row["hr_ci_lo"]
        hi = row["hr_ci_hi"]
        label = (f"{_name(row['group1'], display_names)} vs "
                 f"{_name(row['group2'], display_names)}")

        color = "#d62728" if hr > 1 else "#1f77b4"
        ax.plot([lo, hi], [y, y], color=color, linewidth=2.0)
        ax.plot(hr, y, "D", color=color, markersize=9, zorder=3)

        ax.text(-0.02, y, label, ha="right", va="center", fontsize=9,
                transform=ax.get_yaxis_transform())
        ax.text(1.02, y, f"{hr:.3f} ({lo:.3f}–{hi:.3f})",
                ha="left", va="center", fontsize=8,
                transform=ax.get_yaxis_transform())

    ax.axvline(1.0, color="black", linestyle="--", linewidth=1.2, alpha=0.7)
    ax.set_yticks([])
    ax.set_xlabel("Hazard Ratio (95% CI)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_ylim(-0.5, n - 0.5)
    ax.grid(True, axis="x", alpha=0.3)
    ax.set_xlim(left=0)
    fig.tight_layout()
    return fig


def plot_survival_distribution(
    individual_data: "pd.DataFrame",
    title: str = "Lifespan Distribution",
    treatments: Optional[list[str]] = None,
    plot_type: str = "violin",
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Box/violin plot of individual lifespans by treatment.

    Only recorded deaths are drawn. A censored individual's lifespan is
    unknown — the time it was last seen is a lower bound, not a lifespan — so
    including it would pile weight at the final census and pull every
    summary the shape suggests towards it. The publication version
    (``pubfigures.distribution_data``) excludes them for the same reason.

    Parameters
    ----------
    individual_data : individual-level DataFrame with ``time``, ``event``,
        ``treatment``
    title : plot title
    treatments : subset to plot, in the order given
    plot_type : ``"violin"`` (default) or ``"box"``
    time_label : y-axis unit text (None = "Survival Time (hours)")
    """
    treatments, colors = _setup(individual_data, treatments, colours)

    deaths = (individual_data[individual_data["event"] == 1]
              if "event" in individual_data.columns else individual_data)

    fig, ax = plt.subplots(figsize=(max(8, len(treatments) * 1.5), 6))

    data_by_treatment = [_rows(deaths, t)["time"].values for t in treatments]
    color_list = [colors[t] for t in treatments]

    if plot_type == "violin" and all(len(d) > 1 for d in data_by_treatment):
        parts = ax.violinplot(data_by_treatment, positions=range(len(treatments)),
                              showmedians=True, showextrema=True)
        for i, (pc, color) in enumerate(zip(parts["bodies"], color_list)):
            pc.set_facecolor(color)
            pc.set_alpha(0.7)
        for part_name in ("cbars", "cmins", "cmaxes", "cmedians"):
            if part_name in parts:
                parts[part_name].set_colors("black")
    else:
        bp = ax.boxplot(data_by_treatment, positions=range(len(treatments)), patch_artist=True)
        for patch, color in zip(bp["boxes"], color_list):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

    ax.set_xticks(range(len(treatments)))
    ax.set_xticklabels([_name(t, display_names) for t in treatments],
                       rotation=15, ha="right", fontsize=10)
    ax.set_xlabel("Treatment", fontsize=12)
    ax.set_ylabel(f"Lifespan — {time_label}" if time_label else "Survival Time (hours)",
                  fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_smoothed_hazard(
    lifetable: pd.DataFrame,
    title: str = "Smoothed Hazard Rate",
    sigma: float = SMOOTHED_HAZARD_SIGMA,
    treatments: Optional[list[str]] = None,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Plot a Gaussian-smoothed estimate of the hazard rate over time.

    Parameters
    ----------
    lifetable : DataFrame from ``compute_lifetables()``
    title : plot title
    sigma : Gaussian smoothing bandwidth, in lifetable rows
        (:data:`SMOOTHED_HAZARD_SIGMA` by default)
    treatments : subset of treatments to plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    treatments, colors = _setup(lifetable, treatments, colours)

    for treatment in treatments:
        grp = _rows(lifetable, treatment).copy()
        if grp.empty or len(grp) < 5:
            continue
        color = colors[treatment]

        # Smooth hx using a Gaussian kernel
        hx_smooth = gaussian_filter1d(grp["hx"].values.astype(float), sigma=sigma)
        ax.plot(grp["time"].values, hx_smooth, label=_name(treatment, display_names),
                color=color, linewidth=2.0)
        ax.fill_between(grp["time"].values, 0, hx_smooth, alpha=0.08, color=color)

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Smoothed Hazard Rate", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig


def plot_chamber_overlay_km(
    per_chamber_lt: pd.DataFrame,
    treatment: str,
    excluded_chambers: Optional[set] = None,
    ax: Optional[plt.Axes] = None,
    title: Optional[str] = None,
    time_label: str | None = None,
) -> plt.Figure:
    """Overlay KM curves for every chamber within a single treatment.

    Each chamber gets one translucent step line; line ``gid`` is set to
    ``f"chamber-{chamber_id}"`` so :mod:`mplcursors` can read it back to
    annotate the hovered curve. Excluded chambers (by id) render as red
    dashed lines so the user can visually confirm what's being dropped.

    Parameters
    ----------
    per_chamber_lt : DataFrame
        Output of :func:`lifetable.compute_lifetables_per_chamber`.
    treatment : str
        Treatment to display on this panel.
    excluded_chambers : set, optional
        Chamber ids to render as excluded.
    ax : matplotlib Axes, optional
    title : str, optional
    time_label : str, optional
        x-axis title (None = "Time (hours)").

    Returns
    -------
    matplotlib Figure
    """
    excluded_chambers = excluded_chambers or set()
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    sub = _rows(per_chamber_lt, treatment)
    chambers = sorted(sub["chamber"].unique(), key=lambda c: (isinstance(c, str), c))

    base_color = "#1f77b4"
    for chamber in chambers:
        grp = sub[sub["chamber"] == chamber]
        if grp.empty:
            continue
        times = np.concatenate([[0], grp["time"].values])
        surv = np.concatenate([[1.0], grp["km_lx"].values])
        n_events = int(grp["n_deaths"].sum())
        last_t = float(grp["time"].max()) if len(grp) else 0.0

        is_excluded = chamber in excluded_chambers
        color = "#dc2626" if is_excluded else base_color
        linestyle = "--" if is_excluded else "-"
        alpha = 0.7 if is_excluded else 0.4
        line, = ax.step(
            times, surv, where="post",
            color=color, linestyle=linestyle, alpha=alpha, linewidth=1.5,
        )
        line.set_gid(f"chamber-{chamber}")
        # Stash metadata for mplcursors hover annotations
        line.set_label(
            f"Chamber {chamber} — {n_events} events, last t={last_t:.1f}"
        )

    ax.set_xlabel(time_label or "Time (hours)", fontsize=12)
    ax.set_ylabel("Survival probability (KM)", fontsize=12)
    ax.set_title(
        title if title is not None else f"{treatment} — per-chamber KM overlay",
        fontsize=14,
    )
    ax.set_xlim(left=0)
    ax.set_ylim(0.0, 1.05)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig



# ---------------------------------------------------------------------------
# Figures crossing factors
#
# Part of the Factorial Battery, offered to any Focus varying two or more
# factors: the faceted KM is its Headline Figure, and the lifespan
# interaction plot states in one panel the thing the Cox interaction term is
# testing. Both put the FIRST varying factor on the outer axis — the panels
# of one, the x axis of the other — so the two read the same way round.
# ---------------------------------------------------------------------------

def _require_crossing(factors: dict[str, list]) -> list[str]:
    """The factor names, or an error: a figure that crosses factors needs two
    or more varying ones."""
    names = list(factors)
    if len(names) < 2:
        raise ValueError(
            "A figure crossing factors needs two or more varying factors; got "
            f"{len(names)} ({', '.join(names) or 'none'}).")
    return names


def _level_combos(factors: dict[str, list]) -> list[str]:
    """Every combination of *factors*' levels, joined with ``/``, in display
    order (first factor outermost) — the label a curve or line carries."""
    import itertools

    return ["/".join(map(str, combo))
            for combo in itertools.product(*(list(v) for v in factors.values()))]


def plot_km_faceted(
    lifetable: pd.DataFrame,
    factors: dict[str, list],
    title: str | None = None,
    show_ci: bool = False,
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """One panel per level of the first varying factor; a curve for each level
    (or combination of levels) of the others.

    The Headline Figure of a Focus that crosses factors: a treatment effect
    that differs between panels *is* the interaction, visible without reading
    a coefficient. A curve keeps one colour in every panel — the Focus's
    colour for that level where it names one, else the cycle by level order.
    """
    names = _require_crossing(factors)
    lt = lifetable.copy()
    lt["treatment"] = lt["treatment"].astype(str)
    parts = lt["treatment"].str.split("/", n=1, expand=True)
    if parts.shape[1] < 2:
        raise ValueError(
            "Faceted KM needs treatment labels crossing factors, of the form "
            "'<level1>/<level2>'."
        )
    lt["_f1"], lt["_f2"] = parts[0], parts[1]
    f1, rest = names[0], names[1:]
    l2 = _level_combos({f: factors[f] for f in rest})
    f2 = " × ".join(rest)
    title = title or f"Survival by treatment, faceted by {f1}"
    l1 = list(factors[f1]) or list(dict.fromkeys(lt["_f1"]))

    present1 = [lv for lv in l1 if lv in set(lt["_f1"])]
    if not present1:
        present1 = list(dict.fromkeys(lt["_f1"]))
    colors = _treatment_colors(l2, colours)

    fig, axes = plt.subplots(
        1, len(present1), figsize=(5.5 * len(present1), 5), sharey=True, squeeze=False,
    )
    for ax, level1 in zip(axes[0], present1):
        panel = lt[lt["_f1"] == level1]
        for level2 in l2:
            grp = panel[panel["_f2"] == level2]
            if grp.empty:
                continue
            times = np.concatenate([[0], grp["time"].values])
            surv = np.concatenate([[1.0], grp["km_lx"].values])
            color = colors.get(level2, "#666666")
            ax.step(times, surv, where="post", label=_name(level2, display_names),
                    color=color, linewidth=1.8)
            if show_ci:
                ci_lo = np.concatenate([[1.0], grp["km_ci_lo"].values])
                ci_hi = np.concatenate([[1.0], grp["km_ci_hi"].values])
                ax.fill_between(times, ci_lo, ci_hi, step="post",
                                alpha=0.15, color=color)
            cens = grp[grp["n_censored"] > 0]
            if not cens.empty:
                ax.plot(cens["time"].values, cens["km_lx"].values, "|",
                        color=color, markersize=8, markeredgewidth=1.5)
        ax.set_title(f"{f1}: {level1}", fontsize=12)
        ax.set_xlabel(time_label or "Age", fontsize=11)
        ax.set_ylim(-0.02, 1.05)
        ax.set_xlim(left=0)
        ax.grid(True, alpha=0.3)

    axes[0][0].set_ylabel("Survival probability", fontsize=12)
    axes[0][-1].legend(title=f2, loc="best", fontsize=10)
    fig.suptitle(title, fontsize=14)
    fig.tight_layout()
    return fig


def rmst_se(times, events, tau: float) -> float:
    """The standard error of a restricted mean survival time to *tau*.

    The classical variance Σ A_i² d_i / (n_i (n_i − d_i)) over the deaths at
    or before tau, A_i being the area under the KM curve from the i-th death
    to tau. (lifelines' ``return_variance`` is the variance of min(T, τ)
    itself, not of its estimate, so it cannot stand in here.)
    """
    times = np.asarray(times, dtype=float)
    events = np.asarray(events).astype(int)
    knots = np.unique(times[(events == 1) & (times <= tau)])
    if not len(knots):
        return 0.0
    n = np.array([(times >= t).sum() for t in knots], dtype=float)
    d = np.array([((times == t) & (events == 1)).sum() for t in knots], dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        surv = np.cumprod(1.0 - d / n)
    ## Segment areas between deaths, then each death's area to its right.
    edges = np.concatenate([knots, [tau]])
    tail = np.cumsum((surv * np.diff(edges))[::-1])[::-1]
    with np.errstate(divide="ignore", invalid="ignore"):
        terms = np.where(n > d, tail ** 2 * d / (n * (n - d)), 0.0)
    return float(np.sqrt(np.nansum(terms)))


def cell_lifespan(cell: pd.DataFrame, metric: str = "median",
                  tau: float | None = None) -> tuple[float, float, float] | None:
    """One cell's censoring-aware lifespan and its 95% interval: ``(value,
    low, high)``, or ``None`` when the cell has no such value.

    * ``median`` — the Kaplan-Meier median and its interval read off the KM
      band where it crosses 0.5 (:func:`lifetable.km_median_ci`, the numbers
      the Median survival table reports). A curve that never falls to 0.5
      has no median: ``None``, never the plain median of the recorded times,
      which treats every censored individual as dead. A band edge that never
      reaches 0.5 leaves that limit open (``inf``).
    * ``mean`` — the restricted mean to *tau* (:func:`lifetable.km_rmst`),
      ±1.96·:func:`rmst_se`.

    One function for the analysis figure and the Publication Figure, so the
    two cannot plot different numbers for the same cell.
    """
    from . import lifetable

    if cell is None or not len(cell):
        return None
    if "event" not in cell.columns:
        cell = cell.assign(event=1)
    if metric == "mean":
        tau = float(cell["time"].max()) if tau is None else float(tau)
        value = float(lifetable.km_rmst(cell, tau))
        se = rmst_se(cell["time"], cell["event"], tau)
        return value, value - 1.96 * se, value + 1.96 * se
    stats = lifetable.km_median_ci(cell)
    value = float(stats["median"])
    if not np.isfinite(value):
        return None
    low, high = (float(stats[k]) for k in ("ci_lo", "ci_hi"))
    return (value, low if np.isfinite(low) else -np.inf,
            high if np.isfinite(high) else np.inf)


def plot_lifespan_interaction(
    individual_data: pd.DataFrame,
    factors: dict[str, list],
    metric: str = "median",
    title: str = "Lifespan interaction",
    time_label: str | None = None,
    colours: Optional[dict] = None,
    display_names: Optional[dict] = None,
) -> plt.Figure:
    """Cell lifespan by factor level: non-parallel lines indicate interaction.

    The **first** varying factor runs along the x axis — as it makes the
    panels of the faceted KM — and each combination of the others is a line.

    ``metric`` is ``"median"`` (the Kaplan-Meier median, the default) or
    ``"mean"`` (the restricted mean to a common τ, the earliest last age of
    any cell); both are censoring-aware (:func:`cell_lifespan`). Error bars
    are the statistic's 95% confidence interval; a limit the data never
    reaches is left open. A cell whose survival never falls to 0.5 has no
    median and no point. The formal test is the Cox interaction term, not
    this figure.
    """
    names = _require_crossing(factors)
    f_x, line_factors = names[0], names[1:]
    l1 = _level_combos({f: factors[f] for f in line_factors})
    l2 = [str(lv) for lv in factors[f_x]]
    f1 = " × ".join(line_factors)
    metric = metric.lower()
    if metric not in {"median", "mean"}:
        raise ValueError("metric must be 'median' or 'mean'.")

    def _cell(level_x: str, line: str) -> pd.DataFrame:
        mask = individual_data[f_x].astype(str) == str(level_x)
        for factor, level in zip(line_factors, line.split("/")):
            mask &= individual_data[factor].astype(str) == str(level)
        return individual_data[mask]

    cells = {(lx, line): _cell(lx, line) for line in l1 for lx in l2}
    ## Every cell is restricted to the same τ — the Mean survival table's
    ## rule — so no cell is credited for being followed longer.
    tau = None
    populated = [c for c in cells.values() if len(c)]
    if metric == "mean" and populated:
        from . import lifetable

        tau = float(lifetable.common_tau(pd.concat(populated)))

    fig, ax = plt.subplots(figsize=(7, 5))
    colors = _treatment_colors(l1, colours)
    x_positions = {lv: i for i, lv in enumerate(l2)}

    for line in l1:
        xs, ys, lo_err, hi_err = [], [], [], []
        for level_x in l2:
            cell = cells[(level_x, line)]
            if cell.empty:
                continue
            stat = cell_lifespan(cell, metric, tau)
            if stat is None:
                continue
            value, low, high = stat
            xs.append(x_positions[level_x])
            ys.append(value)
            ## An open limit draws no bar on that side rather than one that
            ## runs off to infinity or stops at an invented value.
            lo_err.append(value - low if np.isfinite(low) else 0.0)
            hi_err.append(high - value if np.isfinite(high) else 0.0)
        if not xs:
            continue
        ax.errorbar(xs, ys, yerr=[lo_err, hi_err], marker="o", markersize=8,
                    capsize=4, linewidth=2, color=colors.get(line, "#666666"),
                    label=_name(line, display_names))

    ax.set_xticks(list(x_positions.values()))
    ax.set_xticklabels([str(lv) for lv in l2])
    ax.set_xlim(-0.35, len(l2) - 0.65)
    ax.set_xlabel(f_x, fontsize=12)
    what = ("Median lifespan" if metric == "median"
            else f"Restricted mean lifespan (τ = {tau:g})")
    ax.set_ylabel(f"{what} — {time_label or 'Age'}", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.legend(title=f1, loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig
