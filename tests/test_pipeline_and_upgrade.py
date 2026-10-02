"""Pipeline behaviour per Focus, output stamping, and the non-destructive upgrade."""

from __future__ import annotations

import json

import pytest

from pysurvanalysis import exclusions, pipeline
from pysurvanalysis.domain import SurvivalExperiment, config as cfgmod, upgrade
from pysurvanalysis.domain.experiment import BlockedFocusError
from pysurvanalysis.domain.focus import Focus
from tests.conftest import FACTORIAL, make_experiment_dir, write_cohort, write_dlife_workbook


def test_a_2x2_focus_earns_the_whole_plot_set(analysed_project):
    project, results = analysed_project
    result = results["rep_a"]
    expected = {p.id for p in project.type.plot_set_for(result.focus_shape)}
    assert set(result.figure_paths) == expected
    assert "km_faceted" in expected and result.headline_plot_id == "km_faceted"
    for path in result.figure_paths.values():
        assert path.is_file() and path.stem.endswith(f"_{FACTORIAL}")


def test_unfiltered_renders_the_whole_battery(tmp_path):
    from pysurvanalysis import plot_registry

    directory = make_experiment_dir(tmp_path / "cust", focus=None)
    result = SurvivalExperiment(directory).run_analysis()
    assert result.focus.name == "Unfiltered"
    assert len(result.figure_paths) >= len(plot_registry.available()) - 2


def test_the_factorial_battery_runs_for_a_2x2_focus(analysed_project):
    _project, results = analysed_project
    titles = [m.get("title") for m in results["rep_a"].cox_analyses]
    assert titles == ["Cox factorial model", "RMST factorial model"]
    cox = results["rep_a"].cox_analyses[0]
    assert cox["lr_interaction"]["p_value"] is not None
    assert "Genotype_mut:Treatment_drug" in " ".join(
        cox["coefficients"]["covariate"].astype(str))


def test_a_one_factor_focus_is_not_offered_the_factorial_battery(tmp_path):
    ## Not a question this slice asks: no model, no crossing figure, no
    ## report section — and no "not applicable" line in every report either.
    directory = make_experiment_dir(tmp_path / "std")
    experiment = SurvivalExperiment(directory)
    experiment.save_focuses([Focus("Geno", {"Genotype": ["wt", "mut"]})])
    result = experiment.run_analysis()
    assert result.cox_analyses == []
    assert "km_faceted" not in result.figure_paths
    assert "interaction_lifespan" not in result.figure_paths
    assert result.not_applicable == []
    assert len(result.lifespan_stats["factor_stats"]) == 0   # it would repeat
    report = experiment.outputs("Geno").report(experiment.name, ".md").read_text()
    assert "Factorial" not in report
    assert "by factor level" not in report
    assert "pooled over Treatment" in report
    ## Comparisons are still relevant to two treatments.
    assert len(result.pairwise_lr) == 1


def test_a_single_treatment_focus_is_offered_no_comparison(tmp_path):
    directory = make_experiment_dir(tmp_path / "one")
    experiment = SurvivalExperiment(directory)
    experiment.save_focuses([Focus("Wt ctrl", {"Genotype": ["wt"],
                                               "Treatment": ["ctrl"]})])
    result = experiment.run_analysis()
    assert result.omnibus_lr == {} and len(result.pairwise_lr) == 0
    assert "hazard_ratio_forest" not in result.figure_paths
    assert result.not_applicable == []
    report = experiment.outputs("Wt ctrl").report(experiment.name, ".md").read_text()
    assert "Omnibus log-rank" not in report and "Pairwise log-rank" not in report


def test_a_three_level_factorial_runs_the_battery(tmp_path):
    directory = make_experiment_dir(
        tmp_path / "three", n_per_cell=15,
        factors={"Genotype": ["wt", "mut", "InR"], "Treatment": ["ctrl", "drug"]})
    result = SurvivalExperiment(directory).run_analysis()
    assert result.focus_shape.describe() == "3×2"
    assert [m["title"] for m in result.cox_analyses] == ["Cox factorial model",
                                                         "RMST factorial model"]
    assert {"km_faceted", "interaction_lifespan"} <= set(result.figure_paths)


def test_an_unbalanced_2x2_is_not_applicable_with_the_missing_cell_named(tmp_path):
    directory = make_experiment_dir(tmp_path / "unbal")
    path = directory / "data" / "cohort.csv"
    import pandas as pd

    frame = pd.read_csv(path)
    frame = frame[~((frame.Genotype == "mut") & (frame.Treatment == "drug"))]
    frame.to_csv(path, index=False)
    result = SurvivalExperiment(directory).run_analysis()
    assert result.cox_analyses == []
    ## Relevant — two factors vary — so its absence is explained.
    reason = next(i["reason"] for i in result.not_applicable
                  if i["action"] == "Factorial Battery")
    assert "Genotype=mut × Treatment=drug" in reason
    ## The figures do not need the cell: a missing cell is a missing curve.
    assert "km_faceted" in result.figure_paths


def test_an_explicit_reference_rebases_the_model_not_the_display(tmp_path):
    directory = make_experiment_dir(tmp_path / "ref")
    experiment = SurvivalExperiment(directory)
    [focus] = experiment.focuses()
    experiment.save_focuses([focus.copy(reference={"Treatment": "drug"})])
    result = experiment.run_analysis()
    covariates = " ".join(result.cox_analyses[0]["coefficients"]["covariate"].astype(str))
    assert "Treatment_ctrl" in covariates and "Treatment_drug" not in covariates
    assert list(result.individual_data["treatment"].cat.categories)[0] == "wt/ctrl"


def test_two_focuses_coexist_instead_of_overwriting(tmp_path):
    directory = make_experiment_dir(tmp_path / "two")
    experiment = SurvivalExperiment(directory)
    experiment.save_focuses(experiment.focuses()
                            + [Focus("Drug only", {"Treatment": ["drug"],
                                                   "Genotype": ["wt", "mut"]})])
    outcome = experiment.run_all()
    assert set(outcome["results"]) == {FACTORIAL, "Drug only"}
    assert experiment.outputs(FACTORIAL).summary.is_file()
    assert experiment.outputs("Drug only").summary.is_file()
    drug = json.loads(experiment.outputs("Drug only").summary.read_text())
    assert drug["focus"]["filters"] == {"Treatment": "drug"}
    assert drug["n_total"] < json.loads(
        experiment.outputs(FACTORIAL).summary.read_text())["n_total"]


def test_redefining_a_focus_makes_its_results_out_of_date(tmp_path):
    directory = make_experiment_dir(tmp_path / "ood")
    experiment = SurvivalExperiment(directory)
    experiment.run_analysis()
    assert experiment.status().focuses[0].state == "analysed"
    [focus] = experiment.focuses()
    experiment.save_focuses([focus.copy(factors={"Genotype": ["wt", "mut"],
                                                 "Treatment": ["ctrl"]})])
    [fs] = experiment.status().focuses
    assert fs.state == "out of date"
    ## Display-only edits do not.
    experiment.run_analysis()
    [focus] = experiment.focuses()
    experiment.save_focuses([focus.copy(display_names={"wt": "wild type"})])
    assert experiment.status().focuses[0].state == "analysed"


def test_renaming_a_focus_moves_its_results(tmp_path):
    directory = make_experiment_dir(tmp_path / "ren")
    experiment = SurvivalExperiment(directory)
    experiment.run_analysis()
    experiment.rename_focus(FACTORIAL, "Crowding 20v40")
    assert not (directory / "analysis" / FACTORIAL).exists()
    outs = experiment.outputs("Crowding 20v40")
    assert outs.summary.is_file() and outs.data("lifetables").is_file()
    payload = json.loads(outs.summary.read_text())
    assert payload["focus"]["name"] == "Crowding 20v40"
    assert all(name.endswith("_Crowding_20v40.png") for name in payload["figures"].values())
    assert experiment.status().focuses[0].state == "analysed"
    assert experiment.orphaned_results() == []


def test_a_hand_renamed_focus_leaves_orphaned_results(tmp_path):
    directory = make_experiment_dir(tmp_path / "orph")
    experiment = SurvivalExperiment(directory)
    experiment.run_analysis()
    config = cfgmod.load_config(directory)
    config["focuses"] = {"Renamed": config["focuses"][FACTORIAL]}
    cfgmod.save_config(directory, config)
    experiment = SurvivalExperiment(directory)
    assert experiment.orphaned_results() == [FACTORIAL]
    assert experiment.status().focuses[0].state == "not analysed"
    experiment.adopt_orphan(FACTORIAL, "Renamed")
    assert experiment.orphaned_results() == []
    assert experiment.status().focuses[0].state == "analysed"


def test_pre_focus_results_are_listed_never_adopted(tmp_path):
    directory = make_experiment_dir(tmp_path / "leg")
    (directory / "analysis" / "plots").mkdir(parents=True)
    (directory / "analysis" / "run_summary.json").write_text("{}")
    experiment = SurvivalExperiment(directory)
    assert {p.name for p in experiment.legacy_results()} == {"plots", "run_summary.json"}
    assert experiment.orphaned_results() == []
    assert experiment.status().focuses[0].state == "not analysed"
    experiment.delete_results(None)
    assert experiment.legacy_results() == []


def test_declared_levels_survive_into_the_analysis(analysed_project):
    _project, results = analysed_project
    treatments = list(results["rep_a"].individual_data["treatment"].cat.categories)
    assert treatments[0] == "wt/ctrl"          # both Reference Levels
    assert treatments == ["wt/ctrl", "wt/drug", "mut/ctrl", "mut/drug"]


def test_a_stale_focus_is_blocked_before_anything_is_written(tmp_path):
    directory = make_experiment_dir(tmp_path / "bad")
    config = cfgmod.load_config(directory)
    config["focuses"] = {"Bad": {"factors": {"Genotype": ["wt", "other"]}}}
    cfgmod.save_config(directory, config)
    experiment = SurvivalExperiment(directory)
    with pytest.raises(BlockedFocusError, match="'other'"):
        experiment.run_analysis()
    assert not experiment.outputs("Bad").root.exists()


def test_a_cell_emptied_by_exclusion_blocks_the_focus(tmp_path):
    directory = tmp_path / "wb"
    write_dlife_workbook(directory / "data" / "wb.xlsx")
    cfgmod.save_config(directory, {"input": {"format": "excel"},
                                   "exclusions": {"group": "qc"}})
    exclusions.write_exclusions(directory, "qc", [4])   # the only a/a chamber
    experiment = SurvivalExperiment(directory)
    [fs] = experiment.status().focuses
    assert fs.state == "blocked" and "a/a" in fs.blocked[0]
    with pytest.raises(BlockedFocusError, match="a/a"):
        experiment.run_analysis()


def test_defined_plots_render_whole_or_are_not_applicable(tmp_path):
    directory = tmp_path / "dp"
    write_dlife_workbook(directory / "data" / "dp.xlsx", defined_plots={
        "Bs": ["b/a", "b/b"],
        "Missing": ["b/a", "c/a"],
    })
    cfgmod.save_config(directory, {"input": {"format": "excel"}})
    experiment = SurvivalExperiment(directory)
    result = experiment.run_analysis()
    assert list(result.defined_plot_paths) == ["Bs"]
    path = result.defined_plot_paths["Bs"]
    assert path.name == "defined_Bs_Unfiltered.png" and path.is_file()
    reason = next(i["reason"] for i in result.not_applicable
                  if i["action"] == "Defined Plot 'Missing'")
    assert "c/a" in reason


def test_a_rectangular_defined_plot_can_become_a_focus(tmp_path):
    from pysurvanalysis import data_loader
    from pysurvanalysis.domain import focus as fm

    path = write_dlife_workbook(tmp_path / "dp2" / "data" / "dp2.xlsx",
                                defined_plots={"Bs": ["b/a", "b/b"]})
    design = fm.discover_design(path)
    [(name, labels)] = data_loader.load_defined_plots(path)
    focus, why = fm.focus_from_defined_plot(name, labels, design)
    assert why == "" and focus.factors == {"Genotype": ["b"], "Treatment": ["a", "b"]}


def test_run_summary_stamps_the_exclusion_group_and_count(tmp_path):
    directory = make_experiment_dir(tmp_path / "excl", type_key="standard_lifespan")
    exclusions.write_exclusions(directory, "review", [1, 2, 3])
    config = cfgmod.load_config(directory)
    config["exclusions"] = {"group": "review"}
    cfgmod.save_config(directory, config)

    experiment = SurvivalExperiment(directory)
    assert experiment.exclusion_group == "review"
    experiment.run_analysis()
    payload = json.loads(
        experiment.outputs(FACTORIAL).summary.read_text(encoding="utf-8"))
    assert payload["exclusion_group"] == "review"
    assert payload["focus"]["definition"]["reference"] == {"Genotype": "wt",
                                                           "Treatment": "ctrl"}
    # CSV cohorts have no chambers, so nothing is actually removed. The stamp
    # records the group that was in force and does not claim removals.
    assert payload["n_excluded"] == 0
    assert payload["n_excluded_listed"] == 3


def test_exclusions_are_written_into_qc(tmp_path):
    directory = make_experiment_dir(tmp_path / "qc_path")
    path = exclusions.write_exclusions(directory, "default", [7])
    assert path.parent.name == "qc"
    assert exclusions.chambers_for_group(directory, "default") == {7}


def test_a_legacy_root_exclusions_file_is_still_read(tmp_path):
    directory = make_experiment_dir(tmp_path / "legacy_excl")
    (directory / "remove_chambers.csv").write_text(
        "group,chamber,note\ndefault,4,old\n", encoding="utf-8")
    assert exclusions.chambers_for_group(directory, "default") == {4}


def test_direct_file_mode_runs_unfiltered_under_the_legacy_parent(tmp_path):
    path = write_cohort(tmp_path / "loose" / "cohort.csv")
    result = pipeline.run_analysis(path, factor_cols=["Genotype", "Treatment"])
    assert result.output_dir == path.parent / "cohort_results" / "Unfiltered"
    assert (result.output_dir / "report_Unfiltered.md").is_file()
    ## Discovery reads the file in its own order: wt was written first.
    assert result.focus.reference_level("Genotype") == "wt"


def test_experiment_mode_writes_to_the_focus_directory(tmp_path):
    directory = make_experiment_dir(tmp_path / "exp")
    result = SurvivalExperiment(directory).run_analysis()
    assert result.output_dir == directory / "analysis" / FACTORIAL


# ── upgrade ────────────────────────────────────────────────────────────────

def _legacy_dir(tmp_path):
    directory = tmp_path / "old"
    write_cohort(directory / "cohort.csv")
    (directory / "remove_chambers.csv").write_text(
        "group,chamber,note\nreview,2,noisy\n", encoding="utf-8")
    (directory / "survival_scripts.yaml").write_text(
        "scripts:\n  - name: Quick\n    steps:\n      - {action: load_data}\n",
        encoding="utf-8")
    (directory / "cohort_results").mkdir()
    (directory / "cohort_results" / "report.md").write_text("old", encoding="utf-8")
    return directory


def test_upgrade_is_detected_and_described_before_it_runs(tmp_path):
    directory = _legacy_dir(tmp_path)
    assert upgrade.needs_upgrade(directory)
    plan = upgrade.plan(directory)
    assert any("survival_config.yaml" in a for a in plan.actions)
    assert any("qc/" in a for a in plan.actions)
    # Described, not done.
    assert not cfgmod.config_path(directory).is_file()


def test_upgrade_never_deletes_or_moves(tmp_path):
    directory = _legacy_dir(tmp_path)
    upgrade.apply(upgrade.plan(directory))

    assert (directory / "survival_scripts.yaml").is_file()   # left in place
    assert (directory / "remove_chambers.csv").is_file()     # copied, not moved
    assert (directory / "qc" / "remove_chambers.csv").is_file()
    assert (directory / "cohort_results" / "report.md").read_text() == "old"


def test_upgrade_imports_scripts_and_the_active_group(tmp_path):
    directory = _legacy_dir(tmp_path)
    upgrade.apply(upgrade.plan(directory))
    config = cfgmod.load_config(directory)
    assert [s["name"] for s in cfgmod.scripts_of(config)] == ["Quick"]
    assert config["exclusions"]["group"] == "review"
    assert config["input"]["format"] == "long"


def test_upgrade_seeds_the_default_script_unless_legacy_scripts_are_imported(tmp_path):
    from pysurvanalysis.script_editor.project_actions import (
        DEFAULT_EXPERIMENT_SCRIPT_NAME,
    )

    ## Legacy scripts are an authored block: imported as-is, not appended to.
    legacy = _legacy_dir(tmp_path)
    plan = upgrade.plan(legacy)
    assert [s["name"] for s in plan.proposed_config["scripts"]] == ["Quick"]
    assert not any("seed" in a for a in plan.actions)

    ## No scripts anywhere: the plan shows the seed and the file carries it.
    bare = tmp_path / "bare"
    write_cohort(bare / "cohort.csv")
    plan = upgrade.plan(bare)
    assert any(DEFAULT_EXPERIMENT_SCRIPT_NAME in a for a in plan.actions)
    upgrade.apply(plan)
    config = cfgmod.load_config(bare)
    assert [s["name"] for s in cfgmod.scripts_of(config)] == [DEFAULT_EXPERIMENT_SCRIPT_NAME]


def test_upgrading_an_upgraded_directory_is_a_no_op(tmp_path):
    directory = _legacy_dir(tmp_path)
    upgrade.apply(upgrade.plan(directory))
    assert not upgrade.needs_upgrade(directory)
    assert upgrade.plan(directory).is_noop


def test_the_analysis_figures_raise_no_warnings(tmp_path):
    """The risk-table figure warned that tight_layout 'results might be
    incorrect' on every run — its layout is hand-tuned, so nothing is left
    for tight_layout to guess at."""
    import warnings

    from pysurvanalysis import lifetable, plotting
    from tests.conftest import make_experiment_dir
    from pysurvanalysis.domain import SurvivalExperiment

    directory = make_experiment_dir(tmp_path / "e", type_key="standard_lifespan")
    data, _factors = SurvivalExperiment(directory).load()
    tables = lifetable.compute_lifetables(data)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        figure = plotting.plot_km_with_risk_table(tables)
    assert [str(w.message) for w in caught] == []
    assert figure.axes                       # both panels are really there


def test_individuals_with_no_level_are_counted_not_silently_dropped(tmp_path):
    import pandas as pd

    directory = make_experiment_dir(tmp_path / "blank")
    path = directory / "data" / "cohort.csv"
    frame = pd.read_csv(path)
    frame.loc[frame.index[:3], "Genotype"] = None
    frame.to_csv(path, index=False)
    experiment = SurvivalExperiment(directory)
    result = experiment.run_analysis()
    assert result.unassigned == 3
    payload = json.loads(experiment.outputs(FACTORIAL).summary.read_text())
    assert payload["focus"]["unassigned"] == 3
    report = experiment.outputs(FACTORIAL).report(experiment.name, ".md").read_text()
    assert "3 individual(s) in the data file have no recorded level" in report
