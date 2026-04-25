"""Tabs for the visual Config Editor.

Each tab is a self-contained widget that reads/writes a slice of the
``survival_config.yaml`` document via :func:`get_state` / :func:`set_state`.
The parent :class:`ConfigEditorWindow` glues them together with a live
YAML preview pane.
"""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import config as cfg_mod


def _parse_csv_list(text: str) -> list[str]:
    return [p.strip() for p in text.split(",") if p.strip()]


def _format_csv_list(values: list | None) -> str:
    if not values:
        return ""
    return ", ".join(str(v) for v in values)


# ---------------------------------------------------------------------------
# GlobalTab
# ---------------------------------------------------------------------------

class GlobalTab(QWidget):
    """Edits ``cfg["global"]``."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        form = QFormLayout()

        self._fmt = QComboBox()
        self._fmt.addItems(list(cfg_mod.INPUT_FORMATS))
        self._fmt.currentTextChanged.connect(lambda _v: self.changed.emit())
        form.addRow("Input format:", self._fmt)

        self._time_col = QLineEdit()
        self._time_col.textChanged.connect(lambda _v: self.changed.emit())
        form.addRow("Time column:", self._time_col)

        self._event_col = QLineEdit()
        self._event_col.textChanged.connect(lambda _v: self.changed.emit())
        form.addRow("Event column:", self._event_col)

        self._factor_cols = QLineEdit()
        self._factor_cols.setPlaceholderText("blank → auto-detect (CSV long)")
        self._factor_cols.textChanged.connect(lambda _v: self.changed.emit())
        form.addRow("Factor columns (CSV long):", self._factor_cols)

        self._tau = QDoubleSpinBox()
        self._tau.setRange(0.0, 1e6)
        self._tau.setDecimals(1)
        self._tau.setSpecialValueText("auto")
        self._tau.valueChanged.connect(lambda _v: self.changed.emit())
        form.addRow("RMST τ (hours):", self._tau)

        self._alpha = QDoubleSpinBox()
        self._alpha.setRange(0.001, 0.5)
        self._alpha.setDecimals(3)
        self._alpha.setSingleStep(0.005)
        self._alpha.valueChanged.connect(lambda _v: self.changed.emit())
        form.addRow("Significance α:", self._alpha)

        self._default_group = QLineEdit()
        self._default_group.textChanged.connect(lambda _v: self.changed.emit())
        form.addRow("Default exclusion group:", self._default_group)

        self._assume_censored = QCheckBox("Assume censored at last census time (Excel)")
        self._assume_censored.toggled.connect(lambda _v: self.changed.emit())
        form.addRow("", self._assume_censored)

        outer.addLayout(form)

        # Experimental design factors → simple table
        outer.addWidget(QLabel("Experimental design factors  (factor → comma-separated levels)"))
        self._factors_table = QTableWidget(0, 2)
        self._factors_table.setHorizontalHeaderLabels(["Factor", "Levels (comma-separated)"])
        self._factors_table.horizontalHeader().setStretchLastSection(True)
        self._factors_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._factors_table.itemChanged.connect(lambda _i: self.changed.emit())
        outer.addWidget(self._factors_table)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("+ Factor")
        add_btn.clicked.connect(self._add_factor_row)
        rm_btn = QPushButton("− Selected")
        rm_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(add_btn)
        btn_row.addWidget(rm_btn)
        btn_row.addStretch(1)
        outer.addLayout(btn_row)

    def _add_factor_row(self) -> None:
        r = self._factors_table.rowCount()
        self._factors_table.insertRow(r)
        self._factors_table.setItem(r, 0, QTableWidgetItem(""))
        self._factors_table.setItem(r, 1, QTableWidgetItem(""))
        self.changed.emit()

    def _remove_selected(self) -> None:
        rows = sorted({i.row() for i in self._factors_table.selectedItems()}, reverse=True)
        for r in rows:
            self._factors_table.removeRow(r)
        if rows:
            self.changed.emit()

    def get_state(self) -> dict[str, Any]:
        factor_cols_txt = self._factor_cols.text().strip()
        factor_cols = _parse_csv_list(factor_cols_txt) if factor_cols_txt else None

        edf: dict[str, list[str]] = {}
        for r in range(self._factors_table.rowCount()):
            name_item = self._factors_table.item(r, 0)
            levels_item = self._factors_table.item(r, 1)
            name = (name_item.text() if name_item else "").strip()
            levels = _parse_csv_list(levels_item.text() if levels_item else "")
            if name:
                edf[name] = levels

        tau_val: float | None = None if self._tau.value() == 0.0 else float(self._tau.value())

        return {
            "input_format": self._fmt.currentText(),
            "time_col": self._time_col.text().strip() or "Age",
            "event_col": self._event_col.text().strip() or "Event",
            "factor_cols": factor_cols,
            "rmst_tau": tau_val,
            "alpha": float(self._alpha.value()),
            "default_exclusion_group": self._default_group.text().strip() or "default",
            "assume_censored": self._assume_censored.isChecked(),
            "experimental_design_factors": edf,
        }

    def set_state(self, g: dict[str, Any]) -> None:
        self.blockSignals(True)
        try:
            fmt = g.get("input_format", "excel")
            idx = self._fmt.findText(fmt)
            if idx >= 0:
                self._fmt.setCurrentIndex(idx)
            self._time_col.setText(str(g.get("time_col", "Age")))
            self._event_col.setText(str(g.get("event_col", "Event")))
            self._factor_cols.setText(_format_csv_list(g.get("factor_cols")))
            tau = g.get("rmst_tau") or 0.0
            try:
                self._tau.setValue(float(tau or 0.0))
            except (TypeError, ValueError):
                self._tau.setValue(0.0)
            try:
                self._alpha.setValue(float(g.get("alpha", 0.05)))
            except (TypeError, ValueError):
                self._alpha.setValue(0.05)
            self._default_group.setText(str(g.get("default_exclusion_group", "default")))
            self._assume_censored.setChecked(bool(g.get("assume_censored", True)))

            self._factors_table.setRowCount(0)
            edf = g.get("experimental_design_factors") or {}
            for name, levels in edf.items():
                r = self._factors_table.rowCount()
                self._factors_table.insertRow(r)
                self._factors_table.setItem(r, 0, QTableWidgetItem(str(name)))
                self._factors_table.setItem(r, 1, QTableWidgetItem(_format_csv_list(levels)))
        finally:
            self.blockSignals(False)


# ---------------------------------------------------------------------------
# CsvWideTab
# ---------------------------------------------------------------------------

class CsvWideTab(QWidget):
    """Edits ``cfg["csv_wide"]`` — only relevant when format == csv_wide."""

    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(12, 12, 12, 12)
        outer.setSpacing(10)

        form = QFormLayout()
        self._factor_names = QLineEdit()
        self._factor_names.setPlaceholderText("e.g. Sex, Diet")
        self._factor_names.textChanged.connect(lambda _v: self.changed.emit())
        form.addRow("Factor names:", self._factor_names)
        outer.addLayout(form)

        outer.addWidget(QLabel("Factor levels  (factor → comma-separated levels)"))
        self._levels_table = QTableWidget(0, 2)
        self._levels_table.setHorizontalHeaderLabels(["Factor", "Levels"])
        self._levels_table.horizontalHeader().setStretchLastSection(True)
        self._levels_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self._levels_table.itemChanged.connect(lambda _i: self.changed.emit())
        outer.addWidget(self._levels_table)

        levels_btn_row = QHBoxLayout()
        add_lvl = QPushButton("+ Factor row")
        add_lvl.clicked.connect(self._add_lvl_row)
        rm_lvl = QPushButton("− Selected")
        rm_lvl.clicked.connect(self._remove_selected_lvl)
        levels_btn_row.addWidget(add_lvl)
        levels_btn_row.addWidget(rm_lvl)
        levels_btn_row.addStretch(1)
        outer.addLayout(levels_btn_row)

        outer.addWidget(QLabel(
            "Column mapping  (one row per CSV column → factor levels + event flag)"
        ))
        self._mapping_table = QTableWidget(0, 3)
        self._mapping_table.setHorizontalHeaderLabels(["Column name", "Factor=Level pairs", "Event (0/1)"])
        self._mapping_table.horizontalHeader().setStretchLastSection(False)
        self._mapping_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._mapping_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._mapping_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._mapping_table.itemChanged.connect(lambda _i: self.changed.emit())
        outer.addWidget(self._mapping_table)

        map_btn_row = QHBoxLayout()
        add_map = QPushButton("+ Mapping row")
        add_map.clicked.connect(self._add_map_row)
        rm_map = QPushButton("− Selected")
        rm_map.clicked.connect(self._remove_selected_map)
        map_btn_row.addWidget(add_map)
        map_btn_row.addWidget(rm_map)
        map_btn_row.addStretch(1)
        outer.addLayout(map_btn_row)

    def _add_lvl_row(self) -> None:
        r = self._levels_table.rowCount()
        self._levels_table.insertRow(r)
        self._levels_table.setItem(r, 0, QTableWidgetItem(""))
        self._levels_table.setItem(r, 1, QTableWidgetItem(""))
        self.changed.emit()

    def _remove_selected_lvl(self) -> None:
        rows = sorted({i.row() for i in self._levels_table.selectedItems()}, reverse=True)
        for r in rows:
            self._levels_table.removeRow(r)
        if rows:
            self.changed.emit()

    def _add_map_row(self) -> None:
        r = self._mapping_table.rowCount()
        self._mapping_table.insertRow(r)
        for c in range(3):
            self._mapping_table.setItem(r, c, QTableWidgetItem(""))
        self.changed.emit()

    def _remove_selected_map(self) -> None:
        rows = sorted({i.row() for i in self._mapping_table.selectedItems()}, reverse=True)
        for r in rows:
            self._mapping_table.removeRow(r)
        if rows:
            self.changed.emit()

    def get_state(self) -> dict[str, Any]:
        factor_names = _parse_csv_list(self._factor_names.text())

        factor_levels: dict[str, list[str]] = {}
        for r in range(self._levels_table.rowCount()):
            name = (self._levels_table.item(r, 0).text() if self._levels_table.item(r, 0) else "").strip()
            levels = _parse_csv_list(self._levels_table.item(r, 1).text() if self._levels_table.item(r, 1) else "")
            if name:
                factor_levels[name] = levels

        col_mapping: list[dict] = []
        for r in range(self._mapping_table.rowCount()):
            col = (self._mapping_table.item(r, 0).text() if self._mapping_table.item(r, 0) else "").strip()
            pairs_text = (self._mapping_table.item(r, 1).text() if self._mapping_table.item(r, 1) else "").strip()
            event_text = (self._mapping_table.item(r, 2).text() if self._mapping_table.item(r, 2) else "").strip()
            if not col:
                continue
            factors = {}
            for pair in _parse_csv_list(pairs_text):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    factors[k.strip()] = v.strip()
            try:
                event_val = int(event_text)
            except (TypeError, ValueError):
                event_val = 1
            col_mapping.append({"col": col, "factors": factors, "event": event_val})

        return {
            "factor_names": factor_names,
            "factor_levels": factor_levels,
            "col_mapping": col_mapping,
        }

    def set_state(self, cw: dict[str, Any]) -> None:
        self.blockSignals(True)
        try:
            self._factor_names.setText(_format_csv_list(cw.get("factor_names")))

            self._levels_table.setRowCount(0)
            for name, levels in (cw.get("factor_levels") or {}).items():
                r = self._levels_table.rowCount()
                self._levels_table.insertRow(r)
                self._levels_table.setItem(r, 0, QTableWidgetItem(str(name)))
                self._levels_table.setItem(r, 1, QTableWidgetItem(_format_csv_list(levels)))

            self._mapping_table.setRowCount(0)
            for entry in (cw.get("col_mapping") or []):
                r = self._mapping_table.rowCount()
                self._mapping_table.insertRow(r)
                self._mapping_table.setItem(r, 0, QTableWidgetItem(str(entry.get("col", ""))))
                pairs = ", ".join(
                    f"{k}={v}" for k, v in (entry.get("factors") or {}).items()
                )
                self._mapping_table.setItem(r, 1, QTableWidgetItem(pairs))
                self._mapping_table.setItem(r, 2, QTableWidgetItem(str(entry.get("event", 1))))
        finally:
            self.blockSignals(False)
