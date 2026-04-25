"""Project YAML configuration: load, save, defaults.

Schema lives in ``survival_config.yaml`` at the project root::

    global:
      input_format: excel        # excel | csv_long | csv_wide
      time_col: Age
      event_col: Event
      factor_cols: [TreatmentNew, Sex]
      rmst_tau: null              # null → use max event time
      alpha: 0.05
      default_exclusion_group: default
      assume_censored: true
      experimental_design_factors:
        TreatmentNew: [Ctrl, Exp]
    csv_wide:
      factor_names: []
      factor_levels: {}
      col_mapping: []
    scripts: []
"""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


CONFIG_FILENAME = "survival_config.yaml"

INPUT_FORMATS = ("excel", "csv_long", "csv_wide")

DEFAULT_CONFIG: dict[str, Any] = {
    "global": {
        "input_format": "excel",
        "time_col": "Age",
        "event_col": "Event",
        "factor_cols": None,
        "rmst_tau": None,
        "alpha": 0.05,
        "default_exclusion_group": "default",
        "assume_censored": True,
        "experimental_design_factors": {},
    },
    "csv_wide": {
        "factor_names": [],
        "factor_levels": {},
        "col_mapping": [],
    },
    "scripts": [],
}


def default_config() -> dict[str, Any]:
    """Return a fresh copy of the default configuration."""
    return deepcopy(DEFAULT_CONFIG)


def _merge(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge *overlay* into *base*; returns *base*."""
    for key, val in overlay.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            _merge(base[key], val)
        else:
            base[key] = val
    return base


def load_config(path: str | Path) -> dict[str, Any]:
    """Load a YAML config and merge over defaults.

    A missing file returns a default config (does not raise).
    """
    p = Path(path)
    cfg = default_config()
    if not p.is_file():
        return cfg
    with p.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        return cfg
    return _merge(cfg, data)


def save_config(path: str | Path, cfg: dict[str, Any]) -> Path:
    """Write *cfg* to *path* as YAML with stable key order."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    out = _normalise_for_dump(cfg)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            out,
            f,
            sort_keys=False,
            indent=2,
            default_flow_style=False,
            allow_unicode=True,
        )
    return p.resolve()


def _normalise_for_dump(cfg: dict[str, Any]) -> dict[str, Any]:
    """Return a dict with the canonical top-level key order for nicer diffs."""
    order = ["global", "csv_wide", "scripts"]
    out: dict[str, Any] = {}
    for key in order:
        if key in cfg:
            out[key] = cfg[key]
    for key, val in cfg.items():
        if key not in out:
            out[key] = val
    return out


def find_config(project_dir: str | Path) -> Path | None:
    """Return the project config path if it exists, else ``None``."""
    p = Path(project_dir) / CONFIG_FILENAME
    return p if p.is_file() else None


def list_yaml_configs(project_dir: str | Path) -> list[Path]:
    """Return all ``*.yaml`` / ``*.yml`` files at the project root."""
    p = Path(project_dir)
    if not p.is_dir():
        return []
    return sorted(list(p.glob("*.yaml")) + list(p.glob("*.yml")))


def validate(cfg: dict[str, Any]) -> list[str]:
    """Return a list of human-readable validation errors (empty == OK)."""
    errors: list[str] = []
    g = cfg.get("global", {})
    fmt = g.get("input_format")
    if fmt not in INPUT_FORMATS:
        errors.append(f"global.input_format must be one of {INPUT_FORMATS}; got {fmt!r}")
    tau = g.get("rmst_tau")
    if tau is not None and not isinstance(tau, (int, float)):
        errors.append("global.rmst_tau must be a number or null")
    alpha = g.get("alpha", 0.05)
    if not isinstance(alpha, (int, float)) or not (0 < alpha < 1):
        errors.append("global.alpha must be a number in (0, 1)")
    if fmt == "csv_wide":
        cw = cfg.get("csv_wide", {}) or {}
        if not cw.get("factor_names"):
            errors.append("csv_wide.factor_names is empty (required for csv_wide)")
        if not cw.get("col_mapping"):
            errors.append("csv_wide.col_mapping is empty (required for csv_wide)")
    return errors
