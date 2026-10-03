"""The **Focus** — a named slice of the factors and levels discovered in a data
file, and the unit of independent analysis (ADR-0011).

Factors are never declared. They are *discovered* from the data file — the
DLife Design sheet's columns after ``StartTime``, or a CSV's factor columns —
with each factor's levels in **first-appearance order**, never alphabetical:
appearance order is what the experimenter typed, and controls usually come
first. What a config declares instead is one or more Focuses::

    focuses:
      Crowding20v40:
        factors:                       # display order: legends, facets, cells
          Sex: [Female, Male]
          Density: ["20x", "40x"]
        reference:                     # optional; omit → first level listed
          Density: "40x"
        display_names: {Female/20x: "F, 20x"}
        colours: {Female/20x: "#b2182b"}

A Focus is the **rectangular product** of the levels it names. A factor it
names with one level is a *filter*; a factor it names with two or more is
*varying* and makes up the treatment label; a discovered factor it does not
name at all is *pooled over*. A cell the product implies but the data never
held is simply absent (an unbalanced design), never an error.

A config with no ``focuses:`` block has one anyway, **Unfiltered** — every
discovered factor at every level — unless it carries a pre-Focus ``factors:``
block, which becomes a Focus named ``Interaction`` verbatim, so every
Reference Level survives the migration.

This module imports nothing heavy at import time: config validation and the
Batch Preflight use it without the analysis stack.
"""

from __future__ import annotations

import difflib
import itertools
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

#: The Focus every config without a ``focuses:`` block has. Named for what it
#: is rather than ``All``, which would collide with "run under all Focuses".
UNFILTERED = "Unfiltered"

#: What a pre-Focus ``factors:`` block becomes. That block only ever meant
#: something to the retired Interaction Experiment type.
MIGRATED_NAME = "Interaction"


#: Output-directory names a Focus cannot take: ``analysis/`` held these before
#: Focuses existed, and a Focus writing there would be mistaken for them.
RESERVED_SLUGS = frozenset({"plots", "statistics", "data_output"})


class NotApplicable(Exception):
    """A real action the active Focus Shape does not admit.

    Raised by an analysis or a figure builder that cannot apply to this slice;
    the caller records it as a **Not Applicable** result — in the run log, the
    Run Summary and the report — and moves on. Never fatal, never silent.
    """

    def __init__(self, reason: str, action: str = ""):
        super().__init__(reason)
        self.reason = reason
        self.action = action


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DiscoveredDesign:
    """What the data file says exists, before any Exclusion Group.

    ``cells`` holds full-factor tuples (in :attr:`factors` order) that the file
    populates. For a DLife workbook that is the Design sheet's chambers; for a
    CSV, the rows themselves.
    """

    factors: tuple[str, ...]
    levels: dict[str, tuple[str, ...]]
    cells: frozenset = frozenset()
    #: ``(chamber, cell)`` for a DLife workbook, so a check can see which cells
    #: an Exclusion Group would empty without reading RawData. Empty for a
    #: CSV, which has no chambers to exclude.
    chamber_cells: tuple = ()

    def cell_dicts(self) -> list[dict[str, str]]:
        return [dict(zip(self.factors, cell)) for cell in self.cells]

    def cells_after(self, excluded: Iterable[Any] = ()) -> list[dict[str, str]]:
        """The cells still populated once *excluded* chambers are removed."""
        if not self.chamber_cells:
            return self.cell_dicts()
        gone = {norm_chamber(c) for c in excluded or ()}
        kept = {cell for chamber, cell in self.chamber_cells
                if norm_chamber(chamber) not in gone}
        return [dict(zip(self.factors, cell)) for cell in kept]


def norm_chamber(value: Any) -> Any:
    """A chamber id compared the way the run compares it — one rule
    (:func:`pysurvanalysis.exclusions.normalize_chamber`) for the file, the
    loader and this estimate, so the preflight and the run cannot disagree
    about which chambers an Exclusion Group removes."""
    from ..exclusions import normalize_chamber

    return normalize_chamber(value)


def _unique_in_order(values: Iterable[Any]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for value in values:
        if value is None:
            continue
        try:
            import math

            if isinstance(value, float) and math.isnan(value):
                continue
        except Exception:  # noqa: BLE001
            pass
        seen.setdefault(str(value), None)
    return tuple(seen)


def design_from_frame(frame, factors: Iterable[str],
                      chamber_col: str | None = None) -> DiscoveredDesign:
    """Discover factors, levels and cells from a frame, in row order."""
    names = tuple(str(f) for f in factors)
    if frame is None or not len(frame) or not names:
        return DiscoveredDesign(names, {f: () for f in names}, frozenset())
    work = frame.dropna(subset=list(names))
    levels = {f: _unique_in_order(work[f].tolist()) for f in names}
    rows = [tuple(str(v) for v in row)
            for row in work[list(names)].itertuples(index=False, name=None)]
    chamber_cells: tuple = ()
    if chamber_col and chamber_col in work.columns:
        chamber_cells = tuple(zip(work[chamber_col].tolist(), rows))
    return DiscoveredDesign(names, levels, frozenset(rows), chamber_cells)


#: Discovery results keyed on (path, size, mtime, input options). Status checks
#: run over every member on every Hub refresh, and a workbook that has not
#: changed must not be re-read for each one.
_DESIGN_CACHE: dict[tuple, DiscoveredDesign] = {}


def discover_design(path: str | Path, input_options: dict | None = None) -> DiscoveredDesign:
    """The design of a data file, read as cheaply as its format allows.

    A DLife workbook is read from its **Design sheet alone** — one row per
    chamber — which is what keeps the Batch Preflight's Blocked-Focus check
    affordable across every member of every Project. A CSV has no separate
    design, so it is loaded.
    """
    from .. import data_loader

    p = Path(path)
    opts = dict(input_options or {})
    try:
        st = p.stat()
        key = (str(p.resolve()), st.st_size, st.st_mtime_ns,
               repr(sorted((k, repr(v)) for k, v in opts.items())))
    except OSError:
        key = None
    if key is not None and key in _DESIGN_CACHE:
        return _DESIGN_CACHE[key]

    if p.suffix.lower() == ".xlsx":
        design, factors = data_loader.load_design(p)
        found = design_from_frame(design, factors, chamber_col="Chamber")
        if key is not None:
            _DESIGN_CACHE[key] = found
        return found

    found = _discover_csv(p, opts)
    if key is not None:
        _DESIGN_CACHE[key] = found
    return found


def _discover_csv(path: Path, opts: dict) -> DiscoveredDesign:
    """A CSV's design, in **file order**.

    Read from the raw rows, not the loaded frame: the loader sorts individuals
    by treatment, which would hand discovery alphabetical levels — and make
    ``mDilp235bx`` the reference over ``wCS`` without anyone choosing it.
    """
    import pandas as pd

    from .. import data_loader

    time_col = str(opts.get("time_col") or "Age")
    event_col = str(opts.get("event_col") or "Event")
    fmt = str(opts.get("format", "auto") or "auto")
    fmt = "auto" if fmt in {"auto", "excel"} else fmt
    if fmt == "auto":
        fmt = data_loader.detect_csv_format(path, time_col=time_col, event_col=event_col)

    if fmt == "long":
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        raw = pd.read_csv(path, sep=sep)
        factor_cols = opts.get("factor_cols") or [
            c for c in raw.columns if c not in {time_col, event_col}]
        if time_col in raw.columns and event_col in raw.columns:
            valid = (pd.to_numeric(raw[time_col], errors="coerce").notna()
                     & pd.to_numeric(raw[event_col], errors="coerce").notna())
            raw = raw[valid]
        return design_from_frame(raw, factor_cols)

    # Wide: the column mapping's order is the file's order of groups — or,
    # with no mapping, the order `input.factor_levels` lists them in.
    frame, factors = data_loader.load_experiment(
        path, time_col=time_col, event_col=event_col, csv_format="wide",
        col_mapping=opts.get("col_mapping"), factor_names=opts.get("factor_names"),
        factor_levels=opts.get("factor_levels"),
    )
    found = design_from_frame(frame, factors)
    mapping = opts.get("col_mapping")
    declared = opts.get("factor_levels") if isinstance(opts.get("factor_levels"), dict) else {}
    if len(factors) == 2 and (isinstance(mapping, list) or declared):
        ordered = {}
        for f, key in zip(factors, ("factor1_level", "factor2_level")):
            if isinstance(mapping, list):
                seen = _unique_in_order(item.get(key) for item in mapping
                                        if isinstance(item, dict))
            else:
                seen = _unique_in_order(declared.get(f) or ())
            rest = [lv for lv in found.levels.get(f, ()) if lv not in seen]
            ordered[f] = tuple(lv for lv in seen if lv in found.levels.get(f, ())) + tuple(rest)
        found = DiscoveredDesign(found.factors, ordered, found.cells, found.chamber_cells)
    return found


# ---------------------------------------------------------------------------
# The Focus
# ---------------------------------------------------------------------------

_SLUG_BAD = re.compile(r"[^A-Za-z0-9._-]+")


def slugify(name: str) -> str:
    """A file-system-safe rendering of a Focus name, used in every output path.

    The name itself is shown as typed everywhere a person reads it; only
    paths and filenames use the slug.
    """
    slug = _SLUG_BAD.sub("_", str(name).strip()).strip("._")
    return slug or "focus"


@dataclass
class Focus:
    """One named slice. ``factors`` maps each named factor to its levels in
    display order."""

    name: str
    factors: dict[str, list[str]] = field(default_factory=dict)
    reference: dict[str, str] = field(default_factory=dict)
    display_names: dict[str, str] = field(default_factory=dict)
    colours: dict[str, str] = field(default_factory=dict)
    #: ``declared`` (written in the config), ``unfiltered`` (derived from the
    #: data because nothing was declared) or ``migrated`` (lifted from a
    #: pre-Focus ``factors:`` block). Only ``declared`` is on disk as-is.
    origin: str = "declared"

    # ── identity ───────────────────────────────────────────────────────────

    @property
    def slug(self) -> str:
        return slugify(self.name)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Focus {self.name} {self.factors}>"

    # ── structure ──────────────────────────────────────────────────────────

    @property
    def varying_factors(self) -> list[str]:
        """Factors named with two or more levels — the ones that label."""
        return [f for f, levels in self.factors.items() if len(levels) >= 2]

    @property
    def filter_factors(self) -> dict[str, str]:
        """Factors named with exactly one level — filters, not labels."""
        return {f: levels[0] for f, levels in self.factors.items() if len(levels) == 1}

    @property
    def label_factors(self) -> list[str]:
        """The factors a treatment label is built from.

        The varying ones; when nothing varies (a single-cell Focus) every named
        factor, so the one treatment still has a name.
        """
        return self.varying_factors or list(self.factors)

    def pooled_over(self, design: DiscoveredDesign | None) -> list[str]:
        """Discovered factors this Focus does not name, so pools across."""
        if design is None:
            return []
        return [f for f in design.factors if f not in self.factors]

    def reference_level(self, factor: str) -> str | None:
        """The Cox baseline for *factor*: the explicit ``reference:`` when it
        names a level of the factor, else the first level listed."""
        levels = self.factors.get(factor) or []
        if not levels:
            return None
        chosen = self.reference.get(factor)
        return str(chosen) if chosen is not None and str(chosen) in levels else levels[0]

    def contains(self, cell: dict[str, str]) -> bool:
        """True when a full cell (factor → level) lies inside this Focus."""
        return all(str(cell.get(f)) in levels for f, levels in self.factors.items())

    def label_of(self, cell: dict[str, str]) -> str:
        return "/".join(str(cell[f]) for f in self.label_factors)

    def implied_labels(self) -> list[str]:
        """Every treatment label the rectangular product implies, in display
        order (first factor outermost)."""
        names = self.label_factors
        return ["/".join(combo) for combo in
                itertools.product(*(self.factors[f] for f in names))]

    def analytic_definition(self) -> dict:
        """What the numbers depend on — compared to decide **Out of Date**.

        Display names and colours are deliberately absent: they change no
        number, so editing them must not invalidate a night's analysis.
        """
        return {
            "factors": {f: list(levels) for f, levels in self.factors.items()},
            "reference": {f: self.reference_level(f) for f in self.factors},
        }

    # ── description ────────────────────────────────────────────────────────

    def describe(self, design: DiscoveredDesign | None = None) -> str:
        """One line a reader can check the slice against."""
        parts: list[str] = []
        for f in self.varying_factors:
            levels = ", ".join(self.factors[f])
            ref = self.reference_level(f)
            parts.append(f"{f}: {levels} (reference {ref})")
        text = " × ".join(parts) if parts else "a single cell"
        filters = self.filter_factors
        if filters:
            text += "; only " + ", ".join(f"{f} = {v}" for f, v in filters.items())
        pooled = self.pooled_over(design)
        if pooled:
            text += "; pooled over " + ", ".join(pooled)
        return text

    # ── config ─────────────────────────────────────────────────────────────

    def to_config(self) -> dict:
        body: dict[str, Any] = {
            "factors": {f: [str(v) for v in levels] for f, levels in self.factors.items()},
        }
        explicit = {f: v for f, v in self.reference.items()
                    if f in self.factors and str(v) in self.factors[f]}
        if explicit:
            body["reference"] = dict(explicit)
        if self.display_names:
            body["display_names"] = dict(self.display_names)
        if self.colours:
            body["colours"] = dict(self.colours)
        return body

    @classmethod
    def from_config(cls, name: str, body: Any) -> "Focus":
        body = body if isinstance(body, dict) else {}
        raw_factors = body.get("factors") or {}
        factors: dict[str, list[str]] = {}
        if isinstance(raw_factors, dict):
            for f, levels in raw_factors.items():
                if isinstance(levels, (list, tuple)):
                    factors[str(f)] = [str(v) for v in levels]
                elif levels is not None:
                    factors[str(f)] = [str(levels)]
                else:
                    factors[str(f)] = []

        def _strmap(key: str) -> dict[str, str]:
            raw = body.get(key) or {}
            return {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}

        return cls(name=str(name), factors=factors, reference=_strmap("reference"),
                   display_names=_strmap("display_names"), colours=_strmap("colours"))

    def copy(self, **changes) -> "Focus":
        data = {
            "name": self.name,
            "factors": {f: list(v) for f, v in self.factors.items()},
            "reference": dict(self.reference),
            "display_names": dict(self.display_names),
            "colours": dict(self.colours),
            "origin": self.origin,
        }
        data.update(changes)
        return Focus(**data)


def unfiltered(design: DiscoveredDesign) -> Focus:
    """Every discovered factor at every level — the default Focus."""
    return Focus(UNFILTERED, {f: list(design.levels.get(f, ())) for f in design.factors},
                 origin="unfiltered")


# ---------------------------------------------------------------------------
# Reading and writing the ``focuses:`` block
# ---------------------------------------------------------------------------

def has_focus_block(config: dict) -> bool:
    block = (config or {}).get("focuses")
    return isinstance(block, dict) and bool(block)


def parse_focuses(config: dict) -> list[Focus]:
    """The declared Focuses, in YAML order (``[]`` when none)."""
    block = (config or {}).get("focuses")
    if not isinstance(block, dict):
        return []
    return [Focus.from_config(str(name), body) for name, body in block.items()]


def focuses_to_config(focuses: Iterable[Focus]) -> dict:
    return {f.name: f.to_config() for f in focuses}


def legacy_factor_block(config: dict) -> dict[str, list[str]]:
    """A pre-Focus ``factors:`` block, order preserved (``{}`` when absent)."""
    raw = (config or {}).get("factors")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, list[str]] = {}
    for name, levels in raw.items():
        if isinstance(levels, (list, tuple)):
            out[str(name)] = [str(v) for v in levels]
    return {k: v for k, v in out.items() if v}


def migrated_focus(config: dict) -> Focus | None:
    """The Focus a pre-Focus ``factors:`` block becomes — verbatim, so the
    level order and therefore every Reference Level is unchanged."""
    block = legacy_factor_block(config)
    if not block:
        return None
    return Focus(MIGRATED_NAME, block, origin="migrated")


def resolve_focuses(config: dict, design: DiscoveredDesign | None = None) -> list[Focus]:
    """The Focuses a config has: declared, else migrated, else Unfiltered.

    *design* is needed only for Unfiltered; without one, a config that
    declares nothing answers ``[]`` rather than inventing a Focus it cannot
    describe.
    """
    declared = parse_focuses(config)
    if declared:
        return declared
    migrated = migrated_focus(config)
    if migrated is not None:
        return [migrated]
    if design is None:
        return []
    return [unfiltered(design)]


def validate_focus_block(config: dict) -> list[str]:
    """Structural problems with ``focuses:`` — no data is read."""
    raw = (config or {}).get("focuses")
    if raw is None:
        return []
    if not isinstance(raw, dict):
        return ["`focuses:` must be a mapping of Focus name → {factors: …}."]
    problems: list[str] = []
    slugs: dict[str, str] = {}
    for name, body in raw.items():
        label = f"Focus {name!r}"
        if not str(name).strip():
            problems.append("A Focus has an empty name.")
            continue
        slug = slugify(str(name))
        if slug.lower() in RESERVED_SLUGS:
            problems.append(f"{label} would write to analysis/{slug}/, which is "
                            f"reserved for pre-Focus results; rename it.")
        if slug in slugs:
            problems.append(f"{label} and Focus {slugs[slug]!r} would write to the "
                            f"same output directory ({slug}); rename one.")
        slugs[slug] = str(name)
        if not isinstance(body, dict):
            problems.append(f"{label} must be a mapping with a `factors:` key.")
            continue
        factors = body.get("factors")
        if not isinstance(factors, dict) or not factors:
            problems.append(f"{label} names no factors — give `factors:` at least "
                            f"one factor with its levels.")
            continue
        focus = Focus.from_config(str(name), body)
        for f, levels in focus.factors.items():
            if not levels:
                problems.append(f"{label}: factor {f!r} lists no levels.")
            elif len(set(levels)) != len(levels):
                problems.append(f"{label}: factor {f!r} lists a level twice.")
        ref = body.get("reference")
        if ref is not None and not isinstance(ref, dict):
            problems.append(f"{label}: `reference:` must map factor → level.")
        else:
            for f, level in (ref or {}).items():
                if str(f) not in focus.factors:
                    problems.append(f"{label}: reference names factor {f!r}, which "
                                    f"the Focus does not name.")
                elif str(level) not in focus.factors[str(f)]:
                    problems.append(f"{label}: reference level {level!r} is not one "
                                    f"of {f}'s levels ({', '.join(focus.factors[str(f)])}).")
        for key in ("display_names", "colours"):
            value = body.get(key)
            if value is not None and not isinstance(value, dict):
                problems.append(f"{label}: `{key}:` must map treatment → value.")
    return problems


# ---------------------------------------------------------------------------
# Blocked Focuses
# ---------------------------------------------------------------------------

STALE = "stale"
EMPTY = "empty"


@dataclass(frozen=True)
class BlockReason:
    """Why a Focus cannot run as declared, and what clears it."""

    kind: str           # stale | empty
    detail: str
    fix: str = ""

    def __str__(self) -> str:
        return self.detail + (f" — {self.fix}" if self.fix else "")


def _close(word: str, choices: Iterable[str]) -> str | None:
    found = difflib.get_close_matches(str(word), [str(c) for c in choices], n=1, cutoff=0.6)
    return found[0] if found else None


def stale_reasons(focus: Focus, design: DiscoveredDesign) -> list[BlockReason]:
    """Factors or levels the Focus names that the data file does not contain.

    Asymmetric on purpose: data holding levels a Focus does not name is the
    normal case — selecting a subset is what a Focus is for.
    """
    out: list[BlockReason] = []
    for f, levels in focus.factors.items():
        if f not in design.factors:
            near = _close(f, design.factors)
            out.append(BlockReason(
                STALE, f"Focus {focus.name!r} names factor {f!r}, which the data "
                       f"file does not have (factors: {', '.join(design.factors) or 'none'})",
                f"rename it to {near!r}?" if near else "edit the Focus"))
            continue
        present = design.levels.get(f, ())
        for level in levels:
            if level not in present:
                near = _close(level, present)
                out.append(BlockReason(
                    STALE, f"Focus {focus.name!r} names level {level!r} of {f}, which "
                           f"the data file does not contain (levels: {', '.join(present)})",
                    f"rename it to {near!r}?" if near else "edit the Focus"))
    return out


def repair_stale(focus: Focus, design: DiscoveredDesign) -> Focus | None:
    """*focus* with every stale factor or level replaced by its close match
    in the data file, or ``None`` when some stale name has no match (or none
    is stale). The fix a Blocked Focus's preflight row offers."""
    if not stale_reasons(focus, design):
        return None
    factors: dict[str, list[str]] = {}
    renamed: dict[str, str] = {}
    for f, levels in focus.factors.items():
        target = f if f in design.factors else _close(f, design.factors)
        if target is None:
            return None
        renamed[f] = target
        present = design.levels.get(target, ())
        fixed = []
        for level in levels:
            match = level if level in present else _close(level, present)
            if match is None:
                return None
            fixed.append(match)
        factors[target] = list(dict.fromkeys(fixed))
    reference = {renamed.get(f, f): v for f, v in focus.reference.items()}
    for f, ref in list(reference.items()):
        if ref not in factors.get(f, []):
            match = _close(ref, factors.get(f, []))
            if match is None:
                reference.pop(f)
            else:
                reference[f] = match
    return focus.copy(factors=factors, reference=reference)


def designed_labels(focus: Focus, design: DiscoveredDesign) -> list[str]:
    """Treatment labels the data file populates inside this Focus, before any
    exclusion, in the Focus's display order."""
    present = {focus.label_of(cell) for cell in design.cell_dicts() if focus.contains(cell)}
    return [label for label in focus.implied_labels() if label in present]


def labels_after_exclusion(focus: Focus, design: DiscoveredDesign,
                           excluded: Iterable[Any] = ()) -> list[str]:
    """Treatment labels still populated once *excluded* chambers go — the
    Design-sheet estimate the preflight uses, no RawData read."""
    present = {focus.label_of(c) for c in design.cells_after(excluded) if focus.contains(c)}
    return [label for label in focus.implied_labels() if label in present]


def empty_reasons(focus: Focus, design: DiscoveredDesign,
                  populated: Iterable[str]) -> list[BlockReason]:
    """Cells the data *did* contain that the exclusions emptied.

    A cell the data never had is absent, and absence is normal; only a cell
    QC removed out from under the Focus blocks it.
    """
    have = set(populated)
    out: list[BlockReason] = []
    for label in designed_labels(focus, design):
        if label not in have:
            out.append(BlockReason(
                EMPTY, f"Focus {focus.name!r}: treatment {label!r} is in the data "
                       f"file but has no individuals once exclusions are applied",
                "change the Exclusion Group or drop that level from the Focus"))
    return out


def block_reasons(focus: Focus, design: DiscoveredDesign,
                  populated: Iterable[str] | None = None) -> list[BlockReason]:
    """Every reason *focus* cannot run. *populated* (treatment labels with
    individuals after exclusion) enables the ``empty`` check."""
    stale = stale_reasons(focus, design)
    if stale or populated is None:
        return stale
    return empty_reasons(focus, design, populated)


# ---------------------------------------------------------------------------
# Applying a Focus to individual-level data
# ---------------------------------------------------------------------------

def apply_focus(frame, focus: Focus):
    """Keep the Focus's rows and relabel ``treatment`` by its varying factors.

    Factor columns become strings (levels are compared as text, the way the
    loader builds labels) and ordered Categoricals in display order;
    ``treatment`` becomes an ordered Categorical over the *populated* labels,
    so every grouping downstream — lifetables, legends, tables — follows the
    Focus's order.

    The frame's ``attrs`` — the loader's ``load_warnings`` among them — are
    carried across explicitly, so what the loader noticed about the file
    reaches the report of every Focus cut from it.
    """
    import copy

    import pandas as pd

    attrs = copy.deepcopy(dict(getattr(frame, "attrs", {}) or {}))
    df = frame.copy()
    mask = pd.Series(True, index=df.index)
    for f, levels in focus.factors.items():
        if f not in df.columns:
            empty = df.iloc[0:0].copy()
            empty.attrs = attrs
            return empty
        df[f] = df[f].astype(str)
        mask &= df[f].isin(levels)
    df = df[mask].copy()
    names = focus.label_factors
    if len(df):
        df["treatment"] = df[names].astype(str).agg("/".join, axis=1)
    else:
        df["treatment"] = pd.Series(dtype=str)
    for f, levels in focus.factors.items():
        df[f] = pd.Categorical(df[f], categories=list(levels), ordered=True)
    populated = [t for t in focus.implied_labels() if t in set(df["treatment"].astype(str))]
    df["treatment"] = pd.Categorical(df["treatment"].astype(str),
                                     categories=populated, ordered=True)
    out = df.sort_values(["treatment", "time"]).reset_index(drop=True)
    out.attrs = attrs
    return out


def populated_labels(frame) -> list[str]:
    """Treatment labels with at least one individual, in category order."""
    if frame is None or not len(frame) or "treatment" not in frame.columns:
        return []
    col = frame["treatment"]
    present = set(col.astype(str))
    if hasattr(col, "cat"):
        return [str(c) for c in col.cat.categories if str(c) in present]
    return list(dict.fromkeys(col.astype(str)))


def model_frame(frame, focus: Focus):
    """A copy whose varying factors put the **Reference Level** first.

    Cox and RMST dummy-code with ``drop_first``, so the first category is the
    baseline. Display order and statistical baseline are separate decisions;
    this is where the second one is applied, and only to the model's copy.
    """
    import pandas as pd

    df = frame.copy()
    for f in focus.varying_factors:
        if f not in df.columns:
            continue
        levels = [str(v) for v in focus.factors[f]]
        ref = focus.reference_level(f)
        ordered = [ref] + [lv for lv in levels if lv != ref]
        present = set(df[f].astype(str))
        ordered = [lv for lv in ordered if lv in present]
        df[f] = pd.Categorical(df[f].astype(str), categories=ordered, ordered=True)
    return df


# ---------------------------------------------------------------------------
# Requirements: what an action needs from a Focus
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Requirement:
    """What an analysis or figure needs from a Focus, in two halves.

    **Relevance** is decided by the Focus's *definition* alone — how many
    factors it varies, how many treatments it implies. An action that is not
    relevant is simply **not offered**: no Hub button, no figure in the run,
    no section in any report, because it is not a question this slice asks.
    A one-factor Focus has no interaction to test, and a report that said so
    in every section would teach readers to skip the note that mattered.

    **Computability** is decided by the *data* — which cells hold
    individuals once exclusions apply. A relevant action the data cannot
    support is **Not Applicable**: recorded with the reason in the run log,
    the Run Summary and the report, never silently missing. Two varying
    factors whose crossing has an empty cell is the case in point: the
    interaction model is the obvious question, and the reader must be told
    why there is no answer.
    """

    key: str
    #: What the action is, in a reader's words — used in every reason.
    label: str
    #: Treatments the Focus must imply (relevance) and populate (computability).
    min_treatments: int = 1
    #: Varying factors the Focus must name.
    min_varying: int = 0
    #: Every pair of varying factors must be fully crossed in the populated
    #: cells — what pairwise interaction terms need to be estimable.
    crossed: bool = False

    def relevant(self, focus: "Focus") -> tuple[bool, str]:
        """Whether *focus*'s definition asks the question this action answers."""
        return self._relevant(focus.name, list(focus.varying_factors),
                              len(focus.implied_labels()))

    def _relevant(self, name: str, varying: list[str], n_implied: int) -> tuple[bool, str]:
        if len(varying) < self.min_varying:
            have = (f"varies only {', '.join(varying)}" if varying
                    else "varies no factor")
            return False, (f"Focus {name!r} {have}; {self.label} needs "
                           f"{self.min_varying} or more varying factors")
        if n_implied < self.min_treatments:
            return False, (f"Focus {name!r} is a single treatment; {self.label} "
                           f"needs {self.min_treatments} or more")
        return True, ""

    def computable(self, shape: "FocusShape") -> tuple[bool, str]:
        """Whether the populated cells can support this action."""
        if len(shape.populated) < self.min_treatments:
            return False, (f"only {len(shape.populated)} treatment(s) of Focus "
                           f"{shape.focus_name!r} hold individuals; {self.label} "
                           f"needs {self.min_treatments} or more")
        if self.crossed and shape.crossing_gaps:
            return False, (f"Focus {shape.focus_name!r} has no individuals for "
                           f"{', '.join(shape.crossing_gaps)}, so {self.label}'s "
                           f"interaction terms cannot be estimated")
        return True, ""


#: Any comparison between treatments: log-rank, Gehan-Wilcoxon, hazard ratios.
COMPARISON = Requirement("comparison", "a comparison between treatments",
                         min_treatments=2)
#: A figure that crosses factors: the faceted KM and the interaction plot.
#: A missing cell is just a missing curve, so crossing is not required.
FACTORIAL_PLOT = Requirement("factorial_plot", "a figure crossing factors",
                             min_treatments=2, min_varying=2)
#: The Factorial Battery's models — Cox and RMST with pairwise interactions.
FACTORIAL_MODEL = Requirement("factorial_model", "the Factorial Battery",
                              min_treatments=2, min_varying=2, crossed=True)

REQUIREMENTS: dict[str, Requirement] = {
    r.key: r for r in (COMPARISON, FACTORIAL_PLOT, FACTORIAL_MODEL)}


def offered(focus: "Focus") -> list[Requirement]:
    """The conditional analyses *focus*'s definition makes relevant."""
    return [r for r in REQUIREMENTS.values() if r.relevant(focus)[0]]


def describe_offer(focus: "Focus", shape: "FocusShape | None" = None) -> str:
    """One line: which conditional analyses this Focus is offered, and which
    of those its data cannot compute."""
    parts = []
    for req in offered(focus):
        text = req.label
        if shape is not None:
            ok, reason = req.computable(shape)
            if not ok:
                text += f" (not computable: {reason})"
        parts.append(text)
    if not parts:
        return ("offers the survivorship battery only — no comparison or "
                "factorial analysis applies to a single treatment")
    return "offers " + "; ".join(parts)


def requirement(spec: "Requirement | str | None") -> Requirement | None:
    """A Requirement from itself or its key (``None`` = no requirement)."""
    if spec is None or isinstance(spec, Requirement):
        return spec
    try:
        return REQUIREMENTS[str(spec)]
    except KeyError:
        raise ValueError(f"Unknown requirement {spec!r}. Known: "
                         f"{', '.join(REQUIREMENTS)}.") from None


# ---------------------------------------------------------------------------
# Focus Shape
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FocusShape:
    """Which analyses and figures apply: varying factors, their level counts,
    which implied cells actually hold individuals, and where the crossing of
    two varying factors has a hole."""

    focus_name: str
    varying: tuple[tuple[str, int], ...]
    populated: tuple[str, ...]
    absent: tuple[str, ...]
    #: Level pairs of two varying factors with no individuals, e.g.
    #: ``"Genotype=mut × Diet=DR"`` — what makes an interaction inestimable.
    crossing_gaps: tuple[str, ...] = ()

    @property
    def n_implied(self) -> int:
        return len(self.populated) + len(self.absent)

    def describe(self) -> str:
        if not self.varying:
            return "single cell"
        text = "×".join(str(n) for _, n in self.varying)
        if self.absent:
            text += f" ({len(self.populated)} of {self.n_implied} cells)"
        return text

    def relevant(self, spec) -> tuple[bool, str]:
        req = requirement(spec)
        if req is None:
            return True, ""
        return req._relevant(self.focus_name, [f for f, _ in self.varying],
                             self.n_implied)

    def admits(self, spec) -> tuple[bool, str]:
        """Relevant *and* computable — what a run needs to perform the action."""
        req = requirement(spec)
        if req is None:
            return True, ""
        ok, reason = self.relevant(req)
        if not ok:
            return ok, reason
        return req.computable(self)


def _crossing_gaps(focus: Focus, populated: Iterable[str]) -> tuple[str, ...]:
    varying = focus.varying_factors
    if len(varying) < 2:
        return ()
    cells = [label.split("/") for label in populated]
    cells = [c for c in cells if len(c) == len(varying)]
    gaps: list[str] = []
    for i, j in itertools.combinations(range(len(varying)), 2):
        seen = {(c[i], c[j]) for c in cells}
        for a in focus.factors[varying[i]]:
            for b in focus.factors[varying[j]]:
                if (a, b) not in seen:
                    gaps.append(f"{varying[i]}={a} × {varying[j]}={b}")
    return tuple(gaps)


def shape_of(focus: Focus, populated: Iterable[str]) -> FocusShape:
    """The Shape of *focus* given the treatment labels that hold individuals —
    from a frame, or from a Run Summary's record of one."""
    present = set(populated)
    implied = focus.implied_labels()
    have = tuple(t for t in implied if t in present)
    return FocusShape(
        focus.name,
        tuple((f, len(focus.factors[f])) for f in focus.varying_factors),
        have,
        tuple(t for t in implied if t not in present),
        _crossing_gaps(focus, have),
    )


def focus_shape(focus: Focus, frame) -> FocusShape:
    """The Shape of *focus* over a frame it has already been applied to."""
    return shape_of(focus, populated_labels(frame))


# ---------------------------------------------------------------------------
# Output naming
# ---------------------------------------------------------------------------

def output_name(stem: str, focus: Focus | str, suffix: str) -> str:
    """``stem_<focus>.ext`` — the Focus name travels with every file, so a
    figure that leaves its directory still says which slice it shows."""
    slug = focus.slug if isinstance(focus, Focus) else slugify(str(focus))
    return f"{stem}_{slug}{suffix}"


def summary_filename(focus: Focus | str) -> str:
    return output_name("run_summary", focus, ".json")


class FocusOutputs:
    """Where one Focus's results live: ``analysis/<focus>/`` and the
    name-suffixed files inside it.

    The single statement of the layout, so the pipeline that writes it and
    every reader — the Hub's status, the Project Report, the Plot Editor —
    cannot disagree about a filename.
    """

    def __init__(self, analysis_dir: str | Path, focus: Focus | str):
        self.slug = focus.slug if isinstance(focus, Focus) else slugify(str(focus))
        self._set_root(Path(analysis_dir) / self.slug)

    @classmethod
    def at(cls, root: str | Path, focus: Focus | str) -> "FocusOutputs":
        """The layout rooted at an explicit directory (a caller-chosen
        ``output_dir``), files still carrying the Focus's name."""
        out = cls.__new__(cls)
        out.slug = focus.slug if isinstance(focus, Focus) else slugify(str(focus))
        out._set_root(Path(root))
        return out

    def _set_root(self, root: Path) -> None:
        self.root = root
        self.plots_dir = self.root / "plots"
        self.data_dir = self.root / "data_output"
        self.stats_dir = self.root / "statistics"

    def ensure(self) -> "FocusOutputs":
        for d in (self.root, self.plots_dir, self.data_dir, self.stats_dir):
            d.mkdir(parents=True, exist_ok=True)
        return self

    def name(self, stem: str, suffix: str) -> str:
        return f"{stem}_{self.slug}{suffix}"

    def data(self, stem: str) -> Path:
        return self.data_dir / self.name(stem, ".csv")

    def stats(self, stem: str) -> Path:
        return self.stats_dir / self.name(stem, ".csv")

    def plot(self, filename: str) -> Path:
        p = Path(filename)
        return self.plots_dir / self.name(p.stem, p.suffix or ".png")

    @property
    def summary(self) -> Path:
        return self.root / self.name("run_summary", ".json")

    def report(self, experiment_name: str, suffix: str) -> Path:
        stem = "report" if suffix == ".md" else f"{experiment_name}_report"
        return self.root / self.name(stem, suffix)


# ---------------------------------------------------------------------------
# Out of Date
# ---------------------------------------------------------------------------

def _effective_references(definition: dict) -> dict[str, str]:
    """Each factor's Reference Level as the model used it — the explicit
    ``reference:`` when it names one of the levels, else the first level.

    Compared instead of the raw ``reference:`` map, so writing down the
    default (as the Focus window now does) never reads as a change, and a
    summary that recorded only explicit references still compares."""
    factors = definition.get("factors") or {}
    chosen = definition.get("reference") or {}
    out: dict[str, str] = {}
    for f, levels in factors.items():
        levels = [str(v) for v in (levels or [])]
        if not levels:
            continue
        ref = chosen.get(f) if isinstance(chosen, dict) else None
        out[f] = str(ref) if ref is not None and str(ref) in levels else levels[0]
    return out


def focus_chambers(focus: Focus, design: DiscoveredDesign | None) -> set[str] | None:
    """The chambers whose individuals fall inside *focus*, as normalised text
    ids — ``None`` when the data has no chamber identities (a CSV) or the
    design is unknown. An exclusion outside this set changes no number of
    this Focus."""
    if design is None or not design.chamber_cells:
        return None
    return {str(norm_chamber(chamber)) for chamber, cell in design.chamber_cells
            if focus.contains(dict(zip(design.factors, cell)))}


def _chamber_ids(values: Iterable[Any] | None) -> set[str]:
    return {str(c) for c in (norm_chamber(v) for v in (values or ())) if c is not None}


def _listing(ids: Iterable[str], limit: int = 8) -> str:
    items = sorted(ids, key=lambda s: (not s.lstrip("-").isdigit(),
                                       int(s) if s.lstrip("-").isdigit() else 0, s))
    text = ", ".join(items[:limit])
    return text + (f" and {len(items) - limit} more" if len(items) > limit else "")


def out_of_date_reasons(focus: Focus, payload: dict, exclusion_group: str | None,
                        *, current: dict | None = None,
                        design: DiscoveredDesign | None = None) -> list[str]:
    """Why saved results no longer describe this Focus (empty = current).

    Results with no recorded definition predate Focuses: they cannot vouch for
    any slice, so they are Out of Date by construction.

    Besides the analytic definition and the Exclusion Group's name, *current*
    — what a run would use now — is compared with what the Run Summary
    recorded, key by key and only where the summary recorded it (older ones
    did not, and a missing record is not evidence of a change):

    ``data_sha256``
        the data file's contents — an edited workbook changes every number;
    ``excluded_chambers``
        the chambers actually removed, within this Focus's chambers (*design*
        says which those are) — editing a group's rows changes the numbers
        as surely as switching groups;
    ``assume_censored``
        the censoring policy (``None`` = not applicable, e.g. a CSV);
    ``omit``
        ``{"analyses": [...], "plots": [...]}`` — what the run left out.
    """
    reasons: list[str] = []
    payload = payload or {}
    recorded = payload.get("focus") or {}
    definition = recorded.get("definition")
    if not definition:
        return ["the saved results predate Focuses and record no definition"]
    now_definition = focus.analytic_definition()
    if definition.get("factors") != now_definition["factors"]:
        reasons.append("the Focus's factors or levels changed")
    elif _effective_references(definition) != _effective_references(now_definition):
        reasons.append("a Reference Level changed")
    analysed_group = payload.get("exclusion_group")
    if (analysed_group or None) != (exclusion_group or None):
        reasons.append(f"analysed under exclusion group {analysed_group or 'none'!r}, "
                       f"config now asks for {exclusion_group or 'none'!r}")
    if not current:
        return reasons

    then_sha, now_sha = payload.get("data_sha256"), current.get("data_sha256")
    if then_sha and now_sha and then_sha != now_sha:
        reasons.append("the data file's contents changed since the analysis")

    if "excluded_chambers" in payload and current.get("excluded_chambers") is not None:
        scope = focus_chambers(focus, design)
        if scope is not None:
            then = _chamber_ids(payload.get("excluded_chambers")) & scope
            now = _chamber_ids(current.get("excluded_chambers")) & scope
            if then != now:
                parts = []
                if now - then:
                    parts.append(f"now also excludes chamber(s) {_listing(now - then)}")
                if then - now:
                    parts.append(f"no longer excludes {_listing(then - now)}")
                reasons.append("the excluded chambers changed — "
                               + "; ".join(parts))

    then_cens, now_cens = payload.get("assume_censored"), current.get("assume_censored")
    if then_cens is not None and now_cens is not None and bool(then_cens) != bool(now_cens):
        reasons.append(f"analysed with assumed censoring "
                       f"{'on' if then_cens else 'off'}, config now has it "
                       f"{'on' if now_cens else 'off'}")

    then_omit, now_omit = payload.get("omit"), current.get("omit")
    if isinstance(then_omit, dict) and isinstance(now_omit, dict):
        for kind in ("analyses", "plots"):
            then = {str(i) for i in then_omit.get(kind) or []}
            now = {str(i) for i in now_omit.get(kind) or []}
            if then != now:
                parts = []
                if now - then:
                    parts.append(f"now leaves out {', '.join(sorted(now - then))}")
                if then - now:
                    parts.append(f"now includes {', '.join(sorted(then - now))}")
                reasons.append(f"the {kind} selection changed — " + "; ".join(parts))
    return reasons


# ---------------------------------------------------------------------------
# Defined Plots
# ---------------------------------------------------------------------------

def _plot_cells(labels: Iterable[str], design: DiscoveredDesign) -> list[dict[str, str]] | None:
    n = len(design.factors)
    cells = []
    for label in labels:
        parts = [p.strip() for p in str(label).split("/")]
        if len(parts) != n:
            return None
        cells.append(dict(zip(design.factors, parts)))
    return cells


def defined_plot_relevant(focus: Focus, design: DiscoveredDesign,
                          labels: list[str]) -> bool:
    """Whether a Defined Plot is about this Focus's slice at all.

    It is when the Focus pools over nothing and every listed treatment the
    data file has lies inside the Focus (and at least one does). A plot
    comparing the sexes is not about a females-only Focus, and saying "not
    applicable" there in every report would be noise. A listed treatment the
    file does not have at all — a typo in the sheet — does not make the plot
    irrelevant: it makes it Not Applicable wherever it is otherwise relevant,
    so the mistake is reported rather than vanishing everywhere.
    """
    cells = _plot_cells(labels, design)
    if cells is None or focus.pooled_over(design):
        return False
    real = [c for c in cells
            if all(c[f] in design.levels.get(f, ()) for f in design.factors)]
    inside = [c for c in real if focus.contains(c)]
    return bool(inside) and len(inside) == len(real)


def defined_plot_match(focus: Focus, design: DiscoveredDesign, labels: list[str],
                       populated: Iterable[str]) -> tuple[list[str], str]:
    """Map a Defined Plot's treatment labels onto *focus*.

    Returns ``(focus_labels, "")`` when every listed treatment is a populated
    treatment of this Focus, else ``([], reason)``. All or nothing: an
    experimenter who listed four curves either gets four or is told why not.
    A Focus that pools over a factor cannot match, since each of its curves
    would be several of the cells the experimenter listed, pooled.
    """
    cells = _plot_cells(labels, design)
    if cells is None:
        return [], (f"its labels are not full {'/'.join(design.factors)} "
                    f"treatments of this data file")
    pooled = focus.pooled_over(design)
    if pooled:
        return [], f"Focus {focus.name!r} pools over {', '.join(pooled)}"
    have = set(populated)
    mapped, missing = [], []
    for label, cell in zip(labels, cells):
        target = focus.label_of(cell) if focus.contains(cell) else None
        if target is None or target not in have:
            missing.append(str(label))
        else:
            mapped.append(target)
    if missing:
        return [], f"not in Focus {focus.name!r}: {', '.join(missing)}"
    order = [t for t in focus.implied_labels() if t in set(mapped)]
    return order, ""


def focus_from_defined_plot(name: str, labels: list[str],
                            design: DiscoveredDesign) -> tuple[Focus | None, str]:
    """Propose a Focus equivalent to a Defined Plot, when one exists.

    Equivalent means the rectangular product of the levels the plot uses
    holds exactly the plot's cells among those the data populates — so the
    promoted Focus analyses the treatments the experimenter listed and no
    others.
    """
    cells = _plot_cells(labels, design)
    if not cells:
        return None, "its labels are not full treatments of this data file"
    factors: dict[str, list[str]] = {}
    for f in design.factors:
        used = {c[f] for c in cells}
        factors[f] = [lv for lv in design.levels.get(f, ()) if lv in used]
        if len(factors[f]) != len(used):
            return None, f"it names a level of {f} the data file does not contain"
    candidate = Focus(name, factors)
    wanted = {tuple(c[f] for f in design.factors) for c in cells}
    inside = {tuple(c[f] for f in design.factors)
              for c in design.cell_dicts() if candidate.contains(c)}
    if inside != wanted:
        extra = sorted("/".join(c) for c in inside - wanted)
        return None, ("its treatments are not a rectangular product of levels "
                      f"(the product would also include {', '.join(extra)})")
    return candidate, ""


# ---------------------------------------------------------------------------
# Copying between members
# ---------------------------------------------------------------------------

def copy_check(focuses: Iterable[Focus], design: DiscoveredDesign,
               existing: Iterable[str] = (),
               excluded: Iterable[Any] = ()) -> tuple[list[Focus], list[str]]:
    """Which of *focuses* can be written into a member with *design*.

    Validated before anything is written: a Focus that would be Blocked in the
    receiving member is reported, not copied — for either reason a Focus is
    blocked: a factor or level this member's data lacks (*stale*), or a cell
    the data holds but the receiving member's active exclusions (*excluded*,
    its chamber ids) empty.
    """
    excluded = list(excluded or ())
    taken = {slugify(n) for n in existing}
    ok: list[Focus] = []
    rejected: list[str] = []
    for focus in focuses:
        if focus.slug in taken:
            rejected.append(f"{focus.name}: a Focus of that name already exists here")
            continue
        reasons = block_reasons(focus, design,
                                labels_after_exclusion(focus, design, excluded))
        if reasons:
            rejected.append(f"{focus.name}: {reasons[0]}")
            continue
        ok.append(focus.copy(origin="declared"))
        taken.add(focus.slug)
    return ok, rejected
