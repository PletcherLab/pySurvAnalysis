"""Lifetable and Kaplan-Meier survival computations.

Produces a single DataFrame containing, for each treatment at each unique
event time:
    n_at_risk   — number alive and uncensored at the start of the interval
    n_deaths    — deaths during the interval
    n_censored  — censored during the interval
    qx          — probability of death in the interval  (d / n)
    px          — probability of surviving the interval  (1 - qx)
    lx          — survivorship (cumulative product of px)
    hx          — estimate of instantaneous hazard, adjusted for interval width
    km_lx       — Kaplan-Meier estimate of survivorship
    se_km       — Greenwood standard error of KM estimate
    km_ci_lo    — 95% CI lower bound for KM
    km_ci_hi    — 95% CI upper bound for KM
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _lifetable_one_treatment(df: pd.DataFrame) -> pd.DataFrame:
    """Compute lifetable for a single treatment group.

    Parameters
    ----------
    df : DataFrame
        Must have columns ``time`` and ``event`` (1=death, 0=censored).
        Pooled across all chambers for this treatment.
    """
    # Get all unique times, sorted
    times = sorted(df["time"].unique())

    records = []
    n_at_risk = len(df)
    cum_surv = 1.0
    greenwood_sum = 0.0

    for i, t in enumerate(times):
        at_t = df[df["time"] == t]
        d = int(at_t["event"].sum())          # deaths at time t
        c = int((at_t["event"] == 0).sum())   # censored at time t

        # Interval width for hazard calculation
        if i + 1 < len(times):
            dt = times[i + 1] - t
        else:
            dt = t - times[i - 1] if i > 0 else 1.0

        if n_at_risk > 0:
            qx = d / n_at_risk
            px = 1.0 - qx
        else:
            qx = 0.0
            px = 1.0

        cum_surv *= px

        # Greenwood's formula for SE of KM
        if n_at_risk > 0 and d > 0 and n_at_risk != d:
            greenwood_sum += d / (n_at_risk * (n_at_risk - d))

        se_km = cum_surv * np.sqrt(greenwood_sum) if greenwood_sum > 0 else 0.0

        # Hazard estimate (adjusted for interval width)
        # Using actuarial approximation: hx = 2*qx / ((1+px)*dt)
        if dt > 0 and (1 + px) > 0:
            hx = 2 * qx / ((1 + px) * dt)
        else:
            hx = 0.0

        records.append({
            "time": t,
            "n_at_risk": n_at_risk,
            "n_deaths": d,
            "n_censored": c,
            "qx": qx,
            "px": px,
            "lx": cum_surv,
            "hx": hx,
            "km_lx": cum_surv,
            "se_km": se_km,
            "km_ci_lo": max(0.0, cum_surv - 1.96 * se_km),
            "km_ci_hi": min(1.0, cum_surv + 1.96 * se_km),
        })

        n_at_risk -= (d + c)

    return pd.DataFrame(records)


def compute_lifetables(individual_data: pd.DataFrame) -> pd.DataFrame:
    """Compute lifetable statistics for all treatments.

    Parameters
    ----------
    individual_data : DataFrame
        Output of ``data_loader.load_experiment()``, with columns
        ``time``, ``event``, ``treatment``, etc.

    Returns
    -------
    DataFrame with a ``treatment`` column and all lifetable columns.
    """
    parts = []
    for treatment, grp in individual_data.groupby("treatment"):
        lt = _lifetable_one_treatment(grp)
        lt.insert(0, "treatment", treatment)
        parts.append(lt)

    return pd.concat(parts, ignore_index=True)


def median_survival(lifetable: pd.DataFrame) -> pd.DataFrame:
    """Extract median survival time for each treatment.

    Returns a DataFrame with treatment, median_time, and the 95% CI bounds
    for the time at which KM crosses 0.5.
    """
    results = []
    for treatment, grp in lifetable.groupby("treatment"):
        below = grp[grp["km_lx"] <= 0.5]
        if len(below) > 0:
            median_t = below["time"].iloc[0]
        else:
            median_t = np.nan
        results.append({"treatment": treatment, "median_survival": median_t})
    return pd.DataFrame(results)


def mean_survival(individual_data: pd.DataFrame) -> pd.DataFrame:
    """Compute restricted mean survival time (RMST) for each treatment.

    Uses the area under the KM curve up to the minimum of the max observed
    times across treatments (common restriction time).
    """
    lifetable = compute_lifetables(individual_data)
    t_max = lifetable.groupby("treatment")["time"].max().min()

    results = []
    for treatment, grp in lifetable.groupby("treatment"):
        grp = grp[grp["time"] <= t_max].copy()
        times = grp["time"].values
        surv = grp["km_lx"].values

        # Trapezoidal integration of survival curve
        if len(times) > 1:
            area = np.trapezoid(surv, times)
        else:
            area = np.nan

        results.append({
            "treatment": treatment,
            "rmst": area,
            "restriction_time": t_max,
        })
    return pd.DataFrame(results)
