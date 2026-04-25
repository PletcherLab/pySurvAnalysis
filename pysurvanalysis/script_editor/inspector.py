"""Inspector — parameter editing form for the selected step."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .actions import Action, ParamSpec


class Inspector(QWidget):
    """Form-based editor for the selected step's parameters."""

    stepEdited = pyqtSignal(int, dict)

    def __init__(self, factors: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._factors = list(factors or [])
        self._idx: int = -1
        self._action: Action | None = None
        self._step: dict = {}
        self._widgets: dict[str, QWidget] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        outer.setSpacing(6)
        outer.addWidget(QLabel("<b>Parameters</b>"))

        self._title = QLabel("(no step selected)")
        self._title.setStyleSheet("color: palette(mid); font-style: italic;")
        outer.addWidget(self._title)

        self._desc = QLabel("")
        self._desc.setWordWrap(True)
        self._desc.setStyleSheet("color: palette(mid); font-size: 9pt;")
        outer.addWidget(self._desc)

        self._form_host = QWidget()
        self._form = QFormLayout(self._form_host)
        outer.addWidget(self._form_host, 1)

    def show_step(self, idx: int, action: Action | None, step: dict) -> None:
        self._idx = idx
        self._action = action
        self._step = dict(step)
        self._clear_form()
        if action is None:
            self._title.setText("(no step selected)")
            self._desc.setText("")
            return
        self._title.setText(f"<b>{action.title}</b>")
        self._desc.setText(action.description)
        for spec in action.params:
            widget, getter = self._build_widget(spec, step.get(spec.name, spec.default))
            self._widgets[spec.name] = widget
            self._form.addRow(spec.label + ":", widget)
            if spec.help:
                widget.setToolTip(spec.help)
            self._wire_change(widget)
        self._update_enabled_states()

    def _clear_form(self) -> None:
        while self._form.rowCount():
            self._form.removeRow(0)
        self._widgets.clear()

    def _build_widget(self, spec: ParamSpec, value: Any) -> tuple[QWidget, Any]:
        kind = spec.kind
        if kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(value) if value is not None else bool(spec.default))
            return w, lambda: w.isChecked()
        if kind == "int":
            w = QSpinBox()
            w.setRange(int(spec.min if spec.min is not None else -10_000_000),
                       int(spec.max if spec.max is not None else 10_000_000))
            try:
                w.setValue(int(value if value is not None else (spec.default or 0)))
            except (TypeError, ValueError):
                w.setValue(0)
            return w, lambda: w.value()
        if kind == "float":
            w = QDoubleSpinBox()
            w.setDecimals(3)
            w.setRange(float(spec.min if spec.min is not None else -1e9),
                       float(spec.max if spec.max is not None else 1e9))
            try:
                w.setValue(float(value if value is not None else (spec.default or 0.0)))
            except (TypeError, ValueError):
                w.setValue(0.0)
            return w, lambda: w.value()
        if kind == "choice":
            w = QComboBox()
            for c in (spec.choices or ()):
                w.addItem(str(c))
            if value is not None:
                idx = w.findText(str(value))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            return w, lambda: w.currentText()
        if kind == "factor":
            w = QComboBox()
            w.addItem("")
            for f in self._factors:
                w.addItem(f)
            if value is not None:
                idx = w.findText(str(value))
                if idx >= 0:
                    w.setCurrentIndex(idx)
            return w, lambda: w.currentText()
        if kind == "factors":
            w = QLineEdit()
            if isinstance(value, (list, tuple)):
                w.setText(", ".join(str(v) for v in value))
            elif value is not None:
                w.setText(str(value))
            w.setPlaceholderText(", ".join(self._factors))
            return w, lambda: [
                p.strip() for p in w.text().split(",") if p.strip()
            ]
        if kind == "list":
            w = QLineEdit()
            if isinstance(value, (list, tuple)):
                w.setText(", ".join(str(v) for v in value))
            elif value is not None:
                w.setText(str(value))
            return w, lambda: [
                p.strip() for p in w.text().split(",") if p.strip()
            ]
        if kind == "path":
            host = QWidget()
            row = QHBoxLayout(host)
            row.setContentsMargins(0, 0, 0, 0)
            edit = QLineEdit()
            if value is not None:
                edit.setText(str(value))
            browse = QPushButton("…")
            browse.setMaximumWidth(28)

            def _pick():
                p = QFileDialog.getExistingDirectory(self, spec.label)
                if p:
                    edit.setText(p)

            browse.clicked.connect(_pick)
            row.addWidget(edit, 1)
            row.addWidget(browse)
            host._edit = edit  # type: ignore[attr-defined]
            return host, lambda: edit.text()
        # default: string
        w = QLineEdit()
        if value is not None:
            w.setText(str(value))
        return w, lambda: w.text()

    def _wire_change(self, w: QWidget) -> None:
        if isinstance(w, QCheckBox):
            w.toggled.connect(self._emit_change)
        elif isinstance(w, (QSpinBox, QDoubleSpinBox)):
            w.valueChanged.connect(self._emit_change)
        elif isinstance(w, QComboBox):
            w.currentTextChanged.connect(self._emit_change)
        elif isinstance(w, QLineEdit):
            w.textChanged.connect(self._emit_change)
        else:
            edit = getattr(w, "_edit", None)
            if isinstance(edit, QLineEdit):
                edit.textChanged.connect(self._emit_change)

    def _collect(self) -> dict:
        if self._action is None:
            return dict(self._step)
        out: dict = {"action": self._action.key}
        for spec in self._action.params:
            w = self._widgets.get(spec.name)
            if w is None:
                continue
            value = self._read_widget(w)
            if value is None or value == "" or value == []:
                # don't write empty defaults — keeps YAML clean
                continue
            out[spec.name] = value
        return out

    def _read_widget(self, w: QWidget) -> Any:
        if isinstance(w, QCheckBox):
            return w.isChecked()
        if isinstance(w, QSpinBox):
            return w.value()
        if isinstance(w, QDoubleSpinBox):
            return w.value()
        if isinstance(w, QComboBox):
            return w.currentText()
        if isinstance(w, QLineEdit):
            text = w.text()
            return text
        edit = getattr(w, "_edit", None)
        if isinstance(edit, QLineEdit):
            return edit.text()
        return None

    def _emit_change(self) -> None:
        if self._action is None or self._idx < 0:
            return
        # Re-coerce list-style params
        out = self._collect()
        for spec in self._action.params:
            if spec.kind in ("factors", "list"):
                w = self._widgets.get(spec.name)
                if isinstance(w, QLineEdit):
                    parts = [p.strip() for p in w.text().split(",") if p.strip()]
                    if parts:
                        out[spec.name] = parts
                    elif spec.name in out:
                        out.pop(spec.name)
        self._update_enabled_states()
        self.stepEdited.emit(self._idx, out)

    def _update_enabled_states(self) -> None:
        if self._action is None:
            return
        for spec in self._action.params:
            if not spec.enabled_when:
                continue
            ctrl = self._widgets.get(spec.enabled_when)
            target = self._widgets.get(spec.name)
            if isinstance(ctrl, QCheckBox) and target is not None:
                target.setEnabled(ctrl.isChecked())
