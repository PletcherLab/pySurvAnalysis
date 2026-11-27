"""The ``about:`` section in ``survival_config.yaml`` (ADR-0014): what the
package does with it, short of the editor.

P10's shared acceptance tests A2–A4 and A7–A8, and P15's S3–S7, at the
domain level. ``test_about_editor.py`` drives ``pysurv-config`` and the Hub.
Everything runs in temporary folders; nothing here knows about labdata's own
files — a catalogue that rewrites the section is just another writer of the
file.
"""

from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path

import pytest
import yaml

from pysurvanalysis import about as about_mod
from pysurvanalysis.domain import Project, SurvivalExperiment, config as cfgmod, layout
from pysurvanalysis.domain.focus import Focus
from tests.conftest import write_dlife_workbook

FOCUS = "Unfiltered"


def full_about() -> dict:
    """Every field, an unknown key, ``run:``, and a level mapping holding
    ``definition``, ``term``, ``label``, ``role`` and an unknown key — the
    section A3 starts from. The factors and levels are the conftest
    workbook's: Genotype and Treatment, each ``a`` and ``b``."""
    return {
        "run": "R-20261127-test-01",
        "title": "Lifespan on two diets, replicate 1",
        "purpose": "Whether the knockdown changes the response to diet.",
        "experimenter": "tester",
        "series": "diet-kd-2026",
        "organism": "Drosophila melanogaster",
        "sex": ["female"],
        "age_at_start": "2-3 days",
        "protocol": {"name": "DLife lifespan", "version": "4",
                     "link": "https://example.org/dlife"},
        "notes": "Incubator 3.",
        "factors": {
            "Genotype": {"kind": "genotype", "levels": {
                "a": "w1118",
                "b": {"definition": "da-GAL4 > UAS-RNAi", "term": "GEN-0042",
                      "label": "da > RNAi", "role": "treatment", "x_other": "kept"},
            }},
            "Treatment": {"kind": "diet", "levels": {"a": "5% SY", "b": "15% SY"}},
        },
        "x_lab": {"a": 1},
    }


def make_member(directory: Path, *, about=None, **config) -> Path:
    """A recording folder: a DLife workbook in ``data/`` and a config naming
    the Standard Lifespan type, *config*'s keys and, given one, *about*."""
    write_dlife_workbook(directory / "data" / "run.xlsx", chambers=4)
    body = {"experiment_type": "standard_lifespan", **config}
    if about is not None:
        body["about"] = about
    cfgmod.save_config(directory, body)
    return directory


def about_on_disk(directory: Path):
    return cfgmod.read_yaml(cfgmod.config_path(directory)).get("about")


def tables(directory: Path) -> dict[str, str]:
    """Every summary table a run wrote, by path: the CSVs under ``analysis/``."""
    root = directory / "analysis"
    return {p.relative_to(root).as_posix(): p.read_text(encoding="utf-8")
            for p in sorted(root.rglob("*.csv"))}


def snapshot(root: Path) -> dict[str, str]:
    """Every path under *root*, with each file's SHA-256."""
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        rel = Path(dirpath).relative_to(root)
        out[rel.as_posix() + "/"] = "<dir>"
        for name in sorted(filenames):
            out[(rel / name).as_posix()] = hashlib.sha256(
                (Path(dirpath) / name).read_bytes()).hexdigest()
    return out


# ---------------------------------------------------------------------------
# S4 — encoding
# ---------------------------------------------------------------------------

CP1252_CONFIG = ("experiment_type: standard_lifespan\n"
                 "about:\n"
                 "  purpose: Ménard’s flies — 25 °C\n")


def test_a_windows_1252_config_loads_and_its_member_analyses(tmp_path):
    member = make_member(tmp_path / "m")
    cfgmod.config_path(member).write_bytes(CP1252_CONFIG.encode("cp1252"))
    experiment = SurvivalExperiment(member)
    assert experiment.config_error is None
    assert experiment.raw_config["about"]["purpose"] == "Ménard’s flies — 25 °C"
    outcome = experiment.run_all()
    assert set(outcome["results"]) == {FOCUS}
    assert not outcome["failed"] and not outcome["blocked"]


def test_a_utf8_config_with_a_byte_order_mark_loads(tmp_path):
    member = make_member(tmp_path / "m")
    cfgmod.config_path(member).write_bytes(
        b"\xef\xbb\xbf" + CP1252_CONFIG.encode("utf-8"))
    experiment = SurvivalExperiment(member)
    assert experiment.config_error is None
    assert experiment.raw_config["experiment_type"] == "standard_lifespan"
    assert experiment.raw_config["about"]["purpose"] == "Ménard’s flies — 25 °C"


def test_a_save_writes_utf8(tmp_path):
    member = make_member(tmp_path / "m")
    cfgmod.config_path(member).write_bytes(CP1252_CONFIG.encode("cp1252"))
    SurvivalExperiment(member).set_included("plots", "hazard", False)
    text = cfgmod.config_path(member).read_bytes().decode("utf-8")
    assert "Ménard’s flies — 25 °C" in text
    assert not text.startswith("﻿")


def test_an_unreadable_config_is_an_error_naming_the_file(tmp_path):
    """0x81 starts no UTF-8 character and is not a Windows-1252 one either."""
    member = make_member(tmp_path / "m")
    path = cfgmod.config_path(member)
    path.write_bytes(b"about:\n  purpose: \x81\x8d\n")
    with pytest.raises(ValueError) as caught:
        cfgmod.load_config(member)
    assert str(path) in str(caught.value)
    assert isinstance(caught.value, cfgmod.ConfigEncodingError)
    ## A member: a listed problem naming the file, never an exception that
    ## stops the Project.
    experiment = SurvivalExperiment(member)
    assert str(path) in experiment.config_error
    assert any(str(path) in problem for problem in experiment.validate())


def test_an_unreadable_member_config_does_not_stop_the_project(tmp_path):
    root = tmp_path / "P"
    Project.create(root, name="P")
    make_member(root / "good")
    bad = make_member(root / "bad")
    cfgmod.config_path(bad).write_bytes(b"about:\n  purpose: \x81\x8d\n")
    project = Project(root)
    assert {m.name for m in project.members()} == {"good", "bad"}
    assert any(str(cfgmod.config_path(bad)) in p for p in project.validate())


# ---------------------------------------------------------------------------
# S5 and A8 — warnings, never errors
# ---------------------------------------------------------------------------

def test_an_undescribed_factor_and_level_each_warn_once_and_it_still_runs(tmp_path):
    about = full_about()
    about["factors"]["Genotype"]["levels"]["zz"] = "a level the workbook lacks"
    about["factors"]["Diet"] = {"kind": "diet", "levels": {"DR": "1% SY"}}
    member = make_member(tmp_path / "m", about=about)
    experiment = SurvivalExperiment(member)
    warnings = experiment.warnings()
    assert len([w for w in warnings if "'zz'" in w]) == 1
    assert len([w for w in warnings if "'Diet'" in w]) == 1
    assert [w for w in warnings if "'zz'" in w][0] == (
        "about.factors.Genotype describes level 'zz', which is not a level of "
        "Genotype in the data file")
    assert [w for w in warnings if "'Diet'" in w][0] == (
        "about.factors names 'Diet', which is not a factor of the data file")
    assert len(warnings) == 2
    assert experiment.validate() == []
    outcome = experiment.run_all()
    assert set(outcome["results"]) == {FOCUS} and not outcome["failed"]


ODD = {
    "title": ["not", "text"],
    "purpose": {"a": 1},
    "sex": 3,
    "protocol": 7,
    "factors": {"Genotype": {"kind": "strain", "levels": ["a", "b"]},
                "Treatment": "not a mapping"},
}


@pytest.mark.parametrize("key", sorted(ODD))
def test_each_odd_field_is_a_warning_and_the_config_loads_saves_and_runs(tmp_path, key):
    about = full_about()
    about[key] = ODD[key]
    member = make_member(tmp_path / "m", about=about)
    experiment = SurvivalExperiment(member)
    assert experiment.config_error is None
    assert experiment.validate() == []
    assert any(w.startswith("about.") for w in experiment.warnings())
    experiment.materialize_focuses()                    # a save
    assert about_on_disk(member) == about
    outcome = experiment.run_all()                      # a run
    assert set(outcome["results"]) == {FOCUS} and not outcome["failed"]


def test_a_long_title_and_an_unknown_kind_warn(tmp_path):
    about = full_about()
    about["title"] = "x" * 61
    about["factors"]["Genotype"]["kind"] = "strain"
    member = make_member(tmp_path / "m", about=about)
    warnings = SurvivalExperiment(member).warnings()
    assert any("61 characters" in w for w in warnings)
    assert any("'strain'" in w for w in warnings)


def test_a_section_that_is_not_a_mapping_is_a_warning(tmp_path):
    member = make_member(tmp_path / "m", about="just a sentence")
    experiment = SurvivalExperiment(member)
    assert experiment.validate() == []
    assert experiment.warnings() == [
        "about: must be a mapping of fields, such as title: and purpose:"]


def test_without_a_readable_workbook_the_about_is_checked_on_its_own(tmp_path):
    """No data file: nothing is called undeclared, and the rest is still checked."""
    about = full_about()
    about["factors"]["Diet"] = {"kind": "food", "levels": {"DR": "1% SY"}}
    directory = tmp_path / "m"
    directory.mkdir()
    cfgmod.save_config(directory, {"about": about})
    warnings = cfgmod.config_warnings(cfgmod.load_config(directory), directory)
    assert warnings == ["about.factors.Diet.kind is 'food'; expected one of "
                        "genotype, treatment, diet, condition, sex, other"]


def test_a_config_without_the_key_reads_no_data_file(tmp_path, monkeypatch):
    member = make_member(tmp_path / "m")

    def boom(*_a, **_k):
        raise AssertionError("the data file was read for a config with no about:")

    monkeypatch.setattr(layout, "folder_design", boom)
    assert cfgmod.config_warnings(cfgmod.load_config(member), member) == []


def test_a_check_that_fails_is_one_more_warning(tmp_path, monkeypatch):
    member = make_member(tmp_path / "m", about=full_about())

    def boom(*_a, **_k):
        raise RuntimeError("broken")

    monkeypatch.setattr(about_mod, "about_problems", boom)
    assert SurvivalExperiment(member).warnings() == [
        "about: could not be checked (RuntimeError: broken)"]


def test_an_unfinished_lifespan_is_a_warning(tmp_path):
    import openpyxl

    member = make_member(tmp_path / "m")
    path = member / "data" / "run.xlsx"
    book = openpyxl.load_workbook(path)
    sheet = book.create_sheet("PrivateData")
    sheet.append(["AssumeCensored", "IsCompleted"])
    sheet.append([1, 0])
    book.save(path)
    experiment = SurvivalExperiment(member)
    [warning] = experiment.warnings()
    assert "still running" in warning and "censored at the last census" in warning
    assert experiment.validate() == []
    sheet["B2"] = 1
    book.save(path)
    assert SurvivalExperiment(member).warnings() == []


# ---------------------------------------------------------------------------
# A2 — inert
# ---------------------------------------------------------------------------

def _statuses(directory: Path):
    return SurvivalExperiment(directory).status().focuses


def test_the_about_changes_no_table_and_puts_nothing_out_of_date(tmp_path):
    member = make_member(tmp_path / "m")
    SurvivalExperiment(member).run_all()
    without = tables(member)
    assert without

    cfgmod.write_about(member, full_about())
    for status in _statuses(member):
        assert status.analyzed and not status.out_of_date
    SurvivalExperiment(member).run_all()
    assert tables(member) == without

    edited = full_about()
    edited["title"] = "Another title"
    edited["factors"]["Genotype"]["levels"]["b"]["definition"] = "something else"
    edited["run"] = "R-20261128-test-09"
    cfgmod.write_about(member, edited)
    for status in _statuses(member):
        assert status.analyzed and not status.out_of_date
    SurvivalExperiment(member).run_all()
    assert tables(member) == without


# ---------------------------------------------------------------------------
# A3, A4 and S3 — every writer keeps the About
# ---------------------------------------------------------------------------

def _focus_writers():
    """Each Experiment method that writes ``survival_config.yaml``."""
    def save_focuses(e):
        e.save_focuses(e.focuses() + [Focus("Genotype", {"Genotype": ["a", "b"]})])

    def materialize(e):
        assert e.materialize_focuses()

    def rename(e):
        e.materialize_focuses()
        e.rename_focus(FOCUS, "Everything")

    def apply_edits(e):
        e.materialize_focuses()
        e.apply_focus_edits(e.focuses() + [Focus("Diet", {"Treatment": ["a", "b"]})])

    def delete(e):
        e.save_focuses(e.focuses() + [Focus("Genotype", {"Genotype": ["a", "b"]})])
        e.delete_focus("Genotype")

    def repair(e):
        e.save_focuses([Focus("Stale", {"Genotype": ["a", "gone"]})])
        e.repair_focus("Stale")

    def set_included(e):
        e.set_included("analyses", "parametric_aft", False)

    return {"save_focuses": save_focuses, "materialize_focuses": materialize,
            "rename_focus": rename, "apply_focus_edits": apply_edits,
            "delete_focus": delete, "repair_focus": repair,
            "set_included": set_included}


FOCUS_WRITERS = _focus_writers()


@pytest.mark.parametrize("writer", sorted(FOCUS_WRITERS))
def test_every_experiment_writer_keeps_the_about(tmp_path, writer):
    member = make_member(tmp_path / "m", about=full_about())
    FOCUS_WRITERS[writer](SurvivalExperiment(member))
    assert about_on_disk(member) == full_about()


@pytest.mark.parametrize("writer", sorted(FOCUS_WRITERS))
def test_every_experiment_writer_writes_the_about_now_on_disk(tmp_path, writer):
    """Loaded with one About; a catalogue rewrites it; the writer saves."""
    member = make_member(tmp_path / "m", about=full_about())
    experiment = SurvivalExperiment(member)
    rewritten = full_about()
    rewritten["title"] = "Rewritten by the catalogue"
    rewritten["factors"]["Genotype"]["levels"]["a"] = {
        "definition": "w1118", "term": "GEN-0001", "role": "reference"}
    config = cfgmod.load_config(member)
    config["about"] = rewritten
    cfgmod.write_yaml(cfgmod.config_path(member), config)
    FOCUS_WRITERS[writer](experiment)
    assert about_on_disk(member) == rewritten


def test_save_config_writes_the_about_on_disk_not_the_one_it_was_given(tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    stale = cfgmod.load_config(member)
    rewritten = full_about()
    rewritten["run"] = "R-20261130-test-02"
    cfgmod.write_about(member, rewritten)
    stale["omit"] = {"plots": ["hazard"]}
    cfgmod.save_config(member, stale)
    on_disk = cfgmod.load_config(member)
    assert on_disk["about"] == rewritten and on_disk["omit"] == {"plots": ["hazard"]}
    assert stale["about"] == rewritten               # memory matches disk
    assert list(on_disk)[:2] == ["experiment_type", "about"]


def test_save_config_drops_an_about_the_file_no_longer_has(tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    stale = cfgmod.load_config(member)
    cfgmod.write_about(member, {})
    cfgmod.save_config(member, stale)
    assert "about" not in cfgmod.load_config(member)


def test_save_config_puts_an_about_back_where_the_file_had_it(tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    on_disk = cfgmod.load_config(member)
    fresh = {k: v for k, v in on_disk.items() if k != "about"}
    cfgmod.save_config(member, fresh)
    assert list(cfgmod.load_config(member)) == list(on_disk)


def test_with_no_key_a_save_is_byte_identical(tmp_path):
    """No key, no change: what save_config writes without about: is what a
    plain dump of the same mapping writes."""
    member = make_member(tmp_path / "m", omit={"plots": ["hazard"]})
    before = cfgmod.config_path(member).read_bytes()
    config = cfgmod.load_config(member)
    cfgmod.save_config(member, config)
    after = cfgmod.config_path(member).read_bytes()
    assert after == before
    assert after == yaml.safe_dump(config, sort_keys=False, indent=2,
                                   default_flow_style=False,
                                   allow_unicode=True).encode("utf-8")


def test_saving_the_about_leaves_every_other_key_equal_in_value(tmp_path):
    """S3, from the editor's writer."""
    member = make_member(
        tmp_path / "m",
        focuses=[{"name": "Genotype", "factors": {"Genotype": ["a", "b"]},
                  "reference": {"Genotype": "a"}}],
        exclusions={"group": "qc1"}, omit={"analyses": ["parametric_aft"]},
        global_={"time_unit": "days"})
    config = cfgmod.load_config(member)
    config["global"] = config.pop("global_")
    cfgmod.write_yaml(cfgmod.config_path(member), config)
    before = cfgmod.load_config(member)
    assert {"focuses", "scripts", "exclusions", "omit", "global"} <= set(before)
    cfgmod.write_about(member, full_about())
    after = cfgmod.load_config(member)
    assert after.pop("about") == full_about()
    assert after == before


def test_write_about_creates_a_config_holding_only_the_about(tmp_path):
    folder = tmp_path / "run"
    write_dlife_workbook(folder / "data" / "run.xlsx")
    cfgmod.write_about(folder, full_about())
    assert cfgmod.load_config(folder) == {"about": full_about()}


def test_write_about_writes_nothing_for_a_blank_section_and_no_file(tmp_path):
    folder = tmp_path / "run"
    folder.mkdir()
    assert cfgmod.write_about(folder, {}) is None
    assert list(folder.iterdir()) == []


def test_write_about_never_writes_over_a_file_it_cannot_read(tmp_path):
    member = make_member(tmp_path / "m")
    path = cfgmod.config_path(member)
    path.write_text("about: [unclosed\n", encoding="utf-8")
    with pytest.raises(ValueError):
        cfgmod.write_about(member, full_about())
    assert path.read_text(encoding="utf-8") == "about: [unclosed\n"


# ---------------------------------------------------------------------------
# Project Defaults, scaffolding and the Project's warning
# ---------------------------------------------------------------------------

def test_project_defaults_never_carry_an_about(tmp_path):
    root = tmp_path / "P"
    project = Project.create(root, name="P", defaults={"about": full_about()})
    assert "about" not in project.defaults
    assert cfgmod.merge_defaults({}, {"about": full_about()}) == {}
    own = {"about": {"title": "Mine"}}
    assert cfgmod.merge_defaults(own, {"about": full_about()}) == own
    ## A hand-written one is said to be ignored, never an error.
    project.config["defaults"]["about"] = full_about()
    project.save()
    project = Project(root)
    make_member(root / "m")
    assert project.validate() == []
    assert any("`defaults: about:` is ignored" in w for w in project.warnings())
    assert "about" not in project.member("m").config


def test_a_project_warns_when_two_members_describe_one_level_differently(tmp_path):
    root = tmp_path / "P"
    Project.create(root, name="P")
    first = full_about()
    second = full_about()
    second["factors"]["Treatment"]["levels"]["b"] = "20% SY"
    make_member(root / "m1", about=first)
    make_member(root / "m2", about=second)
    project = Project(root)
    assert project.validate() == []
    [line] = project.about_warnings()
    assert line == ("about: members describe Treatment 'b' differently "
                    "('15% SY': m1; '20% SY': m2)")
    assert line in project.warnings()
    assert "pooled" not in line


def test_members_that_agree_or_say_nothing_draw_no_warning(tmp_path):
    root = tmp_path / "P"
    Project.create(root, name="P")
    make_member(root / "m1", about=full_about())
    make_member(root / "m2", about=full_about())
    make_member(root / "m3")
    assert Project(root).about_warnings() == []


def test_reference_data_file_writes_no_about(tmp_path):
    """The run's own config may describe it fully; the member that reads its
    workbook gets none of that (P15 item 7)."""
    run = tmp_path / "runs" / "R-1"
    write_dlife_workbook(run / "data" / "R-1.xlsx")
    cfgmod.write_about(run, full_about())
    root = tmp_path / "studies" / "P"
    project = Project.create(root, name="P")
    member = project.reference_data_file(run / "data" / "R-1.xlsx")
    assert "about" not in cfgmod.load_config(member.directory)


# ---------------------------------------------------------------------------
# S6 — two analyses of one recording stay apart
# ---------------------------------------------------------------------------

def test_two_projects_referencing_one_workbook_analyse_independently(tmp_path):
    run = tmp_path / "runs" / "R-1"
    workbook = write_dlife_workbook(run / "data" / "R-1.xlsx")
    cfgmod.write_about(run, full_about())                 # the run's own config
    members = {}
    for name, focus in (("A", Focus("Genotype", {"Genotype": ["a", "b"]})),
                        ("B", Focus("Diet", {"Treatment": ["a", "b"]}))):
        project = Project.create(tmp_path / "studies" / name, name=name)
        member = project.reference_data_file(workbook)
        member.save_focuses([focus])
        member.run_all()
        members[name] = member.directory
    run_before = snapshot(run)
    b_before = snapshot(tmp_path / "studies" / "B")

    a = SurvivalExperiment(members["A"])
    a.rename_focus("Genotype", "Genotypes")
    a.run_all()

    assert snapshot(run) == run_before
    assert snapshot(tmp_path / "studies" / "B") == b_before
    assert [f.name for f in SurvivalExperiment(members["A"]).focuses()] == ["Genotypes"]
    assert [f.name for f in SurvivalExperiment(members["B"]).focuses()] == ["Diet"]
    ## The run folder's config is the About alone, and is never analysed.
    assert cfgmod.load_config(run) == {"about": full_about()}
    assert not (run / "analysis").exists() and not (run / "qc").exists()


# ---------------------------------------------------------------------------
# S7 — never on a report, never sent to an AI provider
# ---------------------------------------------------------------------------

MARKERS = ("MARKER-TITLE", "MARKER-PURPOSE", "MARKER-WHO", "MARKER-SERIES",
           "MARKER-NOTES", "MARKER-LEVEL", "MARKER-PROTOCOL", "MARKER-RUN")


def marked_about() -> dict:
    about = full_about()
    about.update(title="MARKER-TITLE", purpose="MARKER-PURPOSE",
                 experimenter="MARKER-WHO", series="MARKER-SERIES",
                 notes="MARKER-NOTES", run="MARKER-RUN",
                 protocol={"name": "MARKER-PROTOCOL"})
    about["factors"]["Genotype"]["levels"]["a"] = "MARKER-LEVEL"
    return about


def test_no_report_and_no_ai_prompt_holds_the_about(tmp_path):
    from pysurvanalysis import project_report
    from pysurvanalysis.ai import narrative
    from pysurvanalysis.ai.base import Provider

    class Recording(Provider):
        def __init__(self):
            super().__init__(name="fake", env_key="FAKE_KEY", models=("fake-1",))
            self.prompts: list[str] = []

        def available(self) -> bool:
            return True

        def complete(self, system, prompt, max_tokens=1600):
            self.prompts.append(system + "\n" + prompt)
            return "A paragraph."

    root = tmp_path / "P"
    Project.create(root, name="P", question="Does diet matter?")
    make_member(root / "m1", about=marked_about())
    second = marked_about()
    second["factors"]["Genotype"]["levels"]["a"] = "MARKER-LEVEL-OTHER"
    make_member(root / "m2", about=second)
    project = Project(root)
    for member in project.members():
        member.run_all()
    provider = Recording()
    paragraphs = narrative.generate(project, provider=provider)
    assert paragraphs and provider.prompts
    project_report.write_project_report(project, formats=("md",),
                                        narrative=paragraphs)

    for prompt in provider.prompts:
        assert not [m for m in MARKERS if m in prompt]
    written = [p for p in root.rglob("*")
               if p.is_file() and p.suffix in {".md", ".json", ".csv", ".txt"}
               and p.name != cfgmod.CONFIG_FILENAME]
    assert any(p.suffix == ".md" for p in written)
    for path in written:
        text = path.read_text(encoding="utf-8", errors="replace")
        assert not [m for m in MARKERS if m in text], path
