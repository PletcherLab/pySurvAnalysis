"""Statistical tests for survival analysis.

Currently implements:
* Log-rank test (pairwise and omnibus/multi-group)
* Restricted mean survival time (RMST) differences
* Hazard ratio estimates

Designed for extension with Cox proportional hazards, interaction tests, etc.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


def _build_count_table(
    data: pd.DataFrame,
    groups: list[str],
) -> pd.DataFrame:
    """Build a table of observed and expected deaths at each event time.

    Used internally by the log-rank test.
    """
    all_times = sorted(data.loc[data["event"] == 1, "time"].unique())

    records = []
    for t in all_times:
        row = {"time": t}
        for g in groups:
            g_data = data[data["treatment"] == g]
            at_risk = ((g_data["time"] >= t)).sum()
            deaths = ((g_data["time"] == t) & (g_data["event"] == 1)).sum()
            row[f"n_{g}"] = at_risk
            row[f"d_{g}"] = deaths
        records.append(row)

    return pd.DataFrame(records)


def logrank_test(
    data: pd.DataFrame,
    group1: str,
    group2: str,
) -> dict:
    """Two-sample log-rank test (Mantel-Cox).

    Parameters
    ----------
    data : DataFrame with columns ``time``, ``event``, ``treatment``
    group1, group2 : treatment labels to compare

    Returns
    -------
    dict with keys: group1, group2, chi2, p_value, df
    """
    subset = data[data["treatment"].isin([group1, group2])].copy()
    groups = [group1, group2]
    table = _build_count_table(subset, groups)

    # O - E for group1
    observed_1 = 0.0
    expected_1 = 0.0
    variance = 0.0

    for _, row in table.iterrows():
        n1 = row[f"n_{group1}"]
        n2 = row[f"n_{group2}"]
        d1 = row[f"d_{group1}"]
        d2 = row[f"d_{group2}"]
        n_total = n1 + n2
        d_total = d1 + d2

        if n_total == 0:
            continue

        e1 = n1 * d_total / n_total
        observed_1 += d1
        expected_1 += e1

        if n_total > 1:
            v = (n1 * n2 * d_total * (n_total - d_total)) / (n_total ** 2 * (n_total - 1))
            variance += v

    if variance > 0:
        chi2 = (observed_1 - expected_1) ** 2 / variance
        p_value = 1 - stats.chi2.cdf(chi2, df=1)
    else:
        chi2 = 0.0
        p_value = 1.0

    return {
        "group1": group1,
        "group2": group2,
        "observed_1": observed_1,
        "expected_1": expected_1,
        "chi2": round(chi2, 4),
        "p_value": p_value,
        "df": 1,
    }


def logrank_multi(data: pd.DataFrame) -> dict:
    """Multi-group (omnibus) log-rank test.

    Uses the K-sample extension of the log-rank test for K treatment groups.

    Returns
    -------
    dict with keys: chi2, p_value, df, groups
    """
    groups = sorted(data["treatment"].unique())
    k = len(groups)
    if k < 2:
        return {"chi2": 0.0, "p_value": 1.0, "df": 0, "groups": groups}

    event_times = sorted(data.loc[data["event"] == 1, "time"].unique())

    # O-E vector and variance-covariance matrix (K-1 x K-1)
    oe = np.zeros(k - 1)
    V = np.zeros((k - 1, k - 1))

    for t in event_times:
        n = np.array([((data["treatment"] == g) & (data["time"] >= t)).sum() for g in groups], dtype=float)
        d = np.array([((data["treatment"] == g) & (data["time"] == t) & (data["event"] == 1)).sum() for g in groups], dtype=float)

        N = n.sum()
        D = d.sum()

        if N <= 1 or D == 0:
            continue

        e = n * D / N  # expected deaths per group

        for i in range(k - 1):
            oe[i] += d[i] - e[i]
            for j in range(k - 1):
                if i == j:
                    V[i, j] += (n[i] * (N - n[i]) * D * (N - D)) / (N ** 2 * (N - 1))
                else:
                    V[i, j] -= (n[i] * n[j] * D * (N - D)) / (N ** 2 * (N - 1))

    try:
        V_inv = np.linalg.inv(V)
        chi2 = float(oe @ V_inv @ oe)
        p_value = 1 - stats.chi2.cdf(chi2, df=k - 1)
    except np.linalg.LinAlgError:
        chi2 = 0.0
        p_value = 1.0

    return {
        "chi2": round(chi2, 4),
        "p_value": p_value,
        "df": k - 1,
        "groups": groups,
    }


def pairwise_logrank(data: pd.DataFrame) -> pd.DataFrame:
    """Run log-rank tests for every pairwise combination of treatments.

    Returns a DataFrame with one row per pair, including Bonferroni-corrected
    p-values.
    """
    treatments = sorted(data["treatment"].unique())
    results = []

    for g1, g2 in combinations(treatments, 2):
        result = logrank_test(data, g1, g2)
        results.append(result)

    df = pd.DataFrame(results)
    if len(df) > 0:
        n_tests = len(df)
        df["p_bonferroni"] = (df["p_value"] * n_tests).clip(upper=1.0)
        df["significant_0.05"] = df["p_bonferroni"] < 0.05
    return df


def hazard_ratio_estimate(
    data: pd.DataFrame,
    group1: str,
    group2: str,
) -> dict:
    """Estimate hazard ratio using the log-rank O/E method.

    HR = (O1/E1) / (O2/E2) where group1 is numerator.
    This is a simple non-parametric estimate; for proper HR with CI,
    use Cox regression (future extension).
    """
    subset = data[data["treatment"].isin([group1, group2])].copy()
    groups = [group1, group2]
    table = _build_count_table(subset, groups)

    o1, e1, o2, e2 = 0.0, 0.0, 0.0, 0.0
    for _, row in table.iterrows():
        n1 = row[f"n_{group1}"]
        n2 = row[f"n_{group2}"]
        d1 = row[f"d_{group1}"]
        d2 = row[f"d_{group2}"]
        n_total = n1 + n2
        d_total = d1 + d2

        if n_total == 0:
            continue

        o1 += d1
        o2 += d2
        e1 += n1 * d_total / n_total
        e2 += n2 * d_total / n_total

    if e1 > 0 and e2 > 0 and o2 > 0:
        hr = (o1 / e1) / (o2 / e2)
        # Approximate 95% CI using log(HR) ~ Normal
        se_log_hr = np.sqrt(1 / e1 + 1 / e2)
        ci_lo = np.exp(np.log(hr) - 1.96 * se_log_hr)
        ci_hi = np.exp(np.log(hr) + 1.96 * se_log_hr)
    else:
        hr = np.nan
        ci_lo = np.nan
        ci_hi = np.nan

    return {
        "group1": group1,
        "group2": group2,
        "hazard_ratio": round(hr, 4) if not np.isnan(hr) else np.nan,
        "hr_ci_lo": round(ci_lo, 4) if not np.isnan(ci_lo) else np.nan,
        "hr_ci_hi": round(ci_hi, 4) if not np.isnan(ci_hi) else np.nan,
    }


def pairwise_hazard_ratios(data: pd.DataFrame) -> pd.DataFrame:
    """Compute hazard ratio estimates for all pairwise treatment comparisons."""
    treatments = sorted(data["treatment"].unique())
    results = []
    for g1, g2 in combinations(treatments, 2):
        results.append(hazard_ratio_estimate(data, g1, g2))
    return pd.DataFrame(results)


def summary_statistics(data: pd.DataFrame) -> pd.DataFrame:
    """Summary counts per treatment: N, deaths, censored, % censored."""
    records = []
    for treatment, grp in data.groupby("treatment"):
        n = len(grp)
        deaths = int(grp["event"].sum())
        censored = n - deaths
        records.append({
            "treatment": treatment,
            "n_individuals": n,
            "n_deaths": deaths,
            "n_censored": censored,
            "pct_censored": round(100 * censored / n, 1) if n > 0 else 0,
        })
    return pd.DataFrame(records)
