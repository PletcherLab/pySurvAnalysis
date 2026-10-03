"""Fixes to the Hub, the Batch, scripts and the AI narrative found while
writing the in-app manual — each test would have caught its bug.

Qt tests run on the offscreen platform and never trigger a modal: ``_warn``
is replaced wherever an action could reach it.
"""

from __future__ import annotations

import json
import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtCore import Qt  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from pysurvanalysis.domain import Project, config as cfgmod  # noqa: E402
from pysurvanalysis.ui import apply_theme  # noqa: E402

from conftest import FACTORIAL, make_experiment_dir, write_cohort  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    apply_theme(app, "light")
    return app


def _quiet(window):
    window._warned = []
    window._warn = lambda message: window._warned.append(message)
    return window


@pytest.fixture
def own_project(tmp_path):
    """A Project of this module's own, with a question and one member."""
    root = tmp_path / "proj"
    Project.create(root, name="Own", question="Does the drug help?")
    make_experiment_dir(root / "rep_a", minimal=True, n_per_cell=12)
    return Project(root)


@pytest.fixture
def hub(qapp, own_project):
    from pysurvanalysis.apps.hub import HubWindow

    window = HubWindow()
    _quiet(window)
    window._set_selection(own_project.directory)
    window._refresh_all()
    yield window
    window.close()


def _load(hub, name="rep_a"):
    for row in range(hub._members_table.rowCount()):
        if hub._members_table.item(row, 0).text() == name:
            hub._on_member_double_clicked(hub._members_table.model().index(row, 0))
            return
    raise AssertionError(f"no row {name!r}")


# ── 1. the status readout keeps its Focus row ─────────────────────────────

def test_the_status_readout_shows_the_focus_row_when_the_project_has_a_question(hub):
    _load(hub)
    shown = hub._status_panel._label.text()
    assert "Focus:" in shown
    ## The question is still there — in the tooltip, where the overflow goes.
    assert "Does the drug help?" in hub._status_panel.status_text()


# ── 2. stale wording ──────────────────────────────────────────────────────

def test_the_wording_speaks_of_focuses_not_members(hub):
    from PyQt6.QtWidgets import QAbstractButton

    from pysurvanalysis.apps import hub as hub_mod
    from pysurvanalysis.script_editor.project_actions import default_project_script

    tips = {b.text(): b.toolTip() for b in hub.findChildren(QAbstractButton)}
    assert "Focus Inventory" in tips["Project report"]
    assert "Member Inventory" not in tips["Project report"]
    assert "Tools)" not in hub_mod.__doc__
    assert "cannot be run from the Project card" not in default_project_script()["notes"]


# ── 3. the preflight keeps what the user unchecked ────────────────────────

@pytest.fixture
def two_project_batch(tmp_path):
    for name in ("ProjA", "ProjB"):
        Project.create(tmp_path / name)
        make_experiment_dir(tmp_path / name / "m1", minimal=True, n_per_cell=6)
    return tmp_path


def test_a_project_unchecked_in_the_table_stays_unchecked_after_a_rescan(
        qapp, two_project_batch):
    from pysurvanalysis.apps.batch_preflight import BatchPreflightDialog

    dialog = BatchPreflightDialog(None, two_project_batch, checked=["ProjA"])
    try:
        assert dialog.selected_keys == ["ProjA"]
        dialog.reload()                       # what Fix… and Rescan do
        assert dialog.selected_keys == ["ProjA"]
        assert dialog.user_choices == {"ProjB": False}
    finally:
        dialog.close()


def test_a_repaired_project_joins_the_hub_table_unless_the_user_unchecked_it(
        qapp, tmp_path):
    from pysurvanalysis.apps.hub import HubWindow

    Project.create(tmp_path / "Good")
    make_experiment_dir(tmp_path / "Good" / "m1", minimal=True, n_per_cell=6)
    Project.create(tmp_path / "Broken")
    write_cohort(tmp_path / "Broken" / "m" / "data" / "c.csv")
    window = _quiet(HubWindow())
    try:
        window._set_selection(tmp_path)
        window._refresh_all()
        assert window._batch_checked_keys() == ["Good"]
        ## Repaired outside the table: nobody decided its box, so it follows
        ## the Project and joins.
        Project(tmp_path / "Broken").add_member("m")
        window._batch.rescan()
        window._refresh_all()
        assert window._batch_checked_keys() == ["Broken", "Good"]
        ## ...but a box the user unticked stays unticked.
        window._batch_table.item(0, 0).setCheckState(Qt.CheckState.Unchecked)
        window._refresh_all()
        assert window._batch_checked_keys() == ["Good"]
    finally:
        window.close()


# ── 4. a configured member with no data is marked ─────────────────────────

def test_a_configured_member_with_no_data_file_is_marked_blocked(qapp, own_project):
    from pysurvanalysis.apps.batch_preflight import blocked_color
    from pysurvanalysis.apps.hub import HubWindow

    empty = own_project.directory / "rep_empty"
    empty.mkdir()
    cfgmod.save_config(empty, {"input": {"format": "long"}})
    window = _quiet(HubWindow())
    try:
        window._set_selection(own_project.directory)
        window._refresh_all()
        rows = {window._members_table.item(r, 0).text(): r
                for r in range(window._members_table.rowCount())}
        row = rows["rep_empty"]
        assert window._members_table.item(row, 4).text().startswith("blocked")
        cell = window._members_table.item(row, 0)
        assert cell.foreground().color() == blocked_color()
        assert "no data" in cell.toolTip().lower() or "data/" in cell.toolTip()
        ## The healthy member is not.
        assert window._members_table.item(rows["rep_a"], 0).foreground().color() \
            != blocked_color()
    finally:
        window.close()


# ── 5. the numbers each cell stands for ───────────────────────────────────

def test_the_shown_slice_is_the_active_focus_else_the_largest_current_one():
    from pysurvanalysis.apps.hub import HubWindow
    from pysurvanalysis.domain.experiment import ExperimentStatus, FocusStatus
    from pysurvanalysis.domain.focus import Focus

    status = ExperimentStatus(name="m", focuses=(
        FocusStatus("Old", "old", analyzed=True, out_of_date=True, n_total=900),
        FocusStatus("Small", "small", analyzed=True, n_total=40),
        FocusStatus("Big", "big", analyzed=True, n_total=200),
        FocusStatus("Never", "never"),
    ))
    assert HubWindow._shown_slice(status).name == "Big"
    assert HubWindow._shown_slice(status, Focus("Small", {})).name == "Small"
    ## An Active Focus with nothing current falls back; out of date never wins.
    assert HubWindow._shown_slice(status, Focus("Old", {})).name == "Big"
    assert HubWindow._shown_slice(ExperimentStatus(name="m")) is None


def test_the_project_tile_counts_only_current_results(hub, own_project):
    member = own_project.member("rep_a")
    member.run_analysis()
    hub._refresh_all()
    assert "1/1 Focuses analysed" in hub._tiles["project"].toolTip()
    ## A Reference Level changed since: the saved run is Out of Date.
    focus = member.focus(FACTORIAL)
    member.save_focuses([focus.copy(reference={"Treatment": "drug"})])
    hub._refresh_all()
    assert "0/1 Focuses analysed" in hub._tiles["project"].toolTip()


def test_the_qc_tile_counts_the_chambers_the_configuration_removes(tmp_path):
    from pysurvanalysis import exclusions
    from pysurvanalysis.apps.hub import HubWindow
    from pysurvanalysis.domain import SurvivalExperiment
    from tests.conftest import write_dlife_workbook

    directory = tmp_path / "dlife"
    write_dlife_workbook(directory / "data" / "census.xlsx")
    cfgmod.save_config(directory, {"exclusions": {"group": "bad"}})
    ## Two chambers the file has, one it does not.
    exclusions.write_exclusions(directory, "bad", [1, 2, 99])
    experiment = SurvivalExperiment(directory)
    assert HubWindow._chambers_excluded(experiment) == 2


# ── 6. the Plots sub-tile's headline follows the Focus ────────────────────

def test_the_plots_subtile_names_the_faceted_km_for_a_crossed_focus(hub):
    _load(hub)                                # the 2×2 Focus
    assert "headline: km_faceted" in hub._subtiles["plots"].toolTip()


# ── 7. the Project card's Edit scripts… opens the Project level ───────────

def test_the_project_cards_edit_scripts_opens_project_yaml(hub, monkeypatch):
    from pysurvanalysis.script_editor import window as editor_mod

    _load(hub)                                # an experiment is loaded too
    opened = []

    class _Editor:
        def __init__(self, target):
            opened.append(target)
            from PyQt6.QtCore import QObject, pyqtSignal

            class _Sig(QObject):
                scriptsSaved = pyqtSignal(str)

            self._sig = _Sig()
            self.scriptsSaved = self._sig.scriptsSaved

        def show(self):
            pass

    monkeypatch.setattr(editor_mod, "ScriptEditorWindow", _Editor)
    hub._action_open_script_editor(project_level=True)
    hub._action_open_script_editor()
    assert opened == [str(hub._project.directory), str(hub._experiment.directory)]


# ── 8. the QC viewer's saves reach the Active group picker ────────────────

def _groups(hub):
    return [hub._group_combo.itemText(i) for i in range(hub._group_combo.count())]


def test_closing_a_watched_window_refreshes_the_group_picker(hub):
    from PyQt6.QtWidgets import QWidget

    from pysurvanalysis import exclusions
    from pysurvanalysis.apps.hub import _CloseWatcher

    _load(hub)
    exclusions.write_exclusions(hub._experiment.directory, "fresh", ["x"])
    viewer = QWidget()
    _CloseWatcher(viewer, hub._refresh_all)
    viewer.show()
    viewer.close()
    QApplication.instance().processEvents()
    assert "fresh" in _groups(hub)


def test_a_save_in_the_qc_viewer_reaches_the_group_picker(hub, monkeypatch):
    from pysurvanalysis.apps import qc_viewer

    ## This member is a CSV, which the viewer says has no chambers — in a
    ## modal, which offscreen would wait on forever.
    for name in ("information", "warning"):
        monkeypatch.setattr(qc_viewer.QMessageBox, name, lambda *a, **k: None)
    _load(hub)
    hub._action_open_qc_viewer()
    viewer = hub._qc_window
    try:
        ## What the viewer's Save does, minus its dialog: write, then say so.
        from pysurvanalysis import exclusions

        exclusions.write_exclusions(hub._experiment.directory, "saved_now", ["z"])
        viewer.exclusionsSaved.emit("saved_now")
        assert "saved_now" in _groups(hub)
    finally:
        viewer.close()


# ── 9. the Batch picker is saved to batch.yaml ────────────────────────────

def test_designating_a_script_writes_batch_yaml_and_none_removes_it(tmp_path):
    from pysurvanalysis.domain import Batch

    batch = Batch(tmp_path)
    assert batch.designate(None) is False
    assert not batch.config_path.exists()     # no file for "each its own"
    assert batch.designate("Report pipeline") is True
    assert Batch(tmp_path).designated_script == "Report pipeline"
    assert batch.designate(None) is True
    assert Batch(tmp_path).designated_script is None


def test_the_batch_picker_choice_is_persisted(qapp, two_project_batch):
    from pysurvanalysis.apps.hub import BATCH_OWN_SCRIPT_ITEM, HubWindow
    from pysurvanalysis.domain import Batch

    window = _quiet(HubWindow())
    try:
        window._set_selection(two_project_batch)
        window._refresh_all()
        window._batch_script.setCurrentText("Report pipeline")
        window._on_batch_script_chosen(window._batch_script.currentIndex())
        assert Batch(two_project_batch).designated_script == "Report pipeline"
        window._refresh_all()
        assert window._batch_script.currentText() == "Report pipeline"
        window._batch_script.setCurrentText(BATCH_OWN_SCRIPT_ITEM)
        window._on_batch_script_chosen(0)
        assert Batch(two_project_batch).designated_script is None
    finally:
        window.close()


# ── 10. one rule for which script a name means ────────────────────────────

def test_a_central_script_wins_a_name_everywhere(own_project):
    from pysurvanalysis.script_editor.project_actions import resolve_experiment_script

    member_dir = own_project.member("rep_a").directory
    config = cfgmod.load_config(member_dir)
    config["scripts"] = [{"name": "Shared", "steps": [{"action": "load_data"}]}]
    cfgmod.save_config(member_dir, config)
    own_project.config["experiment_scripts"] = [
        {"name": "Shared", "steps": [{"action": "run_analysis"}]}]
    own_project.save()

    project = Project(own_project.directory)
    member = project.member("rep_a")
    listed = [s for s in member.scripts() if s["name"] == "Shared"]
    assert listed == [{"name": "Shared", "steps": [{"action": "run_analysis"}]}]
    assert resolve_experiment_script(member, project, "Shared") == [
        {"action": "run_analysis"}]


def test_the_hub_runs_the_central_script_too(hub, own_project, monkeypatch):
    from pysurvanalysis.script_editor import project_actions

    own_project.config["experiment_scripts"] = [
        {"name": "Standard analysis", "steps": [{"action": "load_data"}]}]
    own_project.save()
    hub._reload_from_disk()
    hub._refresh_all()
    _load(hub)
    ran = []
    monkeypatch.setattr(project_actions, "run_experiment_script",
                        lambda exp, steps, **kw: ran.append(steps))
    monkeypatch.setattr(hub, "_spawn", lambda _name, fn, **kw: fn())
    hub._scripts_combo.setCurrentText("Standard analysis")
    hub._action_run_experiment_script()
    assert ran == [[{"action": "load_data"}]]


# ── 11. the AI narrative: provider, saving, digest ────────────────────────

class _FakeProvider:
    name = "fake"
    model = "fake-1"

    def __init__(self):
        self.calls = 0

    def complete(self, system, prompt, max_tokens=1600):
        self.calls += 1
        return f"Paragraph {self.calls}."


def test_the_narrative_is_saved_and_a_rerun_deletes_it(tmp_path):
    from pysurvanalysis.ai import narrative

    root = tmp_path / "p"
    Project.create(root, name="P")
    make_experiment_dir(root / "rep_a", minimal=True, n_per_cell=8, seed=1)
    make_experiment_dir(root / "rep_b", minimal=True, n_per_cell=8, seed=2)
    project = Project(root)
    for member in project.members():
        member.run_analysis()

    written = narrative.generate(project, provider=_FakeProvider())
    path = narrative.narrative_path(project)
    assert path.is_file()
    assert narrative.load(project) == written
    assert narrative.ACROSS_KEY in written

    ## Re-running one Focus deletes its paragraph and the across paragraph
    ## written from it; the other member's paragraph stays.
    Project(root).member("rep_a").run_analysis()
    kept = narrative.load(Project(root))
    assert set(kept) == {k for k in written if k.startswith("rep_b")}
    on_disk = json.loads(path.read_text(encoding="utf-8"))
    assert "across" not in on_disk
    assert all(not k.startswith("rep_a") for k in on_disk["sections"])

    Project(root).member("rep_b").run_analysis()
    assert narrative.load(Project(root)) == {}
    assert not path.exists()


def test_project_report_with_narrative_uses_the_chosen_provider(hub, monkeypatch):
    from pysurvanalysis import project_report
    from pysurvanalysis.ai import narrative

    asked = []
    monkeypatch.setattr(narrative, "generate",
                        lambda project, provider=None, log=None: asked.append(provider) or {})
    monkeypatch.setattr(project_report, "write_project_report",
                        lambda *a, **k: {"md": "x"})
    monkeypatch.setattr(hub, "_spawn", lambda _name, fn, **kw: fn())
    hub._ai_provider.clear()
    hub._ai_provider.addItems(["anthropic", "openai"])
    hub._ai_provider.setCurrentText("openai")
    hub._action_project_report(with_narrative=True)
    assert asked == ["openai"]


def test_the_digest_reads_the_lr_statistic_under_any_name_and_has_the_mean():
    from pysurvanalysis.ai.narrative import lr_statistic

    assert lr_statistic({"statistic": 1.5, "lr_stat": 9, "chi2": 9}) == 1.5
    assert lr_statistic({"lr_stat": 2.5, "chi2": 9}) == 2.5
    assert lr_statistic({"chi2": 3.5}) == 3.5
    assert lr_statistic({}) is None


def test_the_digest_carries_the_mean_survival_table(tmp_path):
    from pysurvanalysis.ai import narrative
    from pysurvanalysis.project_report import SavedAnalysis

    root = tmp_path / "p"
    Project.create(root, name="P")
    make_experiment_dir(root / "rep_a", minimal=True, n_per_cell=8)
    member = Project(root).member("rep_a")
    member.run_analysis()
    digest = narrative.member_digest(SavedAnalysis(member, member.focus(FACTORIAL)))
    assert "Mean survival" in digest


# ── 12. the Script Editor and the Hub ─────────────────────────────────────

def test_saving_scripts_reloads_the_hubs_configs(hub, monkeypatch):
    from pysurvanalysis.script_editor import window as editor_mod

    _load(hub)
    monkeypatch.setattr(editor_mod.QMessageBox, "information",
                        lambda *a, **k: None)
    editor = editor_mod.ScriptEditorWindow(str(hub._experiment.directory))
    try:
        editor.scriptsSaved.connect(hub._on_scripts_saved)
        editor._scripts.append({"name": "Brand new", "steps": []})
        editor._save()
    finally:
        editor._dirty = False
        editor.close()
    assert "Brand new" in [s["name"] for s in hub._experiment.scripts()]
    combo = [hub._scripts_combo.itemText(i) for i in range(hub._scripts_combo.count())]
    assert "Brand new" in combo


def test_closing_the_editor_over_unsaved_edits_asks(qapp, own_project, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    from pysurvanalysis.script_editor import window as editor_mod

    editor = editor_mod.ScriptEditorWindow(str(own_project.member("rep_a").directory))
    editor.show()
    editor._dirty = True
    monkeypatch.setattr(editor_mod.QMessageBox, "question",
                        lambda *a, **k: QMessageBox.StandardButton.Cancel)
    editor.close()
    assert editor.isVisible()                 # Cancel kept it open
    monkeypatch.setattr(editor_mod.QMessageBox, "question",
                        lambda *a, **k: QMessageBox.StandardButton.Discard)
    editor.close()
    assert not editor.isVisible()


def test_project_level_step_cards_take_the_project_registry(qapp, own_project):
    from PyQt6.QtWidgets import QLabel

    from pysurvanalysis.script_editor import project_actions
    from pysurvanalysis.script_editor.window import ScriptEditorWindow

    editor = ScriptEditorWindow(str(own_project.directory))
    try:
        assert editor._level == "project"
        editor._canvas.set_steps([{"action": "run_in_experiments",
                                   "script": "Standard analysis"},
                                  {"action": "render_publication_figures"}])
        texts = [l.text() for l in editor._canvas.findChildren(QLabel)]
        assert "Run in experiments" in texts
        assert project_actions.PROJECT_ACTIONS[
            "render_publication_figures"].title in texts
        assert "run_in_experiments" not in texts
    finally:
        editor.close()


def test_the_palette_has_no_dead_type_suffix(qapp, own_project):
    from pysurvanalysis.script_editor.window import ScriptEditorWindow

    editor = ScriptEditorWindow(str(own_project.member("rep_a").directory))
    try:
        items = [editor._palette._list.item(i).text()
                 for i in range(editor._palette._list.count())]
        assert not any("·type" in text for text in items)
    finally:
        editor.close()


# ── 13. actions.py ────────────────────────────────────────────────────────

def test_the_rmst_action_offers_no_parameter_it_ignores():
    from pysurvanalysis import plotting
    from pysurvanalysis.script_editor import actions

    assert "include_interactions" not in [p.name for p in actions.POOL["rmst"].params]
    sigma = {p.name: p for p in actions.POOL["hazard_plot"].params}["sigma"]
    assert sigma.default == plotting.SMOOTHED_HAZARD_SIGMA


def test_parametric_aft_logs_a_readable_table(standalone):
    from pysurvanalysis.script_editor import actions
    from pysurvanalysis.script_editor.spec import RunContext

    logged = []
    ctx = RunContext(experiment=standalone, log=logged.append)
    actions.POOL["load_data"].execute({}, ctx)
    actions.POOL["parametric_aft"].execute({}, ctx)
    text = "\n".join(logged)
    assert "AIC" in text and "Weibull" in text
    assert "fitted_model" not in text and "Fitter" not in text


def test_quick_look_figures_use_the_experiments_time_label(standalone):
    import matplotlib

    matplotlib.use("Agg")
    from pysurvanalysis.script_editor import actions
    from pysurvanalysis.script_editor.spec import RunContext

    figures = []
    ctx = RunContext(experiment=standalone,
                     figure=lambda title, fig: figures.append(fig))
    actions.POOL["load_data"].execute({}, ctx)
    actions.POOL["km_curves"].execute({}, ctx)
    expected = standalone.type.resolve_time_label(standalone.config)
    assert figures[0].axes[0].get_xlabel() == expected


@pytest.fixture
def dlife_member(tmp_path):
    """A standalone DLife experiment with two Exclusion Groups."""
    from pysurvanalysis import exclusions
    from pysurvanalysis.domain import SurvivalExperiment
    from tests.conftest import write_dlife_workbook

    directory = tmp_path / "dlife"
    write_dlife_workbook(directory / "data" / "census.xlsx", chambers=8)
    cfgmod.save_config(directory, {"exclusions": {"group": "base"}})
    exclusions.write_exclusions(directory, "base", [1])
    exclusions.write_exclusions(directory, "extra", [2])
    return SurvivalExperiment(directory)


def test_apply_exclusions_after_load_drops_from_the_whole_frame(dlife_member):
    from pysurvanalysis.script_editor import actions
    from pysurvanalysis.script_editor.spec import RunContext

    ctx = RunContext(experiment=dlife_member)
    actions.POOL["load_data"].execute({}, ctx)
    assert 2 in set(ctx.raw_data["chamber"].map(int))
    actions.POOL["apply_exclusions"].execute({"group": "extra"}, ctx)
    ## Not just the current slice: a Focus cut later comes from raw_data.
    assert 2 not in set(ctx.raw_data["chamber"].map(int))
    assert 2 not in set(ctx.data["chamber"].map(int))
    assert ctx.exclusion_group == "base + extra"


def test_a_script_group_is_stamped_on_the_run_it_changed(dlife_member):
    from pysurvanalysis.script_editor import project_actions

    steps = [{"action": "load_data"},
             {"action": "apply_exclusions", "group": "extra"},
             {"action": "run_in_focuses"},
             {"action": "run_analysis"}]
    project_actions.run_experiment_script(dlife_member, steps)
    summary_path = dlife_member.outputs(dlife_member.focuses()[0]).summary
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert summary["exclusion_group"] == "base + extra"
    ## The Hub's experiment is untouched: its config still names one group.
    assert dlife_member.exclusion_group == "base"


def test_the_report_action_honours_output_dir(standalone, tmp_path):
    from pysurvanalysis.script_editor import project_actions

    out = tmp_path / "reports"
    focus = standalone.focuses()[0]
    project_actions.run_experiment_script(
        standalone, [{"action": "report", "output_dir": str(out)}], focus=focus)
    assert any(p.suffix == ".md" for p in out.iterdir())
    assert standalone.outputs(focus).summary.is_file()


# ── 14. the unused runner is gone ─────────────────────────────────────────

def test_the_unused_script_runner_is_gone():
    import importlib.util

    assert importlib.util.find_spec("pysurvanalysis.script_editor.runner") is None


# ── 15. uncaught exceptions are logged, and broken YAML is said ───────────

def test_an_uncaught_exception_is_logged_not_fatal(hub, monkeypatch):
    from pysurvanalysis.apps.hub import install_excepthook

    monkeypatch.setattr(sys, "excepthook", sys.excepthook)
    install_excepthook(hub)
    try:
        raise RuntimeError("boom in a slot")
    except RuntimeError:
        sys.excepthook(*sys.exc_info())
    assert "boom in a slot" in hub._log.toPlainText()


def test_selecting_a_project_with_broken_yaml_warns_instead_of_raising(qapp, tmp_path):
    from pysurvanalysis.apps.hub import HubWindow

    root = tmp_path / "broken"
    Project.create(root, name="Broken")
    (root / cfgmod.PROJECT_FILENAME).write_text("name: Broken\n\tquestion: x\n",
                                               encoding="utf-8")
    window = _quiet(HubWindow())
    try:
        window._set_selection(root)
        window._refresh_all()
        assert window._warned and "project.yaml" in window._warned[-1]
        ## Not loaded, but still validatable: the parse error is the report.
        window._action_validate_project()
        assert "not valid YAML" in window._log.toPlainText().splitlines()[-2]
    finally:
        window.close()


def test_a_broken_batch_yaml_lists_the_batch_but_refuses_to_run_or_write(
        two_project_batch):
    from pysurvanalysis.domain import Batch

    (two_project_batch / cfgmod.BATCH_FILENAME).write_text(
        "script: [unclosed\n", encoding="utf-8")
    batch = Batch(two_project_batch)
    assert batch.config_error and "not valid YAML" in batch.config_error
    assert batch.project_keys() == ["ProjA", "ProjB"]
    with pytest.raises(ValueError):
        batch.run()
    with pytest.raises(ValueError):
        batch.designate("Report pipeline")
    assert "[unclosed" in (two_project_batch / cfgmod.BATCH_FILENAME).read_text(
        encoding="utf-8")                     # never overwritten


def test_the_script_editor_never_saves_over_a_file_it_cannot_parse(
        qapp, own_project, monkeypatch):
    from pysurvanalysis.script_editor import window as editor_mod

    warned = []
    monkeypatch.setattr(editor_mod.QMessageBox, "warning",
                        lambda *a, **k: warned.append(a[2] if len(a) > 2 else ""))
    member_dir = own_project.member("rep_a").directory
    editor = editor_mod.ScriptEditorWindow(str(member_dir))
    try:
        broken = "scripts:\n\t- name: x\n"
        cfgmod.config_path(member_dir).write_text(broken, encoding="utf-8")
        editor._save()
        assert warned
        assert cfgmod.config_path(member_dir).read_text(encoding="utf-8") == broken
    finally:
        editor._dirty = False
        editor.close()


# ── 16. a blank group never silently inherits the Project's ───────────────

def test_a_blank_group_overrides_a_project_default_group(qapp, tmp_path):
    from pysurvanalysis.apps.hub import HubWindow

    root = tmp_path / "p"
    Project.create(root, name="P", defaults={"exclusions": {"group": "qc1"}})
    make_experiment_dir(root / "rep_a", minimal=True, n_per_cell=6)
    window = _quiet(HubWindow())
    try:
        window._set_selection(root)
        window._refresh_all()
        _load(window)
        assert window._experiment.exclusion_group == "qc1"
        window._group_combo.setEditText("")
        window._action_set_exclusion_group()
        assert window._experiment.exclusion_group is None
        assert cfgmod.load_config(root / "rep_a")["exclusions"] == {"group": ""}
    finally:
        window.close()


def test_a_blank_group_with_no_project_default_removes_the_key(hub):
    _load(hub)
    hub._group_combo.setEditText("")
    hub._action_set_exclusion_group()
    assert "exclusions" not in cfgmod.load_config(hub._experiment.directory)


# ── 18. a Batch key with a Windows anchor is refused ──────────────────────

@pytest.mark.parametrize("key", ["/etc", "\\etc", "C:foo", "C:/x", "a\\..\\..\\b"])
def test_a_rooted_or_escaping_key_is_refused_on_any_platform(tmp_path, key):
    from pysurvanalysis.domain.batch import project_directory

    with pytest.raises(ValueError):
        project_directory(tmp_path, key)


def test_a_relative_key_still_resolves(tmp_path):
    from pysurvanalysis.domain.batch import project_directory

    assert project_directory(tmp_path, "Sept2026/ProjA") == \
        tmp_path.resolve() / "Sept2026" / "ProjA"


def test_cox_ph_without_interactions_fits_main_effects_only(tmp_path):
    """The switch used to hide the interaction rows of a model still fitted
    with them; off now means the main-effects model, and no LR test."""
    from pysurvanalysis import statistics
    from pysurvanalysis.domain import SurvivalExperiment
    from tests.conftest import make_experiment_dir

    data, _factors = SurvivalExperiment(make_experiment_dir(tmp_path / "cx")).load()
    both = statistics.cox_interaction_analysis(data, ["Genotype", "Treatment"])
    main = statistics.cox_interaction_analysis(data, ["Genotype", "Treatment"],
                                               interactions=False)
    assert any(":" in c for c in both["coefficients"]["covariate"])
    assert not any(":" in c for c in main["coefficients"]["covariate"])
    assert main["lr_interaction"] is None
    assert main["log_likelihood"] == pytest.approx(both["lr_interaction"]["ll_main"], abs=1e-3)


def test_a_broken_plot_specs_file_is_said_not_raised(qapp, tmp_path, monkeypatch):
    from pysurvanalysis.apps.hub import HubWindow
    from pysurvanalysis.domain import Project
    from tests.conftest import make_experiment_dir

    root = tmp_path / "ps"
    Project.create(root, name="PS")
    make_experiment_dir(root / "rep_a", minimal=True, n_per_cell=10)
    (root / "plot_specs.yaml").write_text("plots:\n\t- bad\n", encoding="utf-8")
    hub = HubWindow(str(root))
    warned = []
    monkeypatch.setattr(hub, "_warn", warned.append)
    try:
        hub._on_member_double_clicked(hub._members_table.model().index(0, 0))
        hub._action_open_plot_editor()
        assert warned and "plot_specs.yaml" in warned[0]
    finally:
        hub.close()
