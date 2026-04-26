"""Read/write saved analysis pipelines.

Scripts are stored in a per-project ``survival_scripts.yaml`` file with a
single top-level ``scripts:`` key. The file is optional — if it doesn't
exist, the project simply has no saved scripts.

Schema::

    scripts:
      - name: Standard report
        steps:
          - { action: load_data }
          - { action: cox_ph, factors: [Treatment, Sex], include_interactions: true }
          - { action: report }
"""

from __future__ import annotations

from pathlib import Path

import yaml


SCRIPTS_FILENAME = "survival_scripts.yaml"


def scripts_path(project_dir: str | Path) -> Path:
    return Path(project_dir) / SCRIPTS_FILENAME


def load_scripts(project_dir: str | Path) -> list[dict]:
    """Return the list of saved scripts (empty if file missing or malformed)."""
    p = scripts_path(project_dir)
    if not p.is_file():
        return []
    try:
        with p.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:  # noqa: BLE001
        return []
    if not isinstance(data, dict):
        return []
    scripts = data.get("scripts") or []
    return [s for s in scripts if isinstance(s, dict)]


def save_scripts(project_dir: str | Path, scripts: list[dict]) -> Path:
    """Write *scripts* to ``survival_scripts.yaml`` (overwrites)."""
    p = scripts_path(project_dir)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        yaml.safe_dump(
            {"scripts": list(scripts)},
            f,
            sort_keys=False,
            indent=2,
            default_flow_style=False,
            allow_unicode=True,
        )
    return p.resolve()
