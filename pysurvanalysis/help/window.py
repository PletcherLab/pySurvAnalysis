"""The manual window and the ``?`` button that opens it at a topic.

One window per application: every ``?`` re-uses it, turning it to the page
the button names, so the manual keeps its place in history (Back/Forward)
instead of stacking a dialog per click.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTextBrowser,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import pages
from .manifest import CHAPTERS, HOME, TITLES

_TOPIC_ROLE = Qt.ItemDataRole.UserRole


class HelpWindow(QWidget):
    """Contents and search on the left, the page on the right."""

    def __init__(self) -> None:
        super().__init__(None, Qt.WindowType.Window)
        self.setWindowTitle("pySurvAnalysis Manual")
        self.resize(1000, 720)
        self._history: list[str] = []
        self._at = -1
        self.current: str | None = None

        outer = QVBoxLayout(self)
        bar = QHBoxLayout()
        self._back = QPushButton("◀ Back")
        self._forward = QPushButton("Forward ▶")
        home = QPushButton("Contents")
        self._back.clicked.connect(lambda: self._step(-1))
        self._forward.clicked.connect(lambda: self._step(1))
        home.clicked.connect(lambda: self.open(HOME))
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search the manual…")
        self._search.setClearButtonEnabled(True)
        self._search.textChanged.connect(self._fill_tree)
        for widget in (self._back, self._forward, home):
            bar.addWidget(widget)
        bar.addWidget(self._search, 1)
        outer.addLayout(bar)

        split = QSplitter(Qt.Orientation.Horizontal)
        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemClicked.connect(self._on_item)
        self._tree.itemActivated.connect(self._on_item)
        self._browser = QTextBrowser()
        self._browser.setOpenLinks(False)
        self._browser.anchorClicked.connect(self._on_link)
        self._browser.setStyleSheet("QTextBrowser { padding: 8px 14px; }")
        split.addWidget(self._tree)
        split.addWidget(self._browser)
        split.setSizes([280, 720])
        outer.addWidget(split, 1)

        QShortcut(QKeySequence(QKeySequence.StandardKey.Find), self,
                  activated=self._search.setFocus)
        QShortcut(QKeySequence(QKeySequence.StandardKey.Back), self,
                  activated=lambda: self._step(-1))
        self._fill_tree()

    # ── navigation ─────────────────────────────────────────────────────────

    def open(self, topic: str, *, record: bool = True) -> None:
        """Show *topic*'s page (an unknown id opens the contents page)."""
        if topic not in TITLES:
            topic = HOME
        if record:
            del self._history[self._at + 1:]
            if not self._history or self._history[-1] != topic:
                self._history.append(topic)
            self._at = len(self._history) - 1
        self.current = topic
        self._browser.setMarkdown(pages.page_text(topic))
        self._browser.verticalScrollBar().setValue(0)
        self._select_in_tree(topic)
        self._back.setEnabled(self._at > 0)
        self._forward.setEnabled(self._at < len(self._history) - 1)

    def _step(self, delta: int) -> None:
        target = self._at + delta
        if 0 <= target < len(self._history):
            self._at = target
            self.open(self._history[target], record=False)

    def _on_link(self, url: QUrl) -> None:
        if url.scheme() == pages.HELP_SCHEME:
            self.open(url.path() or url.toString().split(":", 1)[-1])
        elif url.scheme() in ("http", "https", "mailto"):
            QDesktopServices.openUrl(url)

    def _on_item(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        topic = item.data(0, _TOPIC_ROLE)
        if topic:
            self.open(topic)

    # ── contents / search ──────────────────────────────────────────────────

    def _fill_tree(self) -> None:
        query = self._search.text().strip()
        self._tree.clear()
        if query:
            for topic in pages.search(query):
                item = QTreeWidgetItem([TITLES[topic]])
                item.setData(0, _TOPIC_ROLE, topic)
                self._tree.addTopLevelItem(item)
            if not self._tree.topLevelItemCount():
                self._tree.addTopLevelItem(QTreeWidgetItem(["No matching pages"]))
        else:
            for chapter, topics in CHAPTERS:
                parent = QTreeWidgetItem([chapter])
                parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                for topic, title in topics:
                    child = QTreeWidgetItem([title])
                    child.setData(0, _TOPIC_ROLE, topic)
                    parent.addChild(child)
                self._tree.addTopLevelItem(parent)
            self._tree.expandAll()
        if self.current:
            self._select_in_tree(self.current)

    def _select_in_tree(self, topic: str) -> None:
        blocked = self._tree.blockSignals(True)
        for item in self._tree.findItems("", Qt.MatchFlag.MatchContains
                                         | Qt.MatchFlag.MatchRecursive):
            if item.data(0, _TOPIC_ROLE) == topic:
                self._tree.setCurrentItem(item)
                self._tree.scrollToItem(item)
                break
        self._tree.blockSignals(blocked)


_window: HelpWindow | None = None


def help_window() -> HelpWindow:
    global _window
    if _window is None:
        _window = HelpWindow()
    return _window


def show_help(topic: str = HOME) -> HelpWindow:
    """Open the manual at *topic*, raising the one manual window."""
    window = help_window()
    window.open(topic)
    if window.isMinimized():
        window.showNormal()
    window.show()
    window.raise_()
    window.activateWindow()
    return window


class HelpButton(QToolButton):
    """The small round ``?`` beside an action or group: opens its page."""

    def __init__(self, topic: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.topic = topic
        self.setText("?")
        self.setAutoRaise(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setFixedSize(QSize(18, 18))
        self.setToolTip(f"Help: {TITLES.get(topic, topic)}")
        self.setStyleSheet(
            "QToolButton { border: 1px solid palette(mid); border-radius: 9px;"
            " font-weight: 700; font-size: 8pt; padding: 0px;"
            " color: palette(highlight); background: transparent; }"
            "QToolButton:hover { background: palette(highlight);"
            " color: palette(highlighted-text); }")
        self.clicked.connect(lambda: show_help(self.topic))


def with_help(widget: QWidget, topic: str, *, stretch: bool = True) -> QWidget:
    """*widget* in a row with a ``?`` for *topic* on its right."""
    row = QWidget()
    lay = QHBoxLayout(row)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(4)
    lay.addWidget(widget, 1 if stretch else 0)
    if not stretch:
        lay.addStretch(0)
    lay.addWidget(HelpButton(topic), 0, Qt.AlignmentFlag.AlignVCenter)
    return row


def install_f1(window: QWidget, topic_for) -> QShortcut:
    """F1 in *window* opens the page ``topic_for()`` names (a callable, so it
    can follow whatever panel is open)."""
    return QShortcut(QKeySequence(QKeySequence.StandardKey.HelpContents), window,
                     activated=lambda: show_help(topic_for() or HOME))


def close_help() -> None:
    """Close the manual (tests; app shutdown)."""
    global _window
    if _window is not None:
        _window.close()
        _window.deleteLater()
        _window = None


__all__ = ["HelpButton", "HelpWindow", "close_help", "help_window", "install_f1",
           "show_help", "with_help"]
