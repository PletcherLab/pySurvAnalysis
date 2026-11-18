"""Set data file… writes the path relative to the member folder.

An ambiguous member's candidates are offered by bare name. Writing that name
alone (``data_file: a.csv``) named a file at the member root, which for the
usual two files in ``data/`` does not exist — so the repair turned an
ambiguous member into one with no data. All three places the repair is
offered (the Hub, the Experiment configs dialog, the Batch preflight) now
write ``data/a.csv``.
"""

from __future__ import annotations

import os

import pytest

from pysurvanalysis.domain import Project, SurvivalExperiment, config as cfgmod, layout
from tests.conftest import write_cohort


@pytest.fixture
def ambiguous(tmp_path):
    """A Project whose one member holds two candidate files in ``data/``."""
    root = tmp_path / "batch" / "proj"
    Project.create(root, name="Ambiguous")
    member = root / "rep"
    write_cohort(member / "data" / "a.csv")
    write_cohort(member / "data" / "b.csv", seed=1)
    cfgmod.save_config(member, {"experiment_type": "standard_lifespan",
                                "input": {"format": "long"}})
    item = layout.classify(member)
    assert item.status == layout.AMBIGUOUS and item.candidates == ("a.csv", "b.csv")
    return item


def _settled(member) -> None:
    """The repair worked: the member is usable and loads the chosen file."""
    assert cfgmod.load_config(member)["data_file"] == "data/a.csv"
    assert layout.classify(member).status == layout.OK
    assert SurvivalExperiment(member).data_file() == member / "data" / "a.csv"


def test_the_value_is_relative_to_the_member_folder(ambiguous):
    assert layout.data_file_value(ambiguous.directory, "a.csv") == "data/a.csv"


def test_a_candidate_at_the_root_stays_a_bare_name(tmp_path):
    member = tmp_path / "rep"
    write_cohort(member / "a.csv")
    write_cohort(member / "b.csv", seed=1)
    assert layout.data_file_value(member, "b.csv") == "b.csv"


@pytest.fixture
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_the_hub_writes_the_relative_path(qapp, ambiguous):
    from pysurvanalysis.apps.hub import HubWindow

    window = HubWindow(str(ambiguous.directory.parent))
    try:
        window._warn = lambda message: pytest.fail(message)
        window._prompt_choice = lambda title, label, options: options[0]
        window._name_member_data_file(ambiguous)
    finally:
        window.close()
    _settled(ambiguous.directory)


def test_the_configs_dialog_writes_the_relative_path(qapp, ambiguous,
                                                     monkeypatch):
    import PyQt6.QtWidgets as qtw

    from pysurvanalysis.apps.project_dialogs import MemberConfigsDialog

    monkeypatch.setattr(qtw.QInputDialog, "getItem",
                        staticmethod(lambda *a, **k: ("a.csv", True)))
    dialog = MemberConfigsDialog(None, Project(ambiguous.directory.parent))
    try:
        row = [r.name for r in dialog._rows].index("rep")
        dialog._table.selectRow(row)
        assert dialog._btn_data_file.isEnabled()
        dialog._name_data_file()
    finally:
        dialog.close()
    _settled(ambiguous.directory)


def test_the_preflight_writes_the_relative_path(qapp, ambiguous, monkeypatch):
    import PyQt6.QtWidgets as qtw

    from pysurvanalysis.apps.batch_preflight import BatchPreflightDialog

    monkeypatch.setattr(qtw.QInputDialog, "getItem",
                        staticmethod(lambda *a, **k: ("a.csv", True)))
    batch = ambiguous.directory.parent.parent
    dialog = BatchPreflightDialog(None, batch)
    try:
        dialog._name_data_file(ambiguous)
    finally:
        dialog.close()
    _settled(ambiguous.directory)
