"""Visual editor for ``survival_config.yaml``.

Three tabs (Global, CSV-wide mapping, Scripts list) plus a live YAML
preview pane on the right. Open / Save / Save As + Theme toggle in the
top bar; non-modal Script Editor is launched from the Scripts tab.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import yaml

from .. import config as cfg_mod
from ..ui import ActionButton, Category, TopBar, apply_theme, icon, resolved_mode
from ..ui import settings as ui_settings
from ._config_tabs import CsvWideTab, GlobalTab


class ConfigEditorWindow(QMainWindow):
    """Visual config editor."""

    def __init__(self, initial_path: str | Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("pySurvAnalysis — Config Editor")
        self.resize(1200, 780)
        self._cfg = cfg_mod.default_config()
        self._path: Path | None = None
        self._dirty = False

        self._build_ui()

        if initial_path:
            self._open_path(Path(initial_path))

    # --------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._top_bar = TopBar("pySurvAnalysis — Config Editor")
        for label, slot, ic in (
            ("Open…", self._open_dialog, "open"),
            ("Save", self._save, "save"),
            ("Save As…", self._save_as, "save_as"),
            ("Script Editor…", self._open_script_editor, "scripts"),
        ):
            btn = ActionButton(label, Category.LOAD, icon_name=ic)
            btn.clicked.connect(slot)
            self._top_bar.add_right(btn)

        self._btn_theme = QToolButton()
        self._btn_theme.setIcon(
            icon("theme_dark" if resolved_mode() == "light" else "theme_light")
        )
        self._btn_theme.setIconSize(QSize(18, 18))
        self._btn_theme.setAutoRaise(True)
        self._btn_theme.setToolTip("Toggle light / dark theme")
        self._btn_theme.clicked.connect(self._toggle_theme)
        self._top_bar.add_right(self._btn_theme)

        outer.addWidget(self._top_bar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        self._tabs = QTabWidget()
        self._global_tab = GlobalTab()
        self._csv_wide_tab = CsvWideTab()
        self._scripts_widget = self._make_scripts_widget()
        self._tabs.addTab(self._global_tab, "Global")
        self._tabs.addTab(self._csv_wide_tab, "CSV-wide mapping")
        self._tabs.addTab(self._scripts_widget, "Scripts")
        splitter.addWidget(self._tabs)

        preview_host = QWidget()
        preview_lay = QVBoxLayout(preview_host)
        preview_lay.setContentsMargins(8, 8, 8, 8)
        preview_lay.addWidget(QLabel("Live YAML preview"))
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setStyleSheet(
            'QPlainTextEdit { font-family: "JetBrains Mono", "Menlo", "Consolas", monospace; '
            'font-size: 10pt; }'
        )
        preview_lay.addWidget(self._preview, 1)
        splitter.addWidget(preview_host)

        splitter.setSizes([720, 480])
        outer.addWidget(splitter, 1)

        self._status = QLabel("(no file open)")
        self._status.setStyleSheet("color: palette(mid); padding: 4px 8px;")
        outer.addWidget(self._status)

        self._global_tab.changed.connect(self._on_changed)
        self._csv_wide_tab.changed.connect(self._on_changed)
        self._refresh_all()

    def _make_scripts_widget(self) -> QWidget:
        host = QWidget()
        lay = QVBoxLayout(host)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(8)
        lay.addWidget(QLabel(
            "Saved analysis scripts. Use the Script Editor to add, remove, or "
            "reorder steps."
        ))
        self._scripts_list = QListWidget()
        lay.addWidget(self._scripts_list, 1)
        row = QHBoxLayout()
        edit_btn = QPushButton("Open Script Editor…")
        edit_btn.clicked.connect(self._open_script_editor)
        row.addWidget(edit_btn)
        row.addStretch(1)
        lay.addLayout(row)
        return host

    # -------------------------------------------------------------- IO

    def _open_dialog(self) -> None:
        if not self._maybe_save_changes():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Open survival_config.yaml", "", "YAML (*.yaml *.yml)"
        )
        if path:
            self._open_path(Path(path))

    def _open_path(self, path: Path) -> None:
        if not path.is_file():
            QMessageBox.warning(self, "No file", f"{path} does not exist.")
            return
        self._cfg = cfg_mod.load_config(path)
        self._path = path
        self._dirty = False
        self._refresh_all()

    def _save(self) -> None:
        if self._path is None:
            self._save_as()
            return
        self._collect()
        errors = cfg_mod.validate(self._cfg)
        if errors:
            ans = QMessageBox.question(
                self, "Validation warnings",
                "\n".join(errors) + "\n\nSave anyway?",
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
        cfg_mod.save_config(self._path, self._cfg)
        self._dirty = False
        self._update_status()

    def _save_as(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save config",
            str(self._path or Path.cwd() / cfg_mod.CONFIG_FILENAME),
            "YAML (*.yaml *.yml)",
        )
        if not path:
            return
        self._path = Path(path)
        self._save()

    def _maybe_save_changes(self) -> bool:
        if not self._dirty:
            return True
        ans = QMessageBox.question(
            self, "Unsaved changes",
            "Discard unsaved changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return ans == QMessageBox.StandardButton.Yes

    # ---------------------------------------------------------------- state

    def _refresh_all(self) -> None:
        g = self._cfg.get("global", {}) or {}
        self._global_tab.set_state(g)
        self._csv_wide_tab.set_state(self._cfg.get("csv_wide", {}) or {})
        self._scripts_list.clear()
        for s in (self._cfg.get("scripts") or []):
            n_steps = len(s.get("steps", []) or [])
            QListWidgetItem(f"{s.get('name', '(unnamed)')}  ({n_steps} steps)", self._scripts_list)
        self._update_preview()
        self._update_status()

    def _collect(self) -> None:
        self._cfg["global"] = self._global_tab.get_state()
        self._cfg["csv_wide"] = self._csv_wide_tab.get_state()

    def _on_changed(self) -> None:
        self._dirty = True
        self._collect()
        self._update_preview()
        self._update_status()

    def _update_preview(self) -> None:
        try:
            text = yaml.safe_dump(
                self._cfg, sort_keys=False, indent=2, default_flow_style=False
            )
        except Exception as err:  # noqa: BLE001
            text = f"# could not serialize: {err}"
        self._preview.setPlainText(text)

    def _update_status(self) -> None:
        path = str(self._path) if self._path else "(unsaved)"
        dirty = " ●" if self._dirty else ""
        self._status.setText(f"{path}{dirty}")

    # -------------------------------------------------------------- misc

    def _toggle_theme(self) -> None:
        new_mode = "light" if resolved_mode() == "dark" else "dark"
        ui_settings.set_value("theme", new_mode)
        QMessageBox.information(
            self, "Theme changed",
            "Theme preference saved. Restart the app to apply."
        )

    def _open_script_editor(self) -> None:
        if self._path is None:
            self._save_as()
            if self._path is None:
                return
        self._save()
        from ..script_editor.window import ScriptEditorWindow

        factor_names = list((self._cfg.get("global", {}) or {}).get(
            "experimental_design_factors", {}
        ).keys())
        win = ScriptEditorWindow(self._path, factors=factor_names, parent=self)
        win.scriptsSaved.connect(lambda _p: self._open_path(self._path))  # reload
        win.show()


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, ui_settings.get("theme", "auto"))
    initial = sys.argv[1] if len(sys.argv) > 1 else None
    p: Path | None = None
    if initial is not None:
        ip = Path(initial)
        if ip.is_dir():
            p = ip / cfg_mod.CONFIG_FILENAME
            if not p.is_file():
                p = None
        elif ip.is_file():
            p = ip
    win = ConfigEditorWindow(p)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
