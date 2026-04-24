"""Plotting functions for survival analysis.

All plot functions return a matplotlib Figure so callers can save, embed in
a UI, or display interactively.
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


def _treatment_colors(treatments: list[str]) -> dict[str, str]:
    """Assign a consistent color to each treatment."""
    return {t: COLORS[i % len(COLORS)] for i, t in enumerate(sorted(treatments))}


def plot_km_curves(
    lifetable: pd.DataFrame,
    title: str = "Kaplan\u2013Meier Survival Curves",
    show_ci: bool = True,
    ax: Optional[plt.Axes] = None,
    treatments: Optional[list[str]] = None,
) -> plt.Figure:
    """Plot Kaplan-Meier survival curves for all (or selected) treatments.

    Parameters
    ----------
    lifetable : DataFrame from ``lifetable.compute_lifetables()``
    title : plot title
    show_ci : whether to show 95% confidence bands
    ax : optional existing Axes to draw on
    treatments : optional subset of treatments to plot

    Returns
    -------
    matplotlib Figure
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty:
            continue

        color = colors[treatment]

        # Build step-function coordinates (prepend t=0, lx=1.0)
        times = np.concatenate([[0], grp["time"].values])
        surv = np.concatenate([[1.0], grp["km_lx"].values])

        ax.step(times, surv, where="post", label=treatment, color=color, linewidth=1.5)

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

    ax.set_xlabel("Time (hours)", fontsize=12)
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
) -> plt.Figure:
    """Plot hazard rate (hx) over time for each treatment."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty:
            continue
        color = colors[treatment]
        ax.plot(
            grp["time"], grp["hx"],
            label=treatment, color=color, linewidth=1.2, marker=".", markersize=3,
        )

    ax.set_xlabel("Time (hours)", fontsize=12)
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
) -> plt.Figure:
    """Plot probability of death per interval (qx) over time."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty:
            continue
        color = colors[treatment]
        ax.plot(
            grp["time"], grp["qx"],
            label=treatment, color=color, linewidth=1.2, marker=".", markersize=3,
        )

    ax.set_xlabel("Time (hours)", fontsize=12)
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
) -> plt.Figure:
    """Plot the number at risk over time for each treatment."""
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    else:
        fig = ax.get_figure()

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        # At time 0, n_at_risk equals the first row's value
        n_risk = np.concatenate([[grp["n_at_risk"].iloc[0]], grp["n_at_risk"].values])
        ax.step(times, n_risk, where="post", label=treatment, color=color, linewidth=1.5)

    ax.set_xlabel("Time (hours)", fontsize=12)
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
    n_risk_timepoints: int = 8,
) -> plt.Figure:
    """KM survival curves with an integrated number-at-risk table below.

    The plot area is divided: upper ~75% for the KM curves, lower ~25% for
    the at-risk table showing n_at_risk at evenly spaced timepoints.
    """
    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    # Choose timepoints for at-risk table
    all_times = sorted(lifetable["time"].unique())
    n_pts = min(n_risk_timepoints, len(all_times))
    indices = np.linspace(0, len(all_times) - 1, n_pts, dtype=int)
    risk_times = [all_times[i] for i in indices]

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
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        surv = np.concatenate([[1.0], grp["km_lx"].values])
        ax_km.step(times, surv, where="post", label=treatment, color=color, linewidth=2.0)
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
    ax_risk.set_yticklabels(treatments, fontsize=8)
    ax_risk.set_ylim(-0.5, n_treatments - 0.5)

    for row_idx, treatment in enumerate(treatments):
        grp = lifetable[lifetable["treatment"] == treatment]
        color = colors[treatment]
        for tp in risk_times:
            at_or_before = grp[grp["time"] <= tp]
            if len(at_or_before) == 0:
                n_r = int(grp["n_at_risk"].iloc[0]) if len(grp) > 0 else 0
            else:
                last = at_or_before.iloc[-1]
                n_r = max(0, int(last["n_at_risk"]) - int(last["n_deaths"]) - int(last["n_censored"]))
            ax_risk.text(tp, row_idx, str(n_r), ha="center", va="center",
                         fontsize=8, color=color, fontweight="bold")

    ax_risk.set_xlabel("Time (hours)", fontsize=11)
    ax_risk.set_title("Number at Risk", fontsize=10, pad=2)
    ax_risk.tick_params(axis="y", length=0)
    ax_risk.yaxis.set_ticks_position("left")
    ax_risk.set_facecolor("#f9f9f9")
    ax_risk.grid(False)
    for spine in ax_risk.spines.values():
        spine.set_visible(False)
    ax_risk.spines["bottom"].set_visible(True)

    fig.tight_layout()
    return fig


def plot_nelson_aalen(
    lifetable: pd.DataFrame,
    title: str = "Nelson–Aalen Cumulative Hazard",
    show_ci: bool = True,
    treatments: Optional[list[str]] = None,
) -> plt.Figure:
    """Plot Nelson-Aalen cumulative hazard estimator H(t) for each treatment."""
    fig, ax = plt.subplots(figsize=(10, 6))

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty or "na_H" not in grp.columns:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        na_h = np.concatenate([[0.0], grp["na_H"].values])
        ax.step(times, na_h, where="post", label=treatment, color=color, linewidth=1.8)
        if show_ci and "na_ci_lo" in grp.columns:
            ci_lo = np.concatenate([[0.0], grp["na_ci_lo"].values])
            ci_hi = np.concatenate([[0.0], grp["na_ci_hi"].values])
            ax.fill_between(times, ci_lo, ci_hi, step="post", alpha=0.13, color=color)

    ax.set_xlabel("Time (hours)", fontsize=12)
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
) -> plt.Figure:
    """Plot log(-log(S(t))) vs log(t) for proportional hazards assumption check.

    Under PH assumption, curves for different treatments should be parallel.
    Non-parallel lines suggest PH assumption violation.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty:
            continue
        color = colors[treatment]

        # Filter to positive survival and positive time
        valid = grp[(grp["km_lx"] > 0) & (grp["km_lx"] < 1) & (grp["time"] > 0)]
        if len(valid) < 2:
            continue

        log_t = np.log(valid["time"].values)
        log_neg_log_s = np.log(-np.log(valid["km_lx"].values))

        ax.plot(log_t, log_neg_log_s, label=treatment, color=color, linewidth=1.8,
                marker=".", markersize=4)

    ax.set_xlabel("log(Time)", fontsize=12)
    ax.set_ylabel("log(−log S(t))", fontsize=12)
    ax.set_title(title, fontsize=13)
    ax.legend(loc="upper left", fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.axhline(0, color="gray", linestyle="--", alpha=0.5, linewidth=0.8)
    fig.tight_layout()
    return fig


def plot_cumulative_events(
    lifetable: pd.DataFrame,
    title: str = "Cumulative Events (1 − S(t))",
    treatments: Optional[list[str]] = None,
) -> plt.Figure:
    """Plot cumulative event incidence (1 - KM survival) over time."""
    fig, ax = plt.subplots(figsize=(10, 6))

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment]
        if grp.empty:
            continue
        color = colors[treatment]
        times = np.concatenate([[0], grp["time"].values])
        cum_events = np.concatenate([[0.0], 1.0 - grp["km_lx"].values])
        ax.step(times, cum_events, where="post", label=treatment, color=color, linewidth=1.8)
        ci_hi = np.concatenate([[0.0], 1.0 - grp["km_ci_lo"].values])
        ci_lo = np.concatenate([[0.0], 1.0 - grp["km_ci_hi"].values])
        ax.fill_between(times, ci_lo, ci_hi, step="post", alpha=0.12, color=color)

    ax.set_xlabel("Time (hours)", fontsize=12)
    ax.set_ylabel("Cumulative Event Probability", fontsize=12)
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
) -> plt.Figure:
    """Forest plot of pairwise hazard ratios with 95% CI.

    Parameters
    ----------
    hazard_ratios : DataFrame from ``statistics.pairwise_hazard_ratios()``
    title : plot title
    reference : reference group label (not used directly but shown for context)
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
        label = f"{row['group1']} vs {row['group2']}"

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
    title: str = "Survival Time Distribution",
    treatments: Optional[list[str]] = None,
    plot_type: str = "violin",
) -> plt.Figure:
    """Box/violin plot of individual survival times by treatment.

    Parameters
    ----------
    individual_data : individual-level DataFrame with ``time``, ``treatment``
    title : plot title
    treatments : subset to plot
    plot_type : ``"violin"`` (default) or ``"box"``
    """
    if treatments is None:
        treatments = sorted(individual_data["treatment"].unique())

    colors = _treatment_colors(individual_data["treatment"].unique().tolist())

    fig, ax = plt.subplots(figsize=(max(8, len(treatments) * 1.5), 6))

    data_by_treatment = [
        individual_data[individual_data["treatment"] == t]["time"].values
        for t in treatments
    ]
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
    ax.set_xticklabels(treatments, rotation=15, ha="right", fontsize=10)
    ax.set_xlabel("Treatment", fontsize=12)
    ax.set_ylabel("Survival Time (hours)", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_smoothed_hazard(
    lifetable: pd.DataFrame,
    title: str = "Smoothed Hazard Rate",
    sigma: float = 3.0,
    treatments: Optional[list[str]] = None,
) -> plt.Figure:
    """Plot a Gaussian-smoothed estimate of the hazard rate over time.

    Parameters
    ----------
    lifetable : DataFrame from ``compute_lifetables()``
    title : plot title
    sigma : Gaussian smoothing bandwidth (in index units, ~3 by default)
    treatments : subset of treatments to plot
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    if treatments is None:
        treatments = sorted(lifetable["treatment"].unique())

    colors = _treatment_colors(lifetable["treatment"].unique().tolist())

    for treatment in treatments:
        grp = lifetable[lifetable["treatment"] == treatment].copy()
        if grp.empty or len(grp) < 5:
            continue
        color = colors[treatment]

        # Smooth hx using a Gaussian kernel
        hx_smooth = gaussian_filter1d(grp["hx"].values.astype(float), sigma=sigma)
        ax.plot(grp["time"].values, hx_smooth, label=treatment, color=color, linewidth=2.0)
        ax.fill_between(grp["time"].values, 0, hx_smooth, alpha=0.08, color=color)

    ax.set_xlabel("Time (hours)", fontsize=12)
    ax.set_ylabel("Smoothed Hazard Rate", fontsize=12)
    ax.set_title(title, fontsize=14)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right", fontsize=10)
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    return fig
