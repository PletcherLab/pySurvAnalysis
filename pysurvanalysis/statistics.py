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


def cox_interaction_analysis(
    data: pd.DataFrame,
    factors: list[str],
    selected_factors: list[str] | None = None,
) -> dict:
    """Fit Cox proportional hazards model with main effects and interactions.

    Builds a model with:
    * Main effects for each selected factor (dummy-coded)
    * All pairwise interaction terms between selected factors

    Parameters
    ----------
    data : DataFrame
        Individual-level survival data with columns ``time``, ``event``,
        and one column per factor.
    factors : list[str]
        All available factor column names.
    selected_factors : list[str] or None
        Which factors to include. Defaults to all factors.

    Returns
    -------
    dict with keys:
        model_type    — "cox_ph"
        factors_used  — list of factors in the model
        n_subjects    — number of individuals
        n_events      — number of deaths
        concordance   — concordance index (C-statistic)
        log_likelihood — partial log-likelihood
        AIC           — Akaike information criterion
        coefficients  — DataFrame of covariate name, coef, exp(coef)=HR,
                        se, z, p, lower 95% CI, upper 95% CI
        formula       — human-readable model formula
        warnings      — list of any convergence or assumption warnings
    """
    from lifelines import CoxPHFitter

    if selected_factors is None:
        selected_factors = list(factors)

    selected_factors = [f for f in selected_factors if f in data.columns]
    if len(selected_factors) == 0:
        return {"error": "No valid factors selected"}

    # Build the design matrix with dummy coding
    model_df = data[["time", "event"]].copy()

    dummy_frames = []
    for factor in selected_factors:
        dummies = pd.get_dummies(data[factor], prefix=factor, drop_first=True, dtype=float)
        dummy_frames.append(dummies)

    main_effects = pd.concat(dummy_frames, axis=1)
    model_df = pd.concat([model_df, main_effects], axis=1)

    # Build pairwise interaction terms
    interaction_cols = []
    for i, f1 in enumerate(selected_factors):
        for f2 in selected_factors[i + 1 :]:
            d1 = pd.get_dummies(data[f1], prefix=f1, drop_first=True, dtype=float)
            d2 = pd.get_dummies(data[f2], prefix=f2, drop_first=True, dtype=float)
            for c1 in d1.columns:
                for c2 in d2.columns:
                    int_name = f"{c1}:{c2}"
                    model_df[int_name] = d1[c1].values * d2[c2].values
                    interaction_cols.append(int_name)

    # Build formula description
    main_terms = list(main_effects.columns)
    formula = " + ".join(main_terms)
    if interaction_cols:
        formula += " + " + " + ".join(interaction_cols)

    warnings_list = []

    # Fit Cox model
    cph = CoxPHFitter()
    try:
        cph.fit(
            model_df,
            duration_col="time",
            event_col="event",
            show_progress=False,
        )
    except Exception as e:
        return {
            "model_type": "cox_ph",
            "factors_used": selected_factors,
            "error": str(e),
            "formula": formula,
            "warnings": [str(e)],
        }

    # Check convergence
    if hasattr(cph, "_show_progress") or not cph.summary is not None:
        pass  # lifelines handles convergence internally

    # Extract results
    summary_df = cph.summary.copy()
    summary_df = summary_df.rename(columns={
        "coef": "coef",
        "exp(coef)": "HR",
        "se(coef)": "se",
        "coef lower 95%": "coef_lo",
        "coef upper 95%": "coef_hi",
        "exp(coef) lower 95%": "HR_lo",
        "exp(coef) upper 95%": "HR_hi",
        "z": "z",
        "p": "p_value",
    })
    summary_df.index.name = "covariate"
    summary_df = summary_df.reset_index()

    # Classify each term
    term_types = []
    for cov in summary_df["covariate"]:
        if ":" in cov:
            term_types.append("interaction")
        else:
            term_types.append("main_effect")
    summary_df["term_type"] = term_types

    return {
        "model_type": "cox_ph",
        "factors_used": selected_factors,
        "n_subjects": cph.summary.shape[0] and len(model_df) or len(model_df),
        "n_events": int(model_df["event"].sum()),
        "concordance": round(cph.concordance_index_, 4),
        "log_likelihood": round(cph.log_likelihood_, 4) if hasattr(cph, "log_likelihood_") else None,
        "AIC": round(cph.AIC_partial_, 4) if hasattr(cph, "AIC_partial_") else None,
        "coefficients": summary_df,
        "formula": formula,
        "warnings": warnings_list,
        "log_likelihood_ratio_p": round(
            cph.log_likelihood_ratio_test().p_value, 6
        ) if hasattr(cph, "log_likelihood_ratio_test") else None,
    }


def rmst_interaction_analysis(
    data: pd.DataFrame,
    factors: list[str],
    selected_factors: list[str] | None = None,
    tau: float | None = None,
) -> dict:
    """RMST-based factorial interaction analysis using pseudo-values.

    For each individual, computes a jackknife pseudo-value of the RMST,
    then fits an OLS regression on these pseudo-values with the same
    factorial design (main effects + pairwise interactions) used in the
    Cox analysis.  This approach:

    * Does not assume proportional hazards
    * Coefficients are interpretable as differences in mean survival time
    * Interaction terms measure how the effect of one factor on mean
      survival depends on the level of another factor

    Parameters
    ----------
    data : DataFrame with ``time``, ``event``, and factor columns.
    factors : all available factor column names.
    selected_factors : which factors to include (default: all).
    tau : restriction time.  Defaults to the minimum of the per-treatment
          maximum observed times (so every group is fully observed).

    Returns
    -------
    dict matching the shape returned by ``cox_interaction_analysis`` so
    both can be rendered by the same UI / report code.  Key differences:

    * ``model_type`` is ``"rmst_pseudo"``
    * ``coefficients`` has ``coef`` in *hours* (not log-hazard), and
      ``HR`` / ``HR_lo`` / ``HR_hi`` are set to NaN (not applicable).
    """
    import statsmodels.api as sm

    if selected_factors is None:
        selected_factors = list(factors)
    selected_factors = [f for f in selected_factors if f in data.columns]
    if not selected_factors:
        return {"error": "No valid factors selected", "model_type": "rmst_pseudo"}

    # ── 1. Determine restriction time ────────────────────────────────
    if tau is None:
        tau = data.groupby("treatment")["time"].max().min()

    # ── 2. Compute overall RMST via KM ───────────────────────────────
    from .lifetable import _lifetable_one_treatment

    def _rmst(df: pd.DataFrame, t: float) -> float:
        lt = _lifetable_one_treatment(df)
        lt = lt[lt["time"] <= t]
        times = np.concatenate([[0.0], lt["time"].values])
        surv = np.concatenate([[1.0], lt["km_lx"].values])
        return float(np.trapezoid(surv, times))

    theta_all = _rmst(data, tau)
    n = len(data)

    # ── 3. Jackknife pseudo-values ───────────────────────────────────
    pseudo = np.empty(n)
    idx = data.index.values
    for j, ix in enumerate(idx):
        loo = data.drop(ix)
        theta_loo = _rmst(loo, tau)
        pseudo[j] = n * theta_all - (n - 1) * theta_loo

    # ── 4. Build design matrix ───────────────────────────────────────
    dummy_frames = []
    for factor in selected_factors:
        dummies = pd.get_dummies(data[factor], prefix=factor, drop_first=True, dtype=float)
        dummy_frames.append(dummies)

    X = pd.concat(dummy_frames, axis=1)

    # Interaction terms
    interaction_cols: list[str] = []
    for i, f1 in enumerate(selected_factors):
        for f2 in selected_factors[i + 1:]:
            d1 = pd.get_dummies(data[f1], prefix=f1, drop_first=True, dtype=float)
            d2 = pd.get_dummies(data[f2], prefix=f2, drop_first=True, dtype=float)
            for c1 in d1.columns:
                for c2 in d2.columns:
                    int_name = f"{c1}:{c2}"
                    X[int_name] = d1[c1].values * d2[c2].values
                    interaction_cols.append(int_name)

    main_terms = [c for c in X.columns if c not in interaction_cols]
    formula = " + ".join(main_terms)
    if interaction_cols:
        formula += " + " + " + ".join(interaction_cols)

    X = sm.add_constant(X)
    warnings_list: list[str] = []

    # ── 5. Fit OLS with robust (HC1) standard errors ────────────────
    try:
        model = sm.OLS(pseudo, X).fit(cov_type="HC1")
    except Exception as e:
        return {
            "model_type": "rmst_pseudo",
            "factors_used": selected_factors,
            "error": str(e),
            "formula": formula,
            "warnings": [str(e)],
        }

    # ── 6. Package results ───────────────────────────────────────────
    coef_df = pd.DataFrame({
        "covariate": model.params.index,
        "coef": model.params.values,
        "HR": np.nan,
        "se": model.bse.values,
        "z": model.tvalues.values,
        "p_value": model.pvalues.values,
        "coef_lo": model.conf_int()[0].values,
        "coef_hi": model.conf_int()[1].values,
        "HR_lo": np.nan,
        "HR_hi": np.nan,
    })

    term_types = []
    for cov in coef_df["covariate"]:
        if cov == "const":
            term_types.append("intercept")
        elif ":" in cov:
            term_types.append("interaction")
        else:
            term_types.append("main_effect")
    coef_df["term_type"] = term_types

    return {
        "model_type": "rmst_pseudo",
        "factors_used": selected_factors,
        "n_subjects": n,
        "n_events": int(data["event"].sum()),
        "tau": round(tau, 2),
        "rmst_overall": round(theta_all, 2),
        "r_squared": round(model.rsquared, 4),
        "f_statistic": round(model.fvalue, 4) if np.isfinite(model.fvalue) else None,
        "f_p_value": round(model.f_pvalue, 6) if np.isfinite(model.f_pvalue) else None,
        "coefficients": coef_df,
        "formula": formula,
        "warnings": warnings_list,
        "concordance": None,
        "AIC": round(model.aic, 4),
        "log_likelihood": round(model.llf, 4),
        "log_likelihood_ratio_p": None,
    }


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
