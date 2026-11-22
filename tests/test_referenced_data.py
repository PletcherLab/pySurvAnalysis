"""A Member Experiment reads a data file outside the Project (ADR-0013).

The P03 brief's acceptance tests: P00's shared S1–S8 plus pySurvAnalysis's
V1–V5. The layout is labdata's — locked runs under ``runs/``, a study's
analysis under ``studies/`` — built under a prefix with spaces, an
apostrophe, an ampersand and non-ASCII characters on purpose. Nothing here
knows about labdata's own files: the feature is general, a member's data
file can live elsewhere.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from pysurvanalysis.domain import Project, SurvivalExperiment, config as cfgmod, layout
from pysurvanalysis.domain.experiment import ExperimentError
from pysurvanalysis.domain.project import ProjectError
from tests.conftest import write_dlife_workbook

PREFIX = Path("Experiments & Data") / "MBa'b'ap Ünï" / "managed"
RUN_1 = "R-20261020-test-01"
RUN_2 = "R-20261021-test-02"
ANALYSIS = "A-20261105-test-01"
ANALYSIS_2 = "A-20261106-test-02"
FOCUS = "Unfiltered"

IS_ROOT = hasattr(os, "geteuid") and os.geteuid() == 0


# ---------------------------------------------------------------------------
# The layout
# ---------------------------------------------------------------------------

def run_dir(managed: Path, run: str) -> Path:
    return managed / "runs" / "lifespan" / "2026" / run


def workbook(managed: Path, run: str) -> Path:
    return run_dir(managed, run) / "data" / f"{run}.xlsx"


def key_for(run: str) -> str:
    """``data_file:`` as labdata writes it: relative, forward slashes, ending
    at the workbook inside the run's ``data/``."""
    return f"../../../../../runs/lifespan/2026/{run}/data/{run}.xlsx"


def analysis_dir(managed: Path, name: str = ANALYSIS) -> Path:
    return managed / "studies" / "test-study" / "analyses" / name


def write_member(project_dir: Path, name: str, data_file, **extra) -> Path:
    """A member folder as labdata writes one: a config naming its data file,
    and nothing else."""
    member = project_dir / name
    member.mkdir(parents=True)
    config = {"experiment_type": "standard_lifespan"}
    if data_file is not None:
        config["data_file"] = data_file
    config.update(extra)
    cfgmod.save_config(member, config)
    return member


def _add_chamber_flags(path: Path, excluded: list[int]) -> None:
    import openpyxl

    book = openpyxl.load_workbook(path)
    sheet = book.create_sheet("ChamberFlags")
    sheet.append(["Chamber", "Excluded"])
    for chamber in range(1, 9):
        sheet.append([chamber, 1 if chamber in excluded else 0])
    book.save(path)


def build_managed(tmp: Path) -> Path:
    """Two locked-to-be runs and one analysis whose two members reference
    them. Run 1's workbook flags chamber 8 in its ChamberFlags sheet."""
    managed = tmp / PREFIX
    write_dlife_workbook(workbook(managed, RUN_1), chambers=8)
    _add_chamber_flags(workbook(managed, RUN_1), excluded=[8])
    write_dlife_workbook(workbook(managed, RUN_2), chambers=4, censuses=5,
                         sample_size=15, factors=("Genotype", "Diet"))
    analysis = analysis_dir(managed)
    Project.create(analysis, name="Test study")
    for run in (RUN_1, RUN_2):
        write_member(analysis, run, key_for(run))
    return managed


@pytest.fixture
def managed(tmp_path) -> Path:
    return build_managed(tmp_path)


def snapshot(root: Path) -> dict[str, str]:
    """Every path under *root*, relative, with each file's SHA-256."""
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        rel = Path(dirpath).relative_to(root)
        out[rel.as_posix() + "/"] = "<dir>"
        for name in sorted(filenames):
            data = (Path(dirpath) / name).read_bytes()
            out[(rel / name).as_posix()] = hashlib.sha256(data).hexdigest()
    return out


def lock(root: Path) -> None:
    """Files 0o444, folders 0o555 — what labdata does to a run a week after
    registration."""
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            os.chmod(Path(dirpath) / name, 0o444)
    for dirpath, _dirnames, _filenames in os.walk(root, topdown=False):
        os.chmod(dirpath, 0o555)


def unlock(root: Path) -> None:
    for dirpath, _dirnames, filenames in os.walk(root):
        os.chmod(dirpath, 0o755)
        for name in filenames:
            os.chmod(Path(dirpath) / name, 0o644)


# ---------------------------------------------------------------------------
# S2, S3, S4, V3: one full run, with the runs locked
# ---------------------------------------------------------------------------

def _without_paths(summary: dict) -> dict:
    """A run summary minus what is a path, a name or a time."""
    return {k: v for k, v in summary.items()
            if k not in {"analyzed_at", "input_file", "data_location"}}


@pytest.fixture(scope="module")
def ran(tmp_path_factory):
    """The full pipeline through the key, run once for the module.

    A Batch Run over the whole managed tree executes each Project's ``batch``
    script — every Focus of every member, their reports, the curated
    Publication Figures and the Project Report. Before it, ``runs/`` is
    hashed and made read-only, and classification, Batch discovery and the
    preflight's Blocked-Focus check walk it too. An ordinary member holding
    a copy of run 1 is analysed beside it for S4.
    """
    from pysurvanalysis import pubfigures as pf
    from pysurvanalysis.domain import Batch, discover, upgrade

    tmp = tmp_path_factory.mktemp("full")
    managed = build_managed(tmp)
    analysis = analysis_dir(managed)
    pf.save_specs(analysis, {"km_curves": pf.default_spec("km_curves")})

    plain = tmp / "plain copy"
    (plain / "data").mkdir(parents=True)
    shutil.copy2(workbook(managed, RUN_1), plain / "data" / f"{RUN_1}.xlsx")
    cfgmod.save_config(plain, {"experiment_type": "standard_lifespan"})

    runs = managed / "runs"
    before_runs = snapshot(runs)
    before_tree = snapshot(managed)
    if not IS_ROOT:
        lock(runs)
    logs: list[str] = []
    try:
        classified = layout.members_in(analysis)
        found = discover(managed)
        blocked_focuses = [bp.blocked_focuses() for bp in found["projects"]]
        for member in analysis.iterdir():
            if member.is_dir():
                upgrade.apply(upgrade.plan(member))
        result = Batch(managed).run(log=logs.append)
        plain_outcome = SurvivalExperiment(plain).run_all()
        after_runs = snapshot(runs)
    finally:
        if not IS_ROOT:
            unlock(runs)
    yield SimpleNamespace(
        managed=managed, analysis=analysis, plain=plain, logs=logs,
        classified=classified, found=found, blocked_focuses=blocked_focuses,
        result=result, plain_outcome=plain_outcome,
        before_runs=before_runs, after_runs=after_runs,
        before_tree=before_tree, after_tree=snapshot(managed))


def test_s2_the_full_pipeline_runs_through_the_key(ran):
    assert [o.ok for o in ran.result.outcomes] == [True], ran.logs
    [outcome] = ran.result.outcomes
    assert (outcome.usable, outcome.total) == (2, 2)
    assert not any("FAILED" in line for line in ran.logs), ran.logs
    for run in (RUN_1, RUN_2):
        root = ran.analysis / run / "analysis" / FOCUS
        assert (root / f"run_summary_{FOCUS}.json").is_file()
        assert (root / f"report_{FOCUS}.md").is_file()
        assert (root / f"{run}_report_{FOCUS}.pdf").is_file()
    assert (ran.analysis / f"{ANALYSIS}_report.pdf").is_file()
    assert (ran.analysis / f"{ANALYSIS}_report.md").is_file()


def test_s2_every_output_is_under_a_member_or_the_project(ran):
    prefix = ran.analysis.relative_to(ran.managed).as_posix() + "/"
    changed = {path for path, digest in ran.after_tree.items()
               if ran.before_tree.get(path) != digest}
    assert changed, "the run wrote nothing"
    assert all(path.startswith(prefix) for path in changed), sorted(
        p for p in changed if not p.startswith(prefix))
    ## Direct mode's <stem>_results/ is never reached from a member.
    assert not [p for p in ran.after_tree if "_results/" in p]


def test_s3_the_runs_are_byte_for_byte_untouched(ran):
    if IS_ROOT:
        pytest.skip("running as root: read-only permissions do not bind, "
                    "so only the listing and hash comparison below applies")
    assert ran.after_runs == ran.before_runs


def test_s3_listing_and_hashes_are_identical_even_as_root(ran):
    assert ran.after_runs == ran.before_runs


def test_s3_classification_discovery_and_preflight_see_both_members(ran):
    assert [(m.name, m.status) for m in ran.classified] == [
        (RUN_1, layout.OK), (RUN_2, layout.OK)]
    [project] = ran.found["projects"]
    assert project.key == f"studies/test-study/analyses/{ANALYSIS}"
    assert [m.name for m in project.usable] == [RUN_1, RUN_2]
    assert ran.blocked_focuses == [[]]


def test_s4_a_reference_gives_the_same_numbers_as_a_copy(ran):
    referenced = ran.analysis / RUN_1 / "analysis" / FOCUS
    copied = ran.plain / "analysis" / FOCUS
    name = f"run_summary_{FOCUS}.json"
    ours = json.loads((referenced / name).read_text(encoding="utf-8"))
    theirs = json.loads((copied / name).read_text(encoding="utf-8"))
    assert _without_paths(ours) == _without_paths(theirs)
    tables = sorted(p.name for p in (copied / "data_output").glob("*.csv"))
    assert any("lifetables" in t for t in tables), tables
    for table in tables:
        assert (referenced / "data_output" / table).read_bytes() == \
            (copied / "data_output" / table).read_bytes(), table


def test_v3_focus_output_lands_in_the_member_folder(ran):
    member = ran.analysis / RUN_1
    assert (member / "analysis" / FOCUS / "plots").is_dir()
    assert [p.name for p in (member / "figures" / FOCUS).iterdir()] == [
        f"km_curves_{FOCUS}.svg"]
    assert not (run_dir(ran.managed, RUN_1) / "analysis").exists()


def test_s8_provenance_records_the_key_as_written_and_resolved(ran):
    summary = json.loads((ran.analysis / RUN_1 / "analysis" / FOCUS /
                          f"run_summary_{FOCUS}.json").read_text(encoding="utf-8"))
    resolved = os.path.realpath(workbook(ran.managed, RUN_1))
    assert summary["data_location"] == {"written": key_for(RUN_1),
                                        "resolved": resolved}
    report = (ran.analysis / f"{ANALYSIS}_report.md").read_text(encoding="utf-8")
    assert key_for(RUN_1) in report and resolved in report
    member_report = (ran.analysis / RUN_1 / "analysis" / FOCUS /
                     f"report_{FOCUS}.md").read_text(encoding="utf-8")
    assert key_for(RUN_1) in member_report and resolved in member_report
    assert any(resolved in line for line in ran.logs)


def test_no_key_no_provenance_lines(ran):
    """Contract item 3: an ordinary member's run summary is what it was."""
    summary = json.loads((ran.plain / "analysis" / FOCUS /
                          f"run_summary_{FOCUS}.json").read_text(encoding="utf-8"))
    assert "data_location" not in summary


# ---------------------------------------------------------------------------
# V4: exclusions read from the referenced workbook, written in the member
# ---------------------------------------------------------------------------

def test_v4_chamber_flags_come_from_the_referenced_workbook(ran):
    summary = json.loads((ran.analysis / RUN_1 / "analysis" / FOCUS /
                          f"run_summary_{FOCUS}.json").read_text(encoding="utf-8"))
    assert summary["excluded_chambers"] == ["8"]


def test_v4_an_exclusion_group_is_written_in_the_member_folder(managed):
    from pysurvanalysis import exclusions

    runs_before = snapshot(managed / "runs")
    member = SurvivalExperiment(analysis_dir(managed) / RUN_1)
    assert 8 in {int(c) for c in member.all_excluded_chambers()}
    written = exclusions.write_exclusions(member.directory, "qc", [1])
    assert Path(written) == member.directory / "qc" / "remove_chambers.csv"
    assert snapshot(managed / "runs") == runs_before


# ---------------------------------------------------------------------------
# S5: one recording, one member
# ---------------------------------------------------------------------------

def test_s5_a_second_member_reading_the_same_file_is_a_duplicate(managed):
    from pysurvanalysis import project_report

    analysis = analysis_dir(managed)
    write_member(analysis, "R-dup", key_for(RUN_1))

    project = Project(analysis)
    assert [d.name for d in project.member_dirs()] == [RUN_1, RUN_2]
    assert [m.name for m in project.members()] == [RUN_1, RUN_2]
    assert project.duplicates() == {"R-dup": RUN_1}
    assert any("R-dup" in w and "duplicate" in w for w in project.warnings())

    items = {m.name: m for m in layout.members_in(analysis)}
    assert items["R-dup"].status == layout.DUPLICATE
    assert items["R-dup"].blocked and items["R-dup"].fix is None
    assert RUN_1 in items["R-dup"].detail
    assert items[RUN_1].usable

    rows = project_report._focus_rows(project)
    assert [member.name for member, _fs, _f in rows] == [RUN_1, RUN_2]
    text = project_report.build_project_report(project)
    rendered = json.dumps([str(b) for b in text.blocks])
    assert "R-dup" in rendered and "duplicate" in rendered


def test_s5_two_plain_members_sharing_data_by_symlink_are_both_kept(tmp_path):
    """The lenient rule: no key, no change — even where the tidier rule
    would call them one recording."""
    root = tmp_path / "proj"
    Project.create(root, name="Plain")
    write_dlife_workbook(root / "a" / "data" / "a.xlsx")
    cfgmod.save_config(root / "a", {"experiment_type": "standard_lifespan"})
    (root / "b").mkdir()
    try:
        os.symlink(root / "a" / "data", root / "b" / "data")
    except OSError:
        pytest.skip("symlinks are not available here")
    cfgmod.save_config(root / "b", {"experiment_type": "standard_lifespan"})
    project = Project(root)
    assert [d.name for d in project.member_dirs()] == ["a", "b"]
    assert project.duplicates() == {}
    assert [m.status for m in layout.members_in(root)] == [layout.OK, layout.OK]


# ---------------------------------------------------------------------------
# S6: conflicts are errors, not guesses
# ---------------------------------------------------------------------------

def _resolved(member: Path, value: str) -> str:
    return os.path.realpath(os.path.join(os.path.abspath(member), value))


def test_s6_a_missing_target_blocks_and_the_loader_names_it(managed):
    analysis = analysis_dir(managed)
    value = "../../../../../runs/lifespan/2026/R-nowhere/data/R-nowhere.xlsx"
    member = write_member(analysis, "R-missing", value)
    resolved = _resolved(member, value)

    item = layout.classify(member)
    assert item.status == layout.NO_DATA and resolved in item.detail
    with pytest.raises(layout.DataLocationError) as err:
        SurvivalExperiment(member).data_file()
    message = str(err.value)
    assert "data_file" in message and value in message and resolved in message
    assert isinstance(err.value, ExperimentError)


def test_s6_a_folder_where_a_file_belongs_blocks(managed):
    analysis = analysis_dir(managed)
    value = f"../../../../../runs/lifespan/2026/{RUN_1}/data"
    member = write_member(analysis, "R-folder", value)
    resolved = _resolved(member, value)

    item = layout.classify(member)
    assert item.status == layout.NO_DATA
    assert resolved in item.detail and "folder" in item.detail
    with pytest.raises(layout.DataLocationError) as err:
        SurvivalExperiment(member).data_file()
    assert value in str(err.value) and resolved in str(err.value)


@pytest.mark.parametrize("local", ["data/cohort.xlsx", "cohort.csv"])
def test_s6_the_key_beside_a_recording_of_its_own_is_a_conflict(managed, local):
    analysis = analysis_dir(managed)
    member = analysis / RUN_1
    target = member / local
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(workbook(managed, RUN_1), target)
    resolved = os.path.realpath(workbook(managed, RUN_1))

    item = layout.classify(member)
    assert item.status == layout.CONFLICT and item.blocked and item.fix is None
    assert resolved in item.detail and target.name in item.detail
    with pytest.raises(layout.DataLocationError) as err:
        SurvivalExperiment(member).data_file()
    message = str(err.value)
    assert "data_file" in message and resolved in message and target.name in message
    ## Blocked, but still the Project's member — it is reported, not hidden.
    assert RUN_1 in [d.name for d in Project(analysis).member_dirs()]


def test_s6_an_empty_local_data_folder_is_not_a_conflict(managed):
    member = analysis_dir(managed) / RUN_1
    (member / "data").mkdir()
    assert layout.classify(member).status == layout.OK
    assert SurvivalExperiment(member).data_file() == Path(
        os.path.realpath(workbook(managed, RUN_1)))


@pytest.mark.parametrize("name", ["notes.txt", "._R.xlsx", "~$R.xlsx",
                                  "remove_chambers.csv"])
def test_s6_a_file_the_loader_would_not_read_is_not_a_conflict(managed, name):
    member = analysis_dir(managed) / RUN_1
    (member / name).write_text("not a recording", encoding="utf-8")
    assert layout.classify(member).status == layout.OK
    experiment = SurvivalExperiment(member)
    assert experiment.design().factors          # it loads


def test_s6_a_data_file_inside_the_member_keeps_todays_behaviour(managed):
    """``Set data file…`` names one of several files in the member's own
    folder; the others beside it are not a conflict (S1 depends on this)."""
    member = analysis_dir(managed) / "R-local"
    write_dlife_workbook(member / "data" / "one.xlsx")
    write_dlife_workbook(member / "data" / "two.xlsx")
    cfgmod.save_config(member, {"experiment_type": "standard_lifespan",
                                "data_file": "data/one.xlsx"})
    assert layout.classify(member).status == layout.OK
    assert SurvivalExperiment(member).data_file() == member / "data" / "one.xlsx"


def test_s6_a_refused_load_writes_nothing(managed):
    """The reference is resolved before ``analysis/`` or ``qc/`` is made."""
    member = write_member(
        analysis_dir(managed), "R-missing", "../nowhere/R.xlsx",
        focuses={"All": {"factors": {"Genotype": ["a", "b"]}}})
    before = snapshot(member)
    experiment = SurvivalExperiment(member)
    with pytest.raises(layout.DataLocationError):
        experiment.run_analysis("All")
    outcome = experiment.run_all()
    assert "does not exist" in outcome["failed"]["All"]
    assert snapshot(member) == before


# ---------------------------------------------------------------------------
# S7: two Projects, one recording
# ---------------------------------------------------------------------------

def test_s7_two_projects_reading_one_run_do_not_touch_each_other(managed):
    first = analysis_dir(managed)
    for run in (RUN_1, RUN_2):
        SurvivalExperiment(first / run).run_all()
    before = snapshot(first)

    second = analysis_dir(managed, ANALYSIS_2)
    Project.create(second, name="Second study")
    write_member(second, RUN_1, key_for(RUN_1),
                 **{"global": {"assume_censored": False}})
    outcome = SurvivalExperiment(second / RUN_1).run_all()
    assert not outcome["failed"]

    assert snapshot(first) == before
    ours = json.loads((first / RUN_1 / "analysis" / FOCUS /
                       f"run_summary_{FOCUS}.json").read_text(encoding="utf-8"))
    theirs = json.loads((second / RUN_1 / "analysis" / FOCUS /
                         f"run_summary_{FOCUS}.json").read_text(encoding="utf-8"))
    assert ours["data_sha256"] == theirs["data_sha256"]
    assert ours["assume_censored"] and not theirs["assume_censored"]


# ---------------------------------------------------------------------------
# S8: the linter
# ---------------------------------------------------------------------------

def test_s8_a_relative_key_is_accepted_silently(managed):
    member = SurvivalExperiment(analysis_dir(managed) / RUN_1)
    assert member.validate() == []
    assert member.warnings() == []
    assert cfgmod.config_warnings({"data_file": key_for(RUN_1)}) == []


def test_s8_an_absolute_key_warns_but_still_loads(managed):
    absolute = os.path.realpath(workbook(managed, RUN_1))
    member = write_member(analysis_dir(managed), "R-abs", absolute)
    experiment = SurvivalExperiment(member)
    assert experiment.validate() == []                 # never fatal
    ## (On Windows the same path also has backslashes: a second warning.)
    [warning] = [w for w in experiment.warnings() if "absolute" in w]
    assert absolute in warning
    assert experiment.data_file() == Path(absolute)
    assert any("R-abs" in w and "absolute" in w
               for w in Project(analysis_dir(managed)).warnings())


def test_s8_a_backslash_warns():
    [warning] = cfgmod.config_warnings({"data_file": r"..\runs\R.xlsx"})
    assert "forward slashes" in warning


def test_s8_no_key_no_warning():
    assert cfgmod.config_warnings({"experiment_type": "standard_lifespan"}) == []


def test_the_key_is_never_inherited_from_project_defaults(tmp_path):
    """It names *that* member's file; an inherited one would make every
    member read the same file — and the classifier never honoured it."""
    root = tmp_path / "proj"
    Project.create(root, name="Defaults")
    project = Project(root)
    project.config["defaults"]["data_file"] = "data/shared.xlsx"
    project.save()
    write_dlife_workbook(root / "m" / "data" / "own.xlsx")
    cfgmod.save_config(root / "m", {"experiment_type": "standard_lifespan"})

    project = Project(root)
    member = project.member("m")
    assert "data_file" not in member.config
    assert member.data_file().name == "own.xlsx"
    assert any("defaults: data_file:" in p for p in project.validate())


# ---------------------------------------------------------------------------
# V1, V2: Project.reference_data_file
# ---------------------------------------------------------------------------

def test_v1_reference_data_file_writes_a_relative_key_and_copies_nothing(managed):
    analysis = analysis_dir(managed)
    shutil.rmtree(analysis / RUN_1)
    source = workbook(managed, RUN_1)
    source_bytes = source.read_bytes()
    before = snapshot(managed)

    member = Project(analysis).reference_data_file(source)

    assert member.name == RUN_1 and member.directory == (analysis / RUN_1).resolve()
    config = cfgmod.load_config(member.directory)
    assert config["data_file"] == key_for(RUN_1)
    assert "\\" not in config["data_file"]
    after = snapshot(managed)
    added = set(after) - set(before)
    prefix = (analysis / RUN_1).relative_to(managed).as_posix()
    assert added == {prefix + "/", prefix + "/" + cfgmod.CONFIG_FILENAME}
    assert {k: v for k, v in after.items() if k in before} == before
    assert source.read_bytes() == source_bytes
    assert member.data_file() == Path(os.path.realpath(source))
    assert layout.classify(member.directory).status == layout.OK


def test_v1_a_name_can_be_given(managed):
    analysis = analysis_dir(managed)
    shutil.rmtree(analysis / RUN_1)
    member = Project(analysis).reference_data_file(workbook(managed, RUN_1),
                                                   name="Run one again")
    assert member.directory.name == "Run one again"
    assert cfgmod.load_config(member.directory)["data_file"] == key_for(RUN_1)


def _refused(managed, call, match):
    before = snapshot(managed)
    with pytest.raises(ProjectError, match=match):
        call()
    assert snapshot(managed) == before


def test_v2_refuses_a_file_inside_the_project(managed):
    analysis = analysis_dir(managed)
    loose = analysis / "loose.xlsx"
    write_dlife_workbook(loose)
    _refused(managed, lambda: Project(analysis).reference_data_file(loose),
             "Add experiment")


def test_v2_refuses_a_file_that_fails_validation(managed):
    bad = managed / "runs" / "lifespan" / "2026" / "R-bad" / "data" / "bad.xlsx"
    write_dlife_workbook(bad, drop_column="StartTime")
    _refused(managed,
             lambda: Project(analysis_dir(managed)).reference_data_file(bad),
             "bad.xlsx")


def test_v2_refuses_a_path_with_no_relative_form(managed, monkeypatch):
    """A different drive on Windows, where ``os.path.relpath`` raises."""
    project = Project(analysis_dir(managed))
    source = workbook(managed, RUN_2)
    shutil.rmtree(analysis_dir(managed) / RUN_2)

    def no_relative_path(*_args, **_kwargs):
        raise ValueError("path is on mount 'D:', start on mount 'C:'")

    def call():
        with monkeypatch.context() as patch:
            patch.setattr(os.path, "relpath", no_relative_path)
            project.reference_data_file(source)

    _refused(managed, call, "relative")


def test_v2_refuses_an_existing_destination(managed):
    project = Project(analysis_dir(managed))
    _refused(managed, lambda: project.reference_data_file(workbook(managed, RUN_1)),
             "already exists")


def test_v2_refuses_a_file_another_member_already_reads(managed):
    project = Project(analysis_dir(managed))
    _refused(managed, lambda: project.reference_data_file(
        workbook(managed, RUN_1), name="again"), RUN_1)


# ---------------------------------------------------------------------------
# Writes near the data file: upgrade and direct mode
# ---------------------------------------------------------------------------

def test_upgrade_on_a_referencing_member_writes_nothing(managed):
    from pysurvanalysis.domain import upgrade

    member = analysis_dir(managed) / RUN_1
    before = snapshot(managed)
    assert not upgrade.needs_upgrade(member)
    plan = upgrade.apply(upgrade.plan(member))
    assert plan.is_noop
    assert snapshot(managed) == before


def test_no_member_code_path_reaches_direct_mode(managed, monkeypatch):
    """Direct mode writes ``<stem>_results/`` beside its input file; a
    member's run must never take that branch."""
    from pysurvanalysis import pipeline
    from pysurvanalysis.script_editor import project_actions

    real = pipeline.run_analysis
    seen: list = []

    def spy(*args, **kwargs):
        seen.append(kwargs.get("experiment"))
        return real(*args, **kwargs)

    monkeypatch.setattr(pipeline, "run_analysis", spy)
    project = Project(analysis_dir(managed))
    steps = next(s for s in project.scripts() if s["name"] == "batch")["steps"]
    ctx = project_actions.run_script(project, steps)
    assert not ctx.failures
    assert seen and all(e is not None for e in seen)
    assert not list(managed.rglob("*_results"))


# ---------------------------------------------------------------------------
# V5: the decision is recorded
# ---------------------------------------------------------------------------

ADR_DIR = Path(__file__).resolve().parents[1] / "docs" / "adr"


def test_v5_adr_0013_exists_and_amends_adr_0008():
    [adr] = list(ADR_DIR.glob("0013-*.md"))
    text = adr.read_text(encoding="utf-8")
    assert "data_file" in text and "ADR-0008" in text
    amended = (ADR_DIR / "0008-three-ways-a-member-arrives.md").read_text(
        encoding="utf-8")
    assert "Amended by [ADR-0013]" in amended
    assert adr.name in amended


# ---------------------------------------------------------------------------
# The Hub: a thin button, and the duplicate reported
# ---------------------------------------------------------------------------

@pytest.fixture
def ref_hub(managed, qapp):
    from pysurvanalysis.apps.hub import HubWindow
    from pysurvanalysis.ui import apply_theme

    apply_theme(qapp, "light")
    window = HubWindow(str(analysis_dir(managed)))
    window._warned = []
    window._warn = lambda message: window._warned.append(message)
    yield window
    window.close()


def test_hub_reference_button_calls_the_domain_method(ref_hub, managed,
                                                      monkeypatch):
    import PyQt6.QtWidgets as qtw

    analysis = analysis_dir(managed)
    shutil.rmtree(analysis / RUN_2)
    ref_hub._refresh_all()
    source = workbook(managed, RUN_2)
    monkeypatch.setattr(qtw.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(source), "")))
    ref_hub._action_reference_data_file()
    assert ref_hub._warned == []
    assert cfgmod.load_config(analysis / RUN_2)["data_file"] == key_for(RUN_2)
    assert RUN_2 in [m.name for m in ref_hub._project.members()]


def test_hub_reference_button_says_why_it_refuses(ref_hub, managed, monkeypatch):
    import PyQt6.QtWidgets as qtw

    loose = analysis_dir(managed) / "loose.xlsx"
    write_dlife_workbook(loose)
    monkeypatch.setattr(qtw.QFileDialog, "getOpenFileName",
                        staticmethod(lambda *a, **k: (str(loose), "")))
    ref_hub._action_reference_data_file()
    assert "Add experiment" in ref_hub._warned[-1]
    assert not (analysis_dir(managed) / "loose").exists()


def test_hub_lists_a_duplicate_as_a_blocked_row(managed, qapp):
    write_member(analysis_dir(managed), "R-dup", key_for(RUN_1))
    from pysurvanalysis.apps.hub import HubWindow

    window = HubWindow(str(analysis_dir(managed)))
    try:
        table = window._members_table
        rows = {table.item(r, 0).text(): table.item(r, 4).text()
                for r in range(table.rowCount())}
        assert rows["R-dup"] == "blocked: duplicate"
        assert rows[RUN_1] != "blocked: duplicate"
    finally:
        window.close()
