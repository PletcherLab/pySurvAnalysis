"""The Focus window — author an experiment's Focuses (ADR-0011).

A **Focus** is a named slice of the factors and levels *discovered* in the data
file. This window is where one is made: tick the factors it names, tick and
order each one's levels (order is display order — legends, facets, plot
cells), pick each varying factor's **Reference Level**, and name the
treatments and their colours. The selection is live: N, the treatments, the
**Focus Shape** and anything that would block the Focus update as you edit, so
you can see before analysing whether the Factorial Battery will be offered.

No edit is written until Save, and Save writes the ``focuses:`` block of
``survival_config.yaml`` — the same block that can be edited by hand — with
every varying factor's Reference Level stated, so a later reorder cannot move
it. (Opening the window does write one thing: an experiment's *implicit*
Unfiltered or migrated Focus is materialised into the file first, as CONTEXT
says, so it can be seen and renamed.) A Focus renamed here takes its results
with it; one deleted here leaves its results as Orphaned Results for the Hub
to list. Factors and levels a Focus names that the data file lacks are shown,
marked, so they can be dropped rather than saved back unseen.

A factor left unticked is **pooled over**; a factor ticked with one level is a
**filter**; a factor ticked with two or more levels **varies** and labels the
treatments. The window says which, in words, under the factor list.
"""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..domain import focus as focusmod
from ..domain.focus import Focus
from ..help.window import HelpButton, install_f1, with_help

#: Rows every factor's level list shows before it scrolls — one height for
#: all, so a two-level factor does not collapse to a sliver beside a seven.
VISIBLE_LEVELS = 4


def _empty_factor_reasons(focus: Focus) -> list[str]:
    """A factor box ticked with no level ticked: neither a filter nor pooled
    over, so the Focus cannot be saved until it is one or the other."""
    return [f"factor {f!r} is ticked but none of its levels is — tick the "
            f"levels to keep, or untick {f} to pool over it"
            for f, levels in focus.factors.items() if not levels]


class _LevelList(QListWidget):
    """A level list exactly :data:`VISIBLE_LEVELS` rows tall.

    Measured from the rows themselves, at layout time: a hardcoded row height
    is wrong wherever the platform style or display scaling differs (rows on
    Windows run taller), and a mere maximum let the scroll area squeeze the
    list down to a single row."""

    def __init__(self) -> None:
        super().__init__()
        self.setSizePolicy(self.sizePolicy().horizontalPolicy(),
                           QSizePolicy.Policy.Fixed)

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        hint = super().sizeHint()
        row = self.sizeHintForRow(0) if self.count() else -1
        if row <= 0:
            row = self.fontMetrics().height() + 4
        hint.setHeight(VISIBLE_LEVELS * row + 2 * self.frameWidth())
        return hint

    def minimumSizeHint(self) -> QSize:  # noqa: N802 (Qt override)
        return QSize(super().minimumSizeHint().width(), self.sizeHint().height())


class _FactorBox(QGroupBox):
    """One factor: include it, tick and order its levels, and pick its
    Reference Level.

    Shows the Focus as it is, including what the data file no longer has: a
    level the Focus names but the file lacks is listed (marked, ticked) so it
    can be unticked, and a *stale* box (``stale=True``) stands for a whole
    factor the file lacks, so it can be dropped by unticking it. Hiding
    either would make them impossible to remove — and saved back unseen.
    """

    def __init__(self, factor: str, levels: tuple[str, ...], on_change,
                 *, stale: bool = False) -> None:
        super().__init__(f"{factor} — not in the data file" if stale else factor)
        self.factor = factor
        self.stale = stale
        #: The levels the data file has; anything else shown is stale.
        self._design_levels: tuple[str, ...] = () if stale else tuple(str(v) for v in levels)
        self._on_change = on_change
        self.setCheckable(True)
        self.setChecked(False)
        if stale:
            self.setToolTip(f"This Focus names factor {factor!r}, which the data "
                            f"file does not have, so it is Blocked. Untick the "
                            f"box to drop the factor from the Focus.")
        self.toggled.connect(lambda _on: self._changed())

        lay = QHBoxLayout(self)
        self.levels = _LevelList()
        self.levels.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.levels.setToolTip("Tick the levels this Focus keeps; drag (or use "
                               "▲▼) to set their display order.")
        for level in levels:
            self.levels.addItem(self._item(str(level), True))
        self.levels.itemChanged.connect(lambda _i: self._changed())
        self.levels.model().rowsMoved.connect(lambda *_a: self._changed())
        ## Top-aligned: the ▲▼/Reference column can stand taller than four
        ## rows, and a fixed-height list would otherwise float mid-box.
        lay.addWidget(self.levels, 1, Qt.AlignmentFlag.AlignTop)

        side = QVBoxLayout()
        up = QPushButton("▲")
        down = QPushButton("▼")
        for btn, step in ((up, -1), (down, 1)):
            btn.setFixedWidth(30)
            btn.clicked.connect(lambda _c, s=step: self._move(s))
            side.addWidget(btn)
        ref_head = QHBoxLayout()
        ref_head.setSpacing(4)
        ref_head.addWidget(QLabel("Reference:"))
        ref_head.addStretch(1)
        ref_head.addWidget(HelpButton("reference-level"))
        side.addLayout(ref_head)
        self.reference = QComboBox()
        self.reference.setToolTip(
            "The Cox baseline for this factor. Separate from display order, so "
            "levels can read 20x, 40x while the model baselines on the 40x "
            "control. Defaults to the first level ticked, and is saved "
            "explicitly, so reordering the levels later never moves it.")
        self.reference.currentIndexChanged.connect(lambda _i: self._on_change())
        side.addWidget(self.reference)
        side.addStretch(1)
        lay.addLayout(side)
        self._sync_reference()

    # ── state ──────────────────────────────────────────────────────────────

    def _item(self, level: str, checked: bool) -> QListWidgetItem:
        """A level row. The level itself rides in UserRole, so the label can
        say what is wrong with it without changing what is saved."""
        missing = level not in self._design_levels
        item = QListWidgetItem(f"{level}  (not in the data file)" if missing else level)
        item.setData(Qt.ItemDataRole.UserRole, level)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable
                      | Qt.ItemFlag.ItemIsDragEnabled)
        item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        if missing:
            item.setForeground(QColor("#b91c1c"))
            item.setToolTip(f"The data file has no level {level!r} of "
                            f"{self.factor}, so this Focus is Blocked. Untick "
                            f"it to drop it from the Focus.")
        return item

    @staticmethod
    def _level(item: QListWidgetItem) -> str:
        value = item.data(Qt.ItemDataRole.UserRole)
        return str(value) if value is not None else item.text()

    def chosen_levels(self) -> list[str]:
        return [self._level(self.levels.item(i)) for i in range(self.levels.count())
                if self.levels.item(i).checkState() == Qt.CheckState.Checked]

    def reference_choice(self) -> str | None:
        """The Reference Level, when the factor varies (``None`` otherwise).

        The *effective* one — the first level when nobody chose — so a saved
        Focus always states its baseline, and reordering levels later (here
        or by hand) can never silently move the Cox baseline.
        """
        levels = self.chosen_levels()
        if len(levels) < 2:
            return None
        ref = self.reference.currentData()
        return ref if ref in levels else levels[0]

    def load(self, levels: list[str] | None, reference: str | None) -> None:
        """Show *levels* (ticked, in this order, others after unticked).

        Rebuilt from the data file's levels each time, plus whatever stale
        levels *this* Focus names, so one Focus's stale rows never linger
        into the next one's."""
        blocked = self.levels.blockSignals(True)
        self.levels.clear()
        if levels is None:
            self.setChecked(False)
            for level in self._design_levels:
                self.levels.addItem(self._item(level, True))
        else:
            self.setChecked(True)
            named = [str(lv) for lv in levels]
            for level in named + [lv for lv in self._design_levels if lv not in named]:
                self.levels.addItem(self._item(level, level in named))
        self.levels.blockSignals(blocked)
        self._sync_reference(reference)

    # ── internals ──────────────────────────────────────────────────────────

    def _move(self, step: int) -> None:
        row = self.levels.currentRow()
        target = row + step
        if row < 0 or not 0 <= target < self.levels.count():
            return
        item = self.levels.takeItem(row)
        self.levels.insertItem(target, item)
        self.levels.setCurrentRow(target)
        self._changed()

    def _changed(self) -> None:
        self._sync_reference()
        self._on_change()

    def _sync_reference(self, wanted: str | None = None) -> None:
        current = wanted or self.reference.currentData()
        levels = self.chosen_levels()
        blocked = self.reference.blockSignals(True)
        self.reference.clear()
        for level in levels:
            self.reference.addItem(level, level)
        index = self.reference.findData(current) if current else -1
        self.reference.setCurrentIndex(index if index >= 0 else 0)
        self.reference.setEnabled(self.isChecked() and len(levels) >= 2)
        self.reference.blockSignals(blocked)


class FocusWindow(QDialog):
    """Author every Focus of one experiment; Save writes them all."""

    def __init__(self, parent, experiment, *, select: str | None = None,
                 new: bool = False, log=None) -> None:
        super().__init__(parent)
        self.experiment = experiment
        self._log = log or (lambda _m: None)
        self.setWindowTitle(f"Focuses — {experiment.name}")
        self.setMinimumSize(980, 640)
        #: Set on a successful Save: the Focus to make active.
        self.selected_name: str | None = None

        self.design = experiment.design()
        try:
            self._raw, _factors = experiment.load()
        except Exception as exc:  # noqa: BLE001 - still editable, just no preview
            self._raw = None
            self._log(f"[focus] preview unavailable: {exc}")

        experiment.materialize_focuses()
        #: Working copies, each with the name it had on disk (None = new).
        self._focuses: list[Focus] = [f.copy() for f in experiment.focuses()]
        self._origin: list[str | None] = [f.name for f in self._focuses]
        self._current = -1
        self._loading = False

        outer = QVBoxLayout(self)
        intro = QLabel(
            "A Focus is a named slice of the factors and levels found in "
            f"<b>{experiment.data_file().name}</b>. Each is analysed on its own, "
            "and every output carries its name. Untick a factor to pool over "
            "it; tick one level to keep only that level.")
        intro.setWordWrap(True)
        outer.addWidget(with_help(intro, "focus"))
        install_f1(self, lambda: "focus-window")

        split = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(split, 1)

        # ---- left: the list ----------------------------------------------
        left = QWidget()
        llay = QVBoxLayout(left)
        llay.setContentsMargins(0, 0, 0, 0)
        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_select)
        llay.addWidget(self._list, 1)
        ## Every button carries its "?" so the column stays one width.
        for text, slot, tip, topic in (
                ("New", self._new, "A new Focus over every discovered factor.",
                 "focus-window"),
                ("Duplicate", self._duplicate, "Copy the selected Focus.",
                 "focus-window"),
                ("Delete", self._delete,
                 "Remove the selected Focus. Its results stay on disk as "
                 "Orphaned Results until adopted or deleted in the Hub.",
                 "focus-status"),
                ("Import from DefinedPlots…", self._import_defined,
                 "Propose a Focus for each Defined Plot in the workbook whose "
                 "treatments form a rectangular product of levels.",
                 "defined-plots"),
                ("Copy Focuses from…", self._copy_from,
                 "Copy Focuses from another member of this Project, checked "
                 "against this member's data before anything is added.",
                 "focus-window")):
            btn = QPushButton(text)
            btn.setToolTip(tip)
            btn.clicked.connect(slot)
            llay.addWidget(with_help(btn, topic))
            if text.startswith("Import"):
                self._btn_import = btn
                btn.setEnabled(experiment.data_file().suffix.lower() == ".xlsx")
            if text.startswith("Copy"):
                btn.setEnabled(getattr(experiment, "project", None) is not None)
        split.addWidget(left)

        # ---- right: the editor -------------------------------------------
        right = QWidget()
        rlay = QVBoxLayout(right)
        rlay.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        self._name = QLineEdit()
        self._name.textEdited.connect(lambda _t: self._on_edit())
        form.addRow("Name:", with_help(self._name, "focus-window"))
        rlay.addLayout(form)

        boxes = QWidget()
        blay = QVBoxLayout(boxes)
        blay.setContentsMargins(0, 0, 0, 0)
        self._boxes_layout = blay
        self._boxes: dict[str, _FactorBox] = {}
        #: The selected Focus's factors the data file lacks — rebuilt on each
        #: selection, one unticked-to-drop box each.
        self._stale_boxes: dict[str, _FactorBox] = {}
        for factor in self.design.factors:
            box = _FactorBox(factor, self.design.levels.get(factor, ()), self._on_edit)
            self._boxes[factor] = box
            blay.addWidget(box)
        blay.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(boxes)
        rlay.addWidget(scroll, 2)

        self._preview = QLabel("")
        self._preview.setWordWrap(True)
        self._preview.setTextFormat(Qt.TextFormat.RichText)
        rlay.addWidget(with_help(self._preview, "focus-shape"))

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Treatment", "Display name", "Colour"])
        self._table.verticalHeader().setVisible(False)
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._table.itemChanged.connect(lambda _i: self._harvest_presentation())
        rlay.addWidget(self._table, 1)
        split.addWidget(right)
        split.setSizes([240, 740])

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        self._refresh_list()
        if new:
            self._new()
        else:
            names = [f.name for f in self._focuses]
            self._list.setCurrentRow(names.index(select) if select in names else 0)

    # ── the list ───────────────────────────────────────────────────────────

    def _refresh_list(self) -> None:
        blocked = self._list.blockSignals(True)
        row = self._current
        self._list.clear()
        for focus in self._focuses:
            self._list.addItem(focus.name)
        self._list.blockSignals(blocked)
        if 0 <= row < self._list.count():
            self._list.setCurrentRow(row)

    def _unique(self, stem: str) -> str:
        taken = {f.slug for f in self._focuses}
        name, n = stem, 2
        while focusmod.slugify(name) in taken:
            name, n = f"{stem} {n}", n + 1
        return name

    def _add(self, focus: Focus, origin: str | None = None) -> None:
        self._focuses.append(focus)
        self._origin.append(origin)
        self._refresh_list()
        self._list.setCurrentRow(len(self._focuses) - 1)

    def _new(self) -> None:
        base = focusmod.unfiltered(self.design)
        self._add(base.copy(name=self._unique("New focus"), origin="declared"))

    def _duplicate(self) -> None:
        if self._current < 0:
            return
        focus = self._focuses[self._current]
        self._add(focus.copy(name=self._unique(f"{focus.name} copy")))

    def _delete(self) -> None:
        if self._current < 0:
            return
        if len(self._focuses) == 1:
            QMessageBox.information(self, "Delete Focus",
                                    "An experiment needs at least one Focus.")
            return
        del self._focuses[self._current]
        del self._origin[self._current]
        self._current = min(self._current, len(self._focuses) - 1)
        self._refresh_list()
        self._on_select(self._current)

    def _on_select(self, row: int) -> None:
        self._current = row
        if not 0 <= row < len(self._focuses):
            return
        focus = self._focuses[row]
        self._loading = True
        self._name.setText(focus.name)
        self._rebuild_stale_boxes(focus)
        for factor, box in self._all_boxes().items():
            box.load(focus.factors.get(factor), focus.reference.get(factor))
        self._loading = False
        self._refresh_preview()

    def _rebuild_stale_boxes(self, focus: Focus) -> None:
        """One box per factor *focus* names that the data file lacks, above
        the discovered ones — ticked, so unticking drops the factor."""
        for box in self._stale_boxes.values():
            self._boxes_layout.removeWidget(box)
            box.deleteLater()
        self._stale_boxes = {}
        for index, (factor, levels) in enumerate(
                (f, lv) for f, lv in focus.factors.items() if f not in self._boxes):
            box = _FactorBox(factor, tuple(levels), self._on_edit, stale=True)
            self._stale_boxes[factor] = box
            self._boxes_layout.insertWidget(index, box)

    def _all_boxes(self) -> dict[str, _FactorBox]:
        return {**self._boxes, **self._stale_boxes}

    # ── editing ────────────────────────────────────────────────────────────

    def _focus_from_widgets(self) -> Focus:
        """The selected Focus as the widgets show it.

        The Focus's own factor order is kept (newly ticked factors follow, in
        the data file's order): the treatment labels are built in that order,
        and an edit to one level must not rename every treatment. A factor
        ticked with no level ticked is kept with no levels, so the preview
        and Save can refuse it — treating it as pooled over would be a
        different Focus from the one on screen. Each varying factor's
        Reference Level is written explicitly (see
        :meth:`_FactorBox.reference_choice`).
        """
        current = self._focuses[self._current]
        boxes = self._all_boxes()
        order = [f for f in current.factors if f in boxes] + \
            [f for f in boxes if f not in current.factors]
        factors: dict[str, list[str]] = {}
        reference: dict[str, str] = {}
        for factor in order:
            box = boxes[factor]
            if not box.isChecked():
                continue
            factors[factor] = box.chosen_levels()
            ref = box.reference_choice()
            if ref:
                reference[factor] = ref
        return current.copy(name=self._name.text().strip() or current.name,
                            factors=factors, reference=reference)

    def _on_edit(self) -> None:
        if self._loading or self._current < 0:
            return
        self._focuses[self._current] = self._focus_from_widgets()
        item = self._list.item(self._current)
        if item is not None:
            item.setText(self._focuses[self._current].name)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        focus = self._focuses[self._current]
        lines = [f"<b>{focus.name}</b>: {focus.describe(self.design)}"]
        populated: list[str] = []
        if self._raw is not None and focus.factors:
            frame = focusmod.apply_focus(self._raw, focus)
            populated = focusmod.populated_labels(frame)
            shape = focusmod.focus_shape(focus, frame)
            lines.append(f"N = {len(frame)} · {len(populated)} treatment(s) · "
                         f"shape {shape.describe()}")
            lines.append("This Focus " + focusmod.describe_offer(focus, shape) + ".")
            if shape.absent:
                lines.append("Absent cells (never in the data — not an error): "
                             + ", ".join(shape.absent))
        reasons = (focusmod.block_reasons(focus, self.design, populated)
                   if self._raw is not None else focusmod.stale_reasons(focus, self.design))
        reasons = _empty_factor_reasons(focus) + list(reasons)
        if not focus.factors:
            reasons = ["Tick at least one factor."]
        for reason in reasons:
            lines.append(f"<span style='color:#b91c1c'>Blocked: {reason}</span>")
        self._preview.setText("<br>".join(lines))
        self._fill_table(populated or focus.implied_labels())

    def _fill_table(self, labels: list[str]) -> None:
        from .plot_editor import ColorButton

        focus = self._focuses[self._current]
        self._loading = True
        self._table.setRowCount(0)
        for label in labels:
            row = self._table.rowCount()
            self._table.insertRow(row)
            key = QTableWidgetItem(label)
            key.setFlags(key.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self._table.setItem(row, 0, key)
            self._table.setItem(row, 1, QTableWidgetItem(
                focus.display_names.get(label, "")))
            swatch = ColorButton(focus.colours.get(label, ""))
            swatch.changed.connect(self._harvest_presentation)
            self._table.setCellWidget(row, 2, swatch)
        self._loading = False

    def _harvest_presentation(self) -> None:
        if self._loading or self._current < 0:
            return
        focus = self._focuses[self._current]
        names = dict(focus.display_names)
        colours = dict(focus.colours)
        for row in range(self._table.rowCount()):
            label = self._table.item(row, 0).text()
            text = (self._table.item(row, 1).text() if self._table.item(row, 1) else "").strip()
            if text and text != label:
                names[label] = text
            else:
                names.pop(label, None)
            swatch = self._table.cellWidget(row, 2)
            colour = swatch.color() if swatch is not None else ""
            if colour:
                colours[label] = colour
            else:
                colours.pop(label, None)
        self._focuses[self._current] = focus.copy(display_names=names, colours=colours)

    # ── importing ──────────────────────────────────────────────────────────

    def _pick_many(self, title: str, rows: list[tuple[str, str, bool]]) -> list[str]:
        """A checkable list; ``rows`` are ``(label, tooltip, selectable)``."""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        lay = QVBoxLayout(dialog)
        listing = QListWidget()
        for label, tip, ok in rows:
            item = QListWidgetItem(label)
            item.setToolTip(tip)
            if ok:
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
            listing.addItem(item)
        lay.addWidget(listing)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        lay.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return []
        return [listing.item(i).text() for i in range(listing.count())
                if listing.item(i).flags() & Qt.ItemFlag.ItemIsEnabled
                and listing.item(i).checkState() == Qt.CheckState.Checked]

    def _import_defined(self) -> None:
        from .. import data_loader

        plots = data_loader.load_defined_plots(self.experiment.data_file())
        if not plots:
            QMessageBox.information(self, "Import from DefinedPlots",
                                    "This workbook has no DefinedPlots sheet.")
            return
        proposals: dict[str, Focus] = {}
        rows = []
        for name, labels in plots:
            focus, why = focusmod.focus_from_defined_plot(name, labels, self.design)
            if focus is not None:
                proposals[name] = focus
            rows.append((name, why or focus.describe(self.design), focus is not None))
        chosen = self._pick_many("Import Focuses from DefinedPlots", rows)
        for name in chosen:
            focus = proposals[name]
            self._add(focus.copy(name=self._unique(name)))

    def _copy_from(self) -> None:
        project = getattr(self.experiment, "project", None)
        if project is None:
            return
        others = [m for m in project.members() if m.name != self.experiment.name]
        if not others:
            QMessageBox.information(self, "Copy Focuses",
                                    "This Project has no other member.")
            return
        names = [m.name for m in others]
        choice, ok = QInputDialog.getItem(self, "Copy Focuses from…",
                                          "Member:", names, 0, False)
        if not ok or not choice:
            return
        source = others[names.index(choice)]
        ## Checked against THIS member's active exclusions too: a Focus whose
        ## cell this member's QC emptied would be blocked here just the same.
        try:
            excluded = self.experiment.all_excluded_chambers()
        except Exception:  # noqa: BLE001 - no exclusions known is no exclusions
            excluded = set()
        ok_focuses, rejected = focusmod.copy_check(
            source.focuses(), self.design, existing=[f.name for f in self._focuses],
            excluded=excluded)
        for focus in ok_focuses:
            self._add(focus)
        if rejected:
            QMessageBox.information(
                self, "Copy Focuses",
                "Not copied — they would be blocked here or clash by name:\n\n"
                + "\n".join(rejected))

    # ── saving ─────────────────────────────────────────────────────────────

    def _confirm_stale(self, lines: list[str]) -> bool:
        """Ask before saving Focuses that name what the data file lacks."""
        answer = QMessageBox.question(
            self, "Save blocked Focuses?",
            "These Focuses name factors or levels the data file does not "
            "contain, so they will stay Blocked until the names are fixed:\n\n"
            + "\n".join(lines) + "\n\nSave anyway?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Save

    @staticmethod
    def _with_explicit_references(focus: Focus) -> Focus:
        """*focus* stating every varying factor's Reference Level.

        A reference left implicit is "the first level", so reordering the
        levels — here, or by hand in the YAML — would silently move the Cox
        baseline. Written out, only an explicit change of reference moves
        it; and since Out of Date compares *effective* references, writing
        the default down never puts a result Out of Date.
        """
        reference = {f: v for f, v in focus.reference.items()
                     if f in focus.factors and str(v) in focus.factors[f]}
        for factor in focus.varying_factors:
            reference[factor] = focus.reference_level(factor)
        return focus.copy(reference=reference)

    def accept(self) -> None:  # noqa: D102 - Qt override
        if self._current >= 0:
            self._harvest_presentation()
            ## What is on screen is what is saved — an unedited Focus's working
            ## copy is otherwise whatever was loaded, stale names and all.
            self._focuses[self._current] = self._focus_from_widgets()
        problems = [f"Focus {f.name!r}: {reason}" for f in self._focuses
                    for reason in _empty_factor_reasons(f)]
        if problems:
            QMessageBox.warning(self, "Cannot save", "\n".join(problems))
            return
        self._focuses = [self._with_explicit_references(f) for f in self._focuses]
        problems = focusmod.validate_focus_block(
            {"focuses": focusmod.focuses_to_config(self._focuses)})
        names = [f.name for f in self._focuses]
        if len(set(names)) != len(names):
            problems.append("Two Focuses share a name.")
        if problems:
            QMessageBox.warning(self, "Cannot save", "\n".join(problems))
            return
        stale = [f"- {reason}" for f in self._focuses
                 for reason in focusmod.stale_reasons(f, self.design)]
        if stale and not self._confirm_stale(stale):
            return
        renames = {old: f.name for old, f in zip(self._origin, self._focuses)
                   if old is not None and old != f.name}
        try:
            self.experiment.apply_focus_edits(
                [f.copy(origin="declared") for f in self._focuses], renames)
        except Exception as exc:  # noqa: BLE001 - say why, keep the window open
            QMessageBox.warning(self, "Cannot save", str(exc))
            return
        if 0 <= self._current < len(self._focuses):
            self.selected_name = self._focuses[self._current].name
        self._log(f"[focus] {self.experiment.name}: saved "
                  f"{len(self._focuses)} Focus(es)"
                  + (f"; renamed {', '.join(f'{a} → {b}' for a, b in renames.items())}"
                     if renames else ""))
        super().accept()
