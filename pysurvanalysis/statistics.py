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
    """Fit Cox PH model and return interaction test + PH assumption test.

    Fits two models:
    * **Main-effects model** — dummy-coded factors, no interactions.
    * **Interaction model** — main effects plus all pairwise interaction terms.

    Reports:
    1. Interaction model coefficients (HRs, CIs, p-values).
    2. Omnibus likelihood-ratio test comparing the two models (tests whether
       any interaction term is needed).
    3. Schoenfeld-residuals test of the proportional-hazards assumption for
       each covariate in the interaction model.

    Parameters
    ----------
    data : DataFrame with ``time``, ``event``, and factor columns.
    factors : all available factor column names.
    selected_factors : which factors to include (default: all).

    Returns
    -------
    dict with keys:
        model_type        — "cox_ph"
        factors_used      — list of factors in the model
        n_subjects        — number of individuals
        n_events          — number of observed deaths
        concordance       — C-statistic of the interaction model
        log_likelihood    — partial log-likelihood of the interaction model
        AIC               — AIC of the interaction model
        coefficients      — DataFrame of covariate results
        formula           — human-readable formula for the interaction model
        warnings          — list of warnings
        lr_interaction    — dict with LR omnibus test results (or None if no
                            interaction terms possible)
        ph_test           — DataFrame of Schoenfeld residuals test results
                            (columns: covariate, test_statistic, p_value)
    """
    from lifelines import CoxPHFitter
    from lifelines.statistics import proportional_hazard_test
    from scipy.stats import chi2 as scipy_chi2

    if selected_factors is None:
        selected_factors = list(factors)

    selected_factors = [f for f in selected_factors if f in data.columns]
    if len(selected_factors) == 0:
        return {"error": "No valid factors selected", "model_type": "cox_ph"}

    # ── Build design matrices ──────────────────────────────────────────────
    base_df = data[["time", "event"]].copy()

    dummy_frames = []
    for factor in selected_factors:
        dummies = pd.get_dummies(data[factor], prefix=factor, drop_first=True, dtype=float)
        dummy_frames.append(dummies)
    main_effects = pd.concat(dummy_frames, axis=1)
    main_df = pd.concat([base_df, main_effects], axis=1)

    interaction_cols: list[str] = []
    inter_df = main_df.copy()
    for i, f1 in enumerate(selected_factors):
        for f2 in selected_factors[i + 1:]:
            d1 = pd.get_dummies(data[f1], prefix=f1, drop_first=True, dtype=float)
            d2 = pd.get_dummies(data[f2], prefix=f2, drop_first=True, dtype=float)
            for c1 in d1.columns:
                for c2 in d2.columns:
                    int_name = f"{c1}:{c2}"
                    inter_df[int_name] = d1[c1].values * d2[c2].values
                    interaction_cols.append(int_name)

    main_terms = list(main_effects.columns)
    formula = " + ".join(main_terms)
    if interaction_cols:
        formula += " + " + " + ".join(interaction_cols)

    warnings_list: list[str] = []

    # ── Fit main-effects model ─────────────────────────────────────────────
    cph_main = CoxPHFitter()
    try:
        cph_main.fit(main_df, duration_col="time", event_col="event", show_progress=False)
    except Exception as e:
        return {
            "model_type": "cox_ph",
            "factors_used": selected_factors,
            "error": f"Main-effects model failed: {e}",
            "formula": formula,
            "warnings": [str(e)],
        }

    # ── Fit interaction model ──────────────────────────────────────────────
    cph = CoxPHFitter()
    try:
        cph.fit(inter_df, duration_col="time", event_col="event", show_progress=False)
    except Exception as e:
        return {
            "model_type": "cox_ph",
            "factors_used": selected_factors,
            "error": f"Interaction model failed: {e}",
            "formula": formula,
            "warnings": [str(e)],
        }

    # ── LR omnibus interaction test ────────────────────────────────────────
    lr_interaction: dict | None = None
    if interaction_cols:
        ll_main = float(cph_main.log_likelihood_)
        ll_inter = float(cph.log_likelihood_)
        lr_stat = 2.0 * (ll_inter - ll_main)
        lr_df = len(interaction_cols)
        lr_p = float(scipy_chi2.sf(lr_stat, df=lr_df))
        lr_interaction = {
            "lr_stat": round(lr_stat, 4),
            "df": lr_df,
            "p_value": lr_p,
            "ll_main": round(ll_main, 4),
            "ll_interaction": round(ll_inter, 4),
            "concordance_main": round(float(cph_main.concordance_index_), 4),
            "interaction_cols": interaction_cols,
        }

    # ── Proportional-hazards assumption test (Schoenfeld residuals) ────────
    ph_test_df: pd.DataFrame | None = None
    try:
        ph_result = proportional_hazard_test(cph, inter_df, time_transform="rank")
        ph_summary = ph_result.summary.copy().reset_index()
        # Normalise column names across lifelines versions
        ph_summary.columns = [c.lower().replace(" ", "_") for c in ph_summary.columns]
        col_map = {}
        for c in ph_summary.columns:
            if c in ("covariate", "index", "coef"):
                col_map[c] = "covariate"
            elif "stat" in c or c == "test_statistic":
                col_map[c] = "test_statistic"
            elif c in ("p", "p_value", "p-val"):
                col_map[c] = "p_value"
        ph_summary = ph_summary.rename(columns=col_map)
        keep = [c for c in ("covariate", "test_statistic", "p_value") if c in ph_summary.columns]
        ph_test_df = ph_summary[keep]
    except Exception as e:
        warnings_list.append(f"PH assumption test failed: {e}")

    # ── Extract interaction model coefficients ─────────────────────────────
    summary_df = cph.summary.copy().rename(columns={
        "exp(coef)": "HR",
        "se(coef)": "se",
        "coef lower 95%": "coef_lo",
        "coef upper 95%": "coef_hi",
        "exp(coef) lower 95%": "HR_lo",
        "exp(coef) upper 95%": "HR_hi",
        "p": "p_value",
    })
    summary_df.index.name = "covariate"
    summary_df = summary_df.reset_index()

    term_types = [
        "interaction" if ":" in cov else "main_effect"
        for cov in summary_df["covariate"]
    ]
    summary_df["term_type"] = term_types

    return {
        "model_type": "cox_ph",
        "factors_used": selected_factors,
        "n_subjects": len(inter_df),
        "n_events": int(inter_df["event"].sum()),
        "concordance": round(float(cph.concordance_index_), 4),
        "log_likelihood": round(float(cph.log_likelihood_), 4),
        "AIC": round(float(cph.AIC_partial_), 4),
        "coefficients": summary_df,
        "formula": formula,
        "warnings": warnings_list,
        "log_likelihood_ratio_p": round(
            cph.log_likelihood_ratio_test().p_value, 6
        ) if hasattr(cph, "log_likelihood_ratio_test") else None,
        "lr_interaction": lr_interaction,
        "ph_test": ph_test_df,
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


def gehan_wilcoxon_test(
    data: pd.DataFrame,
    group1: str,
    group2: str,
) -> dict:
    """Two-sample Gehan-Wilcoxon weighted log-rank test.

    Uses number-at-risk as weights at each event time, giving more weight
    to early differences in survival (unlike the unweighted log-rank).

    Returns
    -------
    dict with keys: group1, group2, chi2, p_value, df
    """
    subset = data[data["treatment"].isin([group1, group2])].copy()
    groups = [group1, group2]
    table = _build_count_table(subset, groups)

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

        weight = n_total  # Gehan-Wilcoxon weight
        e1 = n1 * d_total / n_total
        observed_1 += weight * d1
        expected_1 += weight * e1

        if n_total > 1:
            v = (weight ** 2) * (n1 * n2 * d_total * (n_total - d_total)) / (n_total ** 2 * (n_total - 1))
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
        "chi2": round(chi2, 4),
        "p_value": p_value,
        "df": 1,
    }


def pairwise_gehan_wilcoxon(data: pd.DataFrame) -> pd.DataFrame:
    """Run Gehan-Wilcoxon tests for every pairwise combination of treatments.

    Returns a DataFrame with one row per pair, including Bonferroni-corrected
    p-values.
    """
    treatments = sorted(data["treatment"].unique())
    results = []

    for g1, g2 in combinations(treatments, 2):
        result = gehan_wilcoxon_test(data, g1, g2)
        results.append(result)

    df = pd.DataFrame(results)
    if len(df) > 0:
        n_tests = len(df)
        df["p_bonferroni"] = (df["p_value"] * n_tests).clip(upper=1.0)
        df["significant_0.05"] = df["p_bonferroni"] < 0.05
    return df


def fit_parametric_models(
    data: pd.DataFrame,
    treatments: list[str] | None = None,
) -> dict:
    """Fit parametric survival models (Weibull, log-normal, log-logistic).

    For each treatment group and each distribution, fits a parametric
    accelerated failure time (AFT) model via lifelines and returns
    parameter estimates and AIC for model comparison.

    Parameters
    ----------
    data : DataFrame with ``time``, ``event``, ``treatment``
    treatments : subset of treatments to fit (default: all)

    Returns
    -------
    dict with keys:
        results_by_treatment : dict of treatment → list of model dicts
        aic_comparison : DataFrame with AIC for each model/treatment
        best_model_per_treatment : dict of treatment → best model name
    """
    from lifelines import WeibullAFTFitter, LogNormalAFTFitter, LogLogisticAFTFitter

    if treatments is None:
        treatments = sorted(data["treatment"].unique())

    model_classes = {
        "Weibull": WeibullAFTFitter,
        "Log-Normal": LogNormalAFTFitter,
        "Log-Logistic": LogLogisticAFTFitter,
    }

    results_by_treatment: dict[str, list[dict]] = {}
    aic_records = []

    for treatment in treatments:
        grp = data[data["treatment"] == treatment][["time", "event"]].copy()
        if len(grp) < 5 or grp["event"].sum() < 2:
            continue

        treatment_results = []
        for model_name, ModelClass in model_classes.items():
            try:
                model = ModelClass()
                model.fit(grp, duration_col="time", event_col="event")
                aic = float(model.AIC_)
                params = model.params_.to_dict() if hasattr(model.params_, "to_dict") else {}
                median_t = float(model.median_survival_time_) if hasattr(model, "median_survival_time_") else np.nan
                treatment_results.append({
                    "model": model_name,
                    "aic": round(aic, 2),
                    "log_likelihood": round(float(model.log_likelihood_), 4),
                    "params": params,
                    "median_survival": round(median_t, 2) if np.isfinite(median_t) else np.nan,
                    "fitted_model": model,
                })
                aic_records.append({
                    "treatment": treatment,
                    "model": model_name,
                    "aic": round(aic, 2),
                    "log_likelihood": round(float(model.log_likelihood_), 4),
                    "median_survival": round(median_t, 2) if np.isfinite(median_t) else np.nan,
                })
            except Exception:
                pass

        results_by_treatment[treatment] = treatment_results

    aic_df = pd.DataFrame(aic_records)
    best_per_treatment: dict[str, str] = {}
    if len(aic_df) > 0:
        idx = aic_df.groupby("treatment")["aic"].idxmin()
        for _, row in aic_df.loc[idx].iterrows():
            best_per_treatment[row["treatment"]] = row["model"]

    return {
        "results_by_treatment": results_by_treatment,
        "aic_comparison": aic_df,
        "best_model_per_treatment": best_per_treatment,
    }


def survival_quantiles(
    data: pd.DataFrame,
    quantiles: list[float] | None = None,
) -> pd.DataFrame:
    """Compute survival time quantiles from KM curves.

    Returns the time at which survival drops below each quantile for each
    treatment.  Uses the KM step function, so the reported time is the
    first event time where S(t) ≤ (1 - quantile).

    Parameters
    ----------
    data : individual-level DataFrame with ``time``, ``event``, ``treatment``
    quantiles : list of quantiles as fractions, e.g. [0.10, 0.25, 0.50, 0.75, 0.90]

    Returns
    -------
    DataFrame with treatment as index and one column per quantile.
    """
    from .lifetable import _lifetable_one_treatment

    if quantiles is None:
        quantiles = [0.10, 0.25, 0.50, 0.75, 0.90]

    records = []
    for treatment, grp in data.groupby("treatment"):
        lt = _lifetable_one_treatment(grp)
        row: dict = {"treatment": treatment}
        for q in quantiles:
            threshold = 1.0 - q
            below = lt[lt["km_lx"] <= threshold]
            row[f"q{int(q * 100)}"] = float(below["time"].iloc[0]) if len(below) > 0 else np.nan
        records.append(row)

    return pd.DataFrame(records)


def experiment_summary(data: pd.DataFrame) -> dict:
    """Compute experiment-level summary statistics.

    Returns
    -------
    dict with: n_treatments, n_chambers, n_total, n_deaths, n_censored,
               pct_censored, time_min, time_max, factors
    """
    n_total = len(data)
    n_deaths = int(data["event"].sum())
    n_censored = n_total - n_deaths
    treatments = sorted(data["treatment"].unique())

    n_chambers = int(data["chamber"].nunique()) if "chamber" in data.columns else None
    time_min = float(data["time"].min())
    time_max = float(data["time"].max())

    factor_cols = [c for c in data.columns if c not in ("time", "event", "treatment", "chamber")]

    return {
        "n_treatments": len(treatments),
        "n_chambers": n_chambers,
        "n_total": n_total,
        "n_deaths": n_deaths,
        "n_censored": n_censored,
        "pct_censored": round(100 * n_censored / n_total, 1) if n_total > 0 else 0,
        "time_min": time_min,
        "time_max": time_max,
        "treatments": treatments,
        "factors": factor_cols,
    }
