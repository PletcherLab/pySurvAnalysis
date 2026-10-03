"""QC Viewer — chamber-overlay KM panels with hover identification.

For each treatment, draws all chambers' KM curves on one panel as
translucent lines. mplcursors hover annotations reveal the chamber id of
the line under the cursor; clicking a line toggles its excluded state.
"Save Exclusions…" persists the current state to ``qc/remove_chambers.csv``
under a user-named group.

The data is read exactly as a run reads it — the experiment's own data file,
``input:`` options and censoring policy — with one difference: no chamber is
removed, because QC has to show a chamber before anyone can decide about it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("QtAgg")  # noqa: E402

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT

from ..gui_env import sanitize_input_method_environment, use_agg_matplotlib

## Before Qt is imported, not after: the overrides are read when the
## platform plugin initialises.
sanitize_input_method_environment()
use_agg_matplotlib()

from PyQt6.QtCore import QSize, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import data_loader, exclusions, lifetable, plotting
from ..exclusions import normalize_chamber
from ..help.window import HelpButton, install_f1
from ..ui import ActionButton, Category, TopBar, apply_theme, icon, resolved_mode
from ..ui import settings as ui_settings

#: Line colours: kept, excluded, and kept-but-below-the-minimum-N.
_KEPT, _EXCLUDED, _SMALL = "#1f77b4", "#dc2626", "#d97706"


def _chamber_of(gid: str):
    """The chamber id a line's ``chamber-<id>`` gid names, normalised the way
    ``remove_chambers.csv`` is read, so a click and the file agree."""
    return normalize_chamber(gid.split("-", 1)[1])


def _experiment_for(directory: Path):
    """The Experiment Directory at *directory*, its Project's defaults
    applied — or ``None`` for a bare folder with no config."""
    from ..domain import Project, SurvivalExperiment, is_experiment_dir, is_project_dir

    if not is_experiment_dir(directory):
        return None
    project = None
    if is_project_dir(directory.parent):
        try:
            project = Project(directory.parent)
        except Exception:  # noqa: BLE001 - a broken project.yaml: no defaults
            project = None
    return SurvivalExperiment(directory, defaults=project.defaults if project else {},
                              project=project)


def _display_order(frame, design=None) -> list[str]:
    """The treatments of *frame* in display order — never alphabetical.

    A Focus slice carries its order (``apply_focus`` makes ``treatment``
    categorical); the whole file is ordered by the data file's own level
    order, the order every Focus starts from, with any label it cannot place
    (a blank factor) after the rest in order of appearance.
    """
    import pandas as pd

    try:
        from ..statistics import treatment_order
    except ImportError:                      # pragma: no cover - older stats module
        treatment_order = None

    col = frame["treatment"]
    if not isinstance(col.dtype, pd.CategoricalDtype) and design is not None \
            and design.factors:
        ranks = {f: {lv: i for i, lv in enumerate(design.levels.get(f, ()))}
                 for f in design.factors}
        present = list(dict.fromkeys(col.astype(str)))

        def _key(label: str) -> tuple:
            parts = label.split("/")
            if len(parts) != len(design.factors):
                return (1, present.index(label))
            ranked = [ranks[f].get(p) for f, p in zip(design.factors, parts)]
            if any(r is None for r in ranked):
                return (1, present.index(label))
            return (0, *ranked)

        frame = frame.assign(treatment=pd.Categorical(
            col.astype(str), categories=sorted(present, key=_key), ordered=True))
    if treatment_order is not None:
        return treatment_order(frame)
    col = frame["treatment"]
    present = set(col.astype(str))
    if isinstance(col.dtype, pd.CategoricalDtype):
        return [str(c) for c in col.cat.categories if str(c) in present]
    return list(dict.fromkeys(col.astype(str)))


class _ChamberPanel(QWidget):
    """One tab in the QC viewer: KM overlay for a single treatment."""

    def __init__(
        self,
        per_chamber_lt,
        treatment: str,
        excluded: set,
        on_toggle,
        parent: QWidget | None = None,
        *,
        time_label: str | None = None,
        small: dict | None = None,
        min_n: int = 0,
    ) -> None:
        super().__init__(parent)
        self._treatment = treatment
        self._excluded = set(excluded)
        self._on_toggle = on_toggle
        self._per_chamber_lt = per_chamber_lt
        #: chamber → N for chambers below ``global.min_n_per_chamber``.
        self._small = dict(small or {})

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._fig = plotting.plot_chamber_overlay_km(
            per_chamber_lt, treatment, excluded_chambers=self._excluded,
            time_label=time_label,
        )
        self._canvas = FigureCanvasQTAgg(self._fig)
        toolbar = NavigationToolbar2QT(self._canvas, self)
        outer.addWidget(toolbar)
        outer.addWidget(self._canvas, 1)

        ## The hover text says why a curve is amber: a chamber below the
        ## minimum is flagged for a decision, never dropped automatically.
        for line in self._chamber_lines():
            n = self._small.get(_chamber_of(line.get_gid()))
            if n is not None:
                line.set_label(f"{line.get_label()} — N={n}, below the "
                               f"minimum of {min_n} per chamber")

        self._wire_hover_and_click()
        self._restyle()

    def _chamber_lines(self):
        for ax in self._fig.axes:
            for line in ax.get_lines():
                if (line.get_gid() or "").startswith("chamber-"):
                    yield line

    def _wire_hover_and_click(self) -> None:
        try:
            import mplcursors

            cursor = mplcursors.cursor(self._fig, hover=True)

            @cursor.connect("add")
            def _on_add(sel):  # noqa: ANN001
                gid = sel.artist.get_gid() or ""
                label = sel.artist.get_label() or gid
                sel.annotation.set_text(label)
                sel.annotation.get_bbox_patch().set(alpha=0.85)

            self._mpl_cursor = cursor
        except Exception:  # noqa: BLE001
            pass

        self._canvas.mpl_connect("pick_event", self._on_pick)
        for ax in self._fig.axes:
            for line in ax.get_lines():
                line.set_picker(5)

    def _on_pick(self, event) -> None:  # noqa: ANN001
        gid = event.artist.get_gid() or ""
        if not gid.startswith("chamber-"):
            return
        chamber = _chamber_of(gid)
        if chamber in self._excluded:
            self._excluded.discard(chamber)
        else:
            self._excluded.add(chamber)
        self._on_toggle(chamber, chamber in self._excluded)
        self._restyle()

    def update_excluded(self, excluded: set) -> None:
        self._excluded = set(excluded)
        self._restyle()

    def _restyle(self) -> None:
        for line in self._chamber_lines():
            chamber = _chamber_of(line.get_gid())
            if chamber in self._excluded:
                line.set_color(_EXCLUDED)
                line.set_linestyle("--")
                line.set_alpha(0.7)
            elif chamber in self._small:
                line.set_color(_SMALL)
                line.set_linestyle("-")
                line.set_alpha(0.85)
            else:
                line.set_color(_KEPT)
                line.set_linestyle("-")
                line.set_alpha(0.4)
        self._canvas.draw_idle()


class QcViewerWindow(QMainWindow):
    """QC Viewer main window."""

    #: A group was written to ``qc/remove_chambers.csv`` (its name) — so a
    #: caller showing the directory's groups can refresh its list.
    exclusionsSaved = pyqtSignal(str)

    def __init__(self, project_dir: str | Path | None = None, focus=None,
                 experiment=None) -> None:
        super().__init__()
        self.setWindowTitle("pySurvAnalysis — QC Viewer")
        self.resize(1300, 820)

        self._project_dir: Path | None = None
        #: The Experiment Directory, when the folder is one: its config says
        #: how to read the data and which group is active. A caller that has
        #: one (the Hub) passes it, Project defaults already applied.
        self._given_experiment = experiment
        self._experiment = None
        #: The Hub's Active Focus. The viewer SHOWS its chambers — that is
        #: navigation — but the groups it saves belong to the directory: a
        #: chamber's validity is a fact about the chamber, not the slice.
        self._focus = focus
        self._data = None
        self._per_chamber_lt = None
        self._panels: dict[str, _ChamberPanel] = {}
        #: Treatments in display order — the tab order.
        self._order: list[str] = []
        self._excluded: set = set()
        #: The group the selection was loaded from, and what it held on disk —
        #: unsaved clicks are the difference.
        self._group: str = ""
        self._saved: set = set()
        #: chamber → N for chambers below ``global.min_n_per_chamber``.
        self._small: dict = {}
        self._min_n = 0

        self._build_ui()
        install_f1(self, lambda: "qc-viewer")

        if project_dir is not None:
            self._set_project(Path(project_dir))

    # --------------------------------------------------------------- UI

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._top_bar = TopBar("pySurvAnalysis — QC Viewer")
        save_btn = ActionButton(
            "Save Exclusions…", Category.LOAD, icon_name="save", primary=True,
        )
        save_btn.clicked.connect(self._save_exclusions)
        self._top_bar.add_right(save_btn)
        self._top_bar.add_right(HelpButton("exclusions"))

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

        side = QWidget()
        side_lay = QVBoxLayout(side)
        side_lay.setContentsMargins(12, 12, 12, 12)
        side_lay.setSpacing(8)
        side.setMinimumWidth(280)
        side.setMaximumWidth(380)

        side_lay.addLayout(self._heading("Project", "qc-viewer"))
        self._proj_label = QLabel("(no project)")
        self._proj_label.setStyleSheet("color: palette(mid); font-style: italic;")
        side_lay.addWidget(self._proj_label)

        pick_btn = QPushButton("Pick project…")
        pick_btn.clicked.connect(self._pick_project)
        side_lay.addWidget(pick_btn)

        self._focus_box = QCheckBox("")
        self._focus_box.setToolTip(
            "Show only the chambers in the Hub's Active Focus. Exclusions you "
            "save still apply to the whole directory, every Focus alike.")
        self._focus_box.setChecked(self._focus is not None)
        self._focus_box.setVisible(self._focus is not None)
        if self._focus is not None:
            self._focus_box.setText(f"Only Focus {self._focus.name}")
        self._focus_box.toggled.connect(lambda _on: self._reload_data())
        side_lay.addWidget(self._focus_box)

        side_lay.addLayout(self._heading("Active exclusion group", "exclusions"))
        self._group_combo = QComboBox()
        self._group_combo.setEditable(True)
        ## Typing a new name must not throw the selection away: only choosing
        ## an existing group (from the list, or Enter on its name) loads one.
        ## A typed name is just what Save offers to save under.
        self._group_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self._group_combo.currentIndexChanged.connect(self._on_group_changed)
        side_lay.addWidget(self._group_combo)

        side_lay.addWidget(QLabel("Excluded chambers"))
        self._exc_list = QListWidget()
        self._exc_list.itemDoubleClicked.connect(self._on_exc_double_click)
        side_lay.addWidget(self._exc_list, 1)

        self._small_label = QLabel("")
        self._small_label.setWordWrap(True)
        self._small_label.setStyleSheet(f"color: {_SMALL};")
        self._small_label.setVisible(False)
        side_lay.addWidget(self._small_label)

        bar = QHBoxLayout()
        clear_btn = QPushButton("Clear all")
        clear_btn.clicked.connect(self._clear_all)
        side_lay.addWidget(clear_btn)
        side_lay.addLayout(bar)

        splitter.addWidget(side)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._placeholder = QLabel(
            "Pick a project, then load.\n\n"
            "Each tab shows one treatment with all chambers' KM curves overlaid. "
            "Hover a curve to see its chamber id; click a curve to toggle the "
            "chamber's exclusion."
        )
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: palette(mid); font-style: italic;")
        self._tabs.addTab(self._placeholder, "QC")
        splitter.addWidget(self._tabs)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([320, 980])
        outer.addWidget(splitter, 1)

    @staticmethod
    def _heading(text: str, topic: str) -> QHBoxLayout:
        """A side-panel label with its "?" at the right."""
        row = QHBoxLayout()
        row.setSpacing(4)
        row.addWidget(QLabel(text))
        row.addStretch(1)
        row.addWidget(HelpButton(topic))
        return row

    # ------------------------------------------------------------ project

    def _pick_project(self) -> None:
        if not self._settle_unsaved():
            return
        path = QFileDialog.getExistingDirectory(self, "Pick project directory")
        if path:
            self._given_experiment = None
            self._set_project(Path(path))

    def _set_project(self, path: Path) -> None:
        path = path.expanduser().resolve()
        if not path.is_dir():
            QMessageBox.warning(self, "Not a directory", f"{path} is not a directory.")
            return
        self._project_dir = path
        self._proj_label.setText(str(path))
        given = self._given_experiment
        if given is not None and Path(given.directory).resolve() == path:
            self._experiment = given
        else:
            try:
                self._experiment = _experiment_for(path)
            except Exception:  # noqa: BLE001 - a bare folder still gets a viewer
                self._experiment = None

        ## Open on the experiment's ACTIVE group — the one its runs apply —
        ## not merely the first group the file happens to list.
        active = self._experiment.exclusion_group if self._experiment is not None else None
        self._fill_groups(active)
        self._load_group(self._group_combo.currentText().strip())
        self._reload_data()

    def _fill_groups(self, select: str | None) -> None:
        self._group_combo.blockSignals(True)
        self._group_combo.clear()
        groups = exclusions.list_groups(self._project_dir)
        if select and select not in groups:
            groups.append(select)
        for g in groups or ["default"]:
            self._group_combo.addItem(g)
        index = self._group_combo.findText(select) if select else 0
        self._group_combo.setCurrentIndex(max(index, 0))
        self._group_combo.blockSignals(False)

    def _load_group(self, group: str) -> None:
        self._group = group
        self._saved = set(exclusions.chambers_for_group(self._project_dir, group))
        self._excluded = set(self._saved)
        self._refresh_excluded_list()
        for panel in self._panels.values():
            panel.update_excluded(self._excluded)

    def _dirty(self) -> bool:
        return self._project_dir is not None and self._excluded != self._saved

    def _ask_unsaved(self) -> str:
        """``"save"``, ``"discard"`` or ``"cancel"`` for unsaved clicks."""
        answer = QMessageBox.question(
            self, "Unsaved exclusions",
            f"The chambers you clicked are not saved to group "
            f"'{self._group}'.\n\nSave them first?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        return {QMessageBox.StandardButton.Save: "save",
                QMessageBox.StandardButton.Discard: "discard"}.get(answer, "cancel")

    def _settle_unsaved(self) -> bool:
        """Save, discard or keep unsaved clicks; False = the user cancelled."""
        if not self._dirty():
            return True
        choice = self._ask_unsaved()
        if choice == "cancel":
            return False
        if choice == "save":
            self._write(self._group)
        return True

    def _on_group_changed(self, index: int) -> None:
        if self._project_dir is None or index < 0:
            return
        group = self._group_combo.itemText(index).strip()
        if group == self._group:
            return
        if not self._settle_unsaved():
            ## Back to the group whose clicks are still pending.
            self._group_combo.blockSignals(True)
            self._group_combo.setCurrentIndex(self._group_combo.findText(self._group))
            self._group_combo.blockSignals(False)
            return
        self._load_group(group)

    def _reload_data(self) -> None:
        if self._project_dir is None:
            return
        exp = self._experiment
        try:
            if exp is not None:
                ## The experiment's own reading of its data: its data file
                ## (refusing to guess between several), its `input:` options,
                ## its censoring policy — minus every exclusion.
                self._data, _factors = exp.load(apply_exclusions=False)
            else:
                path = self._bare_data_file()
                if path is None:
                    return
                self._data, _factors = data_loader.load_experiment(
                    path, excluded_chambers=set())
        except Exception as err:  # noqa: BLE001
            QMessageBox.warning(self, "Load failed", str(err))
            return

        design = exp.try_design() if exp is not None else None
        if self._focus is not None and self._focus_box.isChecked():
            from ..domain.focus import apply_focus

            self._data = apply_focus(self._data, self._focus)
        self._order = _display_order(self._data, design) if len(self._data) else []
        self._data["treatment"] = self._data["treatment"].astype(str)

        if "chamber" not in self._data.columns or self._data["chamber"].astype(str).eq("N/A").all():
            QMessageBox.information(
                self, "No chambers",
                "The loaded data does not have chamber-level information "
                "(e.g. CSV inputs). The QC viewer only applies to Excel files "
                "with a per-chamber Design sheet.",
            )
            return

        self._small = self._small_chambers()
        self._per_chamber_lt = lifetable.compute_lifetables_per_chamber(self._data)
        self._build_panels()
        self._refresh_excluded_list()

    def _bare_data_file(self) -> Path | None:
        """A folder with no config: the loader's own search, and a choice —
        never a silent pick — when it finds several files."""
        from ..domain.layout import data_candidates

        _base, found = data_candidates(self._project_dir)
        if not found:
            QMessageBox.warning(
                self, "No data",
                "No .xlsx, .csv, or .tsv file found in this directory or its "
                "data/ subdirectory.",
            )
            return None
        if len(found) == 1:
            return found[0]
        names = [p.name for p in found]
        choice, ok = QInputDialog.getItem(
            self, "Which data file?",
            f"This folder holds {len(found)} data files and no "
            f"survival_config.yaml to say which is the experiment.\nShow:",
            names, 0, False)
        return found[names.index(choice)] if ok and choice in names else None

    def _small_chambers(self) -> dict:
        """chamber → N for chambers holding fewer individuals than the
        experiment's ``global.min_n_per_chamber`` (0 = off)."""
        self._min_n = 0
        exp = self._experiment
        if exp is not None:
            g = exp.config.get("global") or {}
            value = g.get("min_n_per_chamber")
            if value is None:
                try:
                    value = exp.type.default_global.get("min_n_per_chamber", 0)
                except ValueError:
                    value = 0
            try:
                self._min_n = max(int(value or 0), 0)
            except (TypeError, ValueError):
                self._min_n = 0
        if not self._min_n:
            return {}
        sizes = self._data.groupby("chamber").size()
        return {normalize_chamber(c): int(n) for c, n in sizes.items()
                if int(n) < self._min_n}

    def _time_label(self) -> str | None:
        if self._experiment is None:
            return None
        try:
            return self._experiment.type.resolve_time_label(self._experiment.config)
        except ValueError:
            return None

    def _build_panels(self) -> None:
        # Remove placeholder + any old panels
        while self._tabs.count():
            w = self._tabs.widget(0)
            self._tabs.removeTab(0)
            if w is not None:
                w.deleteLater()
        self._panels.clear()
        if self._per_chamber_lt is None or len(self._per_chamber_lt) == 0:
            return
        present = set(self._per_chamber_lt["treatment"].astype(str))
        treatments = [t for t in self._order if t in present] + \
            [t for t in dict.fromkeys(self._per_chamber_lt["treatment"].astype(str))
             if t not in self._order]
        time_label = self._time_label()
        chambers_of = self._data.groupby("treatment")["chamber"].unique()
        for treatment in treatments:
            panel = _ChamberPanel(
                self._per_chamber_lt, treatment,
                self._excluded, self._on_panel_toggle, parent=self._tabs,
                time_label=time_label, small=self._small, min_n=self._min_n,
            )
            self._panels[treatment] = panel
            index = self._tabs.addTab(panel, treatment)
            small = sorted({normalize_chamber(c) for c in chambers_of.get(treatment, [])}
                           & set(self._small), key=str)
            if small:
                self._tabs.setTabToolTip(index, "Below the minimum of "
                                         f"{self._min_n} per chamber: "
                                         + ", ".join(f"{c} (N={self._small[c]})"
                                                     for c in small))

    # ------------------------------------------------------------ actions

    def _on_panel_toggle(self, chamber, is_excluded: bool) -> None:
        if is_excluded:
            self._excluded.add(chamber)
        else:
            self._excluded.discard(chamber)
        # Sync siblings
        for panel in self._panels.values():
            panel.update_excluded(self._excluded)
        self._refresh_excluded_list()

    def _refresh_excluded_list(self) -> None:
        self._exc_list.clear()
        sorted_items = sorted(self._excluded, key=lambda x: (isinstance(x, str), str(x).zfill(12)))
        for chamber in sorted_items:
            QListWidgetItem(f"Chamber {chamber}", self._exc_list)
        if self._small:
            listed = sorted(self._small, key=lambda x: (isinstance(x, str), str(x).zfill(12)))
            self._small_label.setText(
                f"Below the minimum of {self._min_n} individuals per chamber "
                f"(amber; flagged, not excluded): "
                + ", ".join(f"{c} (N={self._small[c]})" for c in listed))
        self._small_label.setVisible(bool(self._small))

    def _on_exc_double_click(self, item: QListWidgetItem) -> None:
        text = item.text()
        if not text.startswith("Chamber "):
            return
        self._excluded.discard(normalize_chamber(text[len("Chamber "):]))
        self._refresh_excluded_list()
        for panel in self._panels.values():
            panel.update_excluded(self._excluded)

    def _clear_all(self) -> None:
        self._excluded = set()
        self._refresh_excluded_list()
        for panel in self._panels.values():
            panel.update_excluded(self._excluded)

    def _write(self, group: str) -> Path:
        """Write the selection as *group*'s complete list (notes already in
        the file are kept) and make it the loaded group."""
        path = exclusions.write_exclusions(
            self._project_dir, group,
            sorted(self._excluded, key=lambda x: (isinstance(x, str), str(x).zfill(12))))
        self._group, self._saved = group, set(self._excluded)
        self.exclusionsSaved.emit(group)
        return path

    def _save_exclusions(self) -> None:
        if self._project_dir is None:
            return
        group, ok = QInputDialog.getText(
            self, "Save Exclusions",
            "Save exclusions as group:",
            text=self._group_combo.currentText().strip() or self._group or "default",
        )
        if not ok or not group.strip():
            return
        group = group.strip()
        path = self._write(group)
        QMessageBox.information(
            self, "Saved",
            f"Saved {len(self._excluded)} chamber(s) to {path.name} (group '{group}').",
        )
        self._fill_groups(group)

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        if not self._settle_unsaved():
            event.ignore()
            return
        super().closeEvent(event)

    def _toggle_theme(self) -> None:
        new_mode = "light" if resolved_mode() == "dark" else "dark"
        ui_settings.set_value("theme", new_mode)
        QMessageBox.information(
            self, "Theme changed",
            "Theme preference saved. Restart the app to apply."
        )


def main() -> None:
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, ui_settings.get("theme", "auto"))
    initial = sys.argv[1] if len(sys.argv) > 1 else None
    win = QcViewerWindow(initial)
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
