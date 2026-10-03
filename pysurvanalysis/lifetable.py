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
    km_ci_lo    — 95% CI lower bound for KM (log-log / exponential Greenwood)
    km_ci_hi    — 95% CI upper bound for KM

Treatments come out in display order (:func:`statistics.treatment_order`),
never alphabetically, so every table built from a lifetable lists them the way
the Focus declares them.

Areas under the KM curve (mean survival, RMST) integrate the **step
function** exactly up to the restriction time τ. The curve is flat between
event times, so joining its points with straight lines (trapezoids) cuts a
corner off every step and understates the area, and stopping at the last time
before τ drops the final strip.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .statistics import treatment_groups, treatment_order

#: The two-sided 95% normal quantile — lifelines' exact value, so the KM band
#: and the median's interval match it to the last digit.
_Z95 = 1.959963984540054


def _loglog_band(surv: float, greenwood_sum: float) -> tuple[float, float]:
    """The 95% log-log ("exponential Greenwood") interval for one KM value.

    Built on log(−log S), so it always lies inside [0, 1] and is asymmetric
    where S is near either end — unlike S ± 1.96·SE, which crosses 0 and 1 and
    has to be clipped there exactly where the tail is read. lifelines'
    ``KaplanMeierFitter`` uses the same interval.
    """
    if surv >= 1.0:
        return 1.0, 1.0
    if surv <= 0.0:
        return 0.0, 0.0
    v = np.log(surv)
    spread = _Z95 * np.sqrt(greenwood_sum) / v      # v < 0, so spread <= 0
    lo = float(np.exp(-np.exp(np.log(-v) - spread)))
    hi = float(np.exp(-np.exp(np.log(-v) + spread)))
    return lo, hi


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
    na_H = 0.0       # Nelson-Aalen cumulative hazard
    na_var = 0.0     # Variance for NA CI

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

        # Greenwood's formula for SE of KM. A step where everyone at risk
        # dies (n == d) takes S to 0 and adds nothing — lifelines does the same.
        if n_at_risk > 0 and d > 0 and n_at_risk != d:
            greenwood_sum += d / (n_at_risk * (n_at_risk - d))

        se_km = cum_surv * np.sqrt(greenwood_sum) if greenwood_sum > 0 else 0.0
        km_ci_lo, km_ci_hi = _loglog_band(cum_surv, greenwood_sum)

        # Hazard estimate (adjusted for interval width)
        # Using actuarial approximation: hx = 2*qx / ((1+px)*dt)
        if dt > 0 and (1 + px) > 0:
            hx = 2 * qx / ((1 + px) * dt)
        else:
            hx = 0.0

        # Nelson-Aalen cumulative hazard
        if n_at_risk > 0 and d > 0:
            na_H += d / n_at_risk
            na_var += d / (n_at_risk ** 2)

        na_se = np.sqrt(na_var)
        na_ci_lo = max(0.0, na_H - 1.96 * na_se)
        na_ci_hi = na_H + 1.96 * na_se

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
            "km_ci_lo": km_ci_lo,
            "km_ci_hi": km_ci_hi,
            "na_H": na_H,
            "na_se": na_se,
            "na_ci_lo": na_ci_lo,
            "na_ci_hi": na_ci_hi,
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
    DataFrame with a ``treatment`` column and all lifetable columns, the
    treatments in display order (so :func:`statistics.treatment_order` of the
    result — first appearance — is the Focus's order too).
    """
    parts = []
    for treatment, grp in treatment_groups(individual_data):
        lt = _lifetable_one_treatment(grp)
        lt.insert(0, "treatment", treatment)
        parts.append(lt)

    return pd.concat(parts, ignore_index=True)


def compute_lifetables_per_chamber(individual_data: pd.DataFrame) -> pd.DataFrame:
    """Compute one lifetable per (treatment, chamber).

    Used by the QC viewer to draw an overlay of every chamber's KM curve
    inside a treatment, so outliers can be picked out by eye.

    Returns a DataFrame with columns
    ``treatment, chamber, time, n_at_risk, n_deaths, km_lx`` (plus all the
    other lifetable columns from :func:`_lifetable_one_treatment`).
    Chambers with fewer than 2 individuals are still included; chambers
    with no events show a flat km_lx=1.0 line.
    """
    if "chamber" not in individual_data.columns:
        return pd.DataFrame(
            columns=["treatment", "chamber", "time", "km_lx", "n_at_risk", "n_deaths"]
        )
    parts = []
    ## observed=True: a categorical treatment would otherwise pair every
    ## treatment with every chamber, almost all of them empty.
    order = {t: i for i, t in enumerate(treatment_order(individual_data))}
    groups = sorted(individual_data.groupby(["treatment", "chamber"], observed=True),
                    key=lambda item: order.get(str(item[0][0]), len(order)))
    for (treatment, chamber), grp in groups:
        if len(grp) == 0:
            continue
        lt = _lifetable_one_treatment(grp)
        lt.insert(0, "chamber", chamber)
        lt.insert(0, "treatment", treatment)
        parts.append(lt)
    if not parts:
        return pd.DataFrame(
            columns=["treatment", "chamber", "time", "km_lx", "n_at_risk", "n_deaths"]
        )
    return pd.concat(parts, ignore_index=True)


def _first_at_or_below(lt: pd.DataFrame, column: str, q: float) -> float:
    """The first time *column* of one treatment's lifetable is ≤ *q* — NaN
    when it never gets there (the quantile is "not reached")."""
    below = lt.loc[lt[column] <= q, "time"]
    return float(below.iloc[0]) if len(below) else np.nan


def _median_with_ci(lt: pd.DataFrame) -> tuple[float, float, float]:
    """``(median, lower, upper)`` from one treatment's lifetable.

    The median is the first time KM ≤ 0.5. Its 95% interval is read off the
    KM band the same way — inverting the pointwise interval, as R's
    ``survfit`` and lifelines' ``median_survival_times(confidence_interval_)``
    do: the lower bound is where the band's lower edge first reaches 0.5, the
    upper where its upper edge does — NaN when that edge never gets there.
    """
    if lt is None or not len(lt):
        return np.nan, np.nan, np.nan
    return (_first_at_or_below(lt, "km_lx", 0.5),
            _first_at_or_below(lt, "km_ci_lo", 0.5),
            _first_at_or_below(lt, "km_ci_hi", 0.5))


def km_median_ci(data: pd.DataFrame) -> dict:
    """The KM median and its 95% interval for ONE group of individuals.

    *data* needs ``time`` and ``event``; it is one treatment (or one cell of a
    figure). Returns ``{"median", "ci_lo", "ci_hi"}``, each NaN when not
    reached — the same numbers the Median survival table reports.
    """
    if data is None or not len(data):
        return {"median": np.nan, "ci_lo": np.nan, "ci_hi": np.nan}
    median, lo, hi = _median_with_ci(_lifetable_one_treatment(data))
    return {"median": median, "ci_lo": lo, "ci_hi": hi}


def median_survival(lifetable: pd.DataFrame) -> pd.DataFrame:
    """Extract median survival time for each treatment, with its 95% CI.

    Columns: ``treatment``, ``median_survival``, ``median_ci_lo``,
    ``median_ci_hi`` — the times at which the KM curve and its log-log band
    first reach 0.5 (see :func:`_median_with_ci`). NaN means not reached.
    """
    results = []
    for treatment, grp in treatment_groups(lifetable):
        median_t, lo, hi = _median_with_ci(grp)
        results.append({"treatment": treatment, "median_survival": median_t,
                        "median_ci_lo": lo, "median_ci_hi": hi})
    return pd.DataFrame(results, columns=["treatment", "median_survival",
                                          "median_ci_lo", "median_ci_hi"])


def _km_survival(time, event) -> tuple[np.ndarray, np.ndarray]:
    """Distinct times and the KM survivorship from each onward — the bare
    curve, vectorised, for callers that need it many times over (the RMST
    jackknife refits it once per individual)."""
    t = np.asarray(time, dtype=float)
    e = np.asarray(event, dtype=float)
    if not len(t):
        return np.array([]), np.array([])
    uniq, inv = np.unique(t, return_inverse=True)
    deaths = np.bincount(inv, weights=e, minlength=len(uniq))
    removed = np.bincount(inv, minlength=len(uniq))
    at_risk = len(t) - np.concatenate([[0], np.cumsum(removed)[:-1]])
    return uniq, np.cumprod(1.0 - deaths / at_risk)


def _step_area(times, surv, tau: float) -> float:
    """∫₀^τ S(t) dt for the KM step function — exact.

    S is 1 on [0, t₁) and ``surv[i]`` on [tᵢ, tᵢ₊₁); past the last time it
    stays at its last value (lifelines' ``predict`` does the same), though
    the common-τ rule never asks for that.
    """
    times = np.asarray(times, dtype=float)
    surv = np.asarray(surv, dtype=float)
    keep = times < tau
    starts = np.concatenate([[0.0], times[keep]])
    levels = np.concatenate([[1.0], surv[keep]])
    ends = np.append(starts[1:], tau)
    return float(np.sum(levels * np.clip(ends - starts, 0.0, None)))


def km_rmst(data: pd.DataFrame, tau: float) -> float:
    """Restricted mean survival time of ONE group up to *tau*: the exact area
    under its KM step function (lifelines' ``restricted_mean_survival_time``
    of a fitted ``KaplanMeierFitter`` gives the same number)."""
    if data is None or not len(data) or tau is None or not np.isfinite(tau):
        return np.nan
    times, surv = _km_survival(data["time"], data["event"])
    return _step_area(times, surv, float(tau))


def common_tau(individual_data: pd.DataFrame) -> float:
    """The common restriction time: the smallest of the treatments' last
    observed times (death or censoring).

    Every treatment is followed at least that long, so every RMST compared
    against another is the area over the same window — comparing areas over
    different windows would credit a treatment for being watched longer.
    """
    groups = treatment_groups(individual_data)
    if not groups:
        if individual_data is None or not len(individual_data):
            return np.nan
        return float(individual_data["time"].max())
    return float(min(grp["time"].max() for _, grp in groups))


def mean_survival(individual_data: pd.DataFrame) -> pd.DataFrame:
    """Compute restricted mean survival time (RMST) for each treatment.

    The exact area under each treatment's KM step function from 0 to the
    common restriction time τ (:func:`common_tau`). Columns: ``treatment``,
    ``rmst``, ``restriction_time`` (τ, the same for every row).
    """
    tau = common_tau(individual_data)
    results = [{"treatment": treatment, "rmst": km_rmst(grp, tau),
                "restriction_time": tau}
               for treatment, grp in treatment_groups(individual_data)]
    return pd.DataFrame(results, columns=["treatment", "rmst", "restriction_time"])


def _km_mean_median_one_group(df: pd.DataFrame, tau: float) -> dict:
    """Compute KM-based mean (RMST up to *tau*) and median for a single group.

    Parameters
    ----------
    df : DataFrame with ``time`` and ``event`` columns.
    tau : the restriction time — the caller's common τ, so the means of the
        groups it compares cover the same window.
    """
    lt = _lifetable_one_treatment(df)
    median_t = _first_at_or_below(lt, "km_lx", 0.5) if len(lt) else np.nan
    rmst = km_rmst(df, tau)
    times = lt["time"].values if len(lt) else np.array([])
    return {"median": median_t, "mean_rmst": rmst,
            "t_max": float(times[-1]) if len(times) > 0 else np.nan}


def _top_percentile_mean(df: pd.DataFrame, percentile: float) -> float:
    """Mean lifespan of the longest-lived fraction of *dead* individuals.

    Only meaningful when censoring is minimal (assume_censored=False).

    Parameters
    ----------
    df : DataFrame with ``time`` and ``event`` columns.
    percentile : fraction to keep, e.g. 0.10 for top 10%.
    """
    deaths = df.loc[df["event"] == 1, "time"].sort_values(ascending=False)
    if len(deaths) == 0:
        return np.nan
    n_keep = max(1, int(np.ceil(len(deaths) * percentile)))
    return float(deaths.iloc[:n_keep].mean())


def lifespan_statistics(
    individual_data: pd.DataFrame,
    factors: list[str],
    assume_censored: bool = True,
) -> dict:
    """Compute mean and median lifespan statistics.

    Returns a dict with:
        treatment_stats : DataFrame — one row per treatment combination
        factor_stats    : DataFrame — one row per individual factor level
                          (e.g. all Males pooled, all 40x pooled)
        tau             : the restriction time every ``mean_rmst`` uses

    Columns in each DataFrame:
        group, n, n_deaths, n_censored, mean_rmst, tau, median, t_max
        (and top_10pct_mean, top_5pct_mean when assume_censored=False and n>10)

    ``mean_rmst`` is the area under the KM step function up to the **common**
    τ of :func:`mean_survival` — the smallest of the treatments' last observed
    times — in both tables, so it matches the Mean survival table and two
    rows are always means over the same window. ``t_max`` is still each
    group's own last observed time.
    """
    tau = common_tau(individual_data)

    def _stats_for_group(grp: pd.DataFrame, label: str) -> dict:
        n = len(grp)
        n_deaths = int(grp["event"].sum())
        n_censored = n - n_deaths
        km = _km_mean_median_one_group(grp, tau)

        rec = {
            "group": label,
            "n": n,
            "n_deaths": n_deaths,
            "n_censored": n_censored,
            "mean_rmst": round(km["mean_rmst"], 2) if not np.isnan(km["mean_rmst"]) else np.nan,
            "tau": round(tau, 2) if not np.isnan(tau) else np.nan,
            "median": round(km["median"], 2) if not np.isnan(km["median"]) else np.nan,
            "t_max": round(km["t_max"], 2) if not np.isnan(km["t_max"]) else np.nan,
        }

        if not assume_censored and n_deaths > 10:
            rec["top_10pct_mean"] = round(_top_percentile_mean(grp, 0.10), 2)
            rec["top_5pct_mean"] = round(_top_percentile_mean(grp, 0.05), 2)

        return rec

    # Per treatment combination
    treatment_rows = []
    for treatment, grp in treatment_groups(individual_data):
        treatment_rows.append(_stats_for_group(grp, treatment))
    treatment_stats = pd.DataFrame(treatment_rows)

    # Per individual factor level, in the factor's display order
    factor_rows = []
    for factor in factors:
        col = individual_data[factor]
        if isinstance(col.dtype, pd.CategoricalDtype):
            present = set(col.dropna().astype(str))
            levels = [str(c) for c in col.cat.categories if str(c) in present]
        else:
            levels = list(dict.fromkeys(col.dropna().astype(str)))
        text = col.astype(str)
        for level in levels:
            label = f"{factor}={level}"
            factor_rows.append(_stats_for_group(individual_data[text == level], label))
    factor_stats = pd.DataFrame(factor_rows)

    return {
        "treatment_stats": treatment_stats,
        "factor_stats": factor_stats,
        "tau": tau,
    }


def survival_quantiles(
    lifetable: pd.DataFrame,
    quantiles: list[float] | None = None,
) -> pd.DataFrame:
    """Compute survival time quantiles from the KM lifetable.

    Returns the time at which KM survival crosses each threshold for each
    treatment.

    Parameters
    ----------
    lifetable : DataFrame from ``compute_lifetables()``
    quantiles : survival fractions at which to report time, e.g. [0.90, 0.75, 0.50, 0.25, 0.10]

    Returns
    -------
    DataFrame with treatment and one column per quantile label.
    """
    if quantiles is None:
        quantiles = [0.90, 0.75, 0.50, 0.25, 0.10]

    records = []
    for treatment, grp in treatment_groups(lifetable):
        row: dict = {"treatment": treatment}
        for q in quantiles:
            below = grp[grp["km_lx"] <= q]
            col_name = f"S={int(q * 100)}%"
            row[col_name] = float(below["time"].iloc[0]) if len(below) > 0 else np.nan
        records.append(row)

    return pd.DataFrame(records)
