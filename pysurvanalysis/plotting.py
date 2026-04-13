"""Plotting functions for survival analysis.

All plot functions return a matplotlib Figure so callers can save, embed in
a UI, or display interactively.
"""

from __future__ import annotations

from typing import Optional

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

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
