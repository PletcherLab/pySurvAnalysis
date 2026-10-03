"""Chamber exclusion groups for pySurvAnalysis projects.

Exclusions are stored in ``qc/remove_chambers.csv`` in the Experiment
Directory. Each row names a *group*, a chamber id, and an optional note.
Different groups let different scripts (or manual hub runs) apply different
exclusion sets from the same dataset.

CSV format::

    group,chamber,note
    default,3,low N — early deaths only
    default,7,
    review_v2,12,suspicious survival

Modeled on pyflic's ``base/exclusions.py``; the only difference is the
absence of a ``dfm_id`` column — survival projects don't have DFMs.
"""

from __future__ import annotations

import csv
import math
import numbers
from pathlib import Path
from typing import Any, Iterable

_FILENAME = "remove_chambers.csv"
_QC_SUBDIR = "qc"
_FIELDNAMES = ["group", "chamber", "note"]


def exclusions_path(experiment_dir: str | Path) -> Path:
    """Where an Experiment Directory's exclusion file lives — and where every
    write goes: ``qc/remove_chambers.csv``.

    A pre-overhaul directory keeps its copy at the root. That copy is still
    *read* while ``qc/`` has none (:func:`read_path`), and the first write
    carries its groups over into ``qc/``, but nothing is ever written back to
    the root — two live files would let the run and the QC Viewer disagree.
    """
    return Path(experiment_dir) / _QC_SUBDIR / _FILENAME


def read_path(experiment_dir: str | Path) -> Path:
    """The file reads come from: ``qc/remove_chambers.csv``, or the legacy
    root-level copy when ``qc/`` has none yet."""
    base = Path(experiment_dir)
    qc = exclusions_path(base)
    if qc.is_file():
        return qc
    legacy = base / _FILENAME
    if legacy.is_file():
        return legacy
    return qc


def normalize_chamber(value: Any) -> Any:
    """A chamber id as every part of the app compares it.

    A whole number becomes an ``int`` however it arrives — ``12``, ``12.0``
    (a float column with one blank cell), ``"12"`` or ``"12.0"`` (a CSV saved
    by a spreadsheet); any other id is stripped text, compared exactly.
    ``None`` for a blank. The loader, the Run Summary, the Design-sheet
    estimate and the QC Viewer all go through this, so a chamber the file
    lists is the chamber the run removes.
    """
    if value is None or isinstance(value, bool):
        return None if value is None else str(value)
    if isinstance(value, numbers.Integral):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return int(value) if value.is_integer() else str(value)
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    try:
        number = float(text)
    except ValueError:
        return text
    if not math.isfinite(number):
        return text
    return int(number) if number.is_integer() else str(number)


def _sort_key(chamber: Any) -> tuple:
    return (isinstance(chamber, str), chamber if not isinstance(chamber, str) else 0,
            str(chamber))


def _read_rows(path: Path) -> list[dict]:
    ## utf-8-sig: a spreadsheet's "CSV UTF-8" save starts with a BOM, which
    ## would turn the `group` header into `﻿group` and silently drop
    ## every row.
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [dict(row) for row in csv.DictReader(f)]


def read_exclusions(project_dir: str | Path) -> dict[str, list]:
    """Read ``remove_chambers.csv`` and return ``{group: [chamber, ...]}``.

    Returns an empty dict if the file does not exist or cannot be parsed.
    Chamber lists are sorted (numerically when possible).
    """
    path = read_path(project_dir)
    if not path.exists():
        return {}
    result: dict[str, list] = {}
    try:
        rows = _read_rows(path)
    except Exception:  # noqa: BLE001
        return {}
    for row in rows:
        group = str(row.get("group", "") or "").strip()
        if not group:
            continue
        chamber = normalize_chamber(row.get("chamber"))
        if chamber is None:
            continue
        bucket = result.setdefault(group, [])
        if chamber not in bucket:
            bucket.append(chamber)
    for group in result:
        result[group] = sorted(result[group], key=_sort_key)
    return result


def read_notes(project_dir: str | Path, group: str) -> dict:
    """``{chamber: note}`` for *group*'s rows that carry a note."""
    path = read_path(project_dir)
    if not path.exists():
        return {}
    try:
        rows = _read_rows(path)
    except Exception:  # noqa: BLE001
        return {}
    notes: dict = {}
    for row in rows:
        if str(row.get("group", "") or "").strip() != group:
            continue
        chamber = normalize_chamber(row.get("chamber"))
        note = str(row.get("note", "") or "").strip()
        if chamber is not None and note:
            notes[chamber] = note
    return notes


def list_groups(project_dir: str | Path) -> list[str]:
    """Return group names in the order they first appear in the CSV."""
    path = read_path(project_dir)
    if not path.exists():
        return []
    seen: list[str] = []
    try:
        rows = _read_rows(path)
    except Exception:  # noqa: BLE001
        return []
    for row in rows:
        group = str(row.get("group", "") or "").strip()
        if group and group not in seen:
            seen.append(group)
    return seen


def write_exclusions(
    project_dir: str | Path,
    group: str,
    chambers: Iterable,
    notes: dict | None = None,
) -> Path:
    """Write/update one named *group* in ``qc/remove_chambers.csv``.

    All rows for *group* are replaced with the entries in *chambers*. Rows
    for all other groups are preserved unchanged. If *chambers* is empty,
    all rows for *group* are removed. A pre-overhaul root-level file is the
    starting point when ``qc/`` has none, so its groups move into ``qc/``
    with the first write rather than being left behind.

    Parameters
    ----------
    project_dir:
        Experiment Directory (the file lives in its ``qc/`` subdirectory).
    group:
        Name of the exclusion group to update (e.g. ``"default"``).
    chambers:
        Iterable of chamber ids (int or str) — the complete desired
        exclusion set for this group.
    notes:
        Optional ``{chamber: note_text}`` for per-entry notes. A chamber it
        does not mention keeps the note the file already has for it — the QC
        Viewer has no notes column, and saving from it must not blank the
        notes someone typed into the file.

    Returns
    -------
    Path
        Absolute path to the written ``remove_chambers.csv``.
    """
    path = exclusions_path(project_dir)
    source = read_path(project_dir)
    given = {normalize_chamber(k): v for k, v in (notes or {}).items()}

    ## Unreadable is not empty: rewriting from nothing would delete every
    ## other group in the file, so a file that cannot be parsed stops the
    ## write instead.
    existing_rows: list[dict] = []
    kept_notes: dict = {}
    if source.exists():
        for row in _read_rows(source):
            if str(row.get("group", "") or "").strip() != group:
                existing_rows.append(row)
                continue
            note = str(row.get("note", "") or "").strip()
            chamber = normalize_chamber(row.get("chamber"))
            if chamber is not None and note:
                kept_notes[chamber] = note

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES)
        writer.writeheader()
        for row in existing_rows:
            writer.writerow({k: row.get(k, "") or "" for k in _FIELDNAMES})
        for chamber in chambers:
            key = normalize_chamber(chamber)
            if key is None:
                continue
            note = given[key] if key in given else kept_notes.get(key, "")
            writer.writerow({"group": group, "chamber": key, "note": note or ""})
    return path.resolve()


def chambers_for_group(project_dir: str | Path, group: str) -> set:
    """Convenience: return the set of chambers excluded by *group*."""
    return set(read_exclusions(project_dir).get(group, []))
