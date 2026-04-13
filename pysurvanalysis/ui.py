"""PyQt6 interactive UI for the survival analysis pipeline.

Features:
* Load Excel experiment files
* View Kaplan-Meier curves, hazard rates, mortality, number-at-risk
* Select/deselect individual treatments to plot
* View lifetable data in a table
* View log-rank test results and hazard ratios
* Run analysis on selected subsets of treatments
* Export reports
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("QtAgg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from . import data_loader, lifetable, plotting, statistics, report
from .pipeline import AnalysisResult


class CsvColumnDialog(QDialog):
    """Dialog for mapping CSV columns to time, event, and factor roles.

    Shown whenever the user opens a .csv or .tsv file so they can
    confirm (or override) the auto-detected column assignments.
    """

    def __init__(self, columns: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV Column Mapping")
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Map CSV columns to their roles.\n"
            "All unchecked columns in 'Factor columns' will be excluded."
        ))

        # --- Time column ---
        layout.addWidget(QLabel("Time column (survival time):"))
        self._time_combo = QComboBox()
        self._time_combo.addItems(columns)
        # Pre-select common names
        for candidate in ("Age", "age", "Time", "time", "T", "t"):
            if candidate in columns:
                self._time_combo.setCurrentText(candidate)
                break
        layout.addWidget(self._time_combo)

        # --- Event column ---
        layout.addWidget(QLabel("Event column (1=event, 0=censored):"))
        self._event_combo = QComboBox()
        self._event_combo.addItems(columns)
        for candidate in ("Event", "event", "Status", "status", "E", "e"):
            if candidate in columns:
                self._event_combo.setCurrentText(candidate)
                break
        layout.addWidget(self._event_combo)

        # --- Factor columns ---
        layout.addWidget(QLabel("Factor columns (select all that apply):"))
        self._factor_list = QListWidget()
        self._factor_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        reserved = {self._time_combo.currentText(), self._event_combo.currentText()}
        for col in columns:
            item = QListWidgetItem(col)
            self._factor_list.addItem(item)
            if col not in reserved:
                item.setSelected(True)
        layout.addWidget(self._factor_list)

        # --- Format hint ---
        layout.addWidget(QLabel("Format hint:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(["auto", "long", "wide"])
        layout.addWidget(self._format_combo)

        # --- Buttons ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Update factor pre-selection when time/event combos change
        self._time_combo.currentTextChanged.connect(self._refresh_factor_selection)
        self._event_combo.currentTextChanged.connect(self._refresh_factor_selection)

    def _refresh_factor_selection(self):
        reserved = {self._time_combo.currentText(), self._event_combo.currentText()}
        for i in range(self._factor_list.count()):
            item = self._factor_list.item(i)
            if item.text() in reserved:
                item.setSelected(False)

    def time_col(self) -> str:
        return self._time_combo.currentText()

    def event_col(self) -> str:
        return self._event_combo.currentText()

    def factor_cols(self) -> list[str]:
        return [item.text() for item in self._factor_list.selectedItems()]

    def csv_format(self) -> str:
        return self._format_combo.currentText()


class AnalysisWorker(QThread):
    """Run the analysis in a background thread to keep the UI responsive."""

    finished = pyqtSignal(object)  # emits AnalysisResult
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(
        self,
        input_path: Path,
        output_dir: Path,
        assume_censored: bool = True,
        time_col: str = "Age",
        event_col: str = "Event",
        factor_cols: list[str] | None = None,
        csv_format: str = "auto",
    ):
        super().__init__()
        self.input_path = input_path
        self.output_dir = output_dir
        self.assume_censored = assume_censored
        self.time_col = time_col
        self.event_col = event_col
        self.factor_cols = factor_cols
        self.csv_format = csv_format

    def run(self):
        try:
            self.progress.emit("Loading data...")
            # Excel-only: load chamber exclusions and defined plots
            excluded_chambers: set = set()
            defined_plots: list = []
            if self.input_path.suffix.lower() == ".xlsx":
                excluded_chambers = data_loader.load_chamber_flags(self.input_path)
                defined_plots = data_loader.load_defined_plots(self.input_path)

            individual_data, factors = data_loader.load_experiment(
                self.input_path,
                assume_censored=self.assume_censored,
                excluded_chambers=excluded_chambers,
                time_col=self.time_col,
                event_col=self.event_col,
                factor_cols=self.factor_cols,
                csv_format=self.csv_format,
            )

            self.progress.emit("Computing lifetables...")
            lifetables = lifetable.compute_lifetables(individual_data)

            self.progress.emit("Computing statistics...")
            summary = statistics.summary_statistics(individual_data)
            median_surv = lifetable.median_survival(lifetables)
            mean_surv = lifetable.mean_survival(individual_data)

            self.progress.emit("Running log-rank tests...")
            pairwise_lr = statistics.pairwise_logrank(individual_data)
            omnibus_lr = statistics.logrank_multi(individual_data)

            self.progress.emit("Computing hazard ratios...")
            hazard_ratios = statistics.pairwise_hazard_ratios(individual_data)

            self.progress.emit("Computing lifespan statistics...")
            lifespan_stats = lifetable.lifespan_statistics(
                individual_data, factors, assume_censored=self.assume_censored,
            )

            # Save outputs
            self.output_dir.mkdir(parents=True, exist_ok=True)
            data_dir = self.output_dir / "data_output"
            data_dir.mkdir(exist_ok=True)
            lifetables.to_csv(data_dir / "lifetables.csv", index=False)
            individual_data.to_csv(data_dir / "individual_data.csv", index=False)

            result = AnalysisResult(
                input_file=self.input_path,
                factors=factors,
                individual_data=individual_data,
                lifetables=lifetables,
                summary=summary,
                median_surv=median_surv,
                mean_surv=mean_surv,
                pairwise_lr=pairwise_lr,
                omnibus_lr=omnibus_lr,
                hazard_ratios=hazard_ratios,
                lifespan_stats=lifespan_stats,
                assume_censored=self.assume_censored,
                excluded_chambers=excluded_chambers,
                defined_plots=defined_plots,
            )

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class PlotWidget(QWidget):
    """Widget containing a matplotlib figure with navigation toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def clear(self):
        self.figure.clear()
        self.canvas.draw()

    def update_figure(self, fig: plt.Figure):
        """Replace the current figure content with a new one."""
        self.figure.clear()

        # Copy axes from the source figure
        for src_ax in fig.axes:
            ax = self.figure.add_subplot(111)
            # Transfer lines
            for line in src_ax.get_lines():
                ax.plot(
                    line.get_xdata(), line.get_ydata(),
                    label=line.get_label(),
                    color=line.get_color(),
                    linestyle=line.get_linestyle(),
                    linewidth=line.get_linewidth(),
                    marker=line.get_marker(),
                    markersize=line.get_markersize(),
                    markeredgewidth=line.get_markeredgewidth(),
                    drawstyle=line.get_drawstyle(),
                )
            # Transfer fill_between patches
            for coll in src_ax.collections:
                paths = coll.get_paths()
                if paths:
                    fc = coll.get_facecolor()
                    ec = coll.get_edgecolor()
                    alpha = coll.get_alpha()
                    from matplotlib.collections import PathCollection, PolyCollection
                    if isinstance(coll, PolyCollection):
                        verts = [p.vertices for p in paths]
                        new_coll = PolyCollection(verts, facecolors=fc, edgecolors=ec, alpha=alpha)
                        ax.add_collection(new_coll)

            ax.set_xlabel(src_ax.get_xlabel())
            ax.set_ylabel(src_ax.get_ylabel())
            ax.set_title(src_ax.get_title())
            ax.set_xlim(src_ax.get_xlim())
            ax.set_ylim(src_ax.get_ylim())
            ax.legend(loc="best")
            ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()
        plt.close(fig)


class TreatmentSelector(QGroupBox):
    """Widget for selecting which treatments to display."""

    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Treatment Selection", parent)
        self.checkboxes: dict[str, QCheckBox] = {}
        self._layout = QVBoxLayout()

        btn_layout = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_none = QPushButton("Deselect All")
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._deselect_all)
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        self._layout.addLayout(btn_layout)

        self._cb_container = QVBoxLayout()
        self._layout.addLayout(self._cb_container)
        self._layout.addStretch()
        self.setLayout(self._layout)

    def set_treatments(self, treatments: list[str]):
        # Clear existing
        for cb in self.checkboxes.values():
            self._cb_container.removeWidget(cb)
            cb.deleteLater()
        self.checkboxes.clear()

        for t in sorted(treatments):
            cb = QCheckBox(t)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda: self.selection_changed.emit())
            self.checkboxes[t] = cb
            self._cb_container.addWidget(cb)

    def selected_treatments(self) -> list[str]:
        return [t for t, cb in self.checkboxes.items() if cb.isChecked()]

    def _select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)


class DataTableWidget(QWidget):
    """Widget for displaying a pandas DataFrame in a table."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Treatments")
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)

        self._df: Optional[pd.DataFrame] = None

        layout = QVBoxLayout()
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by treatment:"))
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def set_data(self, df: pd.DataFrame):
        self._df = df
        # Update filter options
        self.filter_combo.blockSignals(True)
        self.filter_combo.clear()
        self.filter_combo.addItem("All Treatments")
        if "treatment" in df.columns:
            for t in sorted(df["treatment"].unique()):
                self.filter_combo.addItem(t)
        self.filter_combo.blockSignals(False)
        self._populate(df)

    def _on_filter_changed(self, text: str):
        if self._df is None:
            return
        if text == "All Treatments" or "treatment" not in self._df.columns:
            self._populate(self._df)
        else:
            self._populate(self._df[self._df["treatment"] == text])

    def _populate(self, df: pd.DataFrame):
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels([str(c) for c in df.columns])

        for i, (_, row) in enumerate(df.iterrows()):
            for j, val in enumerate(row):
                if isinstance(val, float):
                    text = f"{val:.6f}" if abs(val) < 0.001 and val != 0 else f"{val:.4f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, j, item)

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )


class StatisticsWidget(QWidget):
    """Widget for displaying statistical test results."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFontFamily("monospace")

        layout = QVBoxLayout()
        layout.addWidget(self.text)
        self.setLayout(layout)

    def set_results(self, result: AnalysisResult):
        lines = []

        # Excluded chambers notice
        excl = getattr(result, "excluded_chambers", set())
        if excl:
            sorted_excl = sorted(excl, key=lambda x: (str(type(x).__name__), x))
            lines.append("!" * 70)
            lines.append("EXCLUDED CHAMBERS (flagged in ChamberFlags sheet)")
            lines.append("!" * 70)
            lines.append(f"  The following chambers were excluded from ALL analyses:")
            lines.append(f"  {', '.join(str(c) for c in sorted_excl)}")
            lines.append("")

        # Omnibus log-rank
        lr = result.omnibus_lr
        lines.append("=" * 70)
        lines.append("OMNIBUS LOG-RANK TEST (all treatments)")
        lines.append("=" * 70)
        lines.append(f"  Chi-square:          {lr['chi2']:.4f}")
        lines.append(f"  Degrees of freedom:  {lr['df']}")
        lines.append(f"  p-value:             {lr['p_value']:.6f}")
        sig = "YES" if lr["p_value"] < 0.05 else "NO"
        lines.append(f"  Significant (0.05):  {sig}")
        lines.append("")

        # Pairwise log-rank
        lines.append("=" * 70)
        lines.append("PAIRWISE LOG-RANK TESTS (Bonferroni corrected)")
        lines.append("=" * 70)
        if len(result.pairwise_lr) > 0:
            for _, row in result.pairwise_lr.iterrows():
                lines.append(f"\n  {row['group1']}  vs  {row['group2']}")
                lines.append(f"    Chi-square:        {row['chi2']:.4f}")
                lines.append(f"    p-value (raw):     {row['p_value']:.6f}")
                lines.append(f"    p-value (Bonf.):   {row['p_bonferroni']:.6f}")
                sig = "*" if row["p_bonferroni"] < 0.05 else "ns"
                lines.append(f"    Significance:      {sig}")
        lines.append("")

        # Hazard ratios
        lines.append("=" * 70)
        lines.append("HAZARD RATIO ESTIMATES (log-rank O/E method)")
        lines.append("=" * 70)
        if len(result.hazard_ratios) > 0:
            for _, row in result.hazard_ratios.iterrows():
                lines.append(f"\n  {row['group1']}  vs  {row['group2']}")
                if pd.notna(row["hazard_ratio"]):
                    lines.append(f"    HR:                {row['hazard_ratio']:.4f}")
                    lines.append(f"    95% CI:            ({row['hr_ci_lo']:.4f}, {row['hr_ci_hi']:.4f})")
                else:
                    lines.append("    HR:                N/A")
        lines.append("")

        # Summary
        lines.append("=" * 70)
        lines.append("SAMPLE SUMMARY")
        lines.append("=" * 70)
        for _, row in result.summary.iterrows():
            lines.append(
                f"  {row['treatment']:30s}  N={row['n_individuals']:4d}  "
                f"Deaths={row['n_deaths']:4d}  Censored={row['n_censored']:4d}  "
                f"({row['pct_censored']:.1f}% censored)"
            )
        lines.append("")

        # Lifespan statistics
        ls = result.lifespan_stats
        has_top_pct = False

        if ls and "treatment_stats" in ls and len(ls["treatment_stats"]) > 0:
            ts = ls["treatment_stats"]
            has_top_pct = "top_10pct_mean" in ts.columns

            lines.append("=" * 70)
            lines.append("LIFESPAN STATISTICS BY TREATMENT (KM-adjusted)")
            lines.append("=" * 70)
            for _, row in ts.iterrows():
                lines.append(f"\n  {row['group']}")
                lines.append(f"    N={int(row['n'])}  Deaths={int(row['n_deaths'])}  Censored={int(row['n_censored'])}")
                mean_str = f"{row['mean_rmst']:.1f}" if pd.notna(row["mean_rmst"]) else "N/A"
                med_str = f"{row['median']:.1f}" if pd.notna(row["median"]) else "Not reached"
                lines.append(f"    Mean (RMST):     {mean_str} hours")
                lines.append(f"    Median:          {med_str} hours")
                if has_top_pct and pd.notna(row.get("top_10pct_mean")):
                    lines.append(f"    Top 10% mean:    {row['top_10pct_mean']:.1f} hours")
                    lines.append(f"    Top  5% mean:    {row['top_5pct_mean']:.1f} hours")
            lines.append("")

        if ls and "factor_stats" in ls and len(ls["factor_stats"]) > 0:
            fs = ls["factor_stats"]
            has_top_pct_f = "top_10pct_mean" in fs.columns

            lines.append("=" * 70)
            lines.append("LIFESPAN STATISTICS BY FACTOR LEVEL (pooled)")
            lines.append("=" * 70)
            for _, row in fs.iterrows():
                lines.append(f"\n  {row['group']}")
                lines.append(f"    N={int(row['n'])}  Deaths={int(row['n_deaths'])}  Censored={int(row['n_censored'])}")
                mean_str = f"{row['mean_rmst']:.1f}" if pd.notna(row["mean_rmst"]) else "N/A"
                med_str = f"{row['median']:.1f}" if pd.notna(row["median"]) else "Not reached"
                lines.append(f"    Mean (RMST):     {mean_str} hours")
                lines.append(f"    Median:          {med_str} hours")
                if has_top_pct_f and pd.notna(row.get("top_10pct_mean")):
                    lines.append(f"    Top 10% mean:    {row['top_10pct_mean']:.1f} hours")
                    lines.append(f"    Top  5% mean:    {row['top_5pct_mean']:.1f} hours")
            lines.append("")

        self.text.setPlainText("\n".join(lines))


class CoxAnalysisWidget(QWidget):
    """Widget for configuring and running Cox PH and RMST interaction analyses."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._factors: list[str] = []
        self._result: Optional[AnalysisResult] = None

        layout = QVBoxLayout()

        # Factor selection
        factor_group = QGroupBox("Select Factors for Model")
        factor_layout = QVBoxLayout()
        self._factor_checkboxes: dict[str, QCheckBox] = {}
        self._factor_container = QVBoxLayout()
        factor_layout.addLayout(self._factor_container)
        factor_group.setLayout(factor_layout)
        layout.addWidget(factor_group)

        # Run buttons
        btn_layout = QHBoxLayout()
        self.run_cox_btn = QPushButton("Run Cox PH Analysis")
        self.run_cox_btn.setEnabled(False)
        self.run_cox_btn.clicked.connect(self._run_cox)
        btn_layout.addWidget(self.run_cox_btn)

        self.run_rmst_btn = QPushButton("Run RMST Analysis")
        self.run_rmst_btn.setEnabled(False)
        self.run_rmst_btn.clicked.connect(self._run_rmst)
        btn_layout.addWidget(self.run_rmst_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Results display
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFontFamily("monospace")
        layout.addWidget(self.results_text)

        self.setLayout(layout)

    def set_result(self, result: AnalysisResult):
        self._result = result
        self._factors = result.factors

        # Rebuild factor checkboxes
        for cb in self._factor_checkboxes.values():
            self._factor_container.removeWidget(cb)
            cb.deleteLater()
        self._factor_checkboxes.clear()

        for f in self._factors:
            levels = sorted(result.individual_data[f].unique())
            label = f"{f}  ({', '.join(str(lv) for lv in levels)})"
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setProperty("factor_name", f)
            self._factor_checkboxes[f] = cb
            self._factor_container.addWidget(cb)

        self.run_cox_btn.setEnabled(len(self._factors) >= 1)
        self.run_rmst_btn.setEnabled(len(self._factors) >= 1)

        # Render any existing analyses
        self._render_results()

    def _selected_factors(self) -> list[str]:
        return [
            f for f, cb in self._factor_checkboxes.items()
            if cb.isChecked()
        ]

    def _run_cox(self):
        if self._result is None:
            return
        selected = self._selected_factors()
        if len(selected) < 1:
            QMessageBox.warning(
                self, "No Factors Selected",
                "Select at least one factor to run the analysis.",
            )
            return

        cox_result = statistics.cox_interaction_analysis(
            self._result.individual_data,
            self._result.factors,
            selected_factors=selected,
        )
        self._result.cox_analyses.append(cox_result)
        self._render_results()
        output_dir = self._result.input_file.parent / f"{self._result.input_file.stem}_results"
        report.generate_report(self._result, output_dir)

    def _run_rmst(self):
        if self._result is None:
            return
        selected = self._selected_factors()
        if len(selected) < 1:
            QMessageBox.warning(
                self, "No Factors Selected",
                "Select at least one factor to run the analysis.",
            )
            return

        rmst_result = statistics.rmst_interaction_analysis(
            self._result.individual_data,
            self._result.factors,
            selected_factors=selected,
        )
        self._result.cox_analyses.append(rmst_result)
        self._render_results()
        output_dir = self._result.input_file.parent / f"{self._result.input_file.stem}_results"
        report.generate_report(self._result, output_dir)

    def _render_results(self):
        if self._result is None or not self._result.cox_analyses:
            self.results_text.setPlainText(
                "No interaction analyses run yet.\n\n"
                "Select factors above and click one of the analysis buttons:\n\n"
                "  Cox PH:  Fits a Cox proportional hazards model.\n"
                "           Coefficients are log-hazard ratios.\n\n"
                "  RMST:    Fits an OLS model on jackknife pseudo-values\n"
                "           of restricted mean survival time.\n"
                "           Coefficients are differences in mean survival (hours).\n"
                "           Does not assume proportional hazards.\n\n"
                "Results are accumulated and will be appended to the report\n"
                "when the application is closed or a new file is opened."
            )
            return

        lines = []
        for i, result in enumerate(self._result.cox_analyses, 1):
            model_type = result.get("model_type", "cox_ph")
            is_rmst = model_type == "rmst_pseudo"
            type_label = "RMST Pseudo-Value Regression" if is_rmst else "Cox Proportional Hazards"
            factors_str = ", ".join(result.get("factors_used", []))

            lines.append("=" * 70)
            lines.append(f"ANALYSIS {i} [{type_label}]: {factors_str}")
            lines.append("=" * 70)

            if "error" in result:
                lines.append(f"  ERROR: {result['error']}")
                lines.append("")
                continue

            lines.append(f"  Model:         {result.get('formula', 'N/A')}")
            lines.append(f"  N subjects:    {result.get('n_subjects', 'N/A')}")
            lines.append(f"  N events:      {result.get('n_events', 'N/A')}")

            if is_rmst:
                lines.append(f"  Tau (restrict): {result.get('tau', 'N/A')} hours")
                lines.append(f"  Overall RMST:  {result.get('rmst_overall', 'N/A')} hours")
                lines.append(f"  R-squared:     {result.get('r_squared', 'N/A')}")
                if result.get("f_statistic") is not None:
                    lines.append(f"  F-statistic:   {result['f_statistic']}")
                if result.get("f_p_value") is not None:
                    p = result["f_p_value"]
                    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                    lines.append(f"  F p-value:     {p:.6f}  {sig}")
            else:
                if result.get("concordance") is not None:
                    lines.append(f"  Concordance:   {result['concordance']}")
                if result.get("AIC") is not None:
                    lines.append(f"  AIC (partial): {result['AIC']}")
                if result.get("log_likelihood") is not None:
                    lines.append(f"  Log-lik:       {result['log_likelihood']}")
                if result.get("log_likelihood_ratio_p") is not None:
                    p = result["log_likelihood_ratio_p"]
                    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                    lines.append(f"  LR test p:     {p:.6f}  {sig}")
            lines.append("")

            coefs = result.get("coefficients")
            if coefs is not None and len(coefs) > 0:
                # Column headers differ between Cox and RMST
                if is_rmst:
                    hdr_coef = "Coef(hrs)"
                    hdr_extra = "95% CI (hours)"
                else:
                    hdr_coef = "Coef"
                    hdr_extra = "95% CI (HR)"

                for section_type, section_label in [
                    ("intercept", "INTERCEPT:"),
                    ("main_effect", "MAIN EFFECTS:"),
                    ("interaction", "INTERACTION EFFECTS:"),
                ]:
                    subset = coefs[coefs["term_type"] == section_type]
                    if len(subset) == 0:
                        continue
                    lines.append(f"  {section_label}")
                    if is_rmst:
                        lines.append(f"  {'Covariate':<30s} {hdr_coef:>10s} "
                                     f"{'SE':>8s} {'t':>8s} {'p':>10s}  {hdr_extra}")
                    else:
                        lines.append(f"  {'Covariate':<30s} {hdr_coef:>8s} {'HR':>8s} "
                                     f"{'SE':>8s} {'z':>8s} {'p':>10s}  {hdr_extra}")
                    lines.append("  " + "-" * 100)
                    for _, row in subset.iterrows():
                        p_str = f"{row['p_value']:.2e}" if row['p_value'] < 0.0001 else f"{row['p_value']:.4f}"
                        sig = "***" if row['p_value'] < 0.001 else "**" if row['p_value'] < 0.01 else "*" if row['p_value'] < 0.05 else "   "
                        if is_rmst:
                            lines.append(
                                f"  {row['covariate']:<30s} {row['coef']:>10.2f} "
                                f"{row['se']:>8.2f} {row['z']:>8.3f} {p_str:>10s} {sig} "
                                f"({row['coef_lo']:.2f}, {row['coef_hi']:.2f})"
                            )
                        else:
                            lines.append(
                                f"  {row['covariate']:<30s} {row['coef']:>8.4f} {row['HR']:>8.4f} "
                                f"{row['se']:>8.4f} {row['z']:>8.3f} {p_str:>10s} {sig} "
                                f"({row['HR_lo']:.3f}, {row['HR_hi']:.3f})"
                            )
                    lines.append("")

            if result.get("warnings"):
                lines.append("  WARNINGS:")
                for w in result["warnings"]:
                    lines.append(f"    - {w}")
                lines.append("")

            # ── LR omnibus interaction test (Cox only) ──────────────────
            if not is_rmst:
                lr = result.get("lr_interaction")
                lines.append("  " + "-" * 68)
                lines.append("  OMNIBUS LR INTERACTION TEST (main effects vs interaction model)")
                lines.append("  " + "-" * 68)
                if lr is None:
                    lines.append("  (Not applicable — no interaction terms; only one factor selected.)")
                else:
                    p = lr["p_value"]
                    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                    p_str = f"{p:.2e}" if p < 0.0001 else f"{p:.6f}"
                    lines.append(f"  Interaction terms:   {', '.join(lr.get('interaction_cols', []))}")
                    lines.append(f"  Log-lik (main):      {lr['ll_main']}")
                    lines.append(f"  Log-lik (interact.): {lr['ll_interaction']}")
                    lines.append(f"  LR statistic:        {lr['lr_stat']:.4f}  (df={lr['df']})")
                    lines.append(f"  p-value:             {p_str}  {sig}")
                    conclusion = ("Significant interaction" if p < 0.05
                                  else "No significant interaction")
                    lines.append(f"  Conclusion:          {conclusion} (p {'<' if p < 0.05 else '≥'} 0.05)")
                    lines.append(f"  Concordance (main):  {lr['concordance_main']}")
                lines.append("")

                # ── PH assumption test ──────────────────────────────────
                lines.append("  " + "-" * 68)
                lines.append("  PROPORTIONAL HAZARDS ASSUMPTION (Schoenfeld residuals)")
                lines.append("  " + "-" * 68)
                ph = result.get("ph_test")
                if ph is None:
                    lines.append("  (Test could not be computed — see warnings above.)")
                else:
                    lines.append(f"  {'Covariate':<30s} {'Test stat':>10s} {'p-value':>10s}")
                    lines.append("  " + "-" * 55)
                    all_ok = True
                    for _, row in ph.iterrows():
                        p = row.get("p_value", float("nan"))
                        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "   "
                        if p < 0.05:
                            all_ok = False
                        p_str = f"{p:.2e}" if p < 0.0001 else f"{p:.4f}"
                        ts = row.get("test_statistic", float("nan"))
                        lines.append(
                            f"  {str(row.get('covariate', '?')):<30s} {ts:>10.4f} {p_str:>10s} {sig}"
                        )
                    lines.append("")
                    if all_ok:
                        lines.append("  PH assumption appears satisfied for all covariates (p ≥ 0.05).")
                    else:
                        lines.append("  WARNING: PH assumption may be violated for covariate(s) marked *.")
                        lines.append("  Consider a stratified model or time-varying coefficients.")
                lines.append("")

        self.results_text.setPlainText("\n".join(lines))


class DefinedPlotsWidget(QWidget):
    """Widget for browsing KM plots defined in the DefinedPlots sheet."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._lifetables: Optional[pd.DataFrame] = None
        self._defined_plots: list[list[str]] = []

        layout = QVBoxLayout(self)

        top = QHBoxLayout()
        top.addWidget(QLabel("Select plot:"))
        self._selector = QComboBox()
        self._selector.currentIndexChanged.connect(self._show_selected)
        top.addWidget(self._selector)
        top.addStretch()
        layout.addLayout(top)

        self._plot_widget = PlotWidget()
        layout.addWidget(self._plot_widget)

    def set_data(self, lifetables: pd.DataFrame, defined_plots: list[tuple[str, list[str]]]):
        self._lifetables = lifetables
        self._defined_plots = defined_plots

        self._selector.blockSignals(True)
        self._selector.clear()
        available = set(lifetables["treatment"].unique())
        for plot_name, treatment_list in defined_plots:
            valid = [t for t in treatment_list if t in available]
            label = plot_name if plot_name else ", ".join(valid) if valid else "(empty)"
            self._selector.addItem(label)
        self._selector.blockSignals(False)

        if self._selector.count() > 0:
            self._show_selected(0)

    def _show_selected(self, index: int):
        if self._lifetables is None or index < 0 or index >= len(self._defined_plots):
            return
        plot_name, treatment_list = self._defined_plots[index]
        available = set(self._lifetables["treatment"].unique())
        valid = [t for t in treatment_list if t in available]
        if not valid:
            self._plot_widget.clear()
            return
        fig = plotting.plot_km_curves(self._lifetables, treatments=valid, title=plot_name)
        self._plot_widget.update_figure(fig)


class MainWindow(QMainWindow):
    """Main application window for the survival analysis pipeline."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("pySurvAnalysis — Survival Analysis Pipeline")
        self.setMinimumSize(1200, 800)

        self.result: Optional[AnalysisResult] = None
        self._current_file: Optional[Path] = None
        self._csv_params: dict = {}

        self._build_menu()
        self._build_ui()
        self._build_status_bar()

    def _build_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Experiment...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        export_action = QAction("&Export Report...", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._export_report)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        analysis_menu = menubar.addMenu("&Analysis")

        rerun_action = QAction("&Re-run with Selected Treatments", self)
        rerun_action.setShortcut("Ctrl+R")
        rerun_action.triggered.connect(self._rerun_selected)
        analysis_menu.addAction(rerun_action)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # Left panel: treatment selector + options
        left_panel = QVBoxLayout()

        # Assume censored checkbox
        self.assume_censored_cb = QCheckBox("Assume remaining are censored")
        self.assume_censored_cb.setChecked(True)
        self.assume_censored_cb.setToolTip(
            "Checked: cohort size from Design SampleSize; unaccounted\n"
            "individuals added as right-censored at last observation.\n\n"
            "Unchecked: cohort size = sum of deaths + censored per chamber."
        )
        self.assume_censored_cb.stateChanged.connect(self._on_censoring_changed)
        left_panel.addWidget(self.assume_censored_cb)

        self.treatment_selector = TreatmentSelector()
        self.treatment_selector.selection_changed.connect(self._update_plots)

        scroll = QScrollArea()
        scroll.setWidget(self.treatment_selector)
        scroll.setWidgetResizable(True)
        scroll.setMaximumWidth(250)

        left_panel.addWidget(scroll)

        rerun_btn = QPushButton("Re-analyze Selected")
        rerun_btn.clicked.connect(self._rerun_selected)
        left_panel.addWidget(rerun_btn)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)

        # Right panel: tabs
        self.tabs = QTabWidget()

        # Tab 1: KM curves
        self.km_plot = PlotWidget()
        self.tabs.addTab(self.km_plot, "Kaplan\u2013Meier")

        # Tab 2: Hazard
        self.hazard_plot = PlotWidget()
        self.tabs.addTab(self.hazard_plot, "Hazard Rate")

        # Tab 3: Mortality
        self.mortality_plot = PlotWidget()
        self.tabs.addTab(self.mortality_plot, "Mortality (qx)")

        # Tab 4: Number at risk
        self.risk_plot = PlotWidget()
        self.tabs.addTab(self.risk_plot, "Number at Risk")

        # Tab 5: Lifetable data
        self.lifetable_view = DataTableWidget()
        self.tabs.addTab(self.lifetable_view, "Lifetable Data")

        # Tab 6: Statistics
        self.stats_view = StatisticsWidget()
        self.tabs.addTab(self.stats_view, "Statistics")

        # Tab 7: Summary
        self.summary_view = DataTableWidget()
        self.tabs.addTab(self.summary_view, "Summary")

        # Tab 8: Cox Interaction Analysis
        self.cox_view = CoxAnalysisWidget()
        self.tabs.addTab(self.cox_view, "Cox / Interactions")

        # Tab 9: Defined Plots (shown only when data has defined plots)
        self.defined_plots_view = DefinedPlotsWidget()
        self._defined_plots_tab_idx = self.tabs.addTab(self.defined_plots_view, "Defined Plots")
        self.tabs.setTabVisible(self._defined_plots_tab_idx, False)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        main_layout.addWidget(splitter)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("Ready. Open an experiment file to begin.")

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Experiment File", "",
            "Experiment Files (*.xlsx *.xls *.csv *.tsv);;Excel Files (*.xlsx *.xls);;CSV/TSV Files (*.csv *.tsv);;All Files (*)",
        )
        if not path:
            return
        self.load_file(Path(path))

    def _save_pending_cox(self):
        """No-op: report is rewritten immediately after each Cox/RMST analysis run."""
        pass

    def closeEvent(self, event):
        """Save Cox analyses to report when the window is closed."""
        self._save_pending_cox()
        super().closeEvent(event)

    def load_file(self, input_path: Path):
        """Load an experiment file (Excel or CSV/TSV)."""
        self._save_pending_cox()
        self._current_file = input_path

        ext = input_path.suffix.lower()
        if ext in {".csv", ".tsv"}:
            # Read column names and show the mapping dialog
            import pandas as pd
            sep = "\t" if ext == ".tsv" else ","
            try:
                preview = pd.read_csv(input_path, sep=sep, nrows=0)
                columns = list(preview.columns)
            except Exception as e:
                QMessageBox.critical(self, "File Error", f"Could not read CSV:\n{e}")
                return

            dlg = CsvColumnDialog(columns, parent=self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return

            time_col = dlg.time_col()
            event_col = dlg.event_col()
            factor_cols = dlg.factor_cols()
            csv_format = dlg.csv_format()

            if not factor_cols:
                QMessageBox.warning(
                    self, "No Factors",
                    "No factor columns selected. Select at least one factor column.",
                )
                return

            self._csv_params = {
                "time_col": time_col,
                "event_col": event_col,
                "factor_cols": factor_cols,
                "csv_format": csv_format,
            }
            # Disable the assume-censored checkbox for CSV (not applicable)
            self.assume_censored_cb.setEnabled(False)
            self.assume_censored_cb.setToolTip(
                "Not applicable for CSV/TSV input — data is already individual-level."
            )
            self._run_analysis(input_path, assume_censored=True, **self._csv_params)
        else:
            # Excel path: read AssumeCensored from PrivateData
            self._csv_params = {}
            self.assume_censored_cb.setEnabled(True)
            self.assume_censored_cb.setToolTip(
                "Checked: cohort size from Design SampleSize; unaccounted\n"
                "individuals added as right-censored at last observation.\n\n"
                "Unchecked: cohort size = sum of deaths + censored per chamber."
            )
            assume_censored = data_loader.read_assume_censored(input_path)
            self.assume_censored_cb.blockSignals(True)
            self.assume_censored_cb.setChecked(assume_censored)
            self.assume_censored_cb.blockSignals(False)
            self._run_analysis(input_path, assume_censored=assume_censored)

    def _on_censoring_changed(self):
        """Re-run analysis when the user toggles the censoring checkbox (Excel only)."""
        if self._current_file is None:
            return
        assume_censored = self.assume_censored_cb.isChecked()
        self._run_analysis(self._current_file, assume_censored=assume_censored, **getattr(self, "_csv_params", {}))

    def _run_analysis(
        self,
        input_path: Path,
        assume_censored: bool = True,
        time_col: str = "Age",
        event_col: str = "Event",
        factor_cols: list[str] | None = None,
        csv_format: str = "auto",
    ):
        output_dir = input_path.parent / f"{input_path.stem}_results"

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # indeterminate
        self.status_bar.showMessage("Running analysis...")

        self.worker = AnalysisWorker(
            input_path,
            output_dir,
            assume_censored=assume_censored,
            time_col=time_col,
            event_col=event_col,
            factor_cols=factor_cols,
            csv_format=csv_format,
        )
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_analysis_done)
        self.worker.error.connect(self._on_analysis_error)
        self.worker.start()

    def _on_progress(self, msg: str):
        self.status_bar.showMessage(msg)

    def _on_analysis_done(self, result: AnalysisResult):
        self.result = result
        self.progress_bar.setVisible(False)

        treatments = sorted(result.individual_data["treatment"].unique())
        self.treatment_selector.set_treatments(treatments)

        self._update_plots()
        self.lifetable_view.set_data(result.lifetables)
        self.stats_view.set_results(result)
        self.summary_view.set_data(result.summary)
        self.cox_view.set_result(result)

        # Defined Plots tab: show only when plots are defined
        dp = result.defined_plots
        if dp:
            self.defined_plots_view.set_data(result.lifetables, dp)
            self.tabs.setTabVisible(self._defined_plots_tab_idx, True)
        else:
            self.tabs.setTabVisible(self._defined_plots_tab_idx, False)

        # Generate report on the main thread (matplotlib requires it)
        output_dir = result.input_file.parent / f"{result.input_file.stem}_results"
        report.generate_report(result, output_dir)

        self.status_bar.showMessage(
            f"Analysis complete: {result.input_file.name} — "
            f"{len(treatments)} treatments, {len(result.individual_data)} individuals. "
            f"Results saved to {result.input_file.stem}_results/"
        )

    def _on_analysis_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Analysis failed.")
        QMessageBox.critical(self, "Analysis Error", f"An error occurred:\n\n{msg}")

    def _update_plots(self):
        if self.result is None:
            return

        selected = self.treatment_selector.selected_treatments()
        if not selected:
            self.km_plot.clear()
            self.hazard_plot.clear()
            self.mortality_plot.clear()
            self.risk_plot.clear()
            return

        lt = self.result.lifetables

        fig_km = plotting.plot_km_curves(lt, treatments=selected)
        self.km_plot.update_figure(fig_km)

        fig_hz = plotting.plot_hazard(lt, treatments=selected)
        self.hazard_plot.update_figure(fig_hz)

        fig_qx = plotting.plot_mortality(lt, treatments=selected)
        self.mortality_plot.update_figure(fig_qx)

        fig_nr = plotting.plot_number_at_risk(lt, treatments=selected)
        self.risk_plot.update_figure(fig_nr)

    def _rerun_selected(self):
        if self.result is None:
            QMessageBox.information(self, "No Data", "Load an experiment first.")
            return

        selected = self.treatment_selector.selected_treatments()
        if len(selected) < 2:
            QMessageBox.warning(
                self, "Insufficient Selection",
                "Select at least 2 treatments to run statistical comparisons.",
            )
            return

        # Re-run statistics on the selected subset
        subset = self.result.individual_data[
            self.result.individual_data["treatment"].isin(selected)
        ].copy()

        pairwise_lr = statistics.pairwise_logrank(subset)
        omnibus_lr = statistics.logrank_multi(subset)
        hazard_ratios = statistics.pairwise_hazard_ratios(subset)
        lt_subset = self.result.lifetables[
            self.result.lifetables["treatment"].isin(selected)
        ].copy()
        summary = statistics.summary_statistics(subset)
        median_surv = lifetable.median_survival(lt_subset)
        mean_surv = lifetable.mean_survival(subset)
        lifespan_stats = lifetable.lifespan_statistics(
            subset, self.result.factors,
            assume_censored=self.result.assume_censored,
        )

        sub_result = AnalysisResult(
            input_file=self.result.input_file,
            factors=self.result.factors,
            individual_data=subset,
            lifetables=lt_subset,
            summary=summary,
            median_surv=median_surv,
            mean_surv=mean_surv,
            pairwise_lr=pairwise_lr,
            omnibus_lr=omnibus_lr,
            hazard_ratios=hazard_ratios,
            lifespan_stats=lifespan_stats,
            assume_censored=self.result.assume_censored,
        )

        self.stats_view.set_results(sub_result)
        self.summary_view.set_data(summary)
        self.tabs.setCurrentWidget(self.stats_view)
        self.status_bar.showMessage(
            f"Re-analyzed {len(selected)} selected treatments."
        )

    def _export_report(self):
        if self.result is None:
            QMessageBox.information(self, "No Data", "Load an experiment first.")
            return

        dir_path = QFileDialog.getExistingDirectory(
            self, "Select Export Directory", str(self.result.input_file.parent),
        )
        if not dir_path:
            return

        output_dir = Path(dir_path)
        report_path = report.generate_report(self.result, output_dir)
        self.status_bar.showMessage(f"Report exported to {report_path}")
        QMessageBox.information(
            self, "Export Complete",
            f"Report saved to:\n{report_path}",
        )


def launch_ui():
    """Launch the PyQt6 survival analysis application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
