"""Fixes from the 2026-11-22 code review — each test would have caught its bug.

Domain tests first; the few that need the Hub import Qt inside the test and
never trigger a modal.
"""

from __future__ import annotations

import os

import pytest

from pysurvanalysis.domain import SurvivalExperiment, config as cfgmod
from pysurvanalysis.domain import focus as fm
from pysurvanalysis.domain.experiment import ExperimentError

from conftest import make_experiment_dir


# ---------------------------------------------------------------------------
# A Focus save writes over the file as it is now, not as it was loaded
# ---------------------------------------------------------------------------

def _hand_edit(directory, **changes):
    """Change survival_config.yaml behind a loaded experiment's back — a
    script saved in the Script Editor, a key typed into the file."""
    config = cfgmod.load_config(directory)
    config.update(changes)
    cfgmod.save_config(directory, config)


def test_a_focus_save_keeps_what_was_written_to_the_file_since_loading(tmp_path):
    exp = SurvivalExperiment(make_experiment_dir(tmp_path / "lone"))
    script = {"name": "Mine", "steps": [{"action": "run_analysis"}]}
    _hand_edit(exp.directory, scripts=[script], omit={"analyses": ["parametric_aft"]},
               future_key="kept")

    [focus] = exp.focuses()
    exp.save_focuses([focus.copy(colours={"wt/ctrl": "#112233"})])

    after = cfgmod.load_config(exp.directory)
    assert after["future_key"] == "kept"
    assert after["scripts"] == [script]
    assert after["omit"] == {"analyses": ["parametric_aft"]}
    assert after["focuses"][focus.name]["colours"] == {"wt/ctrl": "#112233"}


def test_materialising_never_replaces_focuses_written_since_loading(tmp_path):
    exp = SurvivalExperiment(make_experiment_dir(tmp_path / "lone", focus=None))
    mine = {"Mine": {"factors": {"Genotype": ["wt", "mut"]}}}
    _hand_edit(exp.directory, focuses=mine)

    exp.materialize_focuses()

    assert cfgmod.load_config(exp.directory)["focuses"] == mine
    assert [f.name for f in exp.focuses()] == ["Mine"]


def test_a_focus_save_refuses_a_file_that_no_longer_parses(tmp_path):
    exp = SurvivalExperiment(make_experiment_dir(tmp_path / "lone"))
    broken = "focuses:\n\tA: {}\n"
    exp.config_path.write_text(broken, encoding="utf-8")
    [focus] = exp.focuses()
    with pytest.raises(ExperimentError, match="not valid YAML"):
        exp.save_focuses([focus])
    assert exp.config_path.read_text(encoding="utf-8") == broken


# ---------------------------------------------------------------------------
# Unknown keys inside a Focus ride through a write
# ---------------------------------------------------------------------------

def test_a_focus_keeps_keys_it_does_not_know_through_a_round_trip():
    body = {"factors": {"Sex": ["F", "M"]}, "note": "the crowding arm",
            "future": {"a": [1, 2]}}
    [focus] = fm.parse_focuses({"focuses": {"Crowding": body}})
    renamed = focus.copy(name="Crowding2", colours={"F": "#112233"})
    out = fm.focuses_to_config([renamed])["Crowding2"]
    assert out["note"] == "the crowding arm"
    assert out["future"] == {"a": [1, 2]}
    assert out["colours"] == {"F": "#112233"}


def test_a_focus_save_keeps_a_hand_written_key_inside_the_focus(tmp_path):
    exp = SurvivalExperiment(make_experiment_dir(tmp_path / "lone"))
    config = cfgmod.load_config(exp.directory)
    [name] = config["focuses"]
    config["focuses"][name]["note"] = "why this slice"
    cfgmod.save_config(exp.directory, config)
    exp = SurvivalExperiment(exp.directory)

    exp.rename_focus(name, "Renamed")

    assert cfgmod.load_config(exp.directory)["focuses"]["Renamed"]["note"] == "why this slice"


# ---------------------------------------------------------------------------
# Copy config from… never copies another member's data file
# ---------------------------------------------------------------------------

@pytest.fixture
def quiet_hub():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    from pysurvanalysis.apps.hub import HubWindow

    app = QApplication.instance() or QApplication([])  # noqa: F841 - kept alive
    window = HubWindow()
    window._warned = []
    window._warn = lambda message: window._warned.append(message)
    yield window
    window.close()


def test_copy_config_from_another_member_leaves_its_data_file_behind(
        quiet_hub, tmp_path, monkeypatch):
    import PyQt6.QtWidgets as qtw

    from pysurvanalysis.domain import Project

    from conftest import write_dlife_workbook

    recording = write_dlife_workbook(tmp_path / "runs" / "R1.xlsx")
    project = Project.create(tmp_path / "proj", name="P")
    source = project.reference_data_file(recording)
    _hand_edit(source.directory, global_={"note": "kept"})
    new = project.add_member("rep_new")
    quiet_hub._set_selection(project.directory)
    monkeypatch.setattr(qtw.QFileDialog, "getOpenFileName", staticmethod(
        lambda *a, **k: (str(source.config_path), "")))

    assert quiet_hub._copy_member_config("rep_new", new.directory)

    copied = cfgmod.load_config(new.directory)
    assert "data_file" not in copied
    assert copied["global_"] == {"note": "kept"}
    assert Project(project.directory).duplicates() == {}
