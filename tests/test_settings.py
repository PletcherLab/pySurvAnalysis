"""The persisted UI preferences (``ui.json``) and the suite's isolation from them.

The Hub records every Project it selects in the recent-projects list. Run by
the suite, that wrote pytest's temporary folders into the user's own
``~/.config/pysurvanalysis/ui.json``, so the Hub's recent list filled with
paths that no longer exist.
"""

from __future__ import annotations

from pathlib import Path


def test_the_suite_never_writes_the_real_ui_settings(tmp_path, tmp_path_factory):
    from pysurvanalysis.ui import settings

    settings.add_recent_project(tmp_path)
    base = tmp_path_factory.getbasetemp().resolve()
    written = [p.resolve() for p in base.rglob("ui.json")]
    assert written, "ui.json was written outside the suite's temporary folder"
    assert str(tmp_path.resolve()) in settings.get("recent_projects")


def test_an_empty_xdg_config_home_means_the_default(monkeypatch, tmp_path):
    """The XDG rule: an empty value is unset, never the current directory."""
    from pysurvanalysis.ui import settings

    monkeypatch.setenv("XDG_CONFIG_HOME", "")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert settings.config_file() == tmp_path / ".config" / "pysurvanalysis" / "ui.json"
