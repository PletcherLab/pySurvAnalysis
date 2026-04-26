"""Visual Script Editor window: palette / canvas / inspector / preview."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

import yaml

from .. import scripts_io
from ..ui import ActionButton, Category, TopBar, icon, resolved_mode
from ..ui import settings as ui_settings
from .actions import ACTIONS
from .canvas import Canvas
from .inspector import Inspector
from .palette import Palette


class ScriptEditorWindow(QMainWindow):
    """Edit a project's saved scripts and write to ``survival_scripts.yaml``."""

    scriptsSaved = pyqtSignal(str)  # absolute YAML path

    def __init__(
        self,
        project_dir: str | Path,
        factors: list[str] | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("pySurvAnalysis — Script Editor")
        self.resize(1280, 780)

        self._project_dir = Path(project_dir)
        self._scripts: list[dict] = scripts_io.load_scripts(self._project_dir)
        self._active_idx = 0 if self._scripts else -1
        self._factors = list(factors or [])
        self._dirty = False

        self._build_ui()
        self._load_active_script()

    # --------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._top_bar = TopBar(f"Script Editor — {self._project_dir.name}")
        save_btn = ActionButton("Save", Category.LOAD, icon_name="save", primary=True)
        save_btn.clicked.connect(self._save)
        new_btn = ActionButton("+ New script", Category.SCRIPTS, icon_name="add")
        new_btn.clicked.connect(self._new_script)
        del_btn = ActionButton("− Delete script", Category.QC, icon_name="delete")
        del_btn.clicked.connect(self._delete_script)
        self._top_bar.add_right(new_btn)
        self._top_bar.add_right(del_btn)
        self._top_bar.add_right(save_btn)
        outer.addWidget(self._top_bar)

        # Scripts dropdown + name editor
        ctrl_row = QHBoxLayout()
        ctrl_row.setContentsMargins(12, 8, 12, 8)
        ctrl_row.addWidget(QLabel("Active script:"))
        self._scripts_combo = QComboBox()
        self._scripts_combo.setMinimumWidth(240)
        self._scripts_combo.currentIndexChanged.connect(self._on_script_selected)
        ctrl_row.addWidget(self._scripts_combo)
        rename = ActionButton("Rename…", Category.TOOLS, icon_name="config")
        rename.clicked.connect(self._rename_active)
        ctrl_row.addWidget(rename)
        ctrl_row.addStretch(1)
        outer.addLayout(ctrl_row)

        # Three-pane horizontal splitter, with preview underneath
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        v_splitter.setChildrenCollapsible(False)

        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        h_splitter.setChildrenCollapsible(False)

        self._palette = Palette(ACTIONS)
        self._palette.actionRequested.connect(self._on_action_added)
        h_splitter.addWidget(self._palette)

        self._canvas = Canvas()
        self._canvas.stepsChanged.connect(self._on_steps_changed)
        self._canvas.stepSelected.connect(self._on_step_selected)
        h_splitter.addWidget(self._canvas)

        self._inspector = Inspector(self._factors)
        self._inspector.stepEdited.connect(self._on_step_edited)
        h_splitter.addWidget(self._inspector)

        h_splitter.setSizes([240, 540, 360])
        v_splitter.addWidget(h_splitter)

        # YAML preview at bottom
        preview_host = QWidget()
        preview_lay = QVBoxLayout(preview_host)
        preview_lay.setContentsMargins(8, 4, 8, 4)
        preview_lay.addWidget(QLabel("Live YAML preview"))
        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(220)
        self._preview.setStyleSheet(
            'QPlainTextEdit { font-family: "JetBrains Mono", "Menlo", "Consolas", monospace; '
            'font-size: 10pt; }'
        )
        preview_lay.addWidget(self._preview)
        v_splitter.addWidget(preview_host)
        v_splitter.setSizes([540, 220])

        outer.addWidget(v_splitter, 1)
        self._refresh_scripts_combo()

    # -------------------------------------------------------- script ops

    def _refresh_scripts_combo(self) -> None:
        self._scripts_combo.blockSignals(True)
        self._scripts_combo.clear()
        for s in self._scripts:
            self._scripts_combo.addItem(s.get("name", "(unnamed)"))
        if self._active_idx >= 0:
            self._scripts_combo.setCurrentIndex(self._active_idx)
        self._scripts_combo.blockSignals(False)

    def _on_script_selected(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._scripts):
            return
        self._active_idx = idx
        self._load_active_script()

    def _load_active_script(self) -> None:
        if self._active_idx < 0 or self._active_idx >= len(self._scripts):
            self._canvas.set_steps([])
            self._update_preview()
            return
        script = self._scripts[self._active_idx]
        self._canvas.set_steps(list(script.get("steps") or []))
        self._update_preview()

    def _new_script(self) -> None:
        name, ok = QInputDialog.getText(self, "New script", "Name:")
        if not ok or not name.strip():
            return
        self._scripts.append({"name": name.strip(), "steps": []})
        self._active_idx = len(self._scripts) - 1
        self._dirty = True
        self._refresh_scripts_combo()
        self._load_active_script()

    def _delete_script(self) -> None:
        if self._active_idx < 0:
            return
        ans = QMessageBox.question(
            self, "Delete script",
            f"Delete '{self._scripts[self._active_idx].get('name')}'?",
        )
        if ans != QMessageBox.StandardButton.Yes:
            return
        del self._scripts[self._active_idx]
        self._active_idx = min(self._active_idx, len(self._scripts) - 1)
        self._dirty = True
        self._refresh_scripts_combo()
        self._load_active_script()

    def _rename_active(self) -> None:
        if self._active_idx < 0:
            return
        cur = self._scripts[self._active_idx].get("name", "")
        name, ok = QInputDialog.getText(self, "Rename", "Name:", text=cur)
        if not ok or not name.strip():
            return
        self._scripts[self._active_idx]["name"] = name.strip()
        self._dirty = True
        self._refresh_scripts_combo()
        self._update_preview()

    # -------------------------------------------------------- canvas/inspector

    def _on_action_added(self, action_key: str) -> None:
        if self._active_idx < 0:
            QMessageBox.information(self, "No script", "Create a script first (+ New script).")
            return
        action = ACTIONS.get(action_key)
        if action is None:
            return
        # Build a step with default param values
        step: dict = {"action": action_key}
        for spec in action.params:
            if spec.default is not None:
                step[spec.name] = spec.default
        self._canvas.append_step(step)
        self._dirty = True

    def _on_steps_changed(self, steps: list[dict]) -> None:
        if self._active_idx < 0:
            return
        self._scripts[self._active_idx]["steps"] = list(steps)
        self._dirty = True
        self._update_preview()

    def _on_step_selected(self, idx: int, step: dict) -> None:
        action = ACTIONS.get(step.get("action", "")) if step else None
        self._inspector.show_step(idx, action, step or {})

    def _on_step_edited(self, idx: int, step: dict) -> None:
        if self._active_idx < 0:
            return
        steps = list(self._scripts[self._active_idx].get("steps") or [])
        if 0 <= idx < len(steps):
            steps[idx] = step
            self._scripts[self._active_idx]["steps"] = steps
            self._canvas.set_steps(steps, keep_selection=idx)
            self._dirty = True
            self._update_preview()

    def _update_preview(self) -> None:
        scripts_view = {"scripts": self._scripts}
        try:
            text = yaml.safe_dump(scripts_view, sort_keys=False, indent=2, default_flow_style=False)
        except Exception as err:  # noqa: BLE001
            text = f"# could not serialize: {err}"
        self._preview.setPlainText(text)

    # ------------------------------------------------------------- IO

    def _save(self) -> None:
        path = scripts_io.save_scripts(self._project_dir, deepcopy(self._scripts))
        self._dirty = False
        self.scriptsSaved.emit(str(path))
        QMessageBox.information(self, "Saved", f"Wrote {len(self._scripts)} script(s) to {path}.")
