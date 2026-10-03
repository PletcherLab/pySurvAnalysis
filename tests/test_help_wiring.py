"""Every window outside the Hub carries "?" buttons onto real manual pages.

Each window is built offscreen; the test checks its HelpButtons name topics
the manifest lists, that clicking one opens the manual at that topic, and that
F1 opens the window's own page.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PyQt6")

from PyQt6.QtGui import QShortcut  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

from pysurvanalysis.help.manifest import TITLES  # noqa: E402
from pysurvanalysis.help.window import HelpButton, close_help, help_window  # noqa: E402
from pysurvanalysis.ui import apply_theme  # noqa: E402


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    apply_theme(app, "light")
    return app


@pytest.fixture(autouse=True)
def _close_manual():
    yield
    close_help()


def _check(window, expected: set[str], f1_topic: str) -> None:
    """Every "?" names a listed topic and opens it; *expected* are all there;
    F1 opens *f1_topic*."""
    buttons = window.findChildren(HelpButton)
    topics = {b.topic for b in buttons}
    assert buttons, "no help buttons"
    assert topics <= set(TITLES), topics - set(TITLES)
    assert expected <= topics, expected - topics
    for button in buttons:
        button.click()
        assert help_window().current == button.topic
    shortcuts = [s for s in window.findChildren(QShortcut)
                 if s.key().toString() == "F1"]
    assert shortcuts, "no F1 shortcut"
    shortcuts[0].activated.emit()
    assert help_window().current == f1_topic


@pytest.fixture
def member(tmp_path):
    from pysurvanalysis.domain import Project
    from tests.conftest import make_experiment_dir

    root = tmp_path / "hw"
    Project.create(root, name="HW")
    make_experiment_dir(root / "rep_a", minimal=True, n_per_cell=10, seed=1)
    return Project(root).member("rep_a")


def test_focus_window_help(qapp, member):
    from pysurvanalysis.apps.focus_window import FocusWindow

    window = FocusWindow(None, member)
    try:
        _check(window, {"focus", "focus-window", "reference-level",
                        "focus-shape", "defined-plots", "focus-status"},
               "focus-window")
    finally:
        window.close()


def test_qc_viewer_help(qapp):
    from pysurvanalysis.apps.qc_viewer import QcViewerWindow

    window = QcViewerWindow()
    try:
        _check(window, {"qc-viewer", "exclusions"}, "qc-viewer")
    finally:
        window.close()


def test_plot_editor_help(qapp, member):
    from pysurvanalysis.apps.plot_editor import PlotEditorWindow

    window = PlotEditorWindow(member)
    try:
        _check(window, {"plot-editor-figure", "plot-editor-canvas",
                        "plot-editor-curves", "plot-editor-panels",
                        "plot-editor-colours", "publication-figures"},
               "plot-editor")
    finally:
        window.close()


def test_project_info_dialog_help(qapp, tmp_path):
    from pysurvanalysis.apps.project_dialogs import ProjectInfoDialog

    dialog = ProjectInfoDialog(None, start_dir=str(tmp_path / "new"))
    try:
        _check(dialog, {"project-create", "config-project", "experiment-types",
                        "config-global"}, "project-create")
    finally:
        dialog.close()


def test_member_configs_dialog_help(qapp, member):
    from pysurvanalysis.apps.project_dialogs import MemberConfigsDialog

    dialog = MemberConfigsDialog(None, member.project)
    try:
        _check(dialog, {"project-members", "config-input", "config-experiment"},
               "project-members")
    finally:
        dialog.close()


def test_batch_preflight_help(qapp, member):
    from pysurvanalysis.apps.batch_preflight import BatchPreflightDialog

    dialog = BatchPreflightDialog(None, member.project.directory.parent)
    try:
        _check(dialog, {"preflight", "batch-panel"}, "preflight")
    finally:
        dialog.close()


def test_script_editor_help(qapp, member):
    from pysurvanalysis.script_editor.window import ScriptEditorWindow

    window = ScriptEditorWindow(str(member.directory))
    try:
        _check(window, {"script-editor", "scripts-overview", "script-actions"},
               "script-editor")
    finally:
        window.close()
