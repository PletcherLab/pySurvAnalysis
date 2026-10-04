"""Long tooltips are shown wrapped, never running off the screen."""

from __future__ import annotations

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest  # noqa: E402
from PyQt6.QtCore import QEvent, QPoint  # noqa: E402
from PyQt6.QtGui import QFontMetrics, QHelpEvent  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QApplication,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QToolTip,
)

from pysurvanalysis.ui.tooltips import (  # noqa: E402
    MAX_TOOLTIP_WIDTH,
    install_tooltip_wrapping,
    wrap_lines,
    wrapped_tooltip,
)

LONG = ("Run the ticked analyses and figures under the Active Focus, and write "
        "the results and the report to analysis/<focus>/ — every Focus's "
        "outputs coexist under their own names, so switching changes nothing "
        "on disk.")


@pytest.fixture(scope="module")
def qapp():
    from pysurvanalysis.ui import apply_theme

    app = QApplication.instance() or QApplication([])
    apply_theme(app, "light")
    return app


@pytest.fixture
def metrics(qapp):
    return QFontMetrics(QToolTip.font())


def test_lines_fit_the_width_and_keep_every_word(metrics):
    lines = wrap_lines(LONG, metrics, MAX_TOOLTIP_WIDTH)
    assert len(lines) > 1
    assert all(metrics.horizontalAdvance(line) <= MAX_TOOLTIP_WIDTH for line in lines)
    assert " ".join(lines).split() == LONG.split()


def test_existing_line_breaks_are_kept_and_long_words_split(metrics):
    path = "C:/" + "very_long_folder_name/" * 12
    lines = wrap_lines(f"First line.\n{path}", metrics, MAX_TOOLTIP_WIDTH)
    assert lines[0] == "First line."
    assert "".join(lines[1:]) == path
    assert all(metrics.horizontalAdvance(line) <= MAX_TOOLTIP_WIDTH for line in lines)


def test_placeholders_survive_and_short_plain_text_is_left_to_qt(metrics):
    shown = wrapped_tooltip(LONG, metrics)
    assert "&lt;focus&gt;" in shown                   # shown as typed, not eaten
    assert wrapped_tooltip("Open project…", metrics) is None
    ## Short, but Qt would take <focus> for a tag and drop it.
    assert "&lt;focus&gt;" in wrapped_tooltip("Writes analysis/<focus>/.", metrics)
    assert wrapped_tooltip("<b>Bold</b> on purpose", metrics) is None


def _hover(widget, pos=QPoint(5, 5)):
    event = QHelpEvent(QEvent.Type.ToolTip, pos, widget.mapToGlobal(pos))
    QApplication.sendEvent(widget, event)
    return QToolTip.text()


def test_a_widget_tooltip_is_shown_wrapped(qapp):
    button = QPushButton("Run analysis")
    button.setToolTip(LONG)
    button.show()
    try:
        shown = _hover(button)
        assert shown.count("<br>") >= 1 and "&lt;focus&gt;" in shown
        assert button.toolTip() == LONG                # the text itself untouched
    finally:
        QToolTip.hideText()
        button.close()


def test_an_item_tooltip_in_a_table_is_shown_wrapped(qapp):
    table = QTableWidget(1, 1)
    item = QTableWidgetItem("rep_a")
    item.setToolTip(LONG)
    table.setItem(0, 0, item)
    table.resize(300, 200)
    table.show()
    try:
        cell = table.visualItemRect(item).center()
        assert "<br>" in _hover(table.viewport(), cell)
    finally:
        QToolTip.hideText()
        table.close()


def test_installing_twice_installs_once(qapp):
    assert install_tooltip_wrapping(qapp) is install_tooltip_wrapping(qapp)
