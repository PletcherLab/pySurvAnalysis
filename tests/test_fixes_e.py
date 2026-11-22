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
def quiet_hub(qapp):
    from pysurvanalysis.apps.hub import HubWindow

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


# ---------------------------------------------------------------------------
# Every console script resolves inside the package the wheel ships
# ---------------------------------------------------------------------------

def test_every_console_script_lives_in_the_shipped_package():
    """The wheel ships ``pysurvanalysis/`` alone, so ``main:main`` (the
    repository's root ``main.py``) made the installed ``pysurvanalysis``
    command fail with ModuleNotFoundError."""
    import importlib
    import tomllib
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    meta = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    shipped = meta["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"]
    for command, target in meta["project"]["scripts"].items():
        module, _, func = target.partition(":")
        assert module.split(".")[0] in shipped, f"{command} = {target}"
        assert callable(getattr(importlib.import_module(module), func)), command


def test_python_dash_m_reaches_the_same_command_line():
    from pysurvanalysis import __main__ as entry
    from pysurvanalysis.cli import main

    assert entry.main is main


# ---------------------------------------------------------------------------
# A chamber with a blank factor cell is still a chamber of the file
# ---------------------------------------------------------------------------

BY_GENOTYPE = {"ByGenotype": {"factors": {"Genotype": ["a", "b"]}}}


def _blank_treatment_member(directory, excluded=()):
    """Four chambers (1: b/a, 2: a/b, 3: b/b, 4: a/–): chamber 4's Treatment
    cell is blank. A Focus over Genotype alone pools over Treatment, so
    chamber 4's flies are in its ``a`` treatment."""
    import openpyxl

    from pysurvanalysis import exclusions

    from conftest import write_dlife_workbook

    path = write_dlife_workbook(directory / "data" / "cohort.xlsx", chambers=4)
    book = openpyxl.load_workbook(path)
    sheet = book["Design"]
    header = [c.value for c in sheet[1]]
    ## .value, not cell(value=None): openpyxl's cell() ignores a None value.
    sheet.cell(row=5, column=header.index("Treatment") + 1).value = None
    book.save(path)
    cfgmod.save_config(directory, {"experiment_type": "standard_lifespan",
                                   "input": {"format": "excel"},
                                   "exclusions": {"group": "default"},
                                   "focuses": BY_GENOTYPE})
    exclusions.write_exclusions(directory, "default", list(excluded))
    return SurvivalExperiment(directory)


def test_discovery_keeps_a_chamber_whose_factor_cell_is_blank(tmp_path):
    exp = _blank_treatment_member(tmp_path / "m")
    design = exp.design()
    assert design.levels["Treatment"] == ("a", "b")
    assert {fm.norm_chamber(c) for c, _cell in design.chamber_cells} == {1, 2, 3, 4}
    assert fm.focus_chambers(exp.focus("ByGenotype"), design) == {"1", "2", "3", "4"}


def test_unfiltered_still_leaves_out_the_chamber_with_no_treatment(tmp_path):
    exp = _blank_treatment_member(tmp_path / "m")
    whole = fm.unfiltered(exp.design())
    assert "4" not in fm.focus_chambers(whole, exp.design())


def test_excluding_a_blank_factor_chamber_is_stamped_and_read_as_a_change(tmp_path):
    from pysurvanalysis import exclusions

    exp = _blank_treatment_member(tmp_path / "m", excluded=[4])
    result = exp.run_analysis("ByGenotype")
    assert result.excluded_applied() == ["4"]
    assert not exp.status().focuses[0].out_of_date

    exclusions.write_exclusions(exp.directory, "default", [])
    [status] = SurvivalExperiment(exp.directory).status().focuses
    assert status.out_of_date
    assert any("no longer excludes 4" in r for r in status.out_of_date_reasons)


def test_a_cell_kept_alive_by_a_blank_factor_chamber_is_not_blocked(tmp_path):
    exp = _blank_treatment_member(tmp_path / "m", excluded=[2])
    [status] = exp.status().focuses
    assert status.blocked == ()
    assert exp.run_analysis("ByGenotype").focus_shape.populated == ("a", "b")


# ---------------------------------------------------------------------------
# The Project and Batch discovery agree on who the members are
# ---------------------------------------------------------------------------

def test_a_symlinked_copy_of_a_member_is_one_member_to_the_project_too(project):
    from pysurvanalysis.domain import Project, layout

    (project.directory / "rep_a_link").symlink_to(project.directory / "rep_a",
                                                  target_is_directory=True)
    listed = [m.name for m in layout.members_in(project.directory)]
    members = [d.name for d in Project(project.directory).member_dirs()]
    assert listed == members == ["rep_a", "rep_b"]


def test_a_hidden_folder_is_no_member_of_the_project_either(project):
    import shutil

    from pysurvanalysis.domain import Project, layout

    shutil.copytree(project.directory / "rep_a", project.directory / ".old_rep_a")
    listed = [m.name for m in layout.members_in(project.directory)]
    members = [d.name for d in Project(project.directory).member_dirs()]
    assert listed == members == ["rep_a", "rep_b"]


# ---------------------------------------------------------------------------
# An exclusion file that cannot be read never means "exclude nothing"
# ---------------------------------------------------------------------------

def test_an_exclusion_file_saved_by_excel_as_plain_csv_still_excludes(tmp_path):
    """Excel's "CSV (Comma delimited)" on Windows writes cp1252: one accented
    note made the UTF-8 read fail, and the whole file read as empty."""
    from pysurvanalysis import exclusions

    qc = tmp_path / "qc"
    qc.mkdir()
    (qc / "remove_chambers.csv").write_bytes(
        "group,chamber,note\ndefault,3,mouche écrasée\ndefault,7,\n".encode("cp1252"))
    assert exclusions.chambers_for_group(tmp_path, "default") == {3, 7}
    assert exclusions.read_notes(tmp_path, "default") == {3: "mouche écrasée"}


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0,
                    reason="root reads any file")
def test_a_run_refuses_an_exclusion_file_it_cannot_read(tmp_path):
    from pysurvanalysis import exclusions

    exp = SurvivalExperiment(make_experiment_dir(tmp_path / "lone",
                                                 exclusion_group="default"))
    path = exclusions.write_exclusions(exp.directory, "default", [3])
    path.chmod(0)
    try:
        with pytest.raises(ExperimentError, match="remove_chambers.csv"):
            exp.run_analysis()
        assert not list(exp.analysis_dir.rglob("run_summary_*.json"))
        ## Listing surfaces still answer rather than raise.
        assert exp.excluded_chambers() == set()
    finally:
        path.chmod(0o644)


# ---------------------------------------------------------------------------
# A level with a slash in it (fly genotypes) is one level
# ---------------------------------------------------------------------------

def test_a_genotype_with_a_slash_is_still_fully_crossed():
    focus = fm.Focus("GxD", {"Genotype": ["UAS-InR/+", "da-GS/UAS-InR"],
                             "Diet": ["AL", "DR"]})
    shape = fm.shape_of(focus, focus.implied_labels())
    assert shape.crossing_gaps == ()
    assert shape.admits(fm.FACTORIAL_MODEL) == (True, "")

    partial = fm.shape_of(focus, [t for t in focus.implied_labels()
                                  if t != "da-GS/UAS-InR/DR"])
    assert partial.crossing_gaps == ("Genotype=da-GS/UAS-InR × Diet=DR",)


def _slashed_frame():
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(3)
    rows = []
    for g in ("UAS-InR/+", "da-GS/UAS-InR"):
        for d in ("AL", "DR"):
            for t in rng.gamma(6.0, 6.0, size=30):
                rows.append({"time": round(float(t), 2), "event": 1,
                             "chamber": "N/A", "Genotype": g, "Diet": d})
    focus = fm.Focus("GxD", {"Genotype": ["UAS-InR/+", "da-GS/UAS-InR"],
                             "Diet": ["AL", "DR"]})
    return fm.apply_focus(pd.DataFrame(rows), focus), focus


def test_the_faceted_km_keeps_a_slashed_genotype_whole():
    from pysurvanalysis import lifetable, plotting
    from pysurvanalysis.experiment_types.factorial import factor_levels

    data, focus = _slashed_frame()
    fig = plotting.plot_km_faceted(lifetable.compute_lifetables(data),
                                   factor_levels(focus))
    axes = [ax for ax in fig.axes if ax.get_title()]
    assert [ax.get_title() for ax in axes] == ["Genotype: UAS-InR/+",
                                               "Genotype: da-GS/UAS-InR"]
    assert all(len(ax.get_lines()) >= 2 for ax in axes)


def test_the_interaction_plot_keeps_a_slashed_genotype_whole():
    import pandas as pd

    from pysurvanalysis import plotting
    from pysurvanalysis.experiment_types.factorial import factor_levels

    data, focus = _slashed_frame()
    levels = factor_levels(focus)
    ## The slashed factor on the lines: the second factor varies along x.
    swapped = {"Diet": levels["Diet"], "Genotype": levels["Genotype"]}
    fig = plotting.plot_lifespan_interaction(data, swapped)
    [ax] = fig.axes
    points = sum(len(c.get_children()) and len(c.lines[0].get_xdata())
                 for c in ax.containers)
    assert points == 4, pd.Series([c.lines[0].get_xdata() for c in ax.containers])


# ---------------------------------------------------------------------------
# The census loader says what it cannot use, and survives an empty result
# ---------------------------------------------------------------------------

def _census(design_rows, raw_rows):
    import pandas as pd

    design = pd.DataFrame(design_rows, columns=["Chamber", "SampleSize", "StartTime",
                                                "Genotype"])
    raw = pd.DataFrame(raw_rows, columns=["AgeH", "Chamber", "IntDeaths", "Censored"])
    return raw, design


def test_a_rawdata_chamber_missing_from_the_design_sheet_is_said():
    from pysurvanalysis import data_loader

    raw, design = _census([(1, 5, 0, "wt")],
                          [(24, 1, 2, 0), (48, 1, 3, 0), (24, 9, 4, 0)])
    df = data_loader.build_individual_data(raw, design, ["Genotype"])
    assert len(df) == 5
    assert any("Chamber 9" in w and "Design sheet" in w
               for w in df.attrs["load_warnings"]), df.attrs["load_warnings"]


def test_a_blank_sample_size_assumes_no_survivors_and_says_so():
    from pysurvanalysis import data_loader

    raw, design = _census([(1, None, 0, "wt"), (2, 6, 0, "wt")],
                          [(24, 1, 2, 0), (24, 2, 2, 0)])
    df = data_loader.build_individual_data(raw, design, ["Genotype"],
                                           assume_censored=True)
    assert (df["chamber"] == 1).sum() == 2          # what RawData recorded
    assert (df["chamber"] == 2).sum() == 6          # 2 deaths + 4 assumed censored
    assert any("Chamber 1" in w and "SampleSize" in w
               for w in df.attrs["load_warnings"])


def test_every_chamber_excluded_gives_an_empty_frame_not_a_key_error():
    from pysurvanalysis import data_loader

    raw, design = _census([(1, 5, 0, "wt")], [(24, 1, 2, 0)])
    df = data_loader.build_individual_data(raw, design, ["Genotype"],
                                           excluded_chambers={1})
    assert len(df) == 0
    assert list(df.columns) == ["time", "event", "chamber", "treatment", "Genotype"]


# ---------------------------------------------------------------------------
# The command line's --exclusion-group names both groups, as a script does
# ---------------------------------------------------------------------------

def test_the_command_lines_extra_group_is_stamped_beside_the_configs(
        tmp_path, monkeypatch, capsys):
    import json
    import sys

    from pysurvanalysis import cli, exclusions

    directory = make_experiment_dir(tmp_path / "lone", exclusion_group="default",
                                    n_per_cell=8)
    exclusions.write_exclusions(directory, "default", [3])
    exclusions.write_exclusions(directory, "extra", [5])
    monkeypatch.setattr(sys, "argv", ["pysurvanalysis", "run", str(directory),
                                      "--exclusion-group", "extra"])
    with pytest.raises(SystemExit) as stop:
        cli.main()
    assert stop.value.code == 0, capsys.readouterr().out
    [summary] = (directory / "analysis").rglob("run_summary_*.json")
    assert json.loads(summary.read_text())["exclusion_group"] == "default + extra"
    ## The config alone would not reproduce it, so it reads as Out of Date.
    [status] = SurvivalExperiment(directory).status().focuses
    assert status.out_of_date
