"""``survival_config.yaml`` — read, write, merge, validate.

The config is the authority for everything that used to be UI state: the input
format, the time/event columns, the censoring policy, the active **Exclusion
Group**, the Experiment Type, the declared **Focuses** — named slices of the
factors and levels discovered in the data file (ADR-0011) — and what a run
leaves out (``omit:``, ADR-0012). Factors themselves are never declared.

Unknown keys ride through a write untouched, so a config edited by a future
version of the app — or by hand — is never silently truncated.
"""

from __future__ import annotations

import copy
import os
from pathlib import Path
from typing import Any

import yaml

CONFIG_FILENAME = "survival_config.yaml"
PROJECT_FILENAME = "project.yaml"
BATCH_FILENAME = "batch.yaml"
SPECS_FILENAME = "plot_specs.yaml"

#: Sections merged key-by-key when a Member Experiment inherits Project
#: Defaults. Anything else is replaced wholesale by the member's value.
_DEEP_SECTIONS = ("global", "input", "exclusions", "omit")

#: What an ``omit:`` block can name: the Analysis Set and the Plot Set.
OMIT_KINDS = ("analyses", "plots")

#: Sections a member never inherits. Members rarely share factors, so an
#: inherited Focus would be a Blocked Focus in every member it does not fit,
#: and editing one would put every member's results Out of Date at once.
#: Sharing a design is the explicit *Copy Focuses from…* instead.
NEVER_INHERITED = ("focuses",)

DEFAULT_INPUT: dict[str, Any] = {
    "format": "auto",          # auto | excel | long | wide
    "time_col": "Age",
    "event_col": "Event",
    "factor_cols": None,
    "factor_names": None,
    "col_mapping": None,
    #: Wide format without ``col_mapping``: each factor's levels, from which
    #: the loader matches column names (``Female_20x_death``) to cells.
    "factor_levels": None,
}


def config_path(directory: str | Path) -> Path:
    return Path(directory) / CONFIG_FILENAME


def is_experiment_dir(directory: str | Path) -> bool:
    """True when *directory* is an Experiment Directory (has the marker file).

    ``os.path.isfile``, not ``Path.is_file`` — the latter propagates
    ``PermissionError`` on Python 3.13, and this predicate is called over
    arbitrary trees by the recursive Batch walk. A directory nobody can read
    is "not an experiment", which the walk then reports; it must never be an
    exception out of a structural test.
    """
    return os.path.isfile(config_path(directory))


def load_config(directory: str | Path) -> dict:
    """Read a directory's ``survival_config.yaml`` (``{}`` when absent)."""
    path = config_path(directory)
    if not path.is_file():
        return {}
    return read_yaml(path)


class ConfigSyntaxError(ValueError):
    """A YAML file that cannot be parsed at all — a tab used for indentation,
    an unclosed quote, a missing colon.

    A :class:`ValueError` naming the file, the line and the problem in plain
    words, so every caller that already reports a bad value reports this too;
    ``yaml.YAMLError`` escaped all of them and could abort the Hub over one
    hand-edited file.
    """

    def __init__(self, path: Path, line: int | None, problem: str):
        self.path, self.line, self.problem = Path(path), line, problem
        where = f"{self.path.name}, line {line}" if line else self.path.name
        super().__init__(f"{where}: not valid YAML — {problem}. "
                         f"({self.path})")


def _yaml_problem(exc: yaml.YAMLError) -> tuple[int | None, str]:
    """``(line, plain message)`` from a PyYAML error.

    PyYAML's own text is a multi-line dump with a caret diagram; the first
    sentence of it ("found character '\\t' that cannot start any token") is
    the part a person can act on, and its marks are 0-based. The context
    mark, when there is one, is where the broken construct *began* — the
    line with the unclosed quote or the key missing its colon — which is
    the line to fix; the problem mark is often the line after.
    """
    mark = getattr(exc, "context_mark", None) or getattr(exc, "problem_mark", None)
    line = mark.line + 1 if mark is not None else None
    problem = getattr(exc, "problem", None) or str(exc).splitlines()[0]
    context = getattr(exc, "context", None)
    text = f"{context}, {problem}" if context else str(problem)
    if "'\\t'" in text:
        text += " (YAML indents with spaces, never tabs)"
    return line, text


def read_yaml(path: str | Path) -> dict:
    """Read a YAML mapping, returning ``{}`` for an empty or absent file.

    A file that is not valid YAML raises :class:`ConfigSyntaxError` (a
    ``ValueError``) naming the file and line, never ``yaml.YAMLError``.
    """
    p = Path(path)
    if not p.is_file():
        return {}
    try:
        with p.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except yaml.YAMLError as exc:
        raise ConfigSyntaxError(p, *_yaml_problem(exc)) from None
    if not isinstance(data, dict):
        raise ValueError(f"{p} must contain a YAML mapping, got {type(data).__name__}.")
    return data


def write_yaml(path: str | Path, data: dict) -> Path:
    """Write a YAML mapping, preserving key order."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, indent=2,
                       default_flow_style=False, allow_unicode=True)
    return p.resolve()


def save_config(directory: str | Path, config: dict) -> Path:
    """Write a directory's ``survival_config.yaml``.

    A config with no ``scripts:`` key at all is seeded with the default
    Experiment Script on the way out — the rule :meth:`Project.save` applies
    to ``project.yaml`` (ADR-0007), one level down: every Experiment Directory
    ships a visible, editable ``Standard analysis``, the script a Project's
    ``batch`` script runs in each member. An existing block is never touched —
    an empty list is a deliberate deletion, and re-seeding it would undo the
    user's edit. The config is updated in place so memory matches disk.
    """
    if "scripts" not in config:
        from ..script_editor.project_actions import default_experiment_script

        config["scripts"] = [default_experiment_script()]
    return write_yaml(config_path(directory), config)


def merge_defaults(member: dict, defaults: dict | None) -> dict:
    """Resolve a member config against its Project's ``defaults:``.

    Project Defaults are a *seed and template*, not an authority (ADR-0001):
    anything the member states wins, and the deep sections merge key-by-key so
    a member can override one setting without restating the section.
    """
    resolved = {k: copy.deepcopy(v) for k, v in (defaults or {}).items()
                if k not in NEVER_INHERITED}
    member = member or {}
    for key, value in member.items():
        if key in _DEEP_SECTIONS and isinstance(value, dict) \
                and isinstance(resolved.get(key), dict):
            merged = dict(resolved[key])
            merged.update(value)
            resolved[key] = merged
        else:
            resolved[key] = copy.deepcopy(value)
    return resolved


def input_options(config: dict) -> dict:
    """The ``input:`` section with defaults filled in."""
    opts = dict(DEFAULT_INPUT)
    section = (config or {}).get("input") or {}
    if isinstance(section, dict):
        opts.update({k: v for k, v in section.items() if v is not None
                     or k in DEFAULT_INPUT})
    return opts


def exclusion_group(config: dict) -> str | None:
    """The active Exclusion Group, or ``None`` when exclusions are off.

    The group is configuration, never UI state — the same input and config
    always give the same result, and the name is stamped on every output.
    """
    section = (config or {}).get("exclusions") or {}
    if not isinstance(section, dict):
        return None
    group = section.get("group")
    if group is None or str(group).strip() == "":
        return None
    return str(group).strip()


def omitted(config: dict, kind: str) -> frozenset[str]:
    """The analysis or plot ids (*kind* ``"analyses"`` or ``"plots"``) a run
    leaves out — the boxes unticked in the Hub.

    Stored as what is left *out*, so an untouched config runs everything and
    an analysis added by a later version is included until someone unticks it.
    """
    section = (config or {}).get("omit") or {}
    if not isinstance(section, dict):
        return frozenset()
    items = section.get(kind) or []
    if isinstance(items, str):
        items = [items]
    if not isinstance(items, list):
        return frozenset()
    return frozenset(str(i).strip() for i in items if str(i).strip())


def validate_omit_block(config: dict) -> list[str]:
    from ..experiment_types.base import ALL_ANALYSIS_DEFS, ALL_PLOT_DEFS

    section = (config or {}).get("omit")
    if section is None:
        return []
    if not isinstance(section, dict):
        return ["`omit:` must be a mapping, e.g. `{analyses: [parametric_aft]}`."]
    known = {"analyses": [a.id for a in ALL_ANALYSIS_DEFS],
             "plots": [p.id for p in ALL_PLOT_DEFS]}
    problems: list[str] = []
    for kind, items in section.items():
        if kind not in known:
            problems.append(f"`omit.{kind}` is not something a run can leave out "
                            f"(use {' or '.join(OMIT_KINDS)}).")
            continue
        if items is not None and not isinstance(items, (list, str)):
            problems.append(f"`omit.{kind}` must be a list of ids.")
            continue
        ## A misspelt id leaves nothing out — the run then includes what the
        ## user meant to drop, and nothing on screen says why.
        for item in sorted(omitted(config, kind) - set(known[kind])):
            problems.append(f"`omit.{kind}` names {item!r}, which no run "
                            f"produces. Known: {', '.join(known[kind])}.")
    return problems


def validate_input_block(config: dict) -> list[str]:
    """Problems with the wide-format keys of ``input:`` — no data is read.

    A wide CSV needs its two factor names and one way to tell which cell
    each column holds: ``col_mapping`` (explicit), or ``factor_levels``, from
    which the loader matches column names. Checked here so a typo is a
    Validate YAMLs line rather than a load failure mid-run.
    """
    opts = input_options(config)
    problems: list[str] = []
    names = opts.get("factor_names")
    names_bad = names is not None and (
        not isinstance(names, list)
        or not all(isinstance(n, str) and n.strip() for n in names))
    if names_bad:
        problems.append("`input.factor_names` must be a list of factor names, "
                        "e.g. `[Sex, Density]`.")
        names = None
    levels = opts.get("factor_levels")
    if levels is not None:
        if not isinstance(levels, dict):
            problems.append("`input.factor_levels` must map each factor to its "
                            "levels, e.g. `{Sex: [F, M], Density: [20x, 40x]}`.")
        else:
            for factor, values in levels.items():
                if not isinstance(values, list) or not values:
                    problems.append(f"`input.factor_levels.{factor}` must be a "
                                    f"non-empty list of levels.")
                elif len({str(v) for v in values}) != len(values):
                    problems.append(f"`input.factor_levels.{factor}` lists a "
                                    f"level twice.")
            if names is None:
                if not names_bad:
                    problems.append("`input.factor_levels` needs "
                                    "`input.factor_names` to say which factor "
                                    "is which.")
            elif {str(f) for f in levels} != set(names):
                problems.append(f"`input.factor_levels` must give levels for "
                                f"exactly the factors in `input.factor_names` "
                                f"({', '.join(names)}).")
    mapping = opts.get("col_mapping")
    if mapping is not None and not isinstance(mapping, list):
        problems.append("`input.col_mapping` must be a list of "
                        "`{column, factor1_level, factor2_level, event}` entries.")
    if str(opts.get("format")) == "wide":
        if names is not None and len(names) != 2:
            problems.append("`input.factor_names` must name exactly two factors "
                            "for the wide format.")
        elif names is None and not names_bad:
            problems.append("`input.format: wide` needs `input.factor_names` "
                            "(the two factor names).")
        if mapping is None and levels is None:
            problems.append("`input.format: wide` needs `input.col_mapping` or "
                            "`input.factor_levels` to say which cell each "
                            "column holds.")
    return problems


def scripts_of(config: dict, key: str = "scripts") -> list[dict]:
    """The saved step lists under *key* (``[]`` when absent or malformed)."""
    scripts = (config or {}).get(key) or []
    if not isinstance(scripts, list):
        return []
    return [s for s in scripts if isinstance(s, dict) and s.get("name")]


def validate_config(config: dict) -> list[str]:
    """Problems with a resolved config, type-specific checks included."""
    from ..experiment_types import type_for_config

    problems: list[str] = []
    if not isinstance(config, dict):
        return ["Config must be a YAML mapping."]

    try:
        exp_type = type_for_config(config)
    except ValueError as exc:
        return [str(exc)]

    fmt = input_options(config).get("format", "auto")
    if fmt not in {"auto", "excel", "long", "wide"}:
        problems.append(
            f"`input.format` must be auto, excel, long or wide (got {fmt!r})."
        )
    problems.extend(validate_input_block(config))
    section = config.get("exclusions")
    if section is not None and not isinstance(section, dict):
        problems.append("`exclusions:` must be a mapping, e.g. `{group: default}`.")

    from .focus import validate_focus_block

    problems.extend(validate_focus_block(config))
    problems.extend(validate_omit_block(config))
    problems.extend(exp_type.validate_config(config))
    return problems
