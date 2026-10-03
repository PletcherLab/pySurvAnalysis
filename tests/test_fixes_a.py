"""Statistics, report and saved-result fixes (agent A of the manual bug sweep).

Each test names the bug it would have caught. Numerics are checked against
lifelines wherever lifelines computes the same quantity.
"""

from __future__ import annotations

import hashlib
import json
import warnings

import numpy as np
import pandas as pd
import pytest

from pysurvanalysis import exclusions, lifetable, pipeline, project_report, statistics
from pysurvanalysis import report_builder as rb
from pysurvanalysis.domain import SurvivalExperiment, config as cfgmod
from pysurvanalysis.report_pkg import model as m

from conftest import FACTORIAL, make_experiment_dir, write_dlife_workbook


def _blocks_of(report, kind):
    return [b for b in report.blocks if isinstance(b, kind)]


def _tables(blocks, title_part):
    return [b for b in blocks if isinstance(b, m.Table) and title_part in (b.title or "")]


def _cohort(seed=0, n=40, groups=("wt", "mut"), all_die=False):
    """Census-like times (heavy ties), some censoring, ``treatment`` as an
    ordered Categorical in the given (non-alphabetical) order."""
    rng = np.random.default_rng(seed)
    rows = []
    for i, g in enumerate(groups):
        t = np.round(rng.gamma(4, (30 + 8 * i) / 4, n) / 3) * 3
        e = np.ones(n, int) if all_die else (rng.random(n) > 0.2).astype(int)
        rows += [{"time": float(a), "event": int(b), "treatment": g} for a, b in zip(t, e)]
    frame = pd.DataFrame(rows)
    frame["treatment"] = pd.Categorical(frame["treatment"], categories=list(groups),
                                        ordered=True)
    return frame


@pytest.fixture(scope="module")
def workbook_run(tmp_path_factory):
    """A DLife workbook (8 chambers of 20, 2 per cell) whose Exclusion Group
    lists one chamber the file holds (2) and one it never had (99), with a
    min_n_per_chamber every chamber falls below."""
    directory = tmp_path_factory.mktemp("wb") / "wb"
    write_dlife_workbook(directory / "data" / "wb.xlsx", chambers=8)
    cfgmod.save_config(directory, {"input": {"format": "excel"},
                                   "exclusions": {"group": "qc"},
                                   "global": {"min_n_per_chamber": 25}})
    exclusions.write_exclusions(directory, "qc", [2, 99])
    experiment = SurvivalExperiment(directory)
    result = experiment.run_analysis()
    payload = json.loads(result.outputs.summary.read_text(encoding="utf-8"))
    return experiment, result, payload


# ---------------------------------------------------------------------------
# Contract 3 — display order
# ---------------------------------------------------------------------------

def test_treatment_order_is_category_order_then_first_appearance():
    frame = pd.DataFrame({"treatment": ["wt", "mut", "wt"]})
    assert statistics.treatment_order(frame) == ["wt", "mut"]        # not sorted
    frame["treatment"] = pd.Categorical(frame["treatment"],
                                        categories=["zz", "mut", "wt"], ordered=True)
    ## Category order, unused categories dropped.
    assert statistics.treatment_order(frame) == ["mut", "wt"]


def test_pairwise_tables_and_hazard_ratios_follow_display_order():
    """Bug: pairwise tests and hazard ratios sorted treatments alphabetically,
    so `mut` became group1 (and the HR's numerator) whatever the Focus said."""
    data = _cohort()
    for table in (statistics.pairwise_logrank(data), statistics.pairwise_gehan_wilcoxon(data),
                  statistics.pairwise_hazard_ratios(data)):
        assert list(table.loc[0, ["group1", "group2"]]) == ["wt", "mut"]
    hr = statistics.pairwise_hazard_ratios(data).iloc[0]
    by_hand = statistics.hazard_ratio_estimate(data, "wt", "mut")
    assert hr["hazard_ratio"] == by_hand["hazard_ratio"]
    assert lifetable.compute_lifetables(data)["treatment"].unique().tolist() == ["wt", "mut"]
    assert statistics.summary_statistics(data)["treatment"].tolist() == ["wt", "mut"]
    assert lifetable.median_survival(lifetable.compute_lifetables(data))[
        "treatment"].tolist() == ["wt", "mut"]


def test_the_report_says_which_way_a_hazard_ratio_points(workbook_run):
    _experiment, result, _payload = workbook_run
    [table] = _tables(rb._section_tests(result), "hazard ratios")
    assert "group1 / group2" in table.caption and "earlier" in table.caption


# ---------------------------------------------------------------------------
# KM band, median CI, RMST — against lifelines
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed,all_die", [(0, False), (1, False), (2, True), (3, False)])
def test_km_band_and_median_interval_match_lifelines(seed, all_die):
    """Bug: the KM band was linear Greenwood ±1.96·SE, clipped to [0, 1], and
    no median interval was computed although median_survival promised one."""
    from lifelines import KaplanMeierFitter
    from lifelines.utils import median_survival_times

    data = _cohort(seed, all_die=all_die)
    table = lifetable.compute_lifetables(data)
    medians = lifetable.median_survival(table).set_index("treatment")
    for label, grp in statistics.treatment_groups(data):
        kmf = KaplanMeierFitter().fit(grp["time"], grp["event"])
        rows = table[table["treatment"] == label].set_index("time")
        band = kmf.confidence_interval_.loc[rows.index]
        np.testing.assert_allclose(rows["km_lx"], kmf.survival_function_.loc[rows.index].iloc[:, 0],
                                   atol=1e-12)
        np.testing.assert_allclose(rows["km_ci_lo"], band.iloc[:, 0], atol=1e-12)
        np.testing.assert_allclose(rows["km_ci_hi"], band.iloc[:, 1], atol=1e-12)

        expected = [kmf.median_survival_time_,
                    *median_survival_times(kmf.confidence_interval_).values[0]]
        expected = [np.nan if not np.isfinite(v) else v for v in expected]
        got = medians.loc[label, ["median_survival", "median_ci_lo", "median_ci_hi"]]
        np.testing.assert_allclose(got.astype(float), expected, atol=1e-12)
        ## The per-group helper B's figures call gives the same numbers.
        ci = lifetable.km_median_ci(grp)
        np.testing.assert_allclose([ci["median"], ci["ci_lo"], ci["ci_hi"]], expected,
                                   atol=1e-12)


def test_rmst_integrates_the_step_function_exactly_to_tau():
    """Bug: mean survival joined KM points with trapezoids (understating every
    step) and stopped at the last time at or before τ."""
    from lifelines import KaplanMeierFitter
    from lifelines.utils import restricted_mean_survival_time

    data = _cohort(5)
    means = lifetable.mean_survival(data).set_index("treatment")
    tau = min(g["time"].max() for _, g in statistics.treatment_groups(data))
    assert (means["restriction_time"] == tau).all()
    stats = lifetable.lifespan_statistics(data, [])
    assert stats["tau"] == tau
    for label, grp in statistics.treatment_groups(data):
        kmf = KaplanMeierFitter().fit(grp["time"], grp["event"])
        expected = restricted_mean_survival_time(kmf, t=tau)
        assert means.loc[label, "rmst"] == pytest.approx(expected, abs=1e-9)
        ## lifespan_statistics used to integrate each group to its own last
        ## time; it now uses the same common τ, so the two tables agree.
        row = stats["treatment_stats"].set_index("group").loc[label]
        assert row["mean_rmst"] == pytest.approx(round(expected, 2), abs=1e-9)
        assert row["tau"] == pytest.approx(tau)
    ## A τ between event times takes the partial strip up to τ, too.
    grp = statistics.treatment_groups(data)[0][1]
    kmf = KaplanMeierFitter().fit(grp["time"], grp["event"])
    for t in (grp["time"].median() + 0.37, grp["time"].min() / 2):
        assert lifetable.km_rmst(grp, t) == pytest.approx(
            restricted_mean_survival_time(kmf, t=t), abs=1e-9)


def test_rmst_model_pseudo_values_use_the_exact_area_and_record_tau():
    from lifelines import KaplanMeierFitter
    from lifelines.utils import restricted_mean_survival_time

    rng = np.random.default_rng(7)
    rows = []
    for a in ("wt", "mut"):
        for b in ("ctrl", "drug"):
            t = np.round(rng.gamma(5, 8, 30))
            rows += [{"time": float(x), "event": int(rng.random() > 0.2), "A": a, "B": b,
                      "treatment": f"{a}/{b}"} for x in t]
    data = pd.DataFrame(rows)
    model = statistics.rmst_interaction_analysis(data, ["A", "B"])
    tau = lifetable.common_tau(data)
    assert model["tau"] == pytest.approx(tau)
    kmf = KaplanMeierFitter().fit(data["time"], data["event"])
    assert model["rmst_overall"] == pytest.approx(
        restricted_mean_survival_time(kmf, t=tau), abs=1e-3)
    assert model["r_squared"] is not None and model["f_statistic"] is not None


def test_tau_and_the_fit_reach_the_run_summary_and_the_report(workbook_run):
    _experiment, result, payload = workbook_run
    rmst = next(mdl for mdl in payload["factorial_models"]
                if mdl["model_type"] == "rmst_pseudo")
    assert rmst["tau"] == pytest.approx(float(result.mean_surv["restriction_time"].iloc[0]))
    assert rmst["r_squared"] is not None and "warnings" in rmst
    cox = next(mdl for mdl in payload["factorial_models"] if mdl["model_type"] == "cox_ph")
    assert cox["tau"] is None and isinstance(cox["warnings"], list)
    text = " ".join(b.text for b in rb._section_interaction(result)
                    if isinstance(b, m.Paragraph))
    assert "τ = " in text and "R² = " in text


# ---------------------------------------------------------------------------
# Contract 5 — the Cox LR χ²
# ---------------------------------------------------------------------------

def test_cox_lr_statistic_is_exposed_and_printed(workbook_run):
    """Bug: the model stored `lr_stat` while the report read `statistic`, so
    the χ² cell always printed "—"."""
    _experiment, result, payload = workbook_run
    cox = next(mdl for mdl in result.cox_analyses if mdl["model_type"] == "cox_ph")
    lr = cox["lr_interaction"]
    assert lr["statistic"] == lr["lr_stat"]
    saved = next(mdl for mdl in payload["factorial_models"] if mdl["model_type"] == "cox_ph")
    assert saved["lr_interaction"]["statistic"] == lr["statistic"]
    [table] = [b for b in rb._section_interaction(result)
               if isinstance(b, m.Table) and b.columns[1] == "chi²"]
    assert table.rows[0][1] == rb._num(lr["statistic"]) != "—"


def test_an_old_summary_with_only_lr_stat_still_prints_its_chi2():
    class Old:
        cox_analyses = [{"title": "Cox factorial model", "model_type": "cox_ph",
                         "lr_interaction": {"lr_stat": 3.21, "df": 1, "p_value": 0.07}}]
    [table] = [b for b in rb._section_interaction(Old()) if isinstance(b, m.Table)]
    assert table.rows[0][1] == "3.21"


# ---------------------------------------------------------------------------
# Exclusions: what was actually removed
# ---------------------------------------------------------------------------

def test_only_chambers_the_file_holds_count_as_excluded(workbook_run):
    """Bug: n_excluded_applied counted every listed chamber, including ones
    this data file never had."""
    _experiment, result, payload = workbook_run
    assert result.excluded_applied() == ["2"]
    assert result.n_excluded_applied() == 1
    assert payload["excluded_chambers"] == ["2"]
    assert payload["n_excluded"] == 1 and payload["n_excluded_listed"] == 2
    assert "2" not in set(result.individual_data["chamber"].astype(str))


def test_the_project_report_never_invents_chamber_ids(workbook_run, tmp_path):
    """Bug: SavedAnalysis.excluded_chambers was set(range(n)), printed as
    "0, 1, 2" — chambers that were never excluded."""
    experiment, result, payload = workbook_run
    saved = project_report.SavedAnalysis(experiment, result.focus)
    [para] = [b for b in rb._section_quality(saved) if isinstance(b, m.Paragraph)][:1]
    assert para.text.endswith(": 2.")

    ## A summary written before identities were saved knows only the count.
    old = dict(payload)
    old.pop("excluded_chambers")
    old["n_excluded"] = 3
    saved.payload = old
    assert saved.excluded_applied() is None and saved.excluded_chambers == set()
    text = " ".join(b.text for b in rb._section_quality(saved) if isinstance(b, m.Paragraph))
    assert "3 chamber(s) excluded" in text and "0, 1" not in text


# ---------------------------------------------------------------------------
# Parametric AFT
# ---------------------------------------------------------------------------

def test_parametric_fits_say_what_was_not_fitted():
    """Bug: treatments with < 5 individuals or < 2 deaths, and failed fits,
    vanished from the AFT results without a word."""
    data = _cohort(2, n=30)
    tiny = pd.DataFrame({"time": [3.0, 6.0, 9.0], "event": [1, 0, 0], "treatment": "tiny"})
    few = pd.DataFrame({"time": [3.0, 6.0, 9.0, 12.0, 15.0, 18.0],
                        "event": [1, 0, 0, 0, 0, 0], "treatment": "few"})
    frame = pd.concat([data.assign(treatment=data["treatment"].astype(str)), tiny, few],
                      ignore_index=True)
    fit = statistics.fit_parametric_models(frame)
    reasons = {(i["treatment"], i["model"]): i["reason"] for i in fit["not_fitted"]}
    assert "only 3 individual(s)" in reasons[("tiny", None)]
    assert "only 1 death(s)" in reasons[("few", None)]
    table = fit["table"]
    assert table["treatment"].tolist()[:3] == ["wt", "wt", "wt"]       # display order
    assert table.groupby("treatment", sort=False)["best"].sum().loc[["wt", "mut"]].tolist() == [1, 1]
    assert table.loc[table["treatment"] == "tiny", "note"].str.startswith("not fitted").all()
    records = statistics.parametric_records(fit)
    json.dumps(records)                                                 # JSON-safe
    assert {r["treatment"] for r in records} == {"wt", "mut", "tiny", "few"}


def test_parametric_table_reaches_csv_summary_report_and_project_report(workbook_run):
    """Bug: the report dumped raw dicts, nothing was saved, and the Project
    Report's SavedAnalysis.parametric_models was always {}."""
    experiment, result, payload = workbook_run
    csv = pd.read_csv(result.outputs.stats("parametric_aic"))
    assert list(csv.columns) == list(statistics.PARAMETRIC_COLUMNS)
    assert len(payload["parametric_models"]) == len(csv) > 0
    live = _tables(rb._section_quality(result), "Parametric model fits")
    saved = project_report.SavedAnalysis(experiment, result.focus)
    from_disk = _tables(rb._section_quality(saved), "Parametric model fits")
    assert live and from_disk
    assert live[0].rows == from_disk[0].rows
    assert live[0].columns[:3] == ["Treatment", "Model", "AIC"]
    assert m.Level.OK in live[0].row_levels                         # the best fits


def test_a_failed_parametric_step_is_a_reason_not_a_silence(tmp_path, monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("lifelines exploded")

    monkeypatch.setattr(statistics, "fit_parametric_models", boom)
    directory = make_experiment_dir(tmp_path / "aft")
    result = SurvivalExperiment(directory).run_analysis()
    [table] = _tables(rb._section_quality(result), "Parametric model fits")
    assert "lifelines exploded" in table.rows[0][-1]
    assert table.row_levels == [m.Level.WARN]


# ---------------------------------------------------------------------------
# p-values in the report
# ---------------------------------------------------------------------------

def test_pairwise_rows_are_highlighted_by_the_adjusted_p_and_never_print_0_000():
    """Bug: rows were tinted by the unadjusted p while significant_0.05 used
    Bonferroni, and a tiny p printed as 0.000."""
    pairwise = pd.DataFrame({
        "group1": ["a", "a", "b"], "group2": ["b", "c", "c"],
        "chi2": [4.5, 30.0, 0.1], "p_value": [0.03, 1e-8, 0.75],
        "df": [1, 1, 1], "p_bonferroni": [0.09, 3e-8, 1.0],
        "significant_0.05": [False, True, False]})

    class Result:
        omnibus_lr = {}
        pairwise_lr = pairwise
        pairwise_gw = pd.DataFrame()
        hazard_ratios = pd.DataFrame()

    [table] = _tables(rb._section_tests(Result()), "log-rank")
    assert table.row_levels == [m.Level.NEUTRAL, m.Level.OK, m.Level.NEUTRAL]
    p_col = table.columns.index("p_value")
    assert table.rows[1][p_col] == "<0.0001"
    assert table.rows[0][table.columns.index("p_bonferroni")] == "0.0900"
    assert all("0.000" != row[p_col] for row in table.rows)


def test_p_value_columns_are_recognised_but_s_values_are_not():
    assert all(rb.is_pvalue_column(c) for c in ("p", "p_value", "p_bonferroni", "f_p_value"))
    assert not any(rb.is_pvalue_column(c) for c in ("-log2(p)", "chi2", "coef", "pct"))


# ---------------------------------------------------------------------------
# Model warnings
# ---------------------------------------------------------------------------

def test_fit_warnings_are_collected_not_lost():
    sink: list[str] = []
    with statistics._collect_warnings(sink):
        warnings.warn("convergence halted", RuntimeWarning)
        warnings.warn("old api", DeprecationWarning)
        warnings.warn("convergence halted", RuntimeWarning)
    assert sink == ["convergence halted"]


def test_model_warnings_reach_the_summary_and_the_report(tmp_path, monkeypatch):
    """Bug: a failed Schoenfeld test went into a warnings list nobody read."""
    real = statistics.cox_interaction_analysis

    def warned(*args, **kwargs):
        out = real(*args, **kwargs)
        out["warnings"] = list(out.get("warnings") or []) + [
            "PH assumption test failed: singular matrix"]
        return out

    monkeypatch.setattr(statistics, "cox_interaction_analysis", warned)
    directory = make_experiment_dir(tmp_path / "warn")
    result = SurvivalExperiment(directory).run_analysis()
    payload = json.loads(result.outputs.summary.read_text(encoding="utf-8"))
    cox = next(mdl for mdl in payload["factorial_models"] if mdl["model_type"] == "cox_ph")
    assert "PH assumption test failed: singular matrix" in cox["warnings"]
    [table] = _tables(rb._section_interaction(result), "warnings")
    assert table.rows == [["PH assumption test failed: singular matrix"]]
    assert table.row_levels == [m.Level.WARN]


# ---------------------------------------------------------------------------
# Duplicate factorial models from a script step
# ---------------------------------------------------------------------------

def test_a_factorial_step_after_run_analysis_replaces_the_model(tmp_path):
    """Bug: a cox_interaction step after run_analysis appended a second Cox
    model, which a later report step showed twice."""
    from pysurvanalysis.experiment_types import factorial
    from pysurvanalysis.script_editor.spec import RunContext

    directory = make_experiment_dir(tmp_path / "dup")
    experiment = SurvivalExperiment(directory)
    result = experiment.run_analysis()
    old_cox = result.cox_analyses[0]
    ctx = RunContext(experiment=experiment, data=result.individual_data,
                     focus=result.focus, result=result)
    factorial._exec_cox_interaction({}, ctx)
    factorial._exec_rmst_interaction({"tau": 30.0}, ctx)
    titles = [mdl["title"] for mdl in result.cox_analyses]
    assert titles == ["Cox factorial model", "RMST factorial model"]
    assert result.cox_analyses[0] is not old_cox
    assert result.cox_analyses[0]["reference"] == {"Genotype": "wt", "Treatment": "ctrl"}
    assert result.cox_analyses[1]["tau"] == pytest.approx(30.0)


# ---------------------------------------------------------------------------
# Data quality: min_n_per_chamber, load warnings
# ---------------------------------------------------------------------------

def test_small_chambers_are_flagged_never_excluded(workbook_run):
    """Bug: global.min_n_per_chamber was validated and then ignored."""
    _experiment, result, payload = workbook_run
    assert payload["min_n_per_chamber"] == 25
    flagged = {c["chamber"] for c in payload["small_chambers"]}
    assert flagged == {"1", "3", "4", "5", "6", "7", "8"}           # 2 is excluded
    assert all(c["n"] == 20 for c in payload["small_chambers"])
    assert result.experiment_summary["n_total"] == 7 * 20          # nothing dropped
    [table] = _tables(rb._section_quality(result), "fewer than 25")
    assert [row[0] for row in table.rows] == ["1", "3", "4", "5", "6", "7", "8"]


def test_a_zero_threshold_turns_the_check_off(tmp_path):
    directory = tmp_path / "off"
    write_dlife_workbook(directory / "data" / "off.xlsx")
    cfgmod.save_config(directory, {"input": {"format": "excel"},
                                   "global": {"min_n_per_chamber": 0}})
    result = SurvivalExperiment(directory).run_analysis()
    assert result.small_chambers == []
    assert not _tables(rb._section_quality(result), "fewer than")


def test_load_warnings_reach_the_summary_and_the_report(tmp_path, monkeypatch):
    from pysurvanalysis import data_loader

    real = data_loader.load_experiment

    def noisy(*args, **kwargs):
        frame, factors = real(*args, **kwargs)
        frame.attrs["load_warnings"] = ["chamber 3: 25 deaths and censorings "
                                        "exceed its SampleSize of 20"]
        return frame, factors

    monkeypatch.setattr(data_loader, "load_experiment", noisy)
    directory = make_experiment_dir(tmp_path / "noisy")
    result = SurvivalExperiment(directory).run_analysis()
    payload = json.loads(result.outputs.summary.read_text(encoding="utf-8"))
    assert payload["load_warnings"] == result.load_warnings
    assert "exceed its SampleSize" in payload["load_warnings"][0]
    [table] = _tables(rb._section_quality(result), "loading the data file")
    assert table.row_levels == [m.Level.WARN]


# ---------------------------------------------------------------------------
# Contract 1 — the Run Summary's new keys
# ---------------------------------------------------------------------------

def test_run_summary_records_what_out_of_date_compares(workbook_run):
    experiment, _result, payload = workbook_run
    data_file = experiment.data_file()
    assert payload["data_sha256"] == hashlib.sha256(data_file.read_bytes()).hexdigest()
    assert payload["omit"] == {"analyses": [], "plots": []}
    assert payload["assume_censored"] is True
    assert payload["load_warnings"] == []
    assert isinstance(payload["parametric_models"], list)


def test_run_summary_records_the_omit_selection(tmp_path):
    directory = make_experiment_dir(tmp_path / "omit")
    config = cfgmod.load_config(directory)
    config["omit"] = {"analyses": ["parametric_aft", "gehan_wilcoxon"], "plots": ["mortality"]}
    cfgmod.save_config(directory, config)
    result = SurvivalExperiment(directory).run_analysis()
    payload = json.loads(result.outputs.summary.read_text(encoding="utf-8"))
    assert payload["omit"] == {"analyses": ["gehan_wilcoxon", "parametric_aft"],
                               "plots": ["mortality"]}
    assert payload["parametric_models"] == []
    assert not result.outputs.stats("parametric_aic").exists()


# ---------------------------------------------------------------------------
# Dead code
# ---------------------------------------------------------------------------

def test_the_unused_statistics_survival_quantiles_is_gone():
    assert not hasattr(statistics, "survival_quantiles")
    assert hasattr(lifetable, "survival_quantiles")                  # the one in use
