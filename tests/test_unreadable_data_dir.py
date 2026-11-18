"""An unreadable ``data/`` is refused, never searched past.

The loader searches ``data/`` and then the directory root. When ``data/``
exists but cannot be listed, what it holds is unknown — and an old copy at
the root is exactly the file a fall-through would read in its place. So the
classifier calls the member blocked (``unreadable``, naming the folder) and
the loader raises naming it: the two agree on refusing, which is the point.
An empty, readable ``data/`` still falls through to the root as it always
has.
"""

from __future__ import annotations

import os
import shutil

import pytest

from pysurvanalysis.domain import Project, SurvivalExperiment, config as cfgmod, layout
from pysurvanalysis.domain.experiment import ExperimentError
from tests.conftest import write_cohort

pytestmark = pytest.mark.skipif(
    os.name != "posix" or (hasattr(os, "geteuid") and os.geteuid() == 0),
    reason="needs POSIX permissions that bind (not root)")

CONFIG = {"experiment_type": "standard_lifespan",
          "input": {"format": "long"},
          "focuses": {"All": {"factors": {"Genotype": ["wt", "mut"]}}}}


@pytest.fixture
def locked(tmp_path):
    """A member whose ``data/`` holds the current file but cannot be listed,
    and whose root holds an old copy the fall-through would have read."""
    root = tmp_path / "proj"
    Project.create(root, name="Locked")
    member = root / "rep"
    write_cohort(member / "data" / "cohort.csv")
    write_cohort(member / "cohort_old.csv", seed=9)
    cfgmod.save_config(member, dict(CONFIG))
    data = member / "data"
    os.chmod(data, 0o000)
    yield member
    os.chmod(data, 0o755)


def test_the_classifier_blocks_it_naming_the_folder(locked):
    item = layout.classify(locked)
    assert item.status == layout.UNREADABLE and item.blocked
    assert str(locked / "data") in item.detail
    assert "cohort_old.csv" not in item.candidates
    [listed] = [m for m in layout.members_in(locked.parent) if m.name == "rep"]
    assert listed.status == layout.UNREADABLE


def test_the_loader_refuses_naming_the_folder(locked):
    experiment = SurvivalExperiment(locked)
    with pytest.raises(ExperimentError) as err:
        experiment.data_file()
    assert str(locked / "data") in str(err.value)
    assert not experiment.has_data()
    [problem] = experiment.validate()
    assert str(locked / "data") in problem


def test_a_refused_run_writes_nothing(locked):
    experiment = SurvivalExperiment(locked)
    with pytest.raises(ExperimentError):
        experiment.run_analysis("All")
    assert not (locked / "analysis").exists() and not (locked / "qc").exists()


def test_a_folder_with_no_config_is_blocked_too(locked):
    """Unknown is not absent here either: the old copy at the root must not
    make it look like a folder holding one data file."""
    os.remove(cfgmod.config_path(locked))
    item = layout.classify(locked)
    assert item.status == layout.UNREADABLE and not item.configured
    assert str(locked / "data") in item.detail


def test_a_referencing_member_cannot_vouch_for_no_conflict(locked, tmp_path):
    """Whether the folder holds a data file of its own cannot be checked."""
    elsewhere = tmp_path / "elsewhere" / "cohort.csv"
    write_cohort(elsewhere)
    os.remove(locked / "cohort_old.csv")
    cfgmod.save_config(locked, {**CONFIG, "data_file": "../../elsewhere/cohort.csv"})
    assert layout.classify(locked).status == layout.UNREADABLE
    with pytest.raises(layout.DataLocationError, match="cannot be listed"):
        SurvivalExperiment(locked).data_file()


def test_an_empty_readable_data_folder_still_falls_through(tmp_path):
    """Unchanged: nothing in ``data/`` means the root is searched."""
    member = tmp_path / "rep"
    (member / "data").mkdir(parents=True)
    write_cohort(member / "cohort.csv")
    cfgmod.save_config(member, dict(CONFIG))
    assert layout.classify(member).status == layout.OK
    assert SurvivalExperiment(member).data_file() == member / "cohort.csv"


def test_once_readable_again_the_current_file_is_read(locked):
    os.chmod(locked / "data", 0o755)
    shutil.rmtree(locked / "analysis", ignore_errors=True)
    assert layout.classify(locked).status == layout.OK
    assert SurvivalExperiment(locked).data_file() == locked / "data" / "cohort.csv"


def test_upgrade_says_so_rather_than_no_data_found(locked):
    from pysurvanalysis.domain import upgrade

    os.remove(cfgmod.config_path(locked))
    plan = upgrade.plan(locked)
    assert any(str(locked / "data") in w for w in plan.warnings), plan.warnings
