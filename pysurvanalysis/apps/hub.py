"""Analysis Hub — main entry point for pySurvAnalysis.

Loads survival data, exposes every analysis and plot in the library as
category-coloured buttons, routes figures and stdout to a tabbed
:class:`PlotDock`, and launches the Config Editor and QC Viewer in their
own subprocesses.

Modelled on PyTrackingAnalysis's ``apps/hub.py`` and pyflic's
``base/analysis_hub.py``; see :doc:`the plan file </doc>` for the
card-by-card layout.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # noqa: E402

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSplitter,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import (
    config as cfg_mod,
    data_loader,
    exclusions,
    lifetable,
    plotting,
    report,
    statistics,
)
from ..pipeline import run_analysis
from ..ui import (
    ActionButton,
    Card,
    Category,
    OutputLog,
    PlotDock,
    SidebarNav,
    TopBar,
    ZoomableImageView,
    ZoomableTextView,
    apply_theme,
    icon,
    resolved_mode,
)
from ..ui import settings as ui_settings
from .common import TaskWorker

_SAVED_RE = re.compile(r"^\s*Saved:\s+(\S.*?)\s*$")


def _wrap_layout(layout) -> QWidget:
    host = QWidget()
    host.setLayout(layout)
    return host


class HubWindow(QMainWindow):
    """The Analysis Hub main window."""

    def __init__(self, initial_project: str | None = None) -> None:
        super().__init__()
        self.setWindowTitle("pySurvAnalysis — Analysis Hub")
        self.resize(1350, 860)
        self.setAcceptDrops(True)

        self._project_dir: Path | None = None
        self._data = None  # individual-level DataFrame
        self._factors: list[str] = []
        self._lifetables = None  # cached
        self._cfg: dict = cfg_mod.default_config()
        self._cfg_path: Path | None = None
        self._worker: TaskWorker | None = None
        self._cards: dict[str, Card] = {}
        self._factor_checks: dict[str, QCheckBox] = {}
        self._artifact_tabs: dict[str, QWidget] = {}

        self._build_ui()

        if initial_project:
            self._set_project_dir(initial_project)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._top_bar = TopBar("pySurvAnalysis — Analysis Hub")
        self._interactive_checkbox = QCheckBox("Interactive plots")
        self._interactive_checkbox.setChecked(bool(ui_settings.get("interactive_plots", False)))
        self._interactive_checkbox.toggled.connect(
            lambda v: ui_settings.set_value("interactive_plots", bool(v))
        )
        self._interactive_checkbox.setToolTip(
            "When checked, plot tabs use a live matplotlib canvas with zoom/pan "
            "toolbar and hover tooltips. Off (default): plots render as static "
            "PNGs (faster)."
        )
        self._top_bar.add_right(self._interactive_checkbox)
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

        left_host = QWidget()
        left_lay = QHBoxLayout(left_host)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        self._sidebar = SidebarNav()
        self._sidebar.add_item("project", "Project", "project", category=Category.NEUTRAL)
        self._sidebar.add_item("load", "Load", "load", category=Category.LOAD)
        self._sidebar.add_item("analyze", "Analyze", "logrank", category=Category.ANALYZE)
        self._sidebar.add_item("plots", "Plots", "plots", category=Category.PLOTS)
        self._sidebar.add_item("scripts", "Scripts", "scripts", category=Category.SCRIPTS)
        self._sidebar.add_item("tools", "Tools", "tools", category=Category.TOOLS)
        self._sidebar.add_stretch()
        self._sidebar.itemSelected.connect(self._scroll_to_card)
        left_lay.addWidget(self._sidebar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)
        cards_host = QWidget()
        self._cards_lay = QVBoxLayout(cards_host)
        self._cards_lay.setContentsMargins(12, 12, 12, 12)
        self._cards_lay.setSpacing(12)

        self._build_project_card()
        self._build_load_card()
        self._build_analyze_card()
        self._build_plots_card()
        self._build_scripts_card()
        self._build_tools_card()
        self._cards_lay.addStretch(1)

        scroll.setWidget(cards_host)
        self._cards_scroll = scroll
        left_lay.addWidget(scroll, 1)
        left_host.setMinimumWidth(620)
        splitter.addWidget(left_host)

        self._log = OutputLog()
        self._plot_dock = PlotDock(self._log)
        self._plot_dock.setMinimumWidth(440)
        splitter.addWidget(self._plot_dock)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([640, 740])
        outer.addWidget(splitter, 1)

        self._progress = QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setVisible(False)
        self._progress.setFixedHeight(4)
        outer.addWidget(self._progress)

        self._log.append_line(
            "Welcome to pySurvAnalysis. Pick a project directory under "
            "Project → Browse, then click 'Load data' on the Load card."
        )

    # -------- card: Project --------

    def _build_project_card(self) -> None:
        card = Card(
            "Project",
            category=Category.LOAD,
            subtitle="Pick the experiment folder, choose its config, and pick an exclusion group.",
            icon_name="project",
        )
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)

        self._project_edit = QLineEdit()
        self._project_edit.setPlaceholderText("/path/to/experiment/folder")
        self._project_edit.setReadOnly(True)
        browse = ActionButton("Browse…", Category.NEUTRAL, icon_name="browse")
        browse.clicked.connect(self._pick_project_dir)
        recent_btn = ActionButton("Recent…", Category.NEUTRAL, icon_name="menu")
        recent_btn.clicked.connect(self._show_recent_menu)
        proj_col = QVBoxLayout()
        proj_col.setContentsMargins(0, 0, 0, 0)
        proj_col.setSpacing(6)
        proj_col.addWidget(self._project_edit)
        btn_row = QHBoxLayout()
        btn_row.addWidget(browse)
        btn_row.addWidget(recent_btn)
        btn_row.addStretch(1)
        proj_col.addLayout(btn_row)
        form.addRow("Project dir:", _wrap_layout(proj_col))

        self._config_combo = QComboBox()
        self._config_combo.setToolTip("YAML configs found in the project dir.")
        self._config_combo.currentTextChanged.connect(self._on_config_changed)
        form.addRow("Config:", self._config_combo)

        self._group_combo = QComboBox()
        self._group_combo.setEditable(True)
        self._group_combo.setToolTip(
            "Active exclusion group from remove_chambers.csv. The chambers in "
            "this group are excluded from every analysis."
        )
        form.addRow("Exclusion group:", self._group_combo)

        card.add_body(form)

        launchers = QHBoxLayout()
        edit_cfg = ActionButton("Edit config…", Category.TOOLS, icon_name="config")
        edit_cfg.clicked.connect(lambda: self._launch_subapp("config"))
        qc_view = ActionButton("QC viewer…", Category.QC, icon_name="qc")
        qc_view.clicked.connect(lambda: self._launch_subapp("qc"))
        launchers.addWidget(edit_cfg)
        launchers.addWidget(qc_view)
        launchers.addStretch(1)
        card.add_body(launchers)

        self._cards["project"] = card
        self._cards_lay.addWidget(card)

    # -------- card: Load --------

    def _build_load_card(self) -> None:
        card = Card(
            "Load",
            category=Category.LOAD,
            subtitle="Excel (.xlsx, DLife), CSV long, or CSV wide.",
            icon_name="load",
        )
        self._fmt_excel = QRadioButton("Excel (.xlsx)")
        self._fmt_long = QRadioButton("CSV long")
        self._fmt_wide = QRadioButton("CSV wide")
        self._fmt_excel.setChecked(True)
        grp = QButtonGroup(self)
        grp.addButton(self._fmt_excel)
        grp.addButton(self._fmt_long)
        grp.addButton(self._fmt_wide)
        fmt_row = QHBoxLayout()
        fmt_row.addWidget(self._fmt_excel)
        fmt_row.addWidget(self._fmt_long)
        fmt_row.addWidget(self._fmt_wide)
        fmt_row.addStretch(1)
        card.add_body(fmt_row)

        self._assume_censored = QCheckBox("Assume censored at last census (Excel)")
        self._assume_censored.setChecked(True)
        card.add_body(self._assume_censored)

        load_btn = ActionButton(
            "Load data", Category.LOAD, icon_name="load", primary=True
        )
        load_btn.clicked.connect(self._load_data)
        reload_btn = ActionButton("Reload", Category.TOOLS, icon_name="refresh")
        reload_btn.clicked.connect(self._load_data)
        row = QHBoxLayout()
        row.addWidget(load_btn)
        row.addWidget(reload_btn)
        card.add_body(row)

        self._dataset_summary = QLabel("(no data loaded)")
        self._dataset_summary.setStyleSheet("color: palette(mid); font-style: italic;")
        self._dataset_summary.setWordWrap(True)
        card.add_body(self._dataset_summary)

        self._cards["load"] = card
        self._cards_lay.addWidget(card)

    # -------- card: Analyze --------

    def _build_analyze_card(self) -> None:
        card = Card(
            "Analyze",
            category=Category.ANALYZE,
            subtitle="Pick factors, then run the test or model.",
            icon_name="logrank",
        )
        card.add_section_label("FACTORS")
        self._factors_host = QWidget()
        self._factors_lay = QVBoxLayout(self._factors_host)
        self._factors_lay.setContentsMargins(0, 0, 0, 0)
        self._factors_lay.setSpacing(2)
        self._factors_placeholder = QLabel("Load data to see factors.")
        self._factors_placeholder.setStyleSheet("color: palette(mid); font-style: italic;")
        self._factors_lay.addWidget(self._factors_placeholder)
        card.add_body(self._factors_host)

        self._interactions_check = QCheckBox("Include interactions")
        self._interactions_check.setChecked(True)
        self._interactions_check.setToolTip(
            "When checked, Cox PH and RMST run the full factorial model with "
            "all pairwise interaction terms. Off: main-effects only."
        )
        card.add_body(self._interactions_check)

        tau_row = QHBoxLayout()
        tau_row.addWidget(QLabel("RMST τ (hours, 0 = auto):"))
        self._tau_spin = QDoubleSpinBox()
        self._tau_spin.setRange(0.0, 1e6)
        self._tau_spin.setDecimals(1)
        self._tau_spin.setSingleStep(24)
        self._tau_spin.setValue(0.0)
        tau_row.addWidget(self._tau_spin)
        tau_row.addStretch(1)
        card.add_body(tau_row)

        card.add_section_label("STATISTICS")
        for label, fn in (
            ("Log-rank pairwise", self._action_logrank_pairwise),
            ("Log-rank omnibus", self._action_logrank_omnibus),
            ("Gehan-Wilcoxon pairwise", self._action_gehan_wilcoxon),
            ("Hazard ratios (pairwise)", self._action_hazard_ratios),
            ("Cox PH (interactions)", self._action_cox_ph),
            ("RMST regression", self._action_rmst),
            ("Parametric AFT models", self._action_parametric),
        ):
            btn = ActionButton(label, Category.ANALYZE, icon_name="logrank")
            btn.clicked.connect(fn)
            card.add_body(btn)

        card.add_section_label("PIPELINE")
        full_btn = ActionButton(
            "Run full pipeline (writes report.md)",
            Category.ANALYZE,
            icon_name="report",
            primary=True,
        )
        full_btn.clicked.connect(self._action_full_pipeline)
        card.add_body(full_btn)

        self._cards["analyze"] = card
        self._cards_lay.addWidget(card)

    # -------- card: Plots --------

    def _build_plots_card(self) -> None:
        card = Card(
            "Plots",
            category=Category.PLOTS,
            subtitle="Figures appear as tabs on the right.",
            icon_name="plots",
        )
        for label, fn, ic in (
            ("KM curves", self._action_plot_km, "km"),
            ("KM + risk table", self._action_plot_km_risk, "risk"),
            ("Nelson-Aalen", self._action_plot_nelson_aalen, "hazard"),
            ("Hazard rate", self._action_plot_hazard, "hazard"),
            ("Smoothed hazard", self._action_plot_smoothed_hazard, "hazard"),
            ("Mortality (qx)", self._action_plot_mortality, "plot"),
            ("Number at risk", self._action_plot_number_at_risk, "plot"),
            ("Cumulative events", self._action_plot_cumulative, "plot"),
            ("Hazard ratio forest", self._action_plot_forest, "forest"),
            ("Survival distribution", self._action_plot_distribution, "plot"),
            ("Log-log diagnostic", self._action_plot_log_log, "plot"),
        ):
            btn = ActionButton(label, Category.PLOTS, icon_name=ic)
            btn.clicked.connect(fn)
            card.add_body(btn)
        self._cards["plots"] = card
        self._cards_lay.addWidget(card)

    # -------- card: Scripts --------

    def _build_scripts_card(self) -> None:
        card = Card(
            "Scripts",
            category=Category.SCRIPTS,
            subtitle="Saved analysis pipelines from the active config.",
            icon_name="scripts",
        )
        self._scripts_list = QListWidget()
        self._scripts_list.setMinimumHeight(80)
        self._scripts_list.itemDoubleClicked.connect(
            lambda _item: self._run_selected_script()
        )
        card.add_body(self._scripts_list)

        row = QHBoxLayout()
        run_btn = ActionButton("Run selected", Category.SCRIPTS, icon_name="play", primary=True)
        run_btn.clicked.connect(self._run_selected_script)
        edit_btn = ActionButton("Open Script Editor…", Category.SCRIPTS, icon_name="scripts")
        edit_btn.clicked.connect(self._open_script_editor)
        row.addWidget(run_btn)
        row.addWidget(edit_btn)
        card.add_body(row)
        self._cards["scripts"] = card
        self._cards_lay.addWidget(card)

    # -------- card: Tools --------

    def _build_tools_card(self) -> None:
        card = Card(
            "Tools",
            category=Category.TOOLS,
            subtitle="Reports, exports, settings.",
            icon_name="tools",
        )
        for label, fn, ic in (
            ("Generate report.md", self._action_generate_report, "report"),
            ("Open output directory", self._action_open_output_dir, "open"),
            ("Clear plot tabs", self._action_clear_tabs, "clear"),
        ):
            btn = ActionButton(label, Category.TOOLS, icon_name=ic)
            btn.clicked.connect(fn)
            card.add_body(btn)
        self._cards["tools"] = card
        self._cards_lay.addWidget(card)

    # ------------------------------------------------------------ helpers

    def _scroll_to_card(self, key: str) -> None:
        card = self._cards.get(key)
        if card is None:
            return
        self._cards_scroll.ensureWidgetVisible(card, 0, 16)

    def _toggle_theme(self) -> None:
        new_mode = "light" if resolved_mode() == "dark" else "dark"
        ui_settings.set_value("theme", new_mode)
        QMessageBox.information(
            self,
            "Theme changed",
            "Theme preference saved. Restart the Hub to apply the new theme.",
        )

    def _show_recent_menu(self) -> None:
        recents = ui_settings.get("recent_projects", []) or []
        menu = QMenu(self)
        if not recents:
            act = QAction("(no recent projects)", self)
            act.setEnabled(False)
            menu.addAction(act)
        else:
            for path in recents:
                act = QAction(path, self)
                act.triggered.connect(lambda _checked, p=path: self._set_project_dir(p))
                menu.addAction(act)
        menu.exec(self.cursor().pos())

    def _pick_project_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Pick project directory")
        if path:
            self._set_project_dir(path)

    def _set_project_dir(self, path: str | Path) -> None:
        p = Path(path).expanduser().resolve()
        if not p.is_dir():
            QMessageBox.warning(self, "Not a directory", f"{p} is not a directory.")
            return
        self._project_dir = p
        self._project_edit.setText(str(p))
        ui_settings.add_recent_project(p)
        self._refresh_config_combo()
        self._refresh_group_combo()
        self._refresh_scripts_list()
        self._log.append_line(f"\nProject: {p}")

    def _refresh_config_combo(self) -> None:
        self._config_combo.blockSignals(True)
        self._config_combo.clear()
        if self._project_dir is None:
            self._config_combo.blockSignals(False)
            return
        configs = cfg_mod.list_yaml_configs(self._project_dir)
        if configs:
            for c in configs:
                self._config_combo.addItem(c.name)
            preferred = cfg_mod.CONFIG_FILENAME
            idx = self._config_combo.findText(preferred)
            if idx >= 0:
                self._config_combo.setCurrentIndex(idx)
        else:
            self._config_combo.addItem("(none — using defaults)")
        self._config_combo.blockSignals(False)
        self._on_config_changed(self._config_combo.currentText())

    def _on_config_changed(self, name: str) -> None:
        if self._project_dir is None or not name or name.startswith("(none"):
            self._cfg = cfg_mod.default_config()
            self._cfg_path = None
        else:
            self._cfg_path = self._project_dir / name
            self._cfg = cfg_mod.load_config(self._cfg_path)
            self._log.append_line(f"Loaded config: {self._cfg_path}")
        # Apply config defaults to the Load card
        fmt = (self._cfg.get("global", {}) or {}).get("input_format", "excel")
        if fmt == "csv_long":
            self._fmt_long.setChecked(True)
        elif fmt == "csv_wide":
            self._fmt_wide.setChecked(True)
        else:
            self._fmt_excel.setChecked(True)
        self._assume_censored.setChecked(
            bool((self._cfg.get("global", {}) or {}).get("assume_censored", True))
        )
        tau = (self._cfg.get("global", {}) or {}).get("rmst_tau") or 0.0
        try:
            self._tau_spin.setValue(float(tau or 0.0))
        except (TypeError, ValueError):
            self._tau_spin.setValue(0.0)
        # Default exclusion group
        default_grp = (self._cfg.get("global", {}) or {}).get("default_exclusion_group", "default")
        idx = self._group_combo.findText(default_grp)
        if idx >= 0:
            self._group_combo.setCurrentIndex(idx)
        else:
            self._group_combo.setEditText(default_grp)
        self._refresh_scripts_list()

    def _refresh_group_combo(self) -> None:
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        if self._project_dir is not None:
            groups = exclusions.list_groups(self._project_dir)
            for g in groups:
                self._group_combo.addItem(g)
            if not groups:
                self._group_combo.addItem("default")
        self._group_combo.blockSignals(False)

    def _refresh_scripts_list(self) -> None:
        self._scripts_list.clear()
        scripts = (self._cfg or {}).get("scripts") or []
        for s in scripts:
            name = str(s.get("name", "(unnamed)"))
            n_steps = len(s.get("steps", []) or [])
            QListWidgetItem(f"{name}  ({n_steps} steps)", self._scripts_list)

    # ------------------------------------------------------------ load/run

    def _selected_format(self) -> str:
        if self._fmt_long.isChecked():
            return "csv_long"
        if self._fmt_wide.isChecked():
            return "csv_wide"
        return "excel"

    def _resolve_input_path(self) -> Path | None:
        if self._project_dir is None:
            QMessageBox.warning(self, "No project", "Pick a project directory first.")
            return None
        fmt = self._selected_format()
        if fmt == "excel":
            xlsx = list(self._project_dir.glob("*.xlsx"))
            if not xlsx:
                QMessageBox.warning(self, "No .xlsx", "No .xlsx file found in the project dir.")
                return None
            if len(xlsx) > 1:
                QMessageBox.warning(
                    self, "Multiple .xlsx",
                    f"Found {len(xlsx)} .xlsx files; place exactly one in the project dir.",
                )
                return None
            return xlsx[0]
        # CSV long/wide: pick first .csv or .tsv
        for ext in ("*.csv", "*.tsv"):
            files = list(self._project_dir.glob(ext))
            if files:
                return files[0]
        QMessageBox.warning(self, "No CSV", "No .csv or .tsv file found in the project dir.")
        return None

    def _excluded_set(self) -> set:
        if self._project_dir is None:
            return set()
        group = self._group_combo.currentText().strip() or "default"
        return exclusions.chambers_for_group(self._project_dir, group)

    def _load_data(self) -> None:
        path = self._resolve_input_path()
        if path is None:
            return
        fmt = self._selected_format()
        g = self._cfg.get("global", {}) or {}
        cw = self._cfg.get("csv_wide", {}) or {}
        excluded = self._excluded_set()
        excel_excluded = (
            data_loader.load_chamber_flags(path)
            if path.suffix.lower() == ".xlsx" else set()
        )
        merged_excluded = excluded | excel_excluded

        kwargs = dict(
            assume_censored=self._assume_censored.isChecked(),
            excluded_chambers=merged_excluded,
            time_col=g.get("time_col", "Age"),
            event_col=g.get("event_col", "Event"),
            factor_cols=g.get("factor_cols"),
        )
        if fmt == "csv_long":
            kwargs["csv_format"] = "long"
        elif fmt == "csv_wide":
            kwargs["csv_format"] = "wide"
            kwargs["factor_names"] = cw.get("factor_names")
            kwargs["factor_levels"] = cw.get("factor_levels")
            kwargs["col_mapping"] = cw.get("col_mapping")

        excluded_msg = (
            f"Excluded {len(merged_excluded)} chamber(s) "
            f"(group '{self._group_combo.currentText().strip() or 'default'}'"
            f"{', ChamberFlags sheet' if excel_excluded else ''})."
        ) if merged_excluded else "No chambers excluded."

        def _do_load():
            print(f"Loading {path.name} ({fmt}) …")
            print(excluded_msg)
            data, factors = data_loader.load_experiment(path, **kwargs)
            print(f"Loaded {len(data)} individuals, {data['treatment'].nunique()} treatments, "
                  f"{len(factors)} factor(s): {factors}.")
            return (data, factors)

        def _on_ok(_msg: str, payload: tuple) -> None:
            data, factors = payload
            self._data = data
            self._factors = factors
            self._lifetables = lifetable.compute_lifetables(data)
            self._refresh_factor_checks()
            self._dataset_summary.setText(
                f"<b>{len(data)}</b> individuals · "
                f"<b>{data['treatment'].nunique()}</b> treatments · "
                f"<b>{len(factors)}</b> factor(s) · "
                f"<b>{int(data['event'].sum())}</b> events"
            )

        self._spawn_payload_task("Load data", _do_load, _on_ok)

    def _refresh_factor_checks(self) -> None:
        # Clear existing
        while self._factors_lay.count():
            item = self._factors_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._factor_checks.clear()
        if not self._factors:
            placeholder = QLabel("Load data to see factors.")
            placeholder.setStyleSheet("color: palette(mid); font-style: italic;")
            self._factors_lay.addWidget(placeholder)
            return
        for f in self._factors:
            cb = QCheckBox(f)
            cb.setChecked(True)
            self._factors_lay.addWidget(cb)
            self._factor_checks[f] = cb

    def _selected_factors(self) -> list[str]:
        return [f for f, cb in self._factor_checks.items() if cb.isChecked()]

    # ------------------------------------------------------------ workers

    def _spawn_task(self, name: str, fn) -> None:
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "Busy", f"Another task is running: {self._worker.task_name}.")
            return
        self._progress.setVisible(True)
        self._worker = TaskWorker(name, fn)
        self._worker.log_text.connect(self._on_log_text)
        self._worker.figure_ready.connect(self._on_figure_ready)
        self._worker.finished_ok.connect(self._on_task_ok)
        self._worker.failed.connect(self._on_task_failed)
        self._worker.finished.connect(lambda: self._progress.setVisible(False))
        self._worker.start()

    def _spawn_payload_task(self, name: str, fn, on_ok) -> None:
        """Variant that captures the function's return value for the slot."""
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "Busy", f"Another task is running: {self._worker.task_name}.")
            return
        self._progress.setVisible(True)
        result_holder: dict = {}

        def _wrapped():
            payload = fn()
            result_holder["payload"] = payload
            return f"{name} complete."

        worker = TaskWorker(name, _wrapped)
        self._worker = worker
        worker.log_text.connect(self._on_log_text)
        worker.figure_ready.connect(self._on_figure_ready)

        def _ok(msg: str) -> None:
            try:
                if "payload" in result_holder:
                    on_ok(msg, result_holder["payload"])
            finally:
                self._on_task_ok(msg)

        worker.finished_ok.connect(_ok)
        worker.failed.connect(self._on_task_failed)
        worker.finished.connect(lambda: self._progress.setVisible(False))
        worker.start()

    def _on_log_text(self, text: str) -> None:
        for line in text.splitlines():
            if not line.strip():
                continue
            self._log.append_line(line)
            m = _SAVED_RE.match(line)
            if m:
                self._maybe_surface_artifact(Path(m.group(1)))

    def _on_figure_ready(self, title: str, figure) -> None:
        self._plot_dock.add_figure(
            title, figure, interactive=self._interactive_checkbox.isChecked()
        )

    def _on_task_ok(self, msg: str) -> None:
        self._log.append_line(msg)

    def _on_task_failed(self, msg: str) -> None:
        self._log.append_line(msg)
        QMessageBox.warning(self, "Task failed", msg)

    def _maybe_surface_artifact(self, path: Path) -> None:
        if not path.is_file():
            return
        ext = path.suffix.lower()
        key = str(path.resolve())
        if key in self._artifact_tabs:
            return
        if ext in {".png", ".jpg", ".jpeg"}:
            view = ZoomableImageView(path)
            idx = self._plot_dock.addTab(view, icon("plot"), path.name)
            self._plot_dock.setCurrentIndex(idx)
            self._artifact_tabs[key] = view
        elif ext in {".csv", ".tsv", ".txt", ".md"}:
            view = ZoomableTextView(path)
            idx = self._plot_dock.addTab(view, icon("csv"), path.name)
            self._plot_dock.setCurrentIndex(idx)
            self._artifact_tabs[key] = view

    # ------------------------------------------------------------- guards

    def _require_data(self) -> bool:
        if self._data is None:
            QMessageBox.information(self, "No data", "Load data first.")
            return False
        return True

    # ----------------------------------------------------- analyze actions

    def _action_logrank_pairwise(self) -> None:
        if not self._require_data():
            return
        data = self._data
        def _do():
            res = statistics.pairwise_logrank(data)
            print("Pairwise log-rank tests:")
            print(res.to_string(index=False))
            return None
        self._spawn_task("Log-rank pairwise", _do)

    def _action_logrank_omnibus(self) -> None:
        if not self._require_data():
            return
        data = self._data
        def _do():
            res = statistics.logrank_multi(data)
            print("Omnibus log-rank test:")
            for k, v in res.items():
                print(f"  {k}: {v}")
            return None
        self._spawn_task("Log-rank omnibus", _do)

    def _action_gehan_wilcoxon(self) -> None:
        if not self._require_data():
            return
        data = self._data
        def _do():
            res = statistics.pairwise_gehan_wilcoxon(data)
            print("Pairwise Gehan-Wilcoxon tests:")
            print(res.to_string(index=False))
            return None
        self._spawn_task("Gehan-Wilcoxon pairwise", _do)

    def _action_hazard_ratios(self) -> None:
        if not self._require_data():
            return
        data = self._data
        def _do():
            res = statistics.pairwise_hazard_ratios(data)
            print("Pairwise hazard ratios:")
            print(res.to_string(index=False))
            return [("Hazard-ratio forest", plotting.plot_hazard_ratio_forest(res))]
        self._spawn_task("Hazard ratios", _do)

    def _action_cox_ph(self) -> None:
        if not self._require_data():
            return
        data = self._data
        factors = self._factors
        selected = self._selected_factors() or factors
        include_inter = self._interactions_check.isChecked()
        def _do():
            res = statistics.cox_interaction_analysis(
                data, factors=factors, selected_factors=selected,
            )
            if "error" in res:
                print(res["error"])
                return None
            print(f"Cox PH — factors: {selected} · n={res.get('n_subjects')}, events={res.get('n_events')}")
            print(f"  formula: {res.get('formula')}")
            print(f"  log-likelihood={res.get('log_likelihood'):.2f}, AIC={res.get('AIC'):.2f}, "
                  f"C={res.get('concordance'):.3f}")
            coefs = res.get("coefficients")
            if coefs is not None and len(coefs):
                if not include_inter:
                    coefs = coefs[~coefs["covariate"].astype(str).str.contains(":", regex=False)]
                print("\nCoefficients:")
                print(coefs.to_string(index=False))
            lr = res.get("lr_interaction")
            if lr is not None:
                print(f"\nLR interaction test: chi2={lr.get('chi2'):.3f}, df={lr.get('df')}, p={lr.get('p_value'):.4f}")
            ph = res.get("ph_test")
            if ph is not None and len(ph):
                print("\nProportional hazards (Schoenfeld):")
                print(ph.to_string(index=False))
            return None
        self._spawn_task("Cox PH", _do)

    def _action_rmst(self) -> None:
        if not self._require_data():
            return
        data = self._data
        factors = self._factors
        selected = self._selected_factors() or factors
        tau_value = float(self._tau_spin.value()) or None
        def _do():
            res = statistics.rmst_interaction_analysis(
                data, factors=factors, selected_factors=selected, tau=tau_value,
            )
            if "error" in res:
                print(res["error"])
                return None
            print(f"RMST regression — factors: {selected} · tau={res.get('tau')}")
            coefs = res.get("coefficients")
            if coefs is not None and len(coefs):
                print("\nCoefficients (hours):")
                print(coefs.to_string(index=False))
            for k in ("r_squared", "F_statistic", "F_p_value"):
                if res.get(k) is not None:
                    print(f"  {k}: {res[k]}")
            return None
        self._spawn_task("RMST regression", _do)

    def _action_parametric(self) -> None:
        if not self._require_data():
            return
        data = self._data
        def _do():
            res = statistics.fit_parametric_models(data)
            if not res:
                print("No parametric models could be fit.")
                return None
            for family, summary in res.items():
                print(f"\n{family}:")
                if isinstance(summary, dict):
                    for k, v in summary.items():
                        print(f"  {k}: {v}")
                else:
                    print(f"  {summary}")
            return None
        self._spawn_task("Parametric AFT", _do)

    def _action_full_pipeline(self) -> None:
        path = self._resolve_input_path()
        if path is None:
            return
        excluded = self._excluded_set()
        out_dir = self._project_dir
        def _do():
            run_analysis(
                input_path=path,
                output_dir=out_dir,
                assume_censored=self._assume_censored.isChecked(),
                extra_excluded_chambers=excluded,
            )
            print(f"Saved: {out_dir / 'report.md'}")
            return None
        self._spawn_task("Full pipeline", _do)

    # -------------------------------------------------------- plot actions

    def _plot_call(self, title: str, fn) -> None:
        if not self._require_data():
            return
        if self._lifetables is None:
            self._lifetables = lifetable.compute_lifetables(self._data)
        lt = self._lifetables
        data = self._data
        def _do():
            fig = fn(lt, data)
            return [(title, fig)]
        self._spawn_task(title, _do)

    def _action_plot_km(self) -> None:
        self._plot_call("KM curves", lambda lt, _d: plotting.plot_km_curves(lt))

    def _action_plot_km_risk(self) -> None:
        self._plot_call("KM + risk table", lambda lt, _d: plotting.plot_km_with_risk_table(lt))

    def _action_plot_nelson_aalen(self) -> None:
        self._plot_call("Nelson-Aalen", lambda lt, _d: plotting.plot_nelson_aalen(lt))

    def _action_plot_hazard(self) -> None:
        self._plot_call("Hazard rate", lambda lt, _d: plotting.plot_hazard(lt))

    def _action_plot_smoothed_hazard(self) -> None:
        self._plot_call("Smoothed hazard", lambda lt, _d: plotting.plot_smoothed_hazard(lt))

    def _action_plot_mortality(self) -> None:
        self._plot_call("Mortality (qx)", lambda lt, _d: plotting.plot_mortality(lt))

    def _action_plot_number_at_risk(self) -> None:
        self._plot_call("Number at risk", lambda lt, _d: plotting.plot_number_at_risk(lt))

    def _action_plot_cumulative(self) -> None:
        self._plot_call("Cumulative events", lambda lt, _d: plotting.plot_cumulative_events(lt))

    def _action_plot_forest(self) -> None:
        if not self._require_data():
            return
        data = self._data
        def _do():
            hr = statistics.pairwise_hazard_ratios(data)
            return [("Hazard-ratio forest", plotting.plot_hazard_ratio_forest(hr))]
        self._spawn_task("Hazard-ratio forest", _do)

    def _action_plot_distribution(self) -> None:
        if not self._require_data():
            return
        data = self._data
        def _do():
            return [("Survival distribution", plotting.plot_survival_distribution(data))]
        self._spawn_task("Survival distribution", _do)

    def _action_plot_log_log(self) -> None:
        self._plot_call("Log-log diagnostic", lambda lt, _d: plotting.plot_log_log(lt))

    # -------------------------------------------------------- tools actions

    def _action_generate_report(self) -> None:
        self._action_full_pipeline()

    def _action_open_output_dir(self) -> None:
        if self._project_dir is None:
            QMessageBox.information(self, "No project", "Pick a project first.")
            return
        target = str(self._project_dir)
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", target])
            elif os.name == "nt":
                os.startfile(target)  # type: ignore[attr-defined]
            else:
                subprocess.Popen(["xdg-open", target])
        except Exception as err:  # noqa: BLE001
            QMessageBox.warning(self, "Could not open", str(err))

    def _action_clear_tabs(self) -> None:
        # Close every tab except the OutputLog (idx 0)
        while self._plot_dock.count() > 1:
            w = self._plot_dock.widget(1)
            self._plot_dock.removeTab(1)
            if w is not None:
                w.deleteLater()
        self._artifact_tabs.clear()

    # ---------------------------------------------------- script actions

    def _run_selected_script(self) -> None:
        item = self._scripts_list.currentItem()
        if item is None:
            QMessageBox.information(self, "No script selected", "Pick a script first.")
            return
        idx = self._scripts_list.row(item)
        scripts = (self._cfg or {}).get("scripts") or []
        if idx >= len(scripts):
            return
        script = scripts[idx]
        from ..script_editor.runner import run_script, RunContext

        project_dir = self._project_dir
        data = self._data
        factors = self._factors
        lifetables = self._lifetables

        def _do():
            ctx = RunContext(
                project_dir=project_dir,
                cfg=self._cfg,
                data=data,
                factors=factors,
                lifetables=lifetables,
                log=lambda m: print(m),
                figure=lambda title, fig: _emit_figure(title, fig),
                excluded_chambers=self._excluded_set(),
                assume_censored=self._assume_censored.isChecked(),
            )
            run_script(script, ctx)
            return None

        figs: list[tuple] = []

        def _emit_figure(title: str, fig) -> None:
            figs.append((title, fig))

        self._spawn_task(f"Script: {script.get('name', '?')}", lambda: (_do(), figs)[1])

    def _open_script_editor(self) -> None:
        from ..script_editor.window import ScriptEditorWindow

        cfg_path = self._cfg_path
        if cfg_path is None and self._project_dir is not None:
            cfg_path = self._project_dir / cfg_mod.CONFIG_FILENAME
        if cfg_path is None:
            QMessageBox.information(
                self, "No config", "Pick a project directory first; the editor saves to the project's config."
            )
            return
        win = ScriptEditorWindow(cfg_path, factors=self._factors, parent=self)
        win.scriptsSaved.connect(self._on_scripts_saved)
        win.show()

    def _on_scripts_saved(self, path: str) -> None:
        if self._cfg_path is not None and Path(path).resolve() == self._cfg_path.resolve():
            self._cfg = cfg_mod.load_config(self._cfg_path)
            self._refresh_scripts_list()
            self._log.append_line(f"Reloaded scripts from {path}.")

    # -------------------------------------------------------- subprocesses

    def _launch_subapp(self, which: str) -> None:
        if self._project_dir is None:
            QMessageBox.information(self, "No project", "Pick a project directory first.")
            return
        cmd = [sys.executable, "-m", "pysurvanalysis", which, str(self._project_dir)]
        try:
            subprocess.Popen(cmd)
        except Exception as err:  # noqa: BLE001
            QMessageBox.warning(self, "Launch failed", str(err))

    # ----------------------------------------------------------- DnD

    def dragEnterEvent(self, event):  # noqa: N802 — Qt API
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802 — Qt API
        urls = event.mimeData().urls()
        if not urls:
            return
        p = Path(urls[0].toLocalFile())
        if p.is_dir():
            self._set_project_dir(p)
        elif p.is_file():
            self._set_project_dir(p.parent)


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, ui_settings.get("theme", "auto"))
    initial = sys.argv[1] if len(sys.argv) > 1 else None
    win = HubWindow(initial)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
