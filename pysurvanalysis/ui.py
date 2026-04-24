"""PyQt6 interactive UI for the survival analysis pipeline — v0.3.0

Major improvements:
* Modern Fusion theme with polished dark/light palette
* Dashboard summary panel with key experiment metrics
* New plot tabs: Nelson-Aalen, Log-Log diagnostic, Cumulative Events,
  Smoothed Hazard, Hazard Ratio Forest, Survival Distribution, KM+Risk Table
* Parametric models tab with AIC comparison table
* Styled statistics display (coloured significance)
* Drag-and-drop file / directory support
* Recent files/projects menu (last 5 entries)
* Export dialog supporting PNG, SVG, PDF
* Treatment selector with text filter
* Project directory support (auto-discovers .xlsx)
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

from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QMimeData
from PyQt6.QtGui import QAction, QColor, QDragEnterEvent, QDropEvent, QFont, QPalette
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QFrame,
    QButtonGroup,
    QRadioButton,
)

from . import data_loader, lifetable, plotting, statistics, report
from .pipeline import AnalysisResult


# ─────────────────────────────────────────────────────────────────────────────
# Theme helpers
# ─────────────────────────────────────────────────────────────────────────────

ACCENT = "#1f77b4"
ACCENT_HOVER = "#2a8fd4"
DANGER = "#d62728"
SUCCESS = "#2ca02c"
WARN = "#ff7f0e"

LIGHT_STYLE = """
QMainWindow, QWidget { background-color: #f5f5f5; color: #1a1a1a; }
QTabWidget::pane { border: 1px solid #cccccc; background: #ffffff; }
QTabBar::tab { background: #e0e0e0; color: #333333; padding: 6px 14px;
               border-radius: 4px 4px 0 0; margin-right: 2px; }
QTabBar::tab:selected { background: #ffffff; color: #1f77b4; font-weight: bold; }
QTabBar::tab:hover { background: #d0d8e8; }
QPushButton { background-color: #1f77b4; color: white; border: none;
              padding: 6px 14px; border-radius: 4px; font-size: 13px; }
QPushButton:hover { background-color: #2a8fd4; }
QPushButton:pressed { background-color: #155a8a; }
QPushButton:disabled { background-color: #aaaaaa; color: #666666; }
QGroupBox { border: 1px solid #cccccc; border-radius: 6px;
            margin-top: 10px; padding-top: 8px;
            font-weight: bold; color: #333333; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; top: -2px; }
QTextEdit, QTableWidget { background: #ffffff; border: 1px solid #cccccc;
                           border-radius: 4px; }
QScrollArea { border: none; }
QStatusBar { background: #e8e8e8; }
QLineEdit { background: #ffffff; border: 1px solid #cccccc; border-radius: 4px;
            padding: 3px 6px; }
QComboBox { background: #ffffff; border: 1px solid #cccccc; border-radius: 4px;
             padding: 3px 6px; }
"""

DARK_STYLE = """
QMainWindow, QWidget { background-color: #1e1e2e; color: #cdd6f4; }
QTabWidget::pane { border: 1px solid #45475a; background: #181825; }
QTabBar::tab { background: #313244; color: #bac2de; padding: 6px 14px;
               border-radius: 4px 4px 0 0; margin-right: 2px; }
QTabBar::tab:selected { background: #181825; color: #89b4fa; font-weight: bold; }
QTabBar::tab:hover { background: #3d3f5b; }
QPushButton { background-color: #89b4fa; color: #1e1e2e; border: none;
              padding: 6px 14px; border-radius: 4px; font-size: 13px; font-weight: bold; }
QPushButton:hover { background-color: #b4befe; }
QPushButton:pressed { background-color: #74c7ec; }
QPushButton:disabled { background-color: #45475a; color: #6c7086; }
QGroupBox { border: 1px solid #45475a; border-radius: 6px;
            margin-top: 10px; padding-top: 8px;
            font-weight: bold; color: #bac2de; }
QGroupBox::title { subcontrol-origin: margin; left: 10px; top: -2px; }
QTextEdit, QTableWidget { background: #181825; border: 1px solid #45475a;
                           border-radius: 4px; color: #cdd6f4; }
QScrollArea { border: none; }
QStatusBar { background: #313244; color: #bac2de; }
QLineEdit { background: #181825; border: 1px solid #45475a; border-radius: 4px;
            padding: 3px 6px; color: #cdd6f4; }
QComboBox { background: #181825; border: 1px solid #45475a; border-radius: 4px;
             padding: 3px 6px; color: #cdd6f4; }
"""


# ─────────────────────────────────────────────────────────────────────────────
# Column mapping dialog (CSV)
# ─────────────────────────────────────────────────────────────────────────────

class CsvColumnDialog(QDialog):
    """Dialog for mapping CSV columns to time, event, and factor roles."""

    def __init__(self, columns: list[str], parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV Column Mapping")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            "Map CSV columns to their roles.\n"
            "All unchecked columns in 'Factor columns' will be excluded."
        ))

        layout.addWidget(QLabel("Time column (survival time):"))
        self._time_combo = QComboBox()
        self._time_combo.addItems(columns)
        for candidate in ("Age", "age", "Time", "time", "T", "t"):
            if candidate in columns:
                self._time_combo.setCurrentText(candidate)
                break
        layout.addWidget(self._time_combo)

        layout.addWidget(QLabel("Event column (1=event, 0=censored):"))
        self._event_combo = QComboBox()
        self._event_combo.addItems(columns)
        for candidate in ("Event", "event", "Status", "status", "E", "e"):
            if candidate in columns:
                self._event_combo.setCurrentText(candidate)
                break
        layout.addWidget(self._event_combo)

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

        layout.addWidget(QLabel("Format hint:"))
        self._format_combo = QComboBox()
        self._format_combo.addItems(["auto", "long", "wide"])
        layout.addWidget(self._format_combo)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

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


# ─────────────────────────────────────────────────────────────────────────────
# Background analysis worker
# ─────────────────────────────────────────────────────────────────────────────

class AnalysisWorker(QThread):
    """Run the full analysis pipeline in a background thread."""

    finished = pyqtSignal(object)
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

            self.progress.emit("Computing lifetables (with Nelson-Aalen)...")
            lifetables = lifetable.compute_lifetables(individual_data)

            self.progress.emit("Computing statistics...")
            summary = statistics.summary_statistics(individual_data)
            median_surv = lifetable.median_survival(lifetables)
            mean_surv = lifetable.mean_survival(individual_data)

            self.progress.emit("Running log-rank tests...")
            pairwise_lr = statistics.pairwise_logrank(individual_data)
            omnibus_lr = statistics.logrank_multi(individual_data)

            self.progress.emit("Running Gehan-Wilcoxon tests...")
            pairwise_gw = statistics.pairwise_gehan_wilcoxon(individual_data)

            self.progress.emit("Computing hazard ratios...")
            hazard_ratios = statistics.pairwise_hazard_ratios(individual_data)

            self.progress.emit("Computing lifespan statistics...")
            lifespan_stats = lifetable.lifespan_statistics(
                individual_data, factors, assume_censored=self.assume_censored,
            )

            self.progress.emit("Computing survival quantiles...")
            surv_quantiles = lifetable.survival_quantiles(lifetables)

            self.progress.emit("Fitting parametric models...")
            try:
                parametric_models = statistics.fit_parametric_models(individual_data)
            except Exception:
                parametric_models = {}

            exp_summary = statistics.experiment_summary(individual_data)

            # Save CSV outputs
            self.output_dir.mkdir(parents=True, exist_ok=True)
            data_dir = self.output_dir / "data_output"
            data_dir.mkdir(exist_ok=True)
            stats_dir = self.output_dir / "statistics"
            stats_dir.mkdir(exist_ok=True)
            lifetables.to_csv(data_dir / "lifetables.csv", index=False)
            individual_data.to_csv(data_dir / "individual_data.csv", index=False)
            surv_quantiles.to_csv(stats_dir / "survival_quantiles.csv", index=False)
            if len(pairwise_lr) > 0:
                pairwise_lr.to_csv(stats_dir / "logrank_pairwise.csv", index=False)
            if len(pairwise_gw) > 0:
                pairwise_gw.to_csv(stats_dir / "gehan_wilcoxon_pairwise.csv", index=False)
            if len(hazard_ratios) > 0:
                hazard_ratios.to_csv(stats_dir / "hazard_ratios.csv", index=False)

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
                pairwise_gw=pairwise_gw,
                parametric_models=parametric_models,
                surv_quantiles=surv_quantiles,
                experiment_summary=exp_summary,
            )

            self.finished.emit(result)
        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")


# ─────────────────────────────────────────────────────────────────────────────
# Plot widget
# ─────────────────────────────────────────────────────────────────────────────

class PlotWidget(QWidget):
    """Widget containing a matplotlib figure with navigation toolbar."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.figure = plt.Figure(figsize=(10, 6))
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)
        self.setLayout(layout)

    def clear(self):
        self.figure.clear()
        self.canvas.draw()

    def update_figure(self, fig: plt.Figure):
        """Replace the current figure content with a new one."""
        self.figure.clear()
        for src_ax in fig.axes:
            ax = self.figure.add_subplot(111)
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
            for coll in src_ax.collections:
                from matplotlib.collections import PolyCollection
                if isinstance(coll, PolyCollection):
                    paths = coll.get_paths()
                    if paths:
                        verts = [p.vertices for p in paths]
                        new_coll = PolyCollection(
                            verts,
                            facecolors=coll.get_facecolor(),
                            edgecolors=coll.get_edgecolor(),
                            alpha=coll.get_alpha(),
                        )
                        ax.add_collection(new_coll)

            ax.set_xlabel(src_ax.get_xlabel())
            ax.set_ylabel(src_ax.get_ylabel())
            ax.set_title(src_ax.get_title())
            ax.set_xlim(src_ax.get_xlim())
            ax.set_ylim(src_ax.get_ylim())
            if src_ax.get_legend() is not None:
                ax.legend(loc="best")
            ax.grid(True, alpha=0.3)

        self.figure.tight_layout()
        self.canvas.draw()
        plt.close(fig)

    def export(self, path: str):
        """Export the current figure to a file (PNG, SVG, or PDF)."""
        self.figure.savefig(path, dpi=150, bbox_inches="tight")


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard summary panel
# ─────────────────────────────────────────────────────────────────────────────

class DashboardWidget(QWidget):
    """Key experiment metrics shown as a summary card row."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._cards: list[tuple[QLabel, QLabel]] = []

    def _make_card(self, title: str, value: str) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setLineWidth(1)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("font-size: 10px; color: #888888;")
        v_lbl = QLabel(value)
        v_lbl.setStyleSheet("font-size: 16px; font-weight: bold;")
        v_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        self._cards.append((t_lbl, v_lbl))
        return frame

    def set_data(self, result: AnalysisResult):
        # Clear
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._cards.clear()

        es = result.experiment_summary
        n_t = len(result.individual_data["treatment"].unique())
        n_total = len(result.individual_data)
        n_deaths = int(result.individual_data["event"].sum())
        pct_cens = round(100 * (n_total - n_deaths) / n_total, 1) if n_total > 0 else 0

        metrics = [
            ("Treatments", str(n_t)),
            ("Individuals", str(n_total)),
            ("Deaths", str(n_deaths)),
            ("% Censored", f"{pct_cens}%"),
        ]
        if es.get("n_chambers") is not None:
            metrics.insert(1, ("Chambers", str(es["n_chambers"])))

        if len(result.mean_surv) > 0 and not pd.isna(result.mean_surv["rmst"].mean()):
            mean_rmst = result.mean_surv["rmst"].mean()
            metrics.append(("Mean RMST", f"{mean_rmst:.0f}h"))

        for title, val in metrics:
            self._layout.addWidget(self._make_card(title, val))
        self._layout.addStretch()


# ─────────────────────────────────────────────────────────────────────────────
# Treatment selector with filter
# ─────────────────────────────────────────────────────────────────────────────

class TreatmentSelector(QGroupBox):
    """Checkboxes for selecting which treatments to display, with text filter."""

    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Treatments", parent)
        self.checkboxes: dict[str, QCheckBox] = {}
        self._layout = QVBoxLayout()

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filter treatments…")
        self._filter_edit.textChanged.connect(self._apply_filter)
        self._layout.addWidget(self._filter_edit)

        btn_layout = QHBoxLayout()
        btn_all = QPushButton("All")
        btn_none = QPushButton("None")
        btn_all.setFixedHeight(26)
        btn_none.setFixedHeight(26)
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._deselect_all)
        btn_layout.addWidget(btn_all)
        btn_layout.addWidget(btn_none)
        self._layout.addLayout(btn_layout)

        self._scroll = QScrollArea()
        self._cb_widget = QWidget()
        self._cb_layout = QVBoxLayout(self._cb_widget)
        self._cb_layout.setContentsMargins(0, 0, 0, 0)
        self._cb_layout.setSpacing(2)
        self._scroll.setWidget(self._cb_widget)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._layout.addWidget(self._scroll)
        self._layout.addStretch()
        self.setLayout(self._layout)

    def set_treatments(self, treatments: list[str]):
        for cb in self.checkboxes.values():
            self._cb_layout.removeWidget(cb)
            cb.deleteLater()
        self.checkboxes.clear()

        for t in sorted(treatments):
            cb = QCheckBox(t)
            cb.setChecked(True)
            cb.stateChanged.connect(lambda: self.selection_changed.emit())
            self.checkboxes[t] = cb
            self._cb_layout.addWidget(cb)

        self._filter_edit.clear()

    def _apply_filter(self, text: str):
        for t, cb in self.checkboxes.items():
            cb.setVisible(text.lower() in t.lower())

    def selected_treatments(self) -> list[str]:
        return [t for t, cb in self.checkboxes.items() if cb.isChecked()]

    def _select_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(True)

    def _deselect_all(self):
        for cb in self.checkboxes.values():
            cb.setChecked(False)


# ─────────────────────────────────────────────────────────────────────────────
# Data table widget
# ─────────────────────────────────────────────────────────────────────────────

class DataTableWidget(QWidget):
    """Filterable table display for DataFrames."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)

        self.filter_combo = QComboBox()
        self.filter_combo.addItem("All Treatments")
        self.filter_combo.currentTextChanged.connect(self._on_filter_changed)

        self._df: Optional[pd.DataFrame] = None

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter:"))
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        layout.addWidget(self.table)
        self.setLayout(layout)

    def set_data(self, df: pd.DataFrame):
        self._df = df
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


# ─────────────────────────────────────────────────────────────────────────────
# Statistics widget with colour-coded significance
# ─────────────────────────────────────────────────────────────────────────────

class StatisticsWidget(QWidget):
    """Rich statistics display with HTML colour-coded significance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.setFont(QFont("Courier New", 10))

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.text)
        self.setLayout(layout)

    @staticmethod
    def _sig_html(p: float) -> str:
        if p < 0.001:
            return f'<span style="color:#d62728;font-weight:bold">***</span>'
        if p < 0.01:
            return f'<span style="color:#d62728;font-weight:bold">**</span>'
        if p < 0.05:
            return f'<span style="color:#ff7f0e;font-weight:bold">*</span>'
        return '<span style="color:#888888">ns</span>'

    def set_results(self, result: AnalysisResult):
        html_parts = ['<pre style="font-family:Courier New,monospace;font-size:12px;">']

        # Excluded chambers
        excl = getattr(result, "excluded_chambers", set())
        if excl:
            sorted_excl = sorted(excl, key=lambda x: (str(type(x).__name__), x))
            html_parts.append(f'<span style="color:#d62728">{"!" * 70}\n')
            html_parts.append("EXCLUDED CHAMBERS (flagged in ChamberFlags sheet)\n")
            html_parts.append(f'{"!" * 70}</span>\n')
            html_parts.append(f"  {', '.join(str(c) for c in sorted_excl)}\n\n")

        # Omnibus log-rank
        lr = result.omnibus_lr
        html_parts.append(f'<span style="color:{ACCENT};font-weight:bold">{"=" * 70}\n')
        html_parts.append("OMNIBUS LOG-RANK TEST (all treatments)\n")
        html_parts.append(f'{"=" * 70}</span>\n')
        html_parts.append(f"  Chi-square:   {lr['chi2']:.4f}\n")
        html_parts.append(f"  df:           {lr['df']}\n")
        p = lr["p_value"]
        html_parts.append(f"  p-value:      {p:.6f}  {self._sig_html(p)}\n\n")

        # Pairwise log-rank
        html_parts.append(f'<span style="color:{ACCENT};font-weight:bold">{"=" * 70}\n')
        html_parts.append("PAIRWISE LOG-RANK TESTS (Bonferroni)\n")
        html_parts.append(f'{"=" * 70}</span>\n')
        if len(result.pairwise_lr) > 0:
            for _, row in result.pairwise_lr.iterrows():
                pb = row["p_bonferroni"]
                html_parts.append(f"\n  {row['group1']}  vs  {row['group2']}\n")
                html_parts.append(f"    Chi²:         {row['chi2']:.4f}\n")
                html_parts.append(f"    p raw:        {row['p_value']:.6f}\n")
                html_parts.append(f"    p Bonferroni: {pb:.6f}  {self._sig_html(pb)}\n")
        html_parts.append("\n")

        # Gehan-Wilcoxon
        pairwise_gw = getattr(result, "pairwise_gw", None)
        if pairwise_gw is not None and len(pairwise_gw) > 0:
            html_parts.append(f'<span style="color:{ACCENT};font-weight:bold">{"=" * 70}\n')
            html_parts.append("GEHAN-WILCOXON WEIGHTED LOG-RANK TESTS\n")
            html_parts.append(f'{"=" * 70}</span>\n')
            for _, row in pairwise_gw.iterrows():
                pb = row["p_bonferroni"]
                html_parts.append(f"\n  {row['group1']}  vs  {row['group2']}\n")
                html_parts.append(f"    Chi²:         {row['chi2']:.4f}\n")
                html_parts.append(f"    p Bonferroni: {pb:.6f}  {self._sig_html(pb)}\n")
            html_parts.append("\n")

        # Hazard ratios
        html_parts.append(f'<span style="color:{ACCENT};font-weight:bold">{"=" * 70}\n')
        html_parts.append("HAZARD RATIO ESTIMATES (O/E method)\n")
        html_parts.append(f'{"=" * 70}</span>\n')
        if len(result.hazard_ratios) > 0:
            for _, row in result.hazard_ratios.iterrows():
                html_parts.append(f"\n  {row['group1']}  vs  {row['group2']}\n")
                if pd.notna(row["hazard_ratio"]):
                    hr = row["hazard_ratio"]
                    color = DANGER if hr > 1.0 else SUCCESS
                    html_parts.append(f'    HR: <span style="color:{color};font-weight:bold">{hr:.4f}</span>  ')
                    html_parts.append(f"95% CI: ({row['hr_ci_lo']:.3f}, {row['hr_ci_hi']:.3f})\n")
                else:
                    html_parts.append("    HR: N/A\n")
        html_parts.append("\n")

        # Survival quantiles
        sq = getattr(result, "surv_quantiles", None)
        if sq is not None and len(sq) > 0:
            html_parts.append(f'<span style="color:{ACCENT};font-weight:bold">{"=" * 70}\n')
            html_parts.append("SURVIVAL QUANTILES (time at given survival fraction)\n")
            html_parts.append(f'{"=" * 70}</span>\n')
            q_cols = [c for c in sq.columns if c != "treatment"]
            header = f"  {'Treatment':<28s}  " + "  ".join(f"{c:>8s}" for c in q_cols)
            html_parts.append(header + "\n")
            html_parts.append("  " + "-" * (len(header) - 2) + "\n")
            for _, row in sq.iterrows():
                vals = "  ".join(
                    f"{row[c]:>8.1f}" if not pd.isna(row[c]) else "      NR"
                    for c in q_cols
                )
                html_parts.append(f"  {str(row['treatment']):<28s}  {vals}\n")
            html_parts.append("\n")

        # Lifespan stats
        ls = result.lifespan_stats
        if ls and "treatment_stats" in ls and len(ls["treatment_stats"]) > 0:
            ts = ls["treatment_stats"]
            html_parts.append(f'<span style="color:{ACCENT};font-weight:bold">{"=" * 70}\n')
            html_parts.append("LIFESPAN STATISTICS BY TREATMENT\n")
            html_parts.append(f'{"=" * 70}</span>\n')
            for _, row in ts.iterrows():
                html_parts.append(f"\n  {row['group']}\n")
                html_parts.append(f"    N={int(row['n'])}  Deaths={int(row['n_deaths'])}  Censored={int(row['n_censored'])}\n")
                mean_s = f"{row['mean_rmst']:.1f}" if pd.notna(row["mean_rmst"]) else "N/A"
                med_s = f"{row['median']:.1f}" if pd.notna(row["median"]) else "Not reached"
                html_parts.append(f"    Mean (RMST): {mean_s} hours\n")
                html_parts.append(f"    Median:      {med_s} hours\n")
            html_parts.append("\n")

        # Sample summary
        html_parts.append(f'<span style="color:{ACCENT};font-weight:bold">{"=" * 70}\n')
        html_parts.append("SAMPLE SUMMARY\n")
        html_parts.append(f'{"=" * 70}</span>\n')
        for _, row in result.summary.iterrows():
            html_parts.append(
                f"  {row['treatment']:<30s}  N={row['n_individuals']:4d}  "
                f"Deaths={row['n_deaths']:4d}  Censored={row['n_censored']:4d}  "
                f"({row['pct_censored']:.1f}% censored)\n"
            )

        html_parts.append("</pre>")
        self.text.setHtml("".join(html_parts))


# ─────────────────────────────────────────────────────────────────────────────
# Parametric models tab
# ─────────────────────────────────────────────────────────────────────────────

class ParametricModelsWidget(QWidget):
    """Display AIC comparison table for parametric survival models."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._table = QTableWidget()
        self._table.setAlternatingRowColors(True)
        self._note = QLabel(
            "Parametric AFT models (Weibull, Log-Normal, Log-Logistic) fitted per treatment.\n"
            "Lower AIC indicates better fit.  ✓ = best model."
        )
        self._note.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self._note)
        layout.addWidget(self._table)

    def set_data(self, parametric_models: dict):
        aic_df = parametric_models.get("aic_comparison")
        best = parametric_models.get("best_model_per_treatment", {})
        if aic_df is None or len(aic_df) == 0:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        cols = ["treatment", "model", "aic", "log_likelihood", "median_survival"]
        display_cols = ["Treatment", "Model", "AIC", "Log-Likelihood", "Median Survival"]
        self._table.setColumnCount(len(display_cols))
        self._table.setHorizontalHeaderLabels(display_cols)
        self._table.setRowCount(len(aic_df))

        for i, (_, row) in enumerate(aic_df.iterrows()):
            is_best = best.get(row["treatment"]) == row["model"]
            for j, col in enumerate(cols):
                val = row.get(col, "")
                if isinstance(val, float):
                    text = f"{val:.2f}" if not pd.isna(val) else "N/A"
                else:
                    text = str(val)
                if j == 1 and is_best:
                    text += " ✓"
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if is_best:
                    item.setBackground(QColor("#d4edda"))
                self._table.setItem(i, j, item)

        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )


# ─────────────────────────────────────────────────────────────────────────────
# Cox interaction analysis widget
# ─────────────────────────────────────────────────────────────────────────────

class CoxAnalysisWidget(QWidget):
    """Widget for configuring and running Cox PH and RMST interaction analyses."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._factors: list[str] = []
        self._result: Optional[AnalysisResult] = None

        layout = QVBoxLayout()

        config_tabs = QTabWidget()

        factor_tab = QWidget()
        factor_tab_layout = QVBoxLayout()
        self._factor_checkboxes: dict[str, QCheckBox] = {}
        self._factor_container = QVBoxLayout()
        factor_tab_layout.addLayout(self._factor_container)
        factor_tab_layout.addStretch()
        factor_tab.setLayout(factor_tab_layout)
        config_tabs.addTab(factor_tab, "Select Factors")

        filter_tab = QWidget()
        filter_layout = QVBoxLayout()

        factor_row = QHBoxLayout()
        factor_row.addWidget(QLabel("Filter Factor:"))
        self._filter_factor_combo = QComboBox()
        self._filter_factor_combo.addItem("(None)")
        self._filter_factor_combo.currentTextChanged.connect(self._on_filter_factor_changed)
        factor_row.addWidget(self._filter_factor_combo)
        factor_row.addStretch()
        filter_layout.addLayout(factor_row)

        level_row = QHBoxLayout()
        level_row.addWidget(QLabel("Filter Level:"))
        self._filter_level_combo = QComboBox()
        self._filter_level_combo.setEnabled(False)
        level_row.addWidget(self._filter_level_combo)
        level_row.addStretch()
        filter_layout.addLayout(level_row)

        filter_layout.addStretch()
        filter_tab.setLayout(filter_layout)
        config_tabs.addTab(filter_tab, "Filter Data")

        layout.addWidget(config_tabs)

        btn_layout = QHBoxLayout()
        self.run_cox_btn = QPushButton("Run Cox PH Analysis")
        self.run_cox_btn.setEnabled(False)
        self.run_cox_btn.clicked.connect(self._run_cox)
        btn_layout.addWidget(self.run_cox_btn)

        self.run_rmst_btn = QPushButton("Run RMST Analysis")
        self.run_rmst_btn.setEnabled(False)
        self.run_rmst_btn.clicked.connect(self._run_rmst)
        btn_layout.addWidget(self.run_rmst_btn)

        clear_btn = QPushButton("Clear Results")
        clear_btn.clicked.connect(self._clear_results)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Courier New", 10))
        layout.addWidget(self.results_text)

        self.setLayout(layout)

    def set_result(self, result: AnalysisResult):
        self._result = result
        self._factors = result.factors

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

        self._filter_factor_combo.blockSignals(True)
        self._filter_factor_combo.clear()
        self._filter_factor_combo.addItem("(None)")
        for f in self._factors:
            self._filter_factor_combo.addItem(f)
        self._filter_factor_combo.setCurrentIndex(0)
        self._filter_factor_combo.blockSignals(False)
        self._filter_level_combo.clear()
        self._filter_level_combo.setEnabled(False)

        self._update_run_buttons()
        self._render_results()

    def _selected_factors(self) -> list[str]:
        return [f for f, cb in self._factor_checkboxes.items() if cb.isChecked()]

    def _on_filter_factor_changed(self, text: str):
        self._filter_level_combo.clear()
        for f, cb in self._factor_checkboxes.items():
            cb.setVisible(True)
        if text == "(None)" or self._result is None:
            self._filter_level_combo.setEnabled(False)
        else:
            levels = sorted(self._result.individual_data[text].unique())
            for lv in levels:
                self._filter_level_combo.addItem(str(lv))
            self._filter_level_combo.setEnabled(True)
            if text in self._factor_checkboxes:
                self._factor_checkboxes[text].setVisible(False)
        self._update_run_buttons()

    def _get_filter(self) -> tuple[str | None, str | None]:
        factor = self._filter_factor_combo.currentText()
        if factor == "(None)":
            return None, None
        level = self._filter_level_combo.currentText()
        return factor, level if level else None

    def _apply_filter(self, data: "pd.DataFrame") -> "pd.DataFrame":
        factor, level = self._get_filter()
        if factor is None or level is None:
            return data
        return data[data[factor].astype(str) == level]

    def _update_run_buttons(self):
        filter_factor, _ = self._get_filter()
        available = [f for f in self._factors if f != filter_factor] if filter_factor else self._factors
        min_required = 2 if filter_factor else 1
        can_run = len(available) >= min_required
        self.run_cox_btn.setEnabled(can_run)
        self.run_rmst_btn.setEnabled(can_run)

    def _run_cox(self):
        if self._result is None:
            return
        filter_factor, filter_level = self._get_filter()
        selected = self._selected_factors()
        min_required = 2 if filter_factor else 1
        if len(selected) < min_required:
            QMessageBox.warning(self, "Insufficient Factors", "Select at least one factor to run.")
            return

        data = self._apply_filter(self._result.individual_data)
        cox_result = statistics.cox_interaction_analysis(data, self._result.factors, selected_factors=selected)
        if filter_factor:
            cox_result["filter_factor"] = filter_factor
            cox_result["filter_level"] = filter_level
        self._result.cox_analyses.append(cox_result)
        self._render_results()
        output_dir = self._result.input_file.parent / f"{self._result.input_file.stem}_results"
        report.generate_report(self._result, output_dir)

    def _run_rmst(self):
        if self._result is None:
            return
        filter_factor, filter_level = self._get_filter()
        selected = self._selected_factors()
        min_required = 2 if filter_factor else 1
        if len(selected) < min_required:
            QMessageBox.warning(self, "Insufficient Factors", "Select at least one factor to run.")
            return

        data = self._apply_filter(self._result.individual_data)
        rmst_result = statistics.rmst_interaction_analysis(data, self._result.factors, selected_factors=selected)
        if filter_factor:
            rmst_result["filter_factor"] = filter_factor
            rmst_result["filter_level"] = filter_level
        self._result.cox_analyses.append(rmst_result)
        self._render_results()
        output_dir = self._result.input_file.parent / f"{self._result.input_file.stem}_results"
        report.generate_report(self._result, output_dir)

    def _clear_results(self):
        if self._result is not None:
            self._result.cox_analyses.clear()
        self._render_results()

    def _render_results(self):
        if self._result is None or not self._result.cox_analyses:
            self.results_text.setPlainText(
                "No interaction analyses run yet.\n\n"
                "Select factors above and click an analysis button:\n\n"
                "  Cox PH:  Cox proportional hazards model.\n"
                "           Coefficients are log-hazard ratios.\n\n"
                "  RMST:    OLS on jackknife pseudo-values of RMST.\n"
                "           Coefficients in hours. No PH assumption.\n\n"
                "Results are appended to the report automatically."
            )
            return

        lines = []
        for i, result in enumerate(self._result.cox_analyses, 1):
            model_type = result.get("model_type", "cox_ph")
            is_rmst = model_type == "rmst_pseudo"
            type_label = "RMST" if is_rmst else "Cox PH"
            factors_str = ", ".join(result.get("factors_used", []))

            lines.append("=" * 70)
            lines.append(f"ANALYSIS {i} [{type_label}]: {factors_str}")
            lines.append("=" * 70)

            if "error" in result:
                lines.append(f"  ERROR: {result['error']}")
                lines.append("")
                continue

            if result.get("filter_factor"):
                lines.append(f"  Filter: {result['filter_factor']} == {result['filter_level']}")
            lines.append(f"  Model:     {result.get('formula', 'N/A')}")
            lines.append(f"  N subj:    {result.get('n_subjects', 'N/A')}")
            lines.append(f"  N events:  {result.get('n_events', 'N/A')}")

            if is_rmst:
                lines.append(f"  Tau:       {result.get('tau', 'N/A')} hours")
                lines.append(f"  RMST:      {result.get('rmst_overall', 'N/A')} hours")
                lines.append(f"  R²:        {result.get('r_squared', 'N/A')}")
                if result.get("f_p_value") is not None:
                    p = result["f_p_value"]
                    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                    lines.append(f"  F p-val:   {p:.6f}  {sig}")
            else:
                if result.get("concordance") is not None:
                    lines.append(f"  C-index:   {result['concordance']}")
                if result.get("AIC") is not None:
                    lines.append(f"  AIC:       {result['AIC']}")
            lines.append("")

            coefs = result.get("coefficients")
            if coefs is not None and len(coefs) > 0:
                for section_type, section_label in [
                    ("intercept", "INTERCEPT:"),
                    ("main_effect", "MAIN EFFECTS:"),
                    ("interaction", "INTERACTIONS:"),
                ]:
                    subset = coefs[coefs["term_type"] == section_type]
                    if len(subset) == 0:
                        continue
                    lines.append(f"  {section_label}")
                    for _, row in subset.iterrows():
                        p = row["p_value"]
                        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "   "
                        p_str = f"{p:.2e}" if p < 0.0001 else f"{p:.4f}"
                        if is_rmst:
                            lines.append(
                                f"    {row['covariate']:<28s}  coef={row['coef']:>8.2f}  "
                                f"SE={row['se']:>6.2f}  p={p_str:>10s} {sig}"
                            )
                        else:
                            lines.append(
                                f"    {row['covariate']:<28s}  HR={row['HR']:>7.4f}  "
                                f"p={p_str:>10s} {sig}"
                            )
                    lines.append("")

            if not is_rmst:
                lr = result.get("lr_interaction")
                if lr is not None:
                    p = lr["p_value"]
                    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                    lines.append(f"  LR interaction test: χ²={lr['lr_stat']:.4f}  "
                                 f"df={lr['df']}  p={p:.6f} {sig}")
                    lines.append("")

        self.results_text.setPlainText("\n".join(lines))


# ─────────────────────────────────────────────────────────────────────────────
# Defined plots widget
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# Export dialog
# ─────────────────────────────────────────────────────────────────────────────

class ExportDialog(QDialog):
    """Dialog to export the current plot or full report."""

    def __init__(self, plot_widget: PlotWidget, result: AnalysisResult, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Export")
        self.setMinimumWidth(400)
        self._plot_widget = plot_widget
        self._result = result

        layout = QVBoxLayout(self)

        export_grp = QGroupBox("Export options")
        export_layout = QVBoxLayout(export_grp)

        self._rb_plot_png = QRadioButton("Current plot as PNG")
        self._rb_plot_svg = QRadioButton("Current plot as SVG")
        self._rb_plot_pdf = QRadioButton("Current plot as PDF")
        self._rb_report = QRadioButton("Full Markdown report + all plots")
        self._rb_plot_png.setChecked(True)

        export_layout.addWidget(self._rb_plot_png)
        export_layout.addWidget(self._rb_plot_svg)
        export_layout.addWidget(self._rb_plot_pdf)
        export_layout.addWidget(self._rb_report)
        layout.addWidget(export_grp)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._do_export)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _do_export(self):
        if self._rb_report.isChecked():
            dir_path = QFileDialog.getExistingDirectory(
                self, "Select Export Directory",
                str(self._result.input_file.parent),
            )
            if not dir_path:
                return
            report_path = report.generate_report(self._result, Path(dir_path))
            QMessageBox.information(self, "Export Complete",
                                    f"Report saved to:\n{report_path}")
            self.accept()
            return

        ext = "png" if self._rb_plot_png.isChecked() else ("svg" if self._rb_plot_svg.isChecked() else "pdf")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", "",
            f"{ext.upper()} Files (*.{ext});;All Files (*)",
        )
        if not path:
            return
        self._plot_widget.export(path)
        QMessageBox.information(self, "Export Complete", f"Plot saved to:\n{path}")
        self.accept()


# ─────────────────────────────────────────────────────────────────────────────
# Main window
# ─────────────────────────────────────────────────────────────────────────────

class MainWindow(QMainWindow):
    """Main application window — survival analysis pipeline."""

    MAX_RECENT = 5

    def __init__(self):
        super().__init__()
        self.setWindowTitle("pySurvAnalysis v0.3.0 — Survival Analysis")
        self.setMinimumSize(1280, 850)

        self.result: Optional[AnalysisResult] = None
        self._current_file: Optional[Path] = None
        self._csv_params: dict = {}
        self._theme: str = "light"

        self._settings = QSettings("PletcherLab", "pySurvAnalysis")

        self._build_menu()
        self._build_ui()
        self._build_status_bar()
        self._apply_theme("light")

        self.setAcceptDrops(True)

    # ── Theme ──────────────────────────────────────────────────────────────

    def _apply_theme(self, theme: str):
        self._theme = theme
        self.setStyleSheet(DARK_STYLE if theme == "dark" else LIGHT_STYLE)

    # ── Drag-and-drop ──────────────────────────────────────────────────────

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir() or path.suffix.lower() in {".xlsx", ".csv", ".tsv"}:
                self.load_file(path)
                break

    # ── Menu bar ───────────────────────────────────────────────────────────

    def _build_menu(self):
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        open_action = QAction("&Open Experiment…", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_file)
        file_menu.addAction(open_action)

        open_dir_action = QAction("Open &Project Directory…", self)
        open_dir_action.setShortcut("Ctrl+Shift+O")
        open_dir_action.triggered.connect(self._open_directory)
        file_menu.addAction(open_dir_action)

        file_menu.addSeparator()

        export_action = QAction("&Export…", self)
        export_action.setShortcut("Ctrl+E")
        export_action.triggered.connect(self._show_export_dialog)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        # Recent files submenu
        self._recent_menu = file_menu.addMenu("Recent Files")
        self._rebuild_recent_menu()
        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut("Ctrl+Q")
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Analysis menu
        analysis_menu = menubar.addMenu("&Analysis")

        rerun_action = QAction("&Re-run with Selected Treatments", self)
        rerun_action.setShortcut("Ctrl+R")
        rerun_action.triggered.connect(self._rerun_selected)
        analysis_menu.addAction(rerun_action)

        # View menu
        view_menu = menubar.addMenu("&View")

        light_action = QAction("Light Theme", self)
        light_action.triggered.connect(lambda: self._apply_theme("light"))
        view_menu.addAction(light_action)

        dark_action = QAction("Dark Theme", self)
        dark_action.triggered.connect(lambda: self._apply_theme("dark"))
        view_menu.addAction(dark_action)

    def _rebuild_recent_menu(self):
        self._recent_menu.clear()
        recents = self._settings.value("recentFiles", []) or []
        if not recents:
            self._recent_menu.addAction("(none)").setEnabled(False)
            return
        for p in recents[:self.MAX_RECENT]:
            action = QAction(str(p), self)
            action.triggered.connect(lambda checked, path=p: self.load_file(Path(path)))
            self._recent_menu.addAction(action)

    def _add_recent(self, path: Path):
        recents = self._settings.value("recentFiles", []) or []
        p_str = str(path)
        if p_str in recents:
            recents.remove(p_str)
        recents.insert(0, p_str)
        self._settings.setValue("recentFiles", recents[:self.MAX_RECENT])
        self._rebuild_recent_menu()

    # ── UI layout ──────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_vbox = QVBoxLayout(central)
        main_vbox.setContentsMargins(4, 4, 4, 4)
        main_vbox.setSpacing(4)

        # Dashboard bar
        self.dashboard = DashboardWidget()
        main_vbox.addWidget(self.dashboard)

        # Splitter: left panel | tabs
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel
        left_panel = QVBoxLayout()
        left_panel.setContentsMargins(4, 4, 4, 4)

        load_btn = QPushButton("Open File / Directory")
        load_btn.clicked.connect(self._open_file)
        left_panel.addWidget(load_btn)

        self.assume_censored_cb = QCheckBox("Assume remaining are censored")
        self.assume_censored_cb.setChecked(True)
        self.assume_censored_cb.setToolTip(
            "Checked: cohort size from Design SampleSize;\n"
            "unaccounted individuals added as right-censored.\n\n"
            "Unchecked: cohort = deaths + explicit censored per chamber."
        )
        self.assume_censored_cb.stateChanged.connect(self._on_censoring_changed)
        left_panel.addWidget(self.assume_censored_cb)

        self.treatment_selector = TreatmentSelector()
        self.treatment_selector.selection_changed.connect(self._update_plots)
        left_panel.addWidget(self.treatment_selector)

        rerun_btn = QPushButton("Re-analyze Selected")
        rerun_btn.clicked.connect(self._rerun_selected)
        left_panel.addWidget(rerun_btn)

        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        left_widget.setMaximumWidth(240)

        # Right panel: tabs
        self.tabs = QTabWidget()
        self._build_tabs()

        splitter.addWidget(left_widget)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        main_vbox.addWidget(splitter)

    def _build_tabs(self):
        # KM curves
        self.km_plot = PlotWidget()
        self.tabs.addTab(self.km_plot, "Kaplan–Meier")

        # KM + risk table
        self.km_risk_plot = PlotWidget()
        self.tabs.addTab(self.km_risk_plot, "KM + Risk Table")

        # Nelson-Aalen
        self.na_plot = PlotWidget()
        self.tabs.addTab(self.na_plot, "Nelson–Aalen")

        # Log-Log diagnostic
        self.loglog_plot = PlotWidget()
        self.tabs.addTab(self.loglog_plot, "Log-Log (PH Check)")

        # Cumulative events
        self.cumevents_plot = PlotWidget()
        self.tabs.addTab(self.cumevents_plot, "Cumulative Events")

        # Hazard rate
        self.hazard_plot = PlotWidget()
        self.tabs.addTab(self.hazard_plot, "Hazard Rate")

        # Smoothed hazard
        self.smooth_hazard_plot = PlotWidget()
        self.tabs.addTab(self.smooth_hazard_plot, "Smoothed Hazard")

        # Survival distribution
        self.dist_plot = PlotWidget()
        self.tabs.addTab(self.dist_plot, "Survival Distribution")

        # Mortality
        self.mortality_plot = PlotWidget()
        self.tabs.addTab(self.mortality_plot, "Mortality (qx)")

        # Number at risk
        self.risk_plot = PlotWidget()
        self.tabs.addTab(self.risk_plot, "Number at Risk")

        # Hazard ratio forest
        self.forest_plot = PlotWidget()
        self.tabs.addTab(self.forest_plot, "HR Forest")

        # Lifetable data
        self.lifetable_view = DataTableWidget()
        self.tabs.addTab(self.lifetable_view, "Lifetable")

        # Statistics
        self.stats_view = StatisticsWidget()
        self.tabs.addTab(self.stats_view, "Statistics")

        # Summary
        self.summary_view = DataTableWidget()
        self.tabs.addTab(self.summary_view, "Summary")

        # Parametric models
        self.parametric_view = ParametricModelsWidget()
        self.tabs.addTab(self.parametric_view, "Parametric Models")

        # Cox / RMST interactions
        self.cox_view = CoxAnalysisWidget()
        self.tabs.addTab(self.cox_view, "Cox / RMST")

        # Defined Plots
        self.defined_plots_view = DefinedPlotsWidget()
        self._defined_plots_tab_idx = self.tabs.addTab(self.defined_plots_view, "Defined Plots")
        self.tabs.setTabVisible(self._defined_plots_tab_idx, False)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        self.status_bar.showMessage("Ready. Open an experiment file or project directory.")

    # ── File loading ───────────────────────────────────────────────────────

    def _open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Experiment File", "",
            "Experiment Files (*.xlsx *.xls *.csv *.tsv);;All Files (*)",
        )
        if path:
            self.load_file(Path(path))

    def _open_directory(self):
        dir_path = QFileDialog.getExistingDirectory(self, "Open Project Directory", "")
        if dir_path:
            self.load_file(Path(dir_path))

    def load_file(self, input_path: Path):
        """Load an experiment file or project directory."""
        self._current_file = input_path

        # Project directory: auto-discover xlsx
        if input_path.is_dir():
            xlsx_files = list(input_path.glob("*.xlsx"))
            if len(xlsx_files) == 0:
                QMessageBox.critical(self, "No Excel File",
                                     f"No .xlsx file found in:\n{input_path}")
                return
            if len(xlsx_files) > 1:
                QMessageBox.critical(self, "Multiple Excel Files",
                                     f"Found {len(xlsx_files)} .xlsx files. Place exactly one.")
                return
            xlsx_path = xlsx_files[0]
            output_dir = input_path
            self._csv_params = {}
            self.assume_censored_cb.setEnabled(True)
            assume_censored = data_loader.read_assume_censored(xlsx_path)
            self.assume_censored_cb.blockSignals(True)
            self.assume_censored_cb.setChecked(assume_censored)
            self.assume_censored_cb.blockSignals(False)
            self._add_recent(input_path)
            self._run_analysis(xlsx_path, output_dir=output_dir, assume_censored=assume_censored)
            return

        ext = input_path.suffix.lower()
        if ext in {".csv", ".tsv"}:
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
                QMessageBox.warning(self, "No Factors",
                                    "Select at least one factor column.")
                return

            self._csv_params = {
                "time_col": time_col,
                "event_col": event_col,
                "factor_cols": factor_cols,
                "csv_format": csv_format,
            }
            self.assume_censored_cb.setEnabled(False)
            self.assume_censored_cb.setToolTip("Not applicable for CSV/TSV input.")
            self._add_recent(input_path)
            self._run_analysis(input_path, assume_censored=True, **self._csv_params)
        else:
            self._csv_params = {}
            self.assume_censored_cb.setEnabled(True)
            self.assume_censored_cb.setToolTip(
                "Checked: cohort size from Design SampleSize.\n"
                "Unchecked: cohort = deaths + censored per chamber."
            )
            assume_censored = data_loader.read_assume_censored(input_path)
            self.assume_censored_cb.blockSignals(True)
            self.assume_censored_cb.setChecked(assume_censored)
            self.assume_censored_cb.blockSignals(False)
            self._add_recent(input_path)
            self._run_analysis(input_path, assume_censored=assume_censored)

    def _on_censoring_changed(self):
        if self._current_file is None:
            return
        assume_censored = self.assume_censored_cb.isChecked()
        # For directory mode, find the xlsx
        input_path = self._current_file
        output_dir = None
        if input_path.is_dir():
            xlsx_files = list(input_path.glob("*.xlsx"))
            if xlsx_files:
                output_dir = input_path
                input_path = xlsx_files[0]
        self._run_analysis(input_path, output_dir=output_dir,
                           assume_censored=assume_censored,
                           **getattr(self, "_csv_params", {}))

    def _run_analysis(
        self,
        input_path: Path,
        output_dir: Optional[Path] = None,
        assume_censored: bool = True,
        time_col: str = "Age",
        event_col: str = "Event",
        factor_cols: list[str] | None = None,
        csv_format: str = "auto",
    ):
        if output_dir is None:
            output_dir = input_path.parent / f"{input_path.stem}_results"

        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_bar.showMessage("Running analysis…")

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

        # Dashboard
        self.dashboard.set_data(result)

        # Update all tabs
        self._update_plots()
        self.lifetable_view.set_data(result.lifetables)
        self.stats_view.set_results(result)
        self.summary_view.set_data(result.summary)
        self.cox_view.set_result(result)
        self.parametric_view.set_data(result.parametric_models)

        # Defined plots tab
        dp = result.defined_plots
        if dp:
            self.defined_plots_view.set_data(result.lifetables, dp)
            self.tabs.setTabVisible(self._defined_plots_tab_idx, True)
        else:
            self.tabs.setTabVisible(self._defined_plots_tab_idx, False)

        # Generate report
        output_dir = result.input_file.parent / f"{result.input_file.stem}_results"
        report.generate_report(result, output_dir)

        self.status_bar.showMessage(
            f"Analysis complete: {result.input_file.name} — "
            f"{len(treatments)} treatments, {len(result.individual_data)} individuals. "
            f"Results saved to {output_dir.name}/"
        )

    def _on_analysis_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage("Analysis failed.")
        QMessageBox.critical(self, "Analysis Error", f"An error occurred:\n\n{msg}")

    # ── Plot updates ───────────────────────────────────────────────────────

    def _update_plots(self):
        if self.result is None:
            return

        selected = self.treatment_selector.selected_treatments()
        if not selected:
            for pw in (self.km_plot, self.km_risk_plot, self.na_plot,
                       self.loglog_plot, self.cumevents_plot,
                       self.hazard_plot, self.smooth_hazard_plot,
                       self.dist_plot, self.mortality_plot,
                       self.risk_plot, self.forest_plot):
                pw.clear()
            return

        lt = self.result.lifetables

        self.km_plot.update_figure(plotting.plot_km_curves(lt, treatments=selected))
        self.km_risk_plot.update_figure(plotting.plot_km_with_risk_table(lt, treatments=selected))
        self.na_plot.update_figure(plotting.plot_nelson_aalen(lt, treatments=selected))
        self.loglog_plot.update_figure(plotting.plot_log_log(lt, treatments=selected))
        self.cumevents_plot.update_figure(plotting.plot_cumulative_events(lt, treatments=selected))
        self.hazard_plot.update_figure(plotting.plot_hazard(lt, treatments=selected))
        self.smooth_hazard_plot.update_figure(plotting.plot_smoothed_hazard(lt, treatments=selected))

        ind = self.result.individual_data
        ind_sel = ind[ind["treatment"].isin(selected)]
        self.dist_plot.update_figure(plotting.plot_survival_distribution(ind_sel, treatments=selected))

        self.mortality_plot.update_figure(plotting.plot_mortality(lt, treatments=selected))
        self.risk_plot.update_figure(plotting.plot_number_at_risk(lt, treatments=selected))

        if len(self.result.hazard_ratios) > 0:
            self.forest_plot.update_figure(
                plotting.plot_hazard_ratio_forest(self.result.hazard_ratios)
            )

    # ── Re-analyze selected ────────────────────────────────────────────────

    def _rerun_selected(self):
        if self.result is None:
            QMessageBox.information(self, "No Data", "Load an experiment first.")
            return

        selected = self.treatment_selector.selected_treatments()
        if len(selected) < 2:
            QMessageBox.warning(self, "Insufficient Selection",
                                "Select at least 2 treatments to run statistical comparisons.")
            return

        subset = self.result.individual_data[
            self.result.individual_data["treatment"].isin(selected)
        ].copy()

        lt_subset = self.result.lifetables[
            self.result.lifetables["treatment"].isin(selected)
        ].copy()

        pairwise_lr = statistics.pairwise_logrank(subset)
        omnibus_lr = statistics.logrank_multi(subset)
        pairwise_gw = statistics.pairwise_gehan_wilcoxon(subset)
        hazard_ratios = statistics.pairwise_hazard_ratios(subset)
        summary = statistics.summary_statistics(subset)
        median_surv = lifetable.median_survival(lt_subset)
        mean_surv = lifetable.mean_survival(subset)
        lifespan_stats = lifetable.lifespan_statistics(
            subset, self.result.factors,
            assume_censored=self.result.assume_censored,
        )
        surv_quantiles = lifetable.survival_quantiles(lt_subset)
        exp_summary = statistics.experiment_summary(subset)

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
            pairwise_gw=pairwise_gw,
            surv_quantiles=surv_quantiles,
            experiment_summary=exp_summary,
        )

        self.stats_view.set_results(sub_result)
        self.summary_view.set_data(summary)
        self.tabs.setCurrentWidget(self.stats_view)
        self.status_bar.showMessage(f"Re-analyzed {len(selected)} treatments.")

    # ── Export ─────────────────────────────────────────────────────────────

    def _show_export_dialog(self):
        if self.result is None:
            QMessageBox.information(self, "No Data", "Load an experiment first.")
            return

        current_tab = self.tabs.currentWidget()
        plot_widget = None
        if hasattr(current_tab, "figure"):
            plot_widget = current_tab
        elif hasattr(current_tab, "_plot_widget"):
            plot_widget = current_tab._plot_widget

        if plot_widget is None:
            # Fall back to KM
            plot_widget = self.km_plot

        dlg = ExportDialog(plot_widget, self.result, parent=self)
        dlg.exec()

    # ── Close ──────────────────────────────────────────────────────────────

    def closeEvent(self, event):
        super().closeEvent(event)


# ─────────────────────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────────────────────

def launch_ui():
    """Launch the PyQt6 survival analysis application."""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
