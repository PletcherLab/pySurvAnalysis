"""Data, config, QC and the Focus window: the bugs found while writing the
in-app manual, each pinned by the test that would have caught it.

Offscreen Qt throughout; no test lets a modal open (each one is replaced).
"""

from __future__ import annotations

import json
import os

import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pysurvanalysis import data_loader, exclusions  # noqa: E402
from pysurvanalysis.domain import (  # noqa: E402
    Project,
    ProjectError,
    SurvivalExperiment,
    config as cfgmod,
    focus as fm,
    layout,
)
from pysurvanalysis.domain.experiment import ExperimentError  # noqa: E402
from tests.conftest import make_experiment_dir, write_dlife_workbook  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    from pysurvanalysis.ui import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "light")
    return app


def _workbook_experiment(directory, config=None, **workbook):
    write_dlife_workbook(directory / "data" / "wb.xlsx", **workbook)
    cfgmod.save_config(directory, {"input": {"format": "excel"}, **(config or {})})
    return SurvivalExperiment(directory)


# ── 1. YAML syntax errors ──────────────────────────────────────────────────

BROKEN = "global:\n  time_unit: days\nexclusions:\n\tgroup: default\n"


def test_a_yaml_syntax_error_names_the_file_and_line(tmp_path):
    import yaml

    path = tmp_path / "survival_config.yaml"
    path.write_text(BROKEN, encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        cfgmod.read_yaml(path)
    assert not isinstance(caught.value, yaml.YAMLError)
    text = str(caught.value)
    assert "survival_config.yaml, line 4" in text and "tabs" in text


def test_a_member_whose_config_will_not_parse_is_listed_not_raised(tmp_path):
    root = tmp_path / "proj"
    Project.create(root, name="P")
    make_experiment_dir(root / "good", minimal=True)
    bad = make_experiment_dir(root / "bad", minimal=True)
    (bad / cfgmod.CONFIG_FILENAME).write_text(BROKEN, encoding="utf-8")

    project = Project(root)
    members = {m.name: m for m in project.members()}           # no exception
    assert set(members) == {"bad", "good"}
    problems = project.validate()
    assert any(p.startswith("bad:") and "line 4" in p for p in problems)
    assert project.divergences() == []                           # skipped, not raised

    member = members["bad"]
    assert member.status().problems and member.focuses() == []
    ## Nothing may run or write under it: a write would replace the user's
    ## file with defaults.
    with pytest.raises(ExperimentError):
        member.run_all()
    with pytest.raises(ExperimentError):
        member.save_focuses([fm.Focus("X", {"Genotype": ["wt"]})])
    assert (bad / cfgmod.CONFIG_FILENAME).read_text(encoding="utf-8") == BROKEN

    item = layout.classify(bad)
    assert item.status == layout.BAD_CONFIG and item.blocked and "line 4" in item.detail


def test_a_project_yaml_that_will_not_parse_is_a_project_error(tmp_path):
    root = tmp_path / "proj"
    Project.create(root, name="P")
    (root / cfgmod.PROJECT_FILENAME).write_text("name: [unclosed\n", encoding="utf-8")
    with pytest.raises(ProjectError) as caught:
        Project(root)
    assert isinstance(caught.value, ValueError)
    assert "project.yaml, line 1" in str(caught.value)


# ── 2. Wide CSV without col_mapping ────────────────────────────────────────

def _wide_member(directory, **extra_input):
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "data").mkdir()
    pd.DataFrame({
        "Male_40x_death": [30, 31, 32], "Male_40x_censored": [40, None, None],
        "Male_20x_death": [50, 51, None], "Male_20x_censored": [60, None, None],
        "Female_40x_death": [35, 36, 37], "Female_40x_censored": [45, None, None],
        "Female_20x_death": [55, 56, 57], "Female_20x_censored": [65, 66, None],
    }).to_csv(directory / "data" / "wide.csv", index=False)
    cfgmod.save_config(directory, {"input": {
        "format": "wide", "factor_names": ["Sex", "Density"],
        "factor_levels": {"Sex": ["Female", "Male"], "Density": ["20x", "40x"]},
        **extra_input}})
    return SurvivalExperiment(directory)


def test_a_wide_csv_loads_from_factor_levels_alone(tmp_path):
    exp = _wide_member(tmp_path / "wide")
    assert exp.validate() == []
    data, factors = exp.load()
    assert factors == ["Sex", "Density"] and len(data) == 16
    ## Discovery takes the order factor_levels lists, not the file's columns.
    design = exp.design()
    assert design.levels == {"Sex": ("Female", "Male"), "Density": ("20x", "40x")}
    focus = exp.focuses()[0]
    assert focus.implied_labels()[0] == "Female/20x"


def test_the_pipeline_reads_factor_levels_from_the_config(tmp_path):
    exp = _wide_member(tmp_path / "wide")
    result = exp.run_analysis()
    assert len(result.individual_data) == 16


def test_factor_levels_is_validated(tmp_path):
    problems = cfgmod.validate_input_block({"input": {
        "format": "wide", "factor_names": ["Sex", "Density"],
        "factor_levels": {"Sex": ["F", "F"], "Diet": ["AL"]}}})
    assert any("lists a level twice" in p for p in problems)
    assert any("exactly the factors" in p for p in problems)
    missing = cfgmod.validate_input_block({"input": {"format": "wide",
                                                      "factor_names": ["A", "B"]}})
    assert any("col_mapping" in p and "factor_levels" in p for p in missing)
    assert cfgmod.validate_input_block({"input": {"format": "long"}}) == []


# ── 3. Chamber ids ─────────────────────────────────────────────────────────

def test_a_chamber_written_as_12_0_is_chamber_12_everywhere(tmp_path):
    directory = tmp_path / "wb"
    exp = _workbook_experiment(directory, {"exclusions": {"group": "qc"}}, chambers=4)
    (directory / "qc").mkdir(exist_ok=True)
    (directory / "qc" / "remove_chambers.csv").write_text(
        "group,chamber,note\nqc,2.0,\n", encoding="utf-8")
    assert exclusions.chambers_for_group(directory, "qc") == {2}
    data, _f = exp.load()
    assert 2 not in set(data["chamber"])                           # the run
    focus = exp.focuses()[0]
    estimate = fm.labels_after_exclusion(focus, exp.design(), exp.all_excluded_chambers())
    assert set(estimate) == set(fm.populated_labels(fm.apply_focus(data, focus)))
    assert fm.norm_chamber("12.0") == fm.norm_chamber(12) == 12
    assert fm.norm_chamber("12.5") == "12.5"                       # not 12


# ── 4. exclusions_path ─────────────────────────────────────────────────────

def test_writes_go_to_qc_and_carry_legacy_groups_over(tmp_path):
    (tmp_path / "remove_chambers.csv").write_text(
        "group,chamber,note\nold,3,kept note\n", encoding="utf-8")
    assert exclusions.chambers_for_group(tmp_path, "old") == {3}  # read fallback
    path = exclusions.write_exclusions(tmp_path, "new", [5])
    assert path == (tmp_path / "qc" / "remove_chambers.csv").resolve()
    assert exclusions.exclusions_path(tmp_path) == tmp_path / "qc" / "remove_chambers.csv"
    assert exclusions.read_exclusions(tmp_path) == {"old": [3], "new": [5]}
    assert exclusions.read_notes(tmp_path, "old") == {3: "kept note"}
    assert (tmp_path / "remove_chambers.csv").read_text(encoding="utf-8").count("\n") == 2


def test_saving_a_group_without_notes_keeps_its_notes(tmp_path):
    exclusions.write_exclusions(tmp_path, "g", [1, 2], notes={1: "contaminated"})
    exclusions.write_exclusions(tmp_path, "g", [1, 3])
    assert exclusions.read_notes(tmp_path, "g") == {1: "contaminated"}
    assert exclusions.read_exclusions(tmp_path)["g"] == [1, 3]


def test_a_bom_from_a_spreadsheet_does_not_drop_every_row(tmp_path):
    (tmp_path / "qc").mkdir()
    (tmp_path / "qc" / "remove_chambers.csv").write_bytes(
        "group,chamber,note\r\ng,7,\r\n".encode("utf-8-sig"))
    assert exclusions.chambers_for_group(tmp_path, "g") == {7}


# ── 6. Load warnings ───────────────────────────────────────────────────────

def test_more_scored_than_samplesize_is_a_load_warning(tmp_path):
    ## Six censuses × 2 deaths + 1 censored = 13 scored, against 10 set up.
    exp = _workbook_experiment(tmp_path / "wb", sample_size=10)
    focus = exp.focuses()[0]
    data, _f = exp.load(focus=focus)
    warnings = data.attrs.get("load_warnings")
    assert len(warnings) == 4 and "SampleSize is 10" in warnings[0]
    assert fm.apply_focus(data, focus).attrs["load_warnings"] == warnings


def test_rows_with_no_number_are_counted_not_silently_dropped(tmp_path):
    path = tmp_path / "c.csv"
    pd.DataFrame({"Age": [5, "x", 7], "Event": [1, 1, 0], "G": ["a", "b", "a"]}) \
        .to_csv(path, index=False)
    frame, _f = data_loader.load_csv_long(path)
    assert frame.attrs["load_warnings"] == [
        "1 row(s) dropped: their time or event is blank or not a number."]


# ── 7. Out of Date ─────────────────────────────────────────────────────────

def _summary(focus, **extra):
    return {"focus": {"definition": focus.analytic_definition()},
            "exclusion_group": None, **extra}


def test_out_of_date_compares_what_the_run_used():
    design = fm.DiscoveredDesign(
        ("G",), {"G": ("a", "b", "c")},
        frozenset({("a",), ("b",), ("c",)}),
        ((1, ("a",)), (2, ("b",)), (3, ("c",))))
    focus = fm.Focus("F", {"G": ["a", "b"]})
    payload = _summary(focus, data_sha256="abc", excluded_chambers=["1"],
                       assume_censored=True,
                       omit={"analyses": [], "plots": ["log_log"]})
    now = {"data_sha256": "abc", "excluded_chambers": [1], "assume_censored": True,
           "omit": {"analyses": [], "plots": ["log_log"]}}
    assert fm.out_of_date_reasons(focus, payload, None, current=now, design=design) == []

    def _why(**change):
        return fm.out_of_date_reasons(focus, payload, None,
                                      current={**now, **change}, design=design)

    assert "contents changed" in _why(data_sha256="def")[0]
    assert "excluded chambers" in _why(excluded_chambers=[1, 2])[0]
    assert _why(excluded_chambers=[1, 3]) == []            # chamber 3 is outside F
    assert "assumed censoring" in _why(assume_censored=False)[0]
    assert "plots selection" in _why(omit={"analyses": [], "plots": []})[0]
    ## A summary from before these keys existed is not evidence of a change.
    old = _summary(focus)
    assert fm.out_of_date_reasons(focus, old, None, current={**now, "data_sha256": "x"},
                                  design=design) == []


def test_an_explicit_reference_equal_to_the_default_is_not_a_change():
    focus = fm.Focus("F", {"G": ["a", "b"]})
    payload = _summary(focus)
    payload["focus"]["definition"]["reference"] = {}            # recorded implicitly
    explicit = focus.copy(reference={"G": "a"})
    assert fm.out_of_date_reasons(explicit, payload, None) == []
    assert fm.out_of_date_reasons(focus.copy(reference={"G": "b"}), payload, None)


def test_editing_the_data_file_puts_a_focus_out_of_date(tmp_path):
    exp = SurvivalExperiment(make_experiment_dir(tmp_path / "e", n_per_cell=8))
    focus = exp.focuses()[0]
    out = exp.outputs(focus)
    out.root.mkdir(parents=True)
    now = exp.run_inputs()
    out.summary.write_text(json.dumps(_summary(
        focus, data_sha256=now["data_sha256"], excluded_chambers=[],
        omit={"analyses": [], "plots": []})), encoding="utf-8")
    assert exp.status().focuses[0].state == "analysed"
    with (exp.data_file()).open("a", encoding="utf-8") as fh:
        fh.write("99,1,wt,ctrl\n")
    st = exp.status().focuses[0]
    assert st.state == "out of date" and "contents changed" in st.out_of_date_reasons[0]


# ── 10. Copy Focuses ───────────────────────────────────────────────────────

def test_copy_check_rejects_a_focus_the_exclusions_would_empty_here():
    design = fm.DiscoveredDesign(
        ("G",), {"G": ("a", "b")}, frozenset({("a",), ("b",)}),
        ((1, ("a",)), (2, ("b",))))
    focus = fm.Focus("F", {"G": ["a", "b"]})
    ok, rejected = fm.copy_check([focus], design, excluded={"2"})
    assert ok == [] and "no individuals once exclusions" in rejected[0]
    ok, _ = fm.copy_check([focus], design, excluded=())
    assert [f.name for f in ok] == ["F"]


# ── 11. Rename moves the Markdown report's figures ─────────────────────────

def test_a_rename_moves_the_report_figures_and_relinks_them(tmp_path):
    exp = SurvivalExperiment(make_experiment_dir(tmp_path / "e", n_per_cell=8))
    root = exp.outputs("Factorial").root
    (root / "report_Factorial_figures").mkdir(parents=True)
    (root / "report_Factorial_figures" / "figure_01.png").write_bytes(b"png")
    (root / "report_Factorial.md").write_text(
        "![KM](report_Factorial_figures/figure_01.png)\n", encoding="utf-8")
    exp.rename_focus("Factorial", "Main")
    new_root = exp.outputs("Main").root
    assert (new_root / "report_Main_figures" / "figure_01.png").is_file()
    assert not (new_root / "report_Factorial_figures").exists()
    assert (new_root / "report_Main.md").read_text(encoding="utf-8") == \
        "![KM](report_Main_figures/figure_01.png)\n"


# ── 5. The QC Viewer ───────────────────────────────────────────────────────

@pytest.fixture
def qc_dir(tmp_path):
    directory = tmp_path / "qc_exp"
    _workbook_experiment(directory, {"exclusions": {"group": "strict"},
                                     "global": {"assume_censored": False,
                                                "min_n_per_chamber": 0}},
                         chambers=4, sample_size=20)
    exclusions.write_exclusions(directory, "lenient", [1], notes={1: "dropped vial"})
    exclusions.write_exclusions(directory, "strict", [1, 2], notes={2: "mites"})
    return directory


def _viewer(qc_dir, **kwargs):
    from pysurvanalysis.apps.qc_viewer import QcViewerWindow

    return QcViewerWindow(str(qc_dir), **kwargs)


def test_the_qc_viewer_reads_the_data_as_the_run_does(qapp, qc_dir):
    viewer = _viewer(qc_dir)
    try:
        ## assume_censored: false — 13 recorded per chamber, not SampleSize 20.
        assert set(viewer._data.groupby("chamber").size()) == {13}
        ## Opens on the ACTIVE group, not the first one in the file.
        assert viewer._group_combo.currentText() == "strict"
        assert viewer._excluded == {1, 2}
        ## Tabs follow the file's own level order (Genotype b before a, as the
        ## Design sheet lists them), not the alphabet.
        assert list(viewer._panels) == ["b/a", "b/b", "a/a", "a/b"]
        ## The experiment's time label, not a hard-coded "hours".
        panel = next(iter(viewer._panels.values()))
        assert panel._fig.axes[0].get_xlabel() == "Age (days)"
    finally:
        viewer._saved = set(viewer._excluded)
        viewer.close()


def test_switching_groups_asks_about_unsaved_clicks(qapp, qc_dir):
    viewer = _viewer(qc_dir)
    try:
        viewer._on_panel_toggle(3, True)                     # an unsaved click
        answers = iter(["cancel", "save"])
        viewer._ask_unsaved = lambda: next(answers)
        lenient = viewer._group_combo.findText("lenient")
        viewer._group_combo.setCurrentIndex(lenient)
        assert viewer._group == "strict" and viewer._excluded == {1, 2, 3}
        assert viewer._group_combo.currentText() == "strict"
        viewer._group_combo.setCurrentIndex(lenient)          # now: save first
        assert viewer._group == "lenient" and viewer._excluded == {1}
        assert exclusions.chambers_for_group(qc_dir, "strict") == {1, 2, 3}
        ## Saving from the viewer kept the note typed into the file.
        assert exclusions.read_notes(qc_dir, "strict") == {2: "mites"}
    finally:
        viewer.close()


def test_typing_a_new_group_name_keeps_the_selection(qapp, qc_dir):
    viewer = _viewer(qc_dir)
    try:
        viewer._on_panel_toggle(4, True)
        viewer._group_combo.setEditText("brand_new")
        assert viewer._excluded == {1, 2, 4}
    finally:
        viewer._saved = set(viewer._excluded)
        viewer.close()


def test_the_qc_viewer_flags_chambers_below_the_minimum(qapp, qc_dir):
    config = cfgmod.load_config(qc_dir)
    config["global"]["min_n_per_chamber"] = 14
    cfgmod.save_config(qc_dir, config)
    viewer = _viewer(qc_dir)
    try:
        assert viewer._small == {1: 13, 2: 13, 3: 13, 4: 13}
        assert viewer._small_label.isVisibleTo(viewer)
        colours = {line.get_gid(): line.get_color()
                   for panel in viewer._panels.values()
                   for line in panel._chamber_lines()}
        assert colours == {"chamber-1": "#dc2626", "chamber-2": "#dc2626",
                           "chamber-3": "#d97706", "chamber-4": "#d97706"}
    finally:
        viewer.close()


def test_the_qc_viewer_never_guesses_between_data_files(qapp, qc_dir, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    write_dlife_workbook(qc_dir / "data" / "other.xlsx")
    seen = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: seen.append(a[2])))
    viewer = _viewer(qc_dir)
    try:
        assert viewer._data is None and not viewer._panels
        assert seen and "data_file" in seen[-1]
    finally:
        viewer.close()


# ── 8, 9. The Focus window ─────────────────────────────────────────────────

@pytest.fixture
def focus_exp(tmp_path):
    return SurvivalExperiment(make_experiment_dir(tmp_path / "fw", n_per_cell=8))


def test_saving_writes_every_varying_reference_explicitly(qapp, focus_exp):
    from pysurvanalysis.apps.focus_window import FocusWindow

    window = FocusWindow(None, focus_exp)
    try:
        window.accept()
    finally:
        window.close()
    written = cfgmod.load_config(focus_exp.directory)["focuses"]["Factorial"]
    assert written["reference"] == {"Genotype": "wt", "Treatment": "ctrl"}


def test_stale_factors_and_levels_are_shown_and_can_be_dropped(qapp, focus_exp):
    from PyQt6.QtCore import Qt

    from pysurvanalysis.apps.focus_window import FocusWindow

    focus_exp.save_focuses([fm.Focus("Old", {"Genotype": ["wt", "gone"],
                                             "Diet": ["AL", "DR"],
                                             "Treatment": ["ctrl", "drug"]})])
    window = FocusWindow(None, focus_exp)
    confirmations = []
    window._confirm_stale = lambda lines: confirmations.append(lines) or False
    try:
        assert list(window._stale_boxes) == ["Diet"]
        geno = window._boxes["Genotype"]
        assert geno.chosen_levels() == ["wt", "gone"]
        ## Save without edits: what is on screen, stale names included, and
        ## the user is asked first.
        window.accept()
        assert confirmations and window.result() == 0
        window._stale_boxes["Diet"].setChecked(False)
        gone = next(i for i in range(geno.levels.count())
                    if geno._level(geno.levels.item(i)) == "gone")
        geno.levels.item(gone).setCheckState(Qt.CheckState.Unchecked)
        window._on_edit()
        window.accept()
    finally:
        window.close()
    written = cfgmod.load_config(focus_exp.directory)["focuses"]["Old"]
    assert written["factors"] == {"Genotype": ["wt"], "Treatment": ["ctrl", "drug"]}


def test_a_ticked_factor_with_no_level_ticked_blocks_save(qapp, focus_exp, monkeypatch):
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QMessageBox

    from pysurvanalysis.apps.focus_window import FocusWindow

    warned = []
    monkeypatch.setattr(QMessageBox, "warning",
                        staticmethod(lambda *a, **k: warned.append(a[2])))
    window = FocusWindow(None, focus_exp)
    try:
        box = window._boxes["Treatment"]
        for i in range(box.levels.count()):
            box.levels.item(i).setCheckState(Qt.CheckState.Unchecked)
        window._on_edit()
        assert "none of its levels is" in window._preview.text()
        window.accept()
        assert warned and "Treatment" in warned[0] and window.result() == 0
    finally:
        window.close()
    assert cfgmod.load_config(focus_exp.directory)["focuses"]["Factorial"]["factors"] \
        == {"Genotype": ["wt", "mut"], "Treatment": ["ctrl", "drug"]}


def test_a_real_run_is_current_until_its_chambers_or_censoring_change(tmp_path):
    """The Run Summary's own keys and run_inputs() must agree on a fresh run
    — or every Focus would read Out of Date the moment it was analysed."""
    directory = tmp_path / "wb"
    exp = _workbook_experiment(directory, {"exclusions": {"group": "qc"}}, chambers=8)
    exclusions.write_exclusions(directory, "qc", [2])
    exp.run_analysis()
    assert exp.status().focuses[0].state == "analysed"

    exclusions.write_exclusions(directory, "qc", [2, 3])
    st = SurvivalExperiment(directory).status().focuses[0]
    assert st.state == "out of date"
    assert any("now also excludes chamber(s) 3" in r for r in st.out_of_date_reasons)

    exclusions.write_exclusions(directory, "qc", [2])
    config = cfgmod.load_config(directory)
    config["global"] = {"assume_censored": False}
    cfgmod.save_config(directory, config)
    st = SurvivalExperiment(directory).status().focuses[0]
    assert [r for r in st.out_of_date_reasons if "assumed censoring" in r]
