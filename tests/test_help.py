"""The in-app manual: every page exists, every link and every ``?`` lands."""

from __future__ import annotations

import os
import re
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402

from pysurvanalysis.help import TITLES, analysis_topic, plot_topic  # noqa: E402
from pysurvanalysis.help import pages  # noqa: E402

PACKAGE = Path(__file__).resolve().parents[1] / "pysurvanalysis"


def test_every_topic_has_a_page_under_its_title():
    for topic, title in TITLES.items():
        path = pages.page_path(topic)
        assert path.is_file(), f"no page for {topic!r}"
        first = path.read_text(encoding="utf-8").lstrip("﻿").splitlines()[0]
        assert first.strip() == f"# {title}", topic


def test_no_page_is_outside_the_contents():
    stray = {p.stem for p in pages.TOPICS_DIR.glob("*.md")} - set(TITLES)
    assert not stray, f"pages the contents never list: {sorted(stray)}"


def test_every_link_between_pages_lands():
    broken = [(topic, target) for topic in TITLES for target in pages.links_in(topic)
              if target not in TITLES]
    assert not broken


def test_every_analysis_and_figure_has_a_page():
    from pysurvanalysis.experiment_types.base import ALL_ANALYSIS_DEFS, ALL_PLOT_DEFS

    for analysis in ALL_ANALYSIS_DEFS:
        assert analysis_topic(analysis.id) in TITLES, analysis.id
    for plot in ALL_PLOT_DEFS:
        assert plot_topic(plot.id) in TITLES, plot.id


_CALLS = (re.compile(r'(?:HelpButton|set_help|show_help)\(\s*"([^"]+)"'),
          re.compile(r'with_help\((?:[^()]|\([^()]*\))*?,\s*"([^"]+)"\s*[,)]', re.S),
          re.compile(r'install_f1\([^,]+,\s*lambda:\s*"([^"]+)"'))


def test_every_topic_the_code_names_exists():
    named: dict[str, list[str]] = {}
    for path in PACKAGE.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for pattern in _CALLS:
            for topic in pattern.findall(text):
                named.setdefault(topic, []).append(path.name)
    from pysurvanalysis.apps.hub import HubWindow

    for topic in HubWindow._PANEL_HELP.values():
        named.setdefault(topic, []).append("hub.py")
    assert named, "found no help buttons at all"
    unknown = {t: files for t, files in named.items() if t not in TITLES}
    assert not unknown, unknown


def test_search_finds_by_title_first():
    found = pages.search("hazard ratios")
    assert found[0] == "analysis-hazard-ratios"
    assert pages.search("") == pages.ordered_topics()


# ── the window and the Hub's buttons ───────────────────────────────────────

@pytest.fixture(scope="module")
def qapp():
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def manual(qapp):
    from pysurvanalysis.help.window import close_help

    yield
    close_help()


def test_links_navigate_and_back_returns(manual):
    from PyQt6.QtCore import QUrl

    from pysurvanalysis.help.window import show_help

    window = show_help("analysis-hazard-ratios")
    window._browser.anchorClicked.emit(QUrl("help:focus"))
    assert window.current == "focus"
    window._step(-1)
    assert window.current == "analysis-hazard-ratios"
    assert show_help("no-such-topic").current == "overview"


def test_every_hub_question_mark_opens_its_page(manual, tmp_path):
    from pysurvanalysis.apps.hub import HubWindow
    from pysurvanalysis.domain import Project
    from pysurvanalysis.help.window import HelpButton, help_window
    from tests.conftest import make_experiment_dir

    root = tmp_path / "hp"
    Project.create(root, name="HP")
    make_experiment_dir(root / "rep_a", minimal=True, n_per_cell=12)
    hub = HubWindow(str(root))
    try:
        hub._on_member_double_clicked(hub._members_table.model().index(0, 0))
        buttons = hub.findChildren(HelpButton)
        topics = {b.topic for b in buttons}
        ## A ? beside every analysis and every figure, not just the cards.
        assert {"analysis-interaction", "plot-km-faceted", "analyze-panel",
                "plots-panel", "focus", "qc-viewer"} <= topics
        for button in buttons:
            assert button.topic in TITLES
        for button in buttons[:5]:
            button.click()
            assert help_window().current == button.topic
        ## F1 follows the open panel.
        hub._open_panel_for("plots")
        assert hub._help_topic() == "plots-panel"
        hub.close_panel()
        assert hub._help_topic() == "hub"
    finally:
        hub.close()


def test_the_repository_guide_is_the_exported_manual():
    """doc/user_guide.md is generated; a page edited without re-exporting
    (python -m pysurvanalysis.help.export) is caught here."""
    from pysurvanalysis.help.export import REPO_DOC, manual_markdown

    guide = (REPO_DOC / "user_guide.md").read_text(encoding="utf-8")
    assert guide.replace("\r\n", "\n") == manual_markdown()
