"""The Experiment Directory — one data file, analysed one Focus at a time.

``survival_config.yaml`` at the root marks it; the input workbook/CSV sits at
the root or in ``data/``; outputs go to ``analysis/<focus>/``, one subdirectory
per **Focus**; QC state lives in ``qc/``; publication figures land in
``figures/``. An Experiment Directory is either standalone or a **Member
Experiment** of a Project (ADR-0003) — nothing about the object changes between
those two cases.

The data file may hold several experiments. The directory holds them all and
the Focuses tell them apart (ADR-0011): each is a named slice of the factors and
levels *discovered* in the file, analysed on its own, with its own results.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config as cfgmod
from . import focus as focusmod
from .focus import Focus, FocusOutputs

DATA_SUFFIXES = (".xlsx", ".csv", ".tsv")

#: Sidecar CSVs that live beside the data and must never be mistaken for it.
NON_DATA_NAMES = frozenset({"remove_chambers.csv"})

#: What ``analysis/`` held before Focuses existed. Those results carry no
#: Focus and no recorded definition, so they are listed — never adopted.
LEGACY_RESULT_NAMES = ("run_summary.json", "plots", "statistics", "data_output",
                       "report.md")


def is_data_file(path: Path) -> bool:
    """True for a plausible input file (not a sidecar, not an Excel lock file).

    ``os.path.isfile`` last, and tolerant: the Batch walk classifies
    directories it does not own, and a stat that raises would take down the
    whole scan over one unreadable file.
    """
    return (
        path.suffix.lower() in DATA_SUFFIXES
        and path.name.lower() not in NON_DATA_NAMES
        and not path.name.startswith("~$")
        and os.path.isfile(path)
    )


class ExperimentError(RuntimeError):
    """A problem that prevents an Experiment Directory being used."""


class BlockedFocusError(ExperimentError):
    """A **Blocked Focus**: it cannot run as declared. Its member is not
    blocked — the member's other Focuses run."""

    def __init__(self, focus: Focus, reasons: list):
        self.focus = focus
        self.reasons = list(reasons)
        super().__init__(
            f"Focus {focus.name!r} is blocked:\n  - "
            + "\n  - ".join(str(r) for r in self.reasons))


@dataclass
class FocusStatus:
    """One Focus as the Hub and the Focus Inventory show it — read from its
    Run Summary, never by re-analysing."""

    name: str
    slug: str
    description: str = ""
    origin: str = "declared"
    analyzed: bool = False
    #: The saved results were produced under a different analytic definition
    #: or Exclusion Group than the config now declares.
    out_of_date: bool = False
    out_of_date_reasons: tuple[str, ...] = ()
    #: Why the Focus cannot run as declared (stale names, or a cell an
    #: exclusion emptied — estimated from the Design sheet).
    blocked: tuple[str, ...] = ()
    n_total: int | None = None
    n_deaths: int | None = None
    n_censored: int | None = None
    n_treatments: int | None = None
    analyzed_at: str | None = None
    shape: str | None = None
    #: The Exclusion Group the SAVED results were produced under.
    analysed_group: str | None = None
    n_excluded: int = 0
    #: ``(action, reason)`` pairs recorded by the run.
    not_applicable: tuple[tuple[str, str], ...] = ()

    @property
    def state(self) -> str:
        """analysed / not analysed / out of date / blocked — the Inventory's
        word for it."""
        if self.blocked:
            return "blocked"
        if not self.analyzed:
            return "not analysed"
        if self.out_of_date:
            return "out of date"
        return "analysed"


@dataclass
class ExperimentStatus:
    """What the Hub's members table and the Project Report's inventory show."""

    name: str
    type_key: str = "standard_lifespan"
    exclusion_group: str | None = None
    problems: tuple[str, ...] = ()
    factors: tuple[str, ...] = ()
    focuses: tuple[FocusStatus, ...] = ()
    #: Result directories under ``analysis/`` that no declared Focus names.
    orphaned: tuple[str, ...] = ()
    #: Pre-Focus results sitting in bare ``analysis/``.
    legacy_results: bool = False

    @property
    def analyzed(self) -> bool:
        return any(f.analyzed for f in self.focuses)

    @property
    def n_analyzed(self) -> int:
        return sum(1 for f in self.focuses if f.analyzed and not f.out_of_date)

    @property
    def out_of_date(self) -> bool:
        return any(f.analyzed and f.out_of_date for f in self.focuses)

    @property
    def blocked(self) -> tuple[FocusStatus, ...]:
        return tuple(f for f in self.focuses if f.blocked)

    def _first(self) -> FocusStatus | None:
        return next((f for f in self.focuses if f.analyzed), None)

    @property
    def n_total(self) -> int | None:
        first = self._first()
        return first.n_total if first else None

    @property
    def analyzed_at(self) -> str | None:
        stamps = [f.analyzed_at for f in self.focuses if f.analyzed_at]
        return max(stamps) if stamps else None

    @property
    def n_excluded(self) -> int:
        first = self._first()
        return first.n_excluded if first else 0


class SurvivalExperiment:
    """One Experiment Directory, its config resolved and its type in hand."""

    def __init__(self, directory: str | Path, defaults: dict | None = None,
                 project: Any = None):
        self.directory = Path(directory).resolve()
        if not self.directory.is_dir():
            raise ExperimentError(f"Not a directory: {self.directory}")
        self.defaults = dict(defaults or {})
        self.project = project
        self._reload_config()

        # Populated by :meth:`load` / :meth:`run_analysis`.
        self.data = None
        self.factors: list[str] = []
        self.result = None
        #: The **Active Focus** — UI state, deliberately: every Focus's
        #: outputs coexist under their own names, so switching it changes
        #: nothing on disk. ``None`` means the first Focus.
        self.active_focus: str | None = None

    def _reload_config(self) -> None:
        from ..experiment_types import type_for_config

        self.raw_config = cfgmod.load_config(self.directory)
        self.config = cfgmod.merge_defaults(self.raw_config, self.defaults)
        ## Resolved now, raised on use: a member naming a type this build does
        ## not have must still be constructible, so the Project can list it
        ## and say what is wrong instead of failing to load at all.
        try:
            self._type, self._type_error = type_for_config(self.config), None
        except ValueError as exc:
            self._type, self._type_error = None, exc

    @property
    def type(self):
        if self._type_error is not None:
            raise ValueError(str(self._type_error))
        return self._type

    # ── identity ───────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return self.directory.name

    @property
    def is_configured(self) -> bool:
        return cfgmod.config_path(self.directory).is_file()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        key = self._type.key if self._type is not None else "?"
        return f"<SurvivalExperiment {self.name} type={key}>"

    # ── paths ──────────────────────────────────────────────────────────────

    @property
    def config_path(self) -> Path:
        return cfgmod.config_path(self.directory)

    @property
    def data_dir(self) -> Path:
        return self.directory / "data"

    @property
    def analysis_dir(self) -> Path:
        return self.directory / "analysis"

    @property
    def qc_dir(self) -> Path:
        return self.directory / "qc"

    @property
    def figures_dir(self) -> Path:
        return self.directory / "figures"

    @property
    def specs_path(self) -> Path:
        return self.directory / cfgmod.SPECS_FILENAME

    def outputs(self, focus: Focus | str) -> FocusOutputs:
        """Where *focus*'s results live (``analysis/<focus>/``)."""
        return FocusOutputs(self.analysis_dir, focus)

    def focus_dir(self, focus: Focus | str) -> Path:
        return self.outputs(focus).root

    def ensure_dirs(self) -> None:
        for d in (self.analysis_dir, self.qc_dir):
            d.mkdir(parents=True, exist_ok=True)

    # ── the input file ─────────────────────────────────────────────────────

    def data_file(self) -> Path:
        """The input workbook/CSV.

        A ``data_file:`` key in the config wins; otherwise ``data/`` is searched
        before the directory root. Exactly one candidate must survive — an
        ambiguous directory is an error naming what it found, never a silent
        pick.
        """
        named = self.config.get("data_file")
        if named:
            candidate = Path(named)
            if not candidate.is_absolute():
                candidate = self.directory / candidate
            if not candidate.is_file():
                raise ExperimentError(
                    f"{self.name}: `data_file: {named}` does not exist "
                    f"(looked at {candidate})."
                )
            return candidate

        for base in (self.data_dir, self.directory):
            if not base.is_dir():
                continue
            found = sorted(p for p in base.iterdir() if is_data_file(p))
            if len(found) == 1:
                return found[0]
            if len(found) > 1:
                raise ExperimentError(
                    f"{self.name}: {len(found)} data files in {base.name or '.'} "
                    f"({', '.join(p.name for p in found)}). Name one with "
                    f"`data_file:` in {cfgmod.CONFIG_FILENAME}."
                )
        raise ExperimentError(
            f"{self.name}: no .xlsx/.csv/.tsv found in {self.directory} or its "
            f"data/ subdirectory."
        )

    def has_data(self) -> bool:
        try:
            self.data_file()
        except ExperimentError:
            return False
        return True

    # ── discovery ──────────────────────────────────────────────────────────

    def design(self) -> focusmod.DiscoveredDesign:
        """The factors, levels and cells the data file holds, before any
        exclusion. Cached on the file's size and mtime."""
        return focusmod.discover_design(self.data_file(),
                                        cfgmod.input_options(self.config))

    def try_design(self) -> focusmod.DiscoveredDesign | None:
        """:meth:`design`, or ``None`` when the file cannot be read — status
        and listing surfaces must answer for a broken member, not raise."""
        try:
            return self.design()
        except Exception:  # noqa: BLE001
            return None

    # ── Focuses ────────────────────────────────────────────────────────────

    def declared_focuses(self) -> list[Focus]:
        """Focuses the config states — declared, or migrated from a pre-Focus
        ``factors:`` block. No data is read."""
        return focusmod.resolve_focuses(self.config, None)

    def focuses(self) -> list[Focus]:
        """Every Focus this experiment has: declared, else migrated, else
        **Unfiltered** (which needs the data file's design)."""
        declared = self.declared_focuses()
        if declared:
            return declared
        return focusmod.resolve_focuses(self.config, self.try_design())

    def focus(self, name: str) -> Focus:
        for f in self.focuses():
            if f.name == name:
                return f
        raise ExperimentError(
            f"{self.name} has no Focus named {name!r}. Focuses: "
            f"{', '.join(f.name for f in self.focuses()) or 'none'}.")

    def active(self) -> Focus | None:
        """The Active Focus, falling back to the first when unset or gone."""
        focuses = self.focuses()
        if not focuses:
            return None
        for f in focuses:
            if f.name == self.active_focus:
                return f
        return focuses[0]

    def save_focuses(self, focuses: list[Focus]) -> Path:
        """Write the ``focuses:`` block, retiring any pre-Focus declaration.

        A legacy ``factors:`` block is dropped (its content lives on in the
        Focus it migrated to) and a retired ``experiment_type`` is rewritten,
        so the file says what the app now does with it.
        """
        from ..experiment_types import STANDARD, is_retired

        names = [f.name for f in focuses]
        if len(set(names)) != len(names):
            raise ExperimentError("Two Focuses share a name.")
        slugs = [f.slug for f in focuses]
        if len(set(slugs)) != len(slugs):
            raise ExperimentError("Two Focuses would write to the same output "
                                  "directory; rename one.")
        config = dict(self.raw_config)
        config["focuses"] = focusmod.focuses_to_config(focuses)
        config.pop("factors", None)
        if is_retired(config.get("experiment_type")):
            config["experiment_type"] = STANDARD.key
        path = cfgmod.save_config(self.directory, config)
        self._reload_config()
        return path

    def materialize_focuses(self) -> bool:
        """Write the Focuses this experiment *implicitly* has into its config.

        ``Unfiltered`` and a migrated ``Interaction`` are materialised on first
        use, so they can be seen and renamed, and so a later re-sort of the
        Design sheet cannot move a Reference Level. Returns whether anything
        was written.
        """
        if focusmod.has_focus_block(self.raw_config):
            return False
        focuses = self.focuses()
        if not focuses:
            return False
        self.save_focuses([f.copy(origin="declared") for f in focuses])
        return True

    def rename_focus(self, old: str, new: str) -> Focus:
        """Rename a Focus and move its results with it.

        The directory and its name-suffixed files are renamed as part of the
        rename, so renaming through here cannot orphan anything.
        """
        new = str(new).strip()
        if not new:
            raise ExperimentError("A Focus needs a name.")
        self.materialize_focuses()
        focuses = self.focuses()
        target = next((f for f in focuses if f.name == old), None)
        if target is None:
            raise ExperimentError(f"{self.name} has no Focus named {old!r}.")
        renamed = target.copy(name=new)
        if any(f.slug == renamed.slug for f in focuses if f.name != old):
            raise ExperimentError(f"Another Focus already writes to "
                                  f"analysis/{renamed.slug}/.")
        old_dir, new_dir = self.focus_dir(target), self.focus_dir(renamed)
        if old_dir.is_dir() and old_dir != new_dir:
            if new_dir.exists():
                raise ExperimentError(f"analysis/{renamed.slug}/ already exists; "
                                      f"delete or adopt it first.")
            self._move_results(old_dir, target.slug, renamed)
        self.save_focuses([renamed if f.name == old else f for f in focuses])
        if self.active_focus == old:
            self.active_focus = new
        return renamed

    def apply_focus_edits(self, focuses: list[Focus],
                          renames: dict[str, str] | None = None) -> None:
        """Save an edited set of Focuses in one go — the Focus window's Save.

        *renames* maps each renamed Focus's old name to its new one; their
        results move with them, exactly as :meth:`rename_focus` would move
        them. A Focus left out of *focuses* is deleted, and its results become
        Orphaned Results. Nothing is written if a rename would land on results
        that already exist.
        """
        by_name = {f.name: f for f in focuses}
        moves = []
        for old, new in (renames or {}).items():
            if old == new or new not in by_name:
                continue
            source = self.focus_dir(old)
            if not source.is_dir():
                continue
            target = by_name[new]
            if self.focus_dir(target).exists() and self.focus_dir(target) != source:
                raise ExperimentError(f"analysis/{target.slug}/ already exists; "
                                      f"delete or adopt it before renaming "
                                      f"{old!r} to {new!r}.")
            moves.append((source, focusmod.slugify(old), target))
        for source, old_slug, target in moves:
            if source != self.focus_dir(target):
                self._move_results(source, old_slug, target)
        self.save_focuses(list(focuses))
        if self.active_focus in (renames or {}):
            self.active_focus = renames[self.active_focus]

    def repair_focus(self, name: str) -> Focus | None:
        """Rename a stale Focus's factors and levels to their close matches in
        the data file — the fix a Blocked Focus offers in the preflight.
        Returns the repaired Focus, or ``None`` when no full repair exists."""
        self.materialize_focuses()
        focuses = self.focuses()
        target = next((f for f in focuses if f.name == name), None)
        if target is None:
            raise ExperimentError(f"{self.name} has no Focus named {name!r}.")
        repaired = focusmod.repair_stale(target, self.design())
        if repaired is None:
            return None
        self.save_focuses([repaired if f.name == name else f for f in focuses])
        return repaired

    def delete_focus(self, name: str) -> None:
        """Remove a Focus from the config. Its results stay on disk and are
        listed as **Orphaned Results** until adopted or deleted."""
        self.materialize_focuses()
        focuses = [f for f in self.focuses() if f.name != name]
        if len(focuses) == len(self.focuses()):
            raise ExperimentError(f"{self.name} has no Focus named {name!r}.")
        self.save_focuses(focuses)
        if self.active_focus == name:
            self.active_focus = None

    # ── results on disk ────────────────────────────────────────────────────

    def _move_results(self, source: Path, old_slug: str, focus: Focus) -> None:
        """Move a result directory to *focus*'s place, renaming the
        ``_<old>`` suffix of every file and rewriting the Run Summary's name."""
        import json

        dest = self.focus_dir(focus)
        shutil.move(str(source), str(dest))
        suffix = f"_{old_slug}"
        for path in sorted(dest.rglob("*"), key=lambda p: len(p.parts), reverse=True):
            if path.is_file() and path.stem.endswith(suffix):
                path.rename(path.with_name(
                    path.stem[: -len(suffix)] + f"_{focus.slug}" + path.suffix))
        summary = self.outputs(focus).summary
        if summary.is_file():
            try:
                payload = json.loads(summary.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                return
            record = payload.setdefault("focus", {})
            record["name"], record["slug"] = focus.name, focus.slug
            figures = payload.get("figures") or {}
            payload["figures"] = {
                k: (Path(v).stem[: -len(suffix)] + f"_{focus.slug}" + Path(v).suffix
                    if Path(v).stem.endswith(suffix) else v)
                for k, v in figures.items()}
            summary.write_text(json.dumps(payload, indent=2, default=str),
                               encoding="utf-8")

    def result_dirs(self) -> list[Path]:
        """Subdirectories of ``analysis/`` that hold a Focus's results."""
        if not self.analysis_dir.is_dir():
            return []
        return sorted(d for d in self.analysis_dir.iterdir()
                      if d.is_dir() and d.name not in LEGACY_RESULT_NAMES)

    def orphaned_results(self) -> list[str]:
        """Result directories no declared Focus names — left by a hand rename
        in the YAML or a deleted Focus. Never bound into a report."""
        taken = {f.slug for f in self.focuses()}
        return [d.name for d in self.result_dirs() if d.name not in taken]

    def legacy_results(self) -> list[Path]:
        """Pre-Focus outputs in bare ``analysis/``. Shown as not analysed and
        offered for deletion, never adopted: they record no definition, so
        adopting them would vouch for a slice nobody can check."""
        if not self.analysis_dir.is_dir():
            return []
        out = [self.analysis_dir / n for n in LEGACY_RESULT_NAMES
               if (self.analysis_dir / n).exists()]
        out += sorted(p for p in self.analysis_dir.glob("*_report.pdf"))
        return out

    def adopt_orphan(self, directory_name: str, focus_name: str) -> None:
        """Make an orphaned result directory a declared Focus's results.

        Only into a Focus with no results of its own; what is adopted is then
        judged like any other result — Out of Date if its recorded definition
        differs from the Focus it now belongs to.
        """
        source = self.analysis_dir / directory_name
        if not source.is_dir():
            raise ExperimentError(f"analysis/{directory_name}/ does not exist.")
        focus = self.focus(focus_name)
        if self.focus_dir(focus).exists():
            raise ExperimentError(f"Focus {focus_name!r} already has results.")
        self._move_results(source, directory_name, focus)

    def delete_results(self, directory_name: str | None = None) -> None:
        """Delete an orphaned result directory, or (``None``) the pre-Focus
        legacy results."""
        if directory_name is None:
            for path in self.legacy_results():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            return
        target = self.analysis_dir / directory_name
        if target.resolve().parent != self.analysis_dir.resolve():
            raise ExperimentError(f"{directory_name!r} is not a result directory.")
        if target.is_dir():
            shutil.rmtree(target)

    # ── configuration ──────────────────────────────────────────────────────

    @property
    def exclusion_group(self) -> str | None:
        return cfgmod.exclusion_group(self.config)

    def excluded_chambers(self) -> set:
        from .. import exclusions

        group = self.exclusion_group
        if not group:
            return set()
        return exclusions.chambers_for_group(self.directory, group)

    def all_excluded_chambers(self) -> set:
        """The Exclusion Group's chambers plus the workbook's ChamberFlags —
        everything a run removes."""
        excluded = set(self.excluded_chambers())
        try:
            path = self.data_file()
        except ExperimentError:
            return excluded
        if path.suffix.lower() == ".xlsx":
            from .. import data_loader

            excluded |= set(data_loader.load_chamber_flags(path))
        return excluded

    def omitted(self, kind: str) -> frozenset[str]:
        """The analysis or plot ids every run of this experiment leaves out."""
        return cfgmod.omitted(self.config, kind)

    def set_included(self, kind: str, item_id: str, included: bool) -> None:
        """Tick or untick one analysis or plot: written to ``omit:``, so the
        Hub, a script and a Batch Run all leave out the same things."""
        if kind not in cfgmod.OMIT_KINDS:
            raise ValueError(f"Unknown omit kind {kind!r}.")
        left_out = set(self.omitted(kind))
        if included:
            left_out.discard(item_id)
        else:
            left_out.add(item_id)
        config = cfgmod.load_config(self.directory)
        section = config.get("omit") if isinstance(config.get("omit"), dict) else {}
        inherited = (self.defaults.get("omit") or {}) if isinstance(
            self.defaults.get("omit"), dict) else {}
        ## An empty list is kept only when it overrides a Project default —
        ## otherwise a config nobody narrowed stays free of the block.
        if left_out or inherited.get(kind):
            section[kind] = sorted(left_out)
        else:
            section.pop(kind, None)
        if section:
            config["omit"] = section
        else:
            config.pop("omit", None)
        cfgmod.save_config(self.directory, config)
        self._reload_config()

    def scripts(self) -> list[dict]:
        """Experiment Scripts: the member's own, then the Project's central set."""
        own = cfgmod.scripts_of(self.raw_config, "scripts")
        if self.project is None:
            return own
        central = self.project.experiment_scripts()
        names = {s["name"] for s in own}
        return own + [s for s in central if s["name"] not in names]

    def validate(self) -> list[str]:
        """Config-level problems (no data is loaded)."""
        problems = list(cfgmod.validate_config(self.config))
        if not self.has_data():
            problems.append(
                f"No input data file found in {self.directory.name} "
                f"(looked in data/ and the directory root)."
            )
        return problems

    # ── blocking ───────────────────────────────────────────────────────────

    def block_reasons(self, focus: Focus, data=None) -> list:
        """Why *focus* cannot run. With *data* (the slice, exclusions applied)
        the empty-cell check is exact; without it, it is estimated from the
        Design sheet so no RawData is read."""
        design = self.design()
        if data is not None:
            populated = focusmod.populated_labels(data)
        else:
            populated = focusmod.labels_after_exclusion(
                focus, design, self.all_excluded_chambers())
        return focusmod.block_reasons(focus, design, populated)

    def estimated_shape(self, focus: Focus):
        """*focus*'s Shape as the Design sheet and the active exclusions
        predict it — no RawData read, so the Hub can say before anything runs
        which analyses the Focus will be offered and which it cannot compute.
        ``None`` when the data file cannot be read."""
        design = self.try_design()
        if design is None:
            return None
        populated = focusmod.labels_after_exclusion(
            focus, design, self.all_excluded_chambers())
        return focusmod.shape_of(focus, populated)

    # ── loading and analysis ───────────────────────────────────────────────

    def load(self, extra_excluded: set | None = None, focus: Focus | None = None):
        """Load the individual-level frame, exclusions applied.

        With *focus*, the frame is that Focus's slice — ``treatment``
        relabelled by its varying factors and ordered by its levels — and the
        factors returned are the varying ones. Without, it is the whole file
        with every discovered factor.
        """
        from .. import data_loader

        opts = cfgmod.input_options(self.config)
        path = self.data_file()
        excluded = set(self.excluded_chambers()) | set(extra_excluded or set())
        if path.suffix.lower() == ".xlsx":
            excluded |= set(data_loader.load_chamber_flags(path))

        fmt = str(opts.get("format", "auto"))
        csv_format = "auto" if fmt in {"auto", "excel"} else fmt
        data, factors = data_loader.load_experiment(
            path,
            assume_censored=self.type.resolve_assume_censored(self.config),
            excluded_chambers=excluded,
            time_col=str(opts.get("time_col") or "Age"),
            event_col=str(opts.get("event_col") or "Event"),
            factor_cols=opts.get("factor_cols"),
            csv_format=csv_format,
            col_mapping=opts.get("col_mapping"),
            factor_names=opts.get("factor_names"),
        )
        if focus is not None:
            data = focusmod.apply_focus(data, focus)
            factors = list(focus.varying_factors)
        self.data, self.factors = data, list(factors)
        return data, list(factors)

    def run_analysis(self, focus: Focus | str | None = None, log=None,
                     extra_excluded: set | None = None):
        """Run the battery under one Focus and write ``analysis/<focus>/``.

        *focus* defaults to the Active Focus. The implicit Focuses are written
        into the config first, so the Focus a result names is one the file
        declares. A Blocked Focus raises :class:`BlockedFocusError`.
        """
        from .. import pipeline

        if isinstance(focus, str):
            focus = self.focus(focus)
        if focus is None:
            focus = self.active()
        if focus is None:
            raise ExperimentError(f"{self.name}: no Focus could be resolved — is "
                                  f"the data file readable?")
        if self.materialize_focuses():
            focus = self.focus(focus.name)
        self.ensure_dirs()
        result = pipeline.run_analysis(
            self.data_file(),
            output_dir=self.focus_dir(focus),
            experiment=self,
            focus=focus,
            extra_excluded_chambers=set(extra_excluded or set())
            | set(self.excluded_chambers()),
            log=log,
        )
        self.result = result
        self.data = result.individual_data
        self.factors = list(result.factors)
        return result

    def run_all(self, log=None, extra_excluded: set | None = None,
                only: list[str] | None = None) -> dict:
        """Run every Focus (or those in *only*), continue-on-error.

        Returns ``{"results": {name: result}, "blocked": {name: reasons},
        "failed": {name: message}, "unknown": [names]}``. A Blocked Focus is
        reported, not a failure: the member just has fewer Focuses the run can
        use.
        """
        emit = log or (lambda _m: None)
        self.materialize_focuses()
        focuses = self.focuses()
        wanted = set(only or [])
        out: dict = {"results": {}, "blocked": {}, "failed": {},
                     "unknown": sorted(wanted - {f.name for f in focuses})}
        for name in out["unknown"]:
            emit(f"  Focus {name!r}: not declared here — skipped.")
        for focus in focuses:
            if wanted and focus.name not in wanted:
                continue
            try:
                out["results"][focus.name] = self.run_analysis(
                    focus, log=log, extra_excluded=extra_excluded)
            except BlockedFocusError as exc:
                out["blocked"][focus.name] = [str(r) for r in exc.reasons]
                emit(f"  Focus {focus.name!r}: BLOCKED")
                for reason in exc.reasons:
                    emit(f"    - {reason}")
            except Exception as exc:  # noqa: BLE001 - continue-on-error
                out["failed"][focus.name] = str(exc)
                emit(f"  Focus {focus.name!r}: FAILED: {exc}")
        return out

    # ── status ─────────────────────────────────────────────────────────────

    def focus_status(self, focus: Focus, design=None,
                     check_blocked: bool = True) -> FocusStatus:
        """A cheap, filesystem-only summary of one Focus — never re-analyses."""
        import json

        fs = FocusStatus(name=focus.name, slug=focus.slug, origin=focus.origin,
                         description=focus.describe(design))
        if check_blocked and design is not None:
            try:
                populated = focusmod.labels_after_exclusion(
                    focus, design, self.all_excluded_chambers())
                fs.blocked = tuple(str(r) for r in
                                   focusmod.block_reasons(focus, design, populated))
            except Exception:  # noqa: BLE001 - a status must still list
                pass
        path = self.outputs(focus).summary
        if not path.is_file():
            return fs
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001 - a corrupt summary reads as "not analysed"
            return fs
        fs.analyzed = True
        fs.n_total = payload.get("n_total")
        fs.n_deaths = payload.get("n_deaths")
        fs.n_censored = payload.get("n_censored")
        fs.n_treatments = payload.get("n_treatments")
        fs.analyzed_at = payload.get("analyzed_at")
        fs.n_excluded = int(payload.get("n_excluded") or 0)
        fs.shape = (payload.get("focus") or {}).get("shape")
        fs.analysed_group = payload.get("exclusion_group")
        fs.not_applicable = tuple(
            (str(item.get("action", "")), str(item.get("reason", "")))
            for item in payload.get("not_applicable") or [] if isinstance(item, dict))
        ## Out of Date = the configuration disagrees with what the saved run
        ## recorded: the Focus's analytic definition, or the Exclusion Group.
        ## Compared by content, not by mtime — copying a Project between
        ## drives reorders mtimes but never the record.
        reasons = focusmod.out_of_date_reasons(focus, payload, self.exclusion_group)
        fs.out_of_date = bool(reasons)
        fs.out_of_date_reasons = tuple(reasons)
        return fs

    def status(self, check_blocked: bool = True) -> ExperimentStatus:
        """A cheap summary — reads the config, the Run Summaries and (cached)
        the Design sheet; never the raw census."""
        st = ExperimentStatus(name=self.name,
                              type_key=self._type.key if self._type else "?",
                              exclusion_group=self.exclusion_group)
        try:
            st.problems = tuple(self.validate())
        except Exception as exc:  # noqa: BLE001 - a broken config must still list
            st.problems = (str(exc),)
        design = self.try_design()
        if design is not None:
            st.factors = tuple(design.factors)
        try:
            focuses = self.focuses()
        except Exception:  # noqa: BLE001
            focuses = []
        st.focuses = tuple(self.focus_status(f, design, check_blocked)
                           for f in focuses)
        try:
            st.orphaned = tuple(self.orphaned_results())
            st.legacy_results = bool(self.legacy_results())
        except OSError:
            pass
        return st
