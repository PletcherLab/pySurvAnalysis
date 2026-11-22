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
