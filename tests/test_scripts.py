"""Script registries: core ∪ type, the hard error, the bridges down, and the
Not Applicable rule for steps a Focus Shape does not admit."""

from __future__ import annotations

import pytest

from pysurvanalysis.domain.focus import Focus
from pysurvanalysis.experiment_types import get_type
from pysurvanalysis.script_editor import actions, project_actions

from conftest import FACTORIAL


def test_core_actions_are_available_to_every_type():
    for key in ("standard_lifespan", "interaction", "custom", None):
        registry = actions.registry_for(get_type(key))
        for core in actions.CORE_KEYS:
            assert core in registry


def test_the_factorial_actions_belong_to_every_experiment():
    ## Gated by Focus Shape at run time, not by type: the names are real
    ## everywhere, so a script naming one is valid everywhere.
    registry = actions.registry_for(get_type("standard_lifespan"))
    assert "cox_interaction" in registry
    assert registry["cox_interaction"].requires == "factorial_model"
    assert registry["cox_interaction"].from_type is False


def test_no_type_means_the_general_case():
    assert set(actions.registry_for(None)) == set(
        actions.registry_for(get_type("standard_lifespan")))


def test_unknown_action_is_a_hard_error_naming_step_and_type():
    problems = actions.validate_steps(
        [{"action": "run_analysis"}, {"action": "not_an_action"}],
        get_type("standard_lifespan"))
    assert len(problems) == 1
    assert "Step 2" in problems[0] and "Standard Lifespan" in problems[0]


def test_a_valid_script_validates_clean():
    steps = [{"action": "run_in_focuses"}, {"action": "run_analysis"},
             {"action": "cox_interaction"}]
    assert actions.validate_steps(steps, get_type("standard_lifespan")) == []


def test_a_step_without_an_action_is_flagged():
    assert actions.validate_steps([{}], get_type("standard_lifespan"))


def test_project_registry_cannot_see_experiment_actions():
    assert "run_analysis" not in project_actions.PROJECT_ACTIONS
    assert "run_in_experiments" in project_actions.PROJECT_ACTIONS
    problems = project_actions.validate_project_steps([{"action": "run_analysis"}])
    assert problems and "does not exist" in problems[0]


def test_builtin_project_scripts_are_themselves_valid():
    for name in project_actions.builtin_names():
        assert project_actions.validate_project_steps(
            project_actions.builtin_steps(name)) == []


def test_builtin_experiment_script_is_valid_for_every_type():
    for steps in project_actions.BUILTIN_EXPERIMENT_SCRIPTS.values():
        for key in ("standard_lifespan", "interaction", "custom", None):
            assert actions.validate_steps(steps, get_type(key)) == []


def test_the_batch_script_names_the_default_experiment_script():
    """The two defaults are a pair: a fresh Project's `batch` script must
    name a script every fresh member's file actually carries."""
    default = project_actions.default_experiment_script()
    assert default["name"] == project_actions.DEFAULT_EXPERIMENT_SCRIPT_NAME
    assert default["notes"]
    named = {step["script"] for step in project_actions.default_project_script()["steps"]
             if step["action"] == "run_in_experiments"}
    assert named == {default["name"]}
    for key in ("standard_lifespan", "interaction", "custom", None):
        assert actions.validate_steps(default["steps"], get_type(key)) == []


def test_run_in_experiments_reads_the_members_own_default_script(project):
    """The seeded script is the one that runs — edit it in the file and the
    edit is what run_in_experiments executes, not the in-code built-in."""
    from pysurvanalysis.domain import config as cfgmod

    member = project.members()[0]
    config = cfgmod.load_config(member.directory)
    config["scripts"] = [{"name": project_actions.DEFAULT_EXPERIMENT_SCRIPT_NAME,
                          "steps": [{"action": "not_an_action"}]}]
    cfgmod.save_config(member.directory, config)

    from pysurvanalysis.domain import Project

    reloaded = Project(project.directory)
    with pytest.raises(RuntimeError, match="cannot run as a"):
        project_actions.run_script(
            reloaded, [{"action": "run_in_experiments",
                        "script": project_actions.DEFAULT_EXPERIMENT_SCRIPT_NAME,
                        "only": [member.name]}],
            log=lambda _m: None)


def test_run_in_experiments_refuses_a_script_the_type_cannot_run(project):
    """A hard error, not a skip: a silently skipped step reports as complete."""
    config = dict(project.config)
    config["experiment_scripts"] = [
        {"name": "bad", "steps": [{"action": "not_an_action"}]}]
    from pysurvanalysis.domain import config as cfgmod

    cfgmod.write_yaml(project.config_path, config)

    from pysurvanalysis.domain import Project

    reloaded = Project(project.directory)
    with pytest.raises(RuntimeError, match="cannot run as a"):
        project_actions.run_script(
            reloaded, [{"action": "run_in_experiments", "script": "bad"}],
            log=lambda _m: None)


def test_a_missing_script_name_is_counted_not_raised(project):
    ctx = project_actions.run_script(
        project, [{"action": "run_in_experiments", "script": "nope"}],
        log=lambda _m: None)
    assert sorted(ctx.failures) == ["rep_a", "rep_b"]


def test_only_targets_named_members(project):
    logged: list[str] = []
    ctx = project_actions.run_script(
        project,
        [{"action": "run_in_experiments", "script": "nope", "only": ["rep_a"]}],
        log=logged.append)
    assert ctx.failures == ["rep_a"]
    assert not any("rep_b" in line for line in logged)


def test_an_unknown_member_name_is_logged_and_counted(project):
    ctx = project_actions.run_script(
        project,
        [{"action": "run_in_experiments", "script": "x", "only": ["ghost"]}],
        log=lambda _m: None)
    assert "ghost" in ctx.failures


# ── run_in_focuses and Not Applicable ──────────────────────────────────────

def _two_focus_member(project):
    member = project.member("rep_a")
    member.save_focuses(member.focuses() + [Focus("Geno", {"Genotype": ["wt", "mut"]})])
    return member


def test_run_in_focuses_repeats_the_rest_once_per_focus(project):
    member = _two_focus_member(project)
    logged: list[str] = []
    ctx = project_actions.run_experiment_script(
        member, [{"action": "run_in_focuses"}, {"action": "run_analysis"}],
        log=logged.append)
    assert set(ctx.focus_log) == {FACTORIAL, "Geno"}
    assert member.outputs(FACTORIAL).summary.is_file()
    assert member.outputs("Geno").summary.is_file()


def test_only_limits_run_in_focuses(project):
    member = _two_focus_member(project)
    ctx = project_actions.run_experiment_script(
        member, [{"action": "run_in_focuses", "only": ["Geno"]},
                 {"action": "run_analysis"}], log=lambda _m: None)
    assert set(ctx.focus_log) == {"Geno"}
    assert not member.outputs(FACTORIAL).summary.exists()


def test_a_step_the_shape_cannot_take_is_not_applicable_not_fatal(project):
    import json

    member = _two_focus_member(project)
    logged: list[str] = []
    ctx = project_actions.run_experiment_script(
        member,
        [{"action": "run_in_focuses"}, {"action": "run_analysis"},
         {"action": "cox_interaction"}, {"action": "log_rank_omnibus"}],
        log=logged.append)
    ## The 2×2 Focus fitted the model; the one-factor Focus recorded why it
    ## could not, and still ran the step after it.
    assert ctx.focus_log[FACTORIAL]["not_applicable"] == []
    ## Explicitly asked for, so said — even though the battery is not offered
    ## to a one-factor Focus by default.
    [(action, reason)] = ctx.focus_log["Geno"]["not_applicable"]
    assert action == "Cox factorial model" and "varies only Genotype" in reason
    assert sum("Omnibus log-rank" in line for line in logged) == 2
    payload = json.loads(member.outputs("Geno").summary.read_text())
    assert {"action": action, "reason": reason} in payload["not_applicable"]


def test_unattended_with_no_bridge_runs_every_focus(project):
    ## The pre-Focus default script — just run_analysis — must not analyse
    ## one Focus and stay quiet about the rest when run from a Batch.
    member = _two_focus_member(project)
    ctx = project_actions.run_experiment_script(
        member, [{"action": "run_analysis"}], log=lambda _m: None)
    assert set(ctx.focus_log) == {FACTORIAL, "Geno"}


def test_with_an_active_focus_and_no_bridge_only_that_focus_runs(project):
    member = _two_focus_member(project)
    ctx = project_actions.run_experiment_script(
        member, [{"action": "run_analysis"}], log=lambda _m: None,
        focus=member.focus("Geno"))
    assert set(ctx.focus_log) == {"Geno"}
    assert not member.outputs(FACTORIAL).summary.exists()


def test_a_blocked_focus_is_skipped_and_the_member_does_not_fail(project):
    member = project.member("rep_a")
    member.save_focuses(member.focuses() + [Focus("Stale", {"Genotype": ["wildtype"]})])
    logged: list[str] = []
    ctx = project_actions.run_experiment_script(
        member, [{"action": "run_in_focuses"}, {"action": "run_analysis"}],
        log=logged.append)
    assert ctx.focus_log["Stale"]["blocked"]
    assert member.outputs(FACTORIAL).summary.is_file()
    assert any("BLOCKED" in line for line in logged)


def test_steps_before_the_bridge_run_once(project):
    member = _two_focus_member(project)
    logged: list[str] = []
    project_actions.run_experiment_script(
        member, [{"action": "load_data"}, {"action": "run_in_focuses"},
                 {"action": "log_rank_omnibus"}], log=logged.append)
    assert sum("Load data" in line for line in logged) == 1
    assert sum("Omnibus log-rank" in line for line in logged) == 2


def test_run_in_focuses_cannot_run_as_a_plain_step():
    with pytest.raises(RuntimeError, match="inside an Experiment Script"):
        actions.POOL["run_in_focuses"].execute({}, actions.RunContext())
