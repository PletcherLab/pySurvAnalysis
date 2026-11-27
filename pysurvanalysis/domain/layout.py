"""Experiment Directory layout: what a Batch Run can actually use.

A Project's Member Experiments are discovered by their
``survival_config.yaml`` — but a directory can carry that file and still be
unusable, and a directory holding a perfectly good workbook can be invisible
because nobody scaffolded a config for it. This module names those states so
they are reported *before* an unattended run rather than three hours into one:

* :func:`classify` — what a directory is, and why a run cannot use it.
* :func:`members_in` — every experiment-shaped subdirectory of a Project,
  healthy or **Blocked**, de-duplicated by real path.

"Usable" is decided with the loader's own rule — the same
``DATA_SUFFIXES``/``is_data_file`` filter and the same ``data/``-then-root
search order :class:`SurvivalExperiment.data_file` uses — never a lookalike. A
classifier that says "healthy" where the loader says "no .xlsx/.csv/.tsv
found" is worse than no classifier: it moves the failure from the preflight,
where someone is looking, into the middle of a Batch Run.

**Deliberate divergence from PyTrackingAnalysis.** Upstream's equivalent
module also *files* an "Unfiled Recording" — a DTrack export loose at the
experiment root — into ``data/``, because its loader reads ``data/`` alone.
There is no such state here: this loader searches ``data/`` and then the
directory root, so a workbook at either is already found. What is left of
upstream's blocked-set are the states this loader really does refuse — no
config, no data, and an ambiguous directory holding several candidate files —
plus one of its own: a config that is not valid YAML, reported with its line
rather than raised out of the walk.

**Which file a member reads** is answered once, by :func:`data_location`
(ADR-0013, porting PyTrackingAnalysis's ADR-0018): the loader's search of
``data/`` and the root, or the file its ``data_file:`` names — which may lie
outside the member folder, in a recording the Project does not own. The
loader, this classifier, the Project, Batch discovery and the Hub all ask it,
so none of them can read a different file from the others. A file outside
the member folder is only ever read.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from . import config as cfgmod
from .experiment import ExperimentError, is_data_file

#: Subdirectories of a Project that are never Member Experiments. Output
#: directories are the one thing reliably not a member, and without this a
#: Project root that also holds a stray workbook has its own ``data/`` listed
#: as a candidate member.
_NOT_MEMBERS = {"data", "analysis", "qc", "figures", "__pycache__"}

#: Output directories written beside a report, named for it (``<stem>_figures``
#: from the markdown backend). Matched by suffix rather than listed, because
#: the stem is the report's and so varies with the Project — and a Project that
#: has been reported on once would otherwise offer its own figure dump as a
#: directory to initialize as a member.
_OUTPUT_SUFFIXES = ("_figures",)


def _is_output_dir(name: str) -> bool:
    lowered = name.lower()
    return lowered in _NOT_MEMBERS or lowered.endswith(_OUTPUT_SUFFIXES)

# Status values. The empty string is "not experiment-shaped at all", which is
# not a problem to report — most subdirectories of anything are not.
NOT_AN_EXPERIMENT = ""
OK = "ok"
NO_CONFIG = "no config"
NO_DATA = "no data"
AMBIGUOUS = "ambiguous"
UNREADABLE = "unreadable"
#: ``survival_config.yaml`` is there but is not valid YAML. Only a person
#: with an editor can fix it, so no button is offered.
BAD_CONFIG = "bad config"
#: A second member reading a data file an earlier one already reads
#: (ADR-0013). The fix is deciding which member should read it.
DUPLICATE = "duplicate"
#: ``data_file:`` names a file outside the member folder, and the folder also
#: holds a data file of its own — which is the experiment? Not ``ambiguous``:
#: that status's one-click fix names one of the *local* files, which would
#: settle the question by guessing against the reference.
CONFLICT = "conflict"

#: Which action clears each status. ``None`` means no button can fix it.
_FIX = {NO_CONFIG: "config", AMBIGUOUS: "data_file"}


@dataclass(frozen=True)
class MemberLayout:
    """What one directory is, from its layout alone — no data is read.

    The config *is* parsed (cheaply, and only to honour a ``data_file:`` key),
    because ignoring it would call an explicitly-named input ambiguous.
    """

    directory: Path
    name: str
    status: str
    detail: str = ""
    #: Candidate input files the loader would consider, by name.
    candidates: tuple[str, ...] = ()
    #: Whether ``survival_config.yaml`` is present — the Project's own
    #: membership test, which is not the same question as "can it run".
    configured: bool = False

    @property
    def blocked(self) -> bool:
        """A run cannot use this directory as it stands."""
        return self.status not in (OK, NOT_AN_EXPERIMENT)

    @property
    def usable(self) -> bool:
        return self.status == OK

    @property
    def fix(self) -> str | None:
        """``"config"``, ``"data_file"``, or None when nothing can repair it."""
        return _FIX.get(self.status)

    def describe(self) -> str:
        return f"{self.name}: {self.status}" + (f" — {self.detail}" if self.detail else "")


def _readable(directory: Path) -> bool:
    try:
        os.listdir(directory)
    except OSError:
        return False
    return True


def _candidates(base: Path) -> list[Path]:
    """Input files the loader would find directly in *base*, in its order."""
    if not os.path.isdir(base):
        return []
    try:
        return sorted(p for p in base.iterdir() if is_data_file(p))
    except OSError:
        return []


def data_candidates(directory: Path) -> tuple[Path, list[Path]]:
    """``(base, files)`` — where the loader would look, and what it finds.

    Mirrors :meth:`SurvivalExperiment.data_file`'s search exactly: ``data/``
    first, then the directory root, stopping at the first base that holds
    anything. Stopping matters — a directory with one workbook in ``data/``
    and an old copy at the root is unambiguous to the loader, and calling it
    ambiguous here would block a run that would have succeeded.
    """
    directory = Path(directory)
    for base in (directory / "data", directory):
        if base != directory and _unlistable(base):
            ## Unknown is not empty: what data/ holds cannot be seen, and an
            ## old copy at the root is exactly what reading on would find.
            return base, []
        found = _candidates(base)
        if found:
            return base, found
    return directory, []


def _unlistable(folder: Path) -> bool:
    """*folder* exists as a directory but cannot be listed."""
    return os.path.isdir(folder) and not _readable(folder)


def _unlistable_problem(folder: Path) -> str:
    return (f"{folder} cannot be listed (permissions?) — the data file in it "
            f"cannot be found, and a copy at the directory root is never read "
            f"in its place")


def data_file_value(directory: Path | str, name: str) -> str:
    """What ``data_file:`` must say to name the candidate *name* — its path
    relative to the member folder, in forward slashes: ``data/a.csv`` for a
    file the loader found in ``data/``, ``a.csv`` for one at the root.

    The answer **Set data file…** writes. A candidate is listed by its bare
    name, and writing that name alone named a file at the root — which, for
    the usual two workbooks in ``data/``, does not exist, so the repair turned
    an ambiguous member into one with no data. Looked up in the loader's
    order, ``data/`` before the root; a name found in neither is returned as
    given.
    """
    directory = Path(directory)
    for base in (directory / "data", directory):
        for path in _candidates(base):
            if path.name == name:
                return path.relative_to(directory).as_posix()
    return name


def has_config(directory: Path | str) -> bool:
    """``survival_config.yaml`` at the root — the membership test.

    Deliberately :func:`config.is_experiment_dir` itself: a directory this
    says has no config is one the Project genuinely cannot see, which is what
    makes "scaffold a config" the right offer.
    """
    return cfgmod.is_experiment_dir(directory)


# ---------------------------------------------------------------------------
# Which file a member reads (ADR-0013)
# ---------------------------------------------------------------------------

#: The ``survival_config.yaml`` key naming a member's data file. It belongs to
#: that one config: never inherited from the Project Defaults (it names *this*
#: member's file), and compared across members only to find a duplicate.
DATA_FILE_KEY = "data_file"


class DataLocationError(ExperimentError):
    """A member's ``data_file:`` cannot be read as it stands — the file is
    missing or is a folder, or (outside the member folder) competes with a
    data file of the member's own. The message names the key, the value as
    written and the resolved path."""


#: Why a named file cannot be used; the classifier maps each to a status.
_MISSING = "missing"
_NOT_A_FILE = "not a file"
_NOT_A_PATH = "not a path"
_CONFLICT = "conflict"
#: The member's own ``data/`` exists but cannot be listed.
_UNLISTABLE = "unlistable"


@dataclass(frozen=True)
class DataLocation:
    """Which file one member reads, and how that was decided.

    *path* is the file the loader reads, or None when there is no single one.
    *written* is ``data_file:`` exactly as the config spells it, or None when
    the member names none — then *base* and *candidates* are the loader's own
    search (:func:`data_candidates`) and nothing about the member has changed.
    *external* says the named file lies outside the member folder: a
    **Referenced Data File**, only ever read. *problem* says why the loader
    cannot read the named file; it is empty when it can.
    """

    path: Path | None
    written: str | None = None
    external: bool = False
    problem: str = ""
    kind: str = ""
    base: Path | None = None
    candidates: tuple[Path, ...] = ()

    @property
    def referenced(self) -> bool:
        """The member names its data file with ``data_file:``."""
        return self.written is not None

    @property
    def resolved(self) -> str:
        """The named file as the operating system finds it — ``realpath``,
        exactly as returned (on Windows that may be ``\\\\?\\`` or UNC
        form)."""
        return os.path.realpath(self.path) if self.path is not None else ""

    @property
    def identity(self) -> str | None:
        """What two members are compared by: one data file, one member.
        ``normcase`` because the lab's share is case-insensitive."""
        if self.path is None:
            return None
        return os.path.normcase(os.path.realpath(self.path))

    @property
    def refusal(self) -> str:
        """Why the loader refuses this location, in words naming what it
        looked at — or ``""``. Empty also for a ``data_file:`` inside the
        member folder that does not exist: that keeps the loader's older
        message, word for word."""
        if self.referenced and not self.external:
            return ""
        return self.problem

    def provenance(self) -> dict | None:
        """``{"written", "resolved"}`` for a readable Referenced Data File,
        else None — what a run summary, a report and a load message add. None
        for every other member, whose records stay exactly as they were."""
        if not self.external or self.problem:
            return None
        return {"written": self.written, "resolved": self.resolved}

    def describe(self) -> str:
        """``data_file: <as written> → <resolved>``, for logs and reports."""
        return f"{DATA_FILE_KEY}: {self.written} → {self.resolved}"


def configured_data_file(directory: Path | str, config: dict | None = None):
    """``data_file:`` for *directory*, as written, or None.

    *config* is the member's own config, already parsed — never one merged
    with Project Defaults, since the key is not inherited. Otherwise its
    ``survival_config.yaml`` is read; a file that never mentions the key is
    not parsed at all. One that cannot be read or parsed counts as having no
    key: the classifier reports it as a bad config and the loader refuses it.
    A missing or empty value is no key — both have always read it with a
    truth test.
    """
    if config is None:
        path = cfgmod.config_path(directory)
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError:
            return None
        if DATA_FILE_KEY not in text:
            return None
        try:
            config = cfgmod.read_yaml(path)
        except (ValueError, OSError):
            return None
    if not isinstance(config, dict):
        return None
    value = config.get(DATA_FILE_KEY)
    return value if value else None


def resolve_data_file(directory: Path | str, value: str) -> str:
    """*value* resolved against the member folder *directory*.

    ``realpath`` of the joined path, so ``..`` is taken after any symlink,
    exactly as ``open()`` takes it. An absolute value is kept. Windows accepts
    backslashes as separators natively; elsewhere a backslash is part of a
    name, which is why the linter asks for forward slashes.
    """
    return os.path.realpath(os.path.join(os.path.abspath(str(directory)),
                                         str(value)))


def _contains(folder: str, path: str) -> bool:
    """*path* is *folder* or somewhere beneath it."""
    folder, path = os.path.normcase(folder), os.path.normcase(path)
    try:
        return os.path.commonpath([folder, path]) == folder
    except ValueError:                      # different drives
        return False


def _inside(directory: Path | str, value: str) -> bool:
    """The named file is in the member folder — by name (``data/x.xlsx``,
    even when ``data/`` is a symlink) or by where it really is.

    Inside, ``data_file:`` keeps the job it always had: naming one of several
    files in the member's own folder, which is what **Set data file…**
    writes. Nothing about that changes.
    """
    directory = os.path.abspath(str(directory))
    if _contains(directory, os.path.normpath(os.path.join(directory, value))):
        return True
    return _contains(os.path.realpath(directory),
                     resolve_data_file(directory, value))


def _own_data_files(directory: Path) -> list[Path]:
    """Data files the member folder holds itself: anything
    :func:`data_candidates` would offer from ``data/`` or the root — so never
    a ``~$`` lock file or ``remove_chambers.csv`` — and never a hidden file
    (a Mac leaves ``._cohort.xlsx`` beside every workbook on a share)."""
    return [p for base in (directory / "data", directory)
            for p in _candidates(base) if not p.name.startswith(".")]


def data_location(directory: Path | str, *, config: dict | None = None) -> DataLocation:
    """Which file the member in *directory* reads.

    Without ``data_file:`` this is the loader's search (:func:`data_candidates`),
    and nothing more is checked — except that a ``data/`` which exists but
    cannot be listed is a problem, never a reason to search the root: what it
    holds is unknown, and an old copy at the root is exactly what reading on
    would find. With ``data_file:``, the value is resolved against
    *directory*:

    * A file **inside** the member folder is ``data_file:`` as it has always
      been: it must exist, and other data files beside it are fine.
    * A file **outside** is a Referenced Data File, checked in this order for
      what makes the loader refuse it: a local ``data/`` that cannot be listed
      (so no conflict can be ruled out); a data file of the member's own beside
      the key ("which is the experiment?" — an empty ``data/`` holds none);
      a file that does not exist; a folder where a file belongs. Each problem
      names the key, the value as written and the resolved path.

    A value that is not a string is refused before either.
    """
    directory = Path(directory)
    value = configured_data_file(directory, config)
    if value is None:
        if _unlistable(directory / "data"):
            return DataLocation(None, kind=_UNLISTABLE, base=directory / "data",
                                problem=_unlistable_problem(directory / "data"))
        base, found = data_candidates(directory)
        return DataLocation(found[0] if len(found) == 1 else None,
                            base=base, candidates=tuple(found))
    if not isinstance(value, str):
        return DataLocation(None, repr(value), kind=_NOT_A_PATH,
                            problem=f"`{DATA_FILE_KEY}: {value!r}` is not a "
                                    f"file path")

    if _inside(directory, value):
        ## Today's data_file:, message for message.
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = directory / candidate
        if os.path.isfile(candidate):
            return DataLocation(candidate, value)
        return DataLocation(candidate, value, kind=_MISSING,
                            problem=f"`{DATA_FILE_KEY}: {value}` does not "
                                    f"exist (looked at {candidate})")

    resolved = resolve_data_file(directory, value)
    where = f"`{DATA_FILE_KEY}: {value}` resolves to {resolved}"

    def refused(kind: str, problem: str) -> DataLocation:
        return DataLocation(Path(resolved), value, True, problem, kind)

    if _unlistable(directory / "data"):
        return refused(
            _UNLISTABLE,
            f"{where}, but {directory / 'data'} cannot be listed (permissions?) "
            f"— whether {directory.name} also holds a data file of its own "
            f"cannot be checked")
    own = _own_data_files(directory)
    if own:
        return refused(
            _CONFLICT,
            f"{where}, outside {directory.name}, but {directory.name} also "
            f"holds a data file of its own ({own[0]}) — which is the "
            f"experiment? Remove `{DATA_FILE_KEY}:` or move the local file out")
    if not os.path.exists(resolved):
        return refused(_MISSING, f"{where}, which does not exist")
    if not os.path.isfile(resolved):
        return refused(_NOT_A_FILE, f"{where}, which is a folder, not a file")
    return DataLocation(Path(resolved), value, external=True)


def require_data_location(directory: Path | str, *, config: dict | None = None,
                          name: str | None = None) -> DataLocation:
    """:func:`data_location`, raising :class:`DataLocationError` when the
    member names a file the loader cannot read, or its ``data/`` cannot be
    listed. The loader's entry point; any other member that names no file is
    returned as found, for the loader's own messages."""
    location = data_location(directory, config=config)
    if not location.problem:
        return location
    label = name or Path(directory).name
    source = (f" (set in {cfgmod.config_path(directory)})"
              if location.external or location.kind == _NOT_A_PATH else "")
    raise DataLocationError(f"{label}: {location.problem}{source}.")


def folder_design(directory: Path | str, config: dict | None = None, *,
                  input_opts: dict | None = None):
    """The factors and levels of the data file *directory* reads, or None
    when it reads no single file, or that file cannot be read.

    For describing a folder (ADR-0014): the file is the one
    :func:`data_location` names, and a DLife workbook is read from its Design
    sheet alone (:func:`focus.discover_design`). No Experiment is constructed
    — loading one creates ``analysis/`` and ``qc/`` — and nothing is written.
    *config* is the folder's own config, as for :func:`data_location`;
    *input_opts* says how to read a CSV.
    """
    from . import focus as focusmod

    try:
        location = data_location(directory, config=config)
        if location.path is None or location.problem:
            return None
        return focusmod.discover_design(location.path, input_opts)
    except Exception:  # noqa: BLE001 — a folder that cannot be read is described without it
        return None


class DataLocations:
    """The data files a Project's members read, first come first served.

    One data file is analysed once per Project (ADR-0009's symlink rule,
    extended by ADR-0013): a member whose file an earlier one — in sorted
    order — already reads is a **duplicate**. Files compare by
    ``normcase(realpath(...))``. The rule applies only when one of the two
    names its file with ``data_file:``; two members that name none are left
    as they always were, even when their files are one file by symlink —
    "no key, no change" outranks the tidier rule. Shared with
    :class:`~pysurvanalysis.domain.project.Project`, so the Project and Batch
    discovery agree on who the duplicate is.
    """

    def __init__(self) -> None:
        self._taken: dict[str, tuple[str, DataLocation]] = {}

    def claim(self, name: str, location: DataLocation) -> str | None:
        """Record *name* reading *location*; return the earlier member it
        duplicates, or None when it is the first to read that file."""
        identity = location.identity
        if identity is None:
            return None
        first = self._taken.get(identity)
        if first is not None and (location.referenced or first[1].referenced):
            return first[0]
        self._taken.setdefault(identity, (name, location))
        return None


def duplicate_detail(first: str, location: DataLocation) -> str:
    """Why a member is a duplicate, naming the one that is kept."""
    return (f"reads the same data file as {first} ({location.resolved}) — "
            f"only {first} is analysed")


def classify(directory: Path | str) -> MemberLayout:
    """What *directory* is: usable member, Blocked Experiment, or neither.

    Layout plus the config's ``data_file:`` key — no data is read, so this
    stays cheap enough to run over every subdirectory of every Project in a
    Batch.
    """
    directory = Path(directory)
    if not os.path.isdir(directory):
        return MemberLayout(directory, directory.name, NOT_AN_EXPERIMENT)
    return _classify(directory, data_location(directory))


def _classify(directory: Path, location: DataLocation) -> MemberLayout:
    """:func:`classify` for a directory whose data location is already known
    — the same answer, so :func:`members_in` resolves each member once."""
    name = directory.name

    def _blocked(status, detail, candidates=()):
        return MemberLayout(directory, name, status, detail,
                            tuple(candidates), configured)

    if not _readable(directory):
        ## Unknown is not the same as absent: a directory nobody can list may
        ## hold a member, and silently dropping it would overstate the
        ## Project's coverage in both the preflight and the run summary.
        return MemberLayout(directory, name, UNREADABLE,
                            "cannot be listed (permissions?)")

    configured = has_config(directory)
    try:
        if configured:
            cfgmod.load_config(directory)
    except ValueError as exc:
        ## A blocked member, named with the file and line — never an
        ## exception out of the walk, which would lose every other Project.
        return _blocked(BAD_CONFIG, str(exc))
    if location.kind == _UNLISTABLE:
        ## Blocked, never searched past: the loader refuses it the same way.
        return _blocked(UNREADABLE, location.problem)

    ## An explicit `data_file:` settles the question before any search — it is
    ## exactly how the loader resolves an otherwise-ambiguous directory, and
    ## the fix this module offers for one. Decided by the loader's own rule,
    ## applied to the file the loader will read.
    if location.referenced:
        if location.problem:
            return _blocked(CONFLICT if location.kind == _CONFLICT else NO_DATA,
                            location.problem)
        return MemberLayout(directory, name, OK,
                            candidates=(str(location.written),),
                            configured=True)

    base, found = location.base or directory, list(location.candidates)
    names = tuple(p.name for p in found)
    where = "data/" if base != directory else "the directory root"

    if len(found) > 1:
        ## The loader raises here rather than picking one, so this is a real
        ## block — and unlike upstream's equivalent it has a real fix: name
        ## one with `data_file:`.
        detail = (f"{len(found)} data files in {where} "
                  f"({', '.join(names[:3])}) — which is the experiment?")
        if not configured:
            ## Nothing to write the answer into yet; the config comes first.
            return _blocked(NO_CONFIG,
                            f"holds {len(found)} data files but no "
                            f"{cfgmod.CONFIG_FILENAME}", names)
        return _blocked(AMBIGUOUS, detail, names)

    if found:
        if configured:
            return MemberLayout(directory, name, OK, candidates=names,
                                configured=True)
        return _blocked(NO_CONFIG,
                        f"holds {names[0]} but no {cfgmod.CONFIG_FILENAME}",
                        names)

    if configured:
        return _blocked(NO_DATA,
                        f"{cfgmod.CONFIG_FILENAME} but no "
                        f".xlsx/.csv/.tsv in data/ or the directory root")
    return MemberLayout(directory, name, NOT_AN_EXPERIMENT)


def members_in(project_dir: Path | str) -> list[MemberLayout]:
    """Classify every immediate subdirectory of *project_dir* that could be a
    Member Experiment, in name order.

    Symlinked directories are followed — :meth:`Project.member_dirs` counts
    them, so refusing to would make a Project of symlinked members look empty
    — but a symlinked *copy* of a member already seen is dropped: the same
    recording analysed twice under two names is the failure, not the symlink
    itself. Output directories are excluded by name, unless one carries a
    config of its own: a member somebody named ``data`` is a member, and
    discovery disagreeing with the Project about its own membership is worse
    than the odd name.

    The same rule one step further (ADR-0013): a member reading a data file
    an earlier member already reads is listed as a **duplicate**, a blocked
    member naming the one kept (:class:`DataLocations`).
    """
    project_dir = Path(project_dir)
    found: list[MemberLayout] = []
    seen: set[str] = set()
    reads = DataLocations()
    try:
        entries = sorted(project_dir.iterdir(), key=lambda p: p.name)
    except OSError:
        return []
    for path in entries:
        if path.name.startswith("."):
            continue
        if not os.path.isdir(path):
            continue
        if _is_output_dir(path.name) and not has_config(path):
            continue
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        location = data_location(path)
        if has_config(path):
            first = reads.claim(path.name, location)
            if first is not None:
                found.append(MemberLayout(
                    path, path.name, DUPLICATE,
                    duplicate_detail(first, location), configured=True))
                continue
        item = _classify(path, location)
        if item.status != NOT_AN_EXPERIMENT:
            found.append(item)
    return found


def initializable_dirs(project_dir: Path | str) -> list[MemberLayout]:
    """Immediate subdirectories of *project_dir* that hold no config yet.

    The candidates for "initialize this existing directory as a member".
    :func:`members_in` answers the narrower question "what is already
    experiment-shaped", and a folder somebody made and has not filled yet
    answers it *no* — which is exactly the folder that needs initializing, so
    it must not be invisible here for want of being a member already.

    Output directories are excluded by name, as there; a directory that
    already carries a ``survival_config.yaml`` is a member and has nothing
    left to initialize.
    """
    project_dir = Path(project_dir)
    found: list[MemberLayout] = []
    seen: set[str] = set()
    try:
        entries = sorted(project_dir.iterdir(), key=lambda p: p.name)
    except OSError:
        return []
    for path in entries:
        if path.name.startswith("."):
            continue
        if not os.path.isdir(path):
            continue
        if _is_output_dir(path.name):
            continue
        if has_config(path):
            continue
        real = os.path.realpath(path)
        if real in seen:
            continue
        seen.add(real)
        found.append(classify(path))
    return found
