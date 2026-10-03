"""Statistical tests for survival analysis.

Currently implements:
* Log-rank and Gehan-Wilcoxon tests (pairwise and omnibus/multi-group)
* Pairwise hazard ratio estimates (log-rank O/E)
* The Factorial Battery's models — Cox main effects vs interactions, and the
  RMST pseudo-value regression
* Parametric AFT fits per treatment

Treatments are always taken in **display order** (:func:`treatment_order`) —
the Focus's level order, never alphabetical — so a pairwise table, a hazard
ratio's direction and every figure agree about which treatment comes first.
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Display order
# ---------------------------------------------------------------------------

def treatment_order(frame: pd.DataFrame) -> list[str]:
    """The treatments of *frame* in display order, as text.

    The ``treatment`` column's category order when it is categorical — which
    :func:`~pysurvanalysis.domain.focus.apply_focus` makes it, in the Focus's
    level order — otherwise the order of first appearance. Only labels with at
    least one row are returned. Never alphabetical: sorting would put
    ``mDilp235bx`` before ``wCS`` in every table and flip the direction of
    every pairwise hazard ratio, whatever order the Focus declared.
    """
    if frame is None or "treatment" not in getattr(frame, "columns", ()) or not len(frame):
        return []
    col = frame["treatment"]
    present = list(dict.fromkeys(col.dropna().astype(str)))
    if isinstance(col.dtype, pd.CategoricalDtype):
        seen = set(present)
        return [str(c) for c in col.cat.categories if str(c) in seen]
    return present


def treatment_groups(frame: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """``(label, rows)`` per treatment, in :func:`treatment_order`."""
    if frame is None or "treatment" not in getattr(frame, "columns", ()) or not len(frame):
        return []
    labels = frame["treatment"].astype(str)
    return [(t, frame[labels == t]) for t in treatment_order(frame)]


@contextmanager
def _collect_warnings(sink: list[str]):
    """Record what a model fit warns about into *sink*, deduplicated.

    A fit that "converged" with a warning (a near-singular design, a halted
    Newton step, a PH test that could not run) produces numbers that look as
    sound as any other; the warning is part of the result and travels with
    it into the model dict, the Run Summary and the report. Library
    housekeeping (deprecations, future-version notices) is not. Kept even
    when the fit then fails, since the warning often says why.
    """
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            yield
        finally:
            for w in caught:
                if issubclass(w.category, (DeprecationWarning, PendingDeprecationWarning,
                                           FutureWarning)):
                    continue
                lines = str(w.message).strip().splitlines()
                if lines and lines[0] not in sink:
                    sink.append(lines[0])


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
    dict with keys: chi2, p_value, df, groups (in display order)
    """
    groups = treatment_order(data)
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
    p-values. Pairs follow display order: ``group1`` is the treatment earlier
    in :func:`treatment_order`.
    """
    treatments = treatment_order(data)
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
    """Compute hazard ratio estimates for all pairwise treatment comparisons.

    Each ratio is ``group1`` over ``group2``, where ``group1`` is the treatment
    earlier in display order (:func:`treatment_order`) — so the direction of
    every ratio follows the Focus's level order, not the alphabet.
    """
    treatments = treatment_order(data)
    results = []
    for g1, g2 in combinations(treatments, 2):
        results.append(hazard_ratio_estimate(data, g1, g2))
    return pd.DataFrame(results)


def cox_interaction_analysis(
    data: pd.DataFrame,
    factors: list[str],
    selected_factors: list[str] | None = None,
    interactions: bool = True,
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
    interactions : ``False`` fits the main-effects model alone — its
        coefficients, its PH test, and no LR interaction test.

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
        warnings          — what the fits and the PH test warned about (a
                            convergence problem, a PH test that could not
                            run) — reported with the model, never dropped
        lr_interaction    — dict with LR omnibus test results (or None if no
                            interaction terms possible); the χ² is
                            ``statistic`` (``lr_stat`` is kept for readers of
                            summaries written before the rename)
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
    for i, f1 in enumerate(selected_factors if interactions else []):
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
        with _collect_warnings(warnings_list):
            cph_main.fit(main_df, duration_col="time", event_col="event", show_progress=False)
    except Exception as e:
        return {
            "model_type": "cox_ph",
            "factors_used": selected_factors,
            "error": f"Main-effects model failed: {e}",
            "formula": formula,
            "warnings": warnings_list + [str(e)],
        }

    # ── Fit interaction model ──────────────────────────────────────────────
    ## With no interaction terms (one factor, or interactions off) the two
    ## models are the same model; fitting it twice only doubles the warnings.
    cph = cph_main
    if interaction_cols:
        cph = CoxPHFitter()
        try:
            with _collect_warnings(warnings_list):
                cph.fit(inter_df, duration_col="time", event_col="event",
                        show_progress=False)
        except Exception as e:
            return {
                "model_type": "cox_ph",
                "factors_used": selected_factors,
                "error": f"Interaction model failed: {e}",
                "formula": formula,
                "warnings": warnings_list + [str(e)],
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
            ## "statistic" is the name every reader looks for; "lr_stat" stays
            ## for anything still reading summaries written before it.
            "statistic": round(lr_stat, 4),
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
        with _collect_warnings(warnings_list):
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
    ## lifelines' "cmp to" is the null value each β is tested against — 0 in
    ## every row of every model here, so a column of zeros the report would
    ## print beside the p-values.
    summary_df = summary_df.drop(columns=["cmp to"], errors="ignore").reset_index()

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
          maximum observed times (so every group is fully observed) — the
          same common τ as the Mean survival table.

    Returns
    -------
    dict matching the shape returned by ``cox_interaction_analysis`` so
    both can be rendered by the same UI / report code.  Key differences:

    * ``model_type`` is ``"rmst_pseudo"``
    * ``tau`` is the restriction time used, ``r_squared`` / ``f_statistic`` /
      ``f_p_value`` describe the regression
    * ``coefficients`` has ``coef`` in the data's time unit (not
      log-hazard), and ``HR`` / ``HR_lo`` / ``HR_hi`` are NaN (not applicable).
    """
    import statsmodels.api as sm

    from .lifetable import _km_survival, _step_area, common_tau

    if selected_factors is None:
        selected_factors = list(factors)
    selected_factors = [f for f in selected_factors if f in data.columns]
    if not selected_factors:
        return {"error": "No valid factors selected", "model_type": "rmst_pseudo"}

    # ── 1. Determine restriction time ────────────────────────────────
    if tau is None:
        tau = common_tau(data)
    tau = float(tau)

    # ── 2. RMST of the whole sample: the exact area under the KM step
    #       function up to τ (trapezoids would understate every step) ──
    times = data["time"].to_numpy(dtype=float)
    events = data["event"].to_numpy(dtype=float)

    def _rmst(t: np.ndarray, e: np.ndarray) -> float:
        steps, surv = _km_survival(t, e)
        return _step_area(steps, surv, tau)

    theta_all = _rmst(times, events)
    n = len(data)

    # ── 3. Jackknife pseudo-values ───────────────────────────────────
    ## Leaving out either of two individuals with the same (time, event)
    ## gives the same curve, so each distinct pair is refitted once — census
    ## data ties heavily, which makes this the difference between seconds
    ## and minutes on a large Focus.
    pseudo = np.empty(n)
    loo_cache: dict[tuple[float, float], float] = {}
    keep = np.ones(n, dtype=bool)
    for j in range(n):
        key = (times[j], events[j])
        theta_loo = loo_cache.get(key)
        if theta_loo is None:
            keep[j] = False
            theta_loo = _rmst(times[keep], events[keep])
            keep[j] = True
            loo_cache[key] = theta_loo
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
        with _collect_warnings(warnings_list):
            model = sm.OLS(pseudo, X).fit(cov_type="HC1")
            fvalue = float(np.squeeze(model.fvalue))
            f_pvalue = float(np.squeeze(model.f_pvalue))
    except Exception as e:
        return {
            "model_type": "rmst_pseudo",
            "factors_used": selected_factors,
            "error": str(e),
            "formula": formula,
            "tau": round(tau, 4),
            "warnings": warnings_list + [str(e)],
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
        "tau": round(tau, 4),
        "rmst_overall": round(theta_all, 4),
        "r_squared": round(float(model.rsquared), 4),
        "f_statistic": round(fvalue, 4) if np.isfinite(fvalue) else None,
        "f_p_value": f_pvalue if np.isfinite(f_pvalue) else None,
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
    for treatment, grp in treatment_groups(data):
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
    p-values. Pairs follow display order, as :func:`pairwise_logrank`.
    """
    treatments = treatment_order(data)
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


#: Below these a treatment gets no parametric fit (and a row saying why).
AFT_MIN_INDIVIDUALS = 5
AFT_MIN_DEATHS = 2


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
        aic_comparison : DataFrame with AIC for each fitted model/treatment
                         (plus ``delta_aic`` from the treatment's best, and
                         ``best``)
        best_model_per_treatment : dict of treatment → best model name
        not_fitted : ``{"treatment", "model", "reason"}`` for every treatment
                     too small to fit (``model`` None) and every fit that
                     failed — said, never silently missing
        table : :func:`parametric_table` of the above — every treatment ×
                model, fitted or not, in display order
    """
    from lifelines import WeibullAFTFitter, LogNormalAFTFitter, LogLogisticAFTFitter

    if treatments is None:
        treatments = treatment_order(data)

    model_classes = {
        "Weibull": WeibullAFTFitter,
        "Log-Normal": LogNormalAFTFitter,
        "Log-Logistic": LogLogisticAFTFitter,
    }

    results_by_treatment: dict[str, list[dict]] = {}
    aic_records = []
    not_fitted: list[dict] = []
    labels = data["treatment"].astype(str)

    for treatment in treatments:
        grp = data[labels == str(treatment)][["time", "event"]].copy()
        ## Two parameters from fewer than five individuals or one death is
        ## not an estimate. Recorded, so the report says why the treatment
        ## has no row rather than leaving it to look forgotten.
        if len(grp) < AFT_MIN_INDIVIDUALS:
            not_fitted.append({"treatment": treatment, "model": None,
                               "reason": f"only {len(grp)} individual(s) — "
                                         f"needs at least {AFT_MIN_INDIVIDUALS}"})
            continue
        n_deaths = int(grp["event"].sum())
        if n_deaths < AFT_MIN_DEATHS:
            not_fitted.append({"treatment": treatment, "model": None,
                               "reason": f"only {n_deaths} death(s) — "
                                         f"needs at least {AFT_MIN_DEATHS}"})
            continue

        treatment_results = []
        for model_name, ModelClass in model_classes.items():
            try:
                model = ModelClass()
                model.fit(grp, duration_col="time", event_col="event")
                aic = float(model.AIC_)
                if not np.isfinite(aic):
                    raise ValueError("the fit did not converge (non-finite AIC)")
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
            except Exception as exc:  # noqa: BLE001 - one failed family is a row, not a crash
                message = str(exc).strip().splitlines()
                not_fitted.append({"treatment": treatment, "model": model_name,
                                   "reason": f"fit failed: "
                                             f"{message[0] if message else type(exc).__name__}"})

        results_by_treatment[treatment] = treatment_results

    aic_df = pd.DataFrame(aic_records, columns=["treatment", "model", "aic",
                                                "log_likelihood", "median_survival"])
    best_per_treatment: dict[str, str] = {}
    if len(aic_df) > 0:
        idx = aic_df.groupby("treatment", sort=False)["aic"].idxmin()
        for _, row in aic_df.loc[idx].iterrows():
            best_per_treatment[row["treatment"]] = row["model"]
        aic_df["delta_aic"] = (aic_df["aic"]
                               - aic_df.groupby("treatment", sort=False)["aic"].transform("min")).round(2)
        aic_df["best"] = [best_per_treatment.get(t) == mdl
                          for t, mdl in zip(aic_df["treatment"], aic_df["model"])]

    fit = {
        "results_by_treatment": results_by_treatment,
        "aic_comparison": aic_df,
        "best_model_per_treatment": best_per_treatment,
        "not_fitted": not_fitted,
    }
    fit["table"] = parametric_table(fit, order=list(treatments),
                                    models=list(model_classes))
    return fit


#: The columns of :func:`parametric_table` — the CSV, the Run Summary's
#: ``parametric_models`` records and the report's table.
PARAMETRIC_COLUMNS = ("treatment", "model", "aic", "delta_aic", "log_likelihood",
                      "median_survival", "best", "note")


def parametric_table(fit: dict | None, order: list[str] | None = None,
                     models: list[str] | None = None) -> pd.DataFrame:
    """One row per treatment × model, fitted or not — the readable form of
    :func:`fit_parametric_models`.

    Fitted rows carry ``aic``, ``delta_aic`` (from that treatment's best, so 0
    marks it), ``log_likelihood``, the model's ``median_survival`` and
    ``best``; a family that failed, or a treatment too small to fit (``model``
    empty), carries the reason in ``note`` instead of numbers.
    """
    columns = list(PARAMETRIC_COLUMNS)
    if not fit:
        return pd.DataFrame(columns=columns)
    if isinstance(fit.get("table"), pd.DataFrame) and order is None:
        return fit["table"]
    if fit.get("error"):
        ## The whole step failed — one row saying so, so the CSV, the Run
        ## Summary and the report all carry the reason.
        return pd.DataFrame([{"treatment": None, "model": None, "aic": np.nan,
                              "delta_aic": np.nan, "log_likelihood": np.nan,
                              "median_survival": np.nan, "best": False,
                              "note": f"not fitted: {fit['error']}"}], columns=columns)
    aic = fit.get("aic_comparison")
    rows: list[dict] = []
    for rec in (aic.to_dict("records") if isinstance(aic, pd.DataFrame) else []):
        rows.append({**rec, "note": "lowest AIC" if rec.get("best") else ""})
    for item in fit.get("not_fitted") or []:
        rows.append({"treatment": item.get("treatment"), "model": item.get("model"),
                     "aic": np.nan, "delta_aic": np.nan, "log_likelihood": np.nan,
                     "median_survival": np.nan, "best": False,
                     "note": f"not fitted: {item.get('reason')}"})
    if not rows:
        return pd.DataFrame(columns=columns)
    frame = pd.DataFrame(rows).reindex(columns=columns)
    order = order or list(dict.fromkeys(str(t) for t in frame["treatment"]))
    models = models or ["Weibull", "Log-Normal", "Log-Logistic"]
    t_rank = {str(t): i for i, t in enumerate(order)}
    m_rank = {m: i for i, m in enumerate(models)}
    frame["_t"] = frame["treatment"].astype(str).map(t_rank).fillna(len(t_rank))
    frame["_m"] = frame["model"].map(m_rank).fillna(-1)
    frame = frame.sort_values(["_t", "_m"], kind="stable").drop(columns=["_t", "_m"])
    frame["best"] = frame["best"].fillna(False).astype(bool)
    return frame.reset_index(drop=True)


def parametric_records(fit: dict | None) -> list[dict]:
    """:func:`parametric_table` as JSON-safe records (NaN → None) — what the
    Run Summary stores under ``parametric_models``."""
    table = parametric_table(fit)
    records: list[dict] = []
    for rec in table.to_dict("records"):
        clean = {}
        for key, value in rec.items():
            if isinstance(value, (float, np.floating)):
                clean[key] = None if not np.isfinite(value) else float(value)
            elif isinstance(value, (np.integer,)):
                clean[key] = int(value)
            elif isinstance(value, (bool, np.bool_)):
                clean[key] = bool(value)
            elif value is None or (not isinstance(value, str) and pd.isna(value)):
                clean[key] = None
            else:
                clean[key] = str(value)
        records.append(clean)
    return records


def experiment_summary(data: pd.DataFrame) -> dict:
    """Compute experiment-level summary statistics.

    Returns
    -------
    dict with: n_treatments, n_chambers, n_total, n_deaths, n_censored,
               pct_censored, time_min, time_max, treatments (display
               order), factors
    """
    n_total = len(data)
    n_deaths = int(data["event"].sum())
    n_censored = n_total - n_deaths
    treatments = treatment_order(data)

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
