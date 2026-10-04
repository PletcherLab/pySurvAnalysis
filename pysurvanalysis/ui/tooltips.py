"""Tooltips that wrap instead of running off the screen.

Qt shows a plain-text tooltip on one line per newline, as wide as the text —
it only wraps once a line is wider than the whole screen — so the app's
paragraph-long tooltips ran off its right edge. One application-wide event
filter rewraps every tooltip as it is shown, to :data:`MAX_TOOLTIP_WIDTH`,
leaving the tooltip text itself untouched: the hundreds of ``setToolTip``
calls stay plain sentences, and tests reading ``toolTip()`` see what was set.

It also fixes the other plain-text failure: Qt guesses a tooltip is HTML when
a tag-like ``<…>`` comes before its first line break, so ``analysis/<focus>/``
lost its ``<focus>``. A wrapped tooltip is shown escaped, so it reads as typed.
"""

from __future__ import annotations

import html
import re

from PyQt6.QtCore import QEvent, QObject, QRect, Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QHeaderView,
    QTabBar,
    QToolTip,
    QWidget,
)

#: Widest a tooltip is drawn, in logical (DPI-independent) pixels — roughly
#: 65 characters of the tooltip font, a comfortable reading line.
MAX_TOOLTIP_WIDTH = 440

#: Text that is deliberately HTML: it starts with a real formatting tag. Left
#: to Qt, which already word-wraps rich text.
_REAL_TAG = re.compile(
    r"^\s*<(?:qt|html|p|b|i|u|br|span|div|table|ul|ol|h[1-6]|font|tt|code)\b",
    re.IGNORECASE)


def wrap_lines(text: str, metrics: QFontMetrics, width: int) -> list[str]:
    """*text* broken into lines no wider than *width* pixels.

    Existing line breaks are kept; lines break between words, and a single
    word wider than the line (a long path) is split where it must be.
    """
    out: list[str] = []
    for paragraph in text.split("\n"):
        if metrics.horizontalAdvance(paragraph) <= width:
            out.append(paragraph)
            continue
        line = ""
        for word in paragraph.split(" "):
            candidate = f"{line} {word}" if line else word
            if metrics.horizontalAdvance(candidate) <= width:
                line = candidate
                continue
            if line:
                out.append(line)
            line = ""
            while metrics.horizontalAdvance(word) > width:
                cut = len(word)
                while cut > 1 and metrics.horizontalAdvance(word[:cut]) > width:
                    cut -= 1
                out.append(word[:cut])
                word = word[cut:]
            line = word
        out.append(line)
    return out


def wrapped_tooltip(text: str, metrics: QFontMetrics,
                    width: int = MAX_TOOLTIP_WIDTH) -> str | None:
    """The HTML to show for *text*, or ``None`` when Qt's own rendering is
    already right (short plain text, or deliberate HTML)."""
    if not text or _REAL_TAG.match(text):
        return None
    lines = wrap_lines(text, metrics, width)
    if len(lines) == len(text.split("\n")) and "<" not in text:
        return None
    ## `white-space: pre` so the lines break exactly where they were measured,
    ## not again by Qt's own (wider) rich-text wrap.
    body = "<br>".join(html.escape(line, quote=False) for line in lines)
    return f"<div style='white-space:pre'>{body}</div>"


def _tip_at(widget: QWidget, pos) -> tuple[str, QRect]:
    """The tooltip text *widget* would show at *pos*, and the area it is
    valid for — an item's own tooltip in an item view, a tab's in a tab bar,
    the widget's otherwise."""
    parent = widget.parentWidget()
    if isinstance(widget, QHeaderView) or isinstance(parent, QHeaderView):
        header = widget if isinstance(widget, QHeaderView) else parent
        section = header.logicalIndexAt(pos)
        model = header.model()
        if section >= 0 and model is not None:
            tip = model.headerData(section, header.orientation(),
                                   Qt.ItemDataRole.ToolTipRole)
            if tip:
                return str(tip), QRect()
        return "", QRect()
    if isinstance(parent, QAbstractItemView) and widget is parent.viewport():
        index = parent.indexAt(pos)
        tip = index.data(Qt.ItemDataRole.ToolTipRole) if index.isValid() else None
        ## No item tooltip: the event goes on to the view itself, which
        ## shows its own — handled when the filter sees the view.
        return (str(tip), parent.visualRect(index)) if tip else ("", QRect())
    if isinstance(widget, QTabBar):
        tab = widget.tabAt(pos)
        if tab >= 0 and widget.tabToolTip(tab):
            return widget.tabToolTip(tab), widget.tabRect(tab)
    return widget.toolTip(), QRect()


class TooltipWrapper(QObject):
    """Application event filter that shows long tooltips wrapped."""

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 (Qt override)
        if event.type() != QEvent.Type.ToolTip or not isinstance(obj, QWidget):
            return False
        try:
            text, rect = _tip_at(obj, event.pos())
            shown = wrapped_tooltip(text, QFontMetrics(QToolTip.font()))
        except Exception:  # noqa: BLE001 - never lose a tooltip to the wrapper
            return False
        if shown is None:
            return False
        QToolTip.showText(event.globalPos(), shown, obj, rect,
                          obj.toolTipDuration())
        return True


def install_tooltip_wrapping(app: QApplication | None = None) -> TooltipWrapper | None:
    """Install the wrapper on *app* once (repeat calls are no-ops)."""
    app = app or QApplication.instance()
    if app is None:
        return None
    existing = getattr(app, "_psurv_tooltip_wrapper", None)
    if existing is not None:
        return existing
    wrapper = TooltipWrapper(app)
    app.installEventFilter(wrapper)
    app._psurv_tooltip_wrapper = wrapper
    return wrapper
