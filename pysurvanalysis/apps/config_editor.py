"""``pysurv-config`` — describe one recording: its ``about:`` section.

A lifespan recording is described in its own folder, usually before any
Project exists, and a catalogue then files it from there (ADR-0014). This
window opens such a folder — a DLife workbook at its root or in ``data/``, or
the one ``data_file:`` names, with or without a ``survival_config.yaml`` — and
shows two tabs:

* **About** — the section's fields, in the person's own words: title, purpose,
  experimenter, series, the flies, the protocol, notes, each factor's kind
  and a line for what each level means. ``run:`` is the catalogue's and is
  shown, never typed. **Start from another recording…** fills in what
  recordings of one series share.
* **Design** — the workbook's design, read-only: its factors and levels, its
  chambers with their sample sizes, and the chambers its ChamberFlags sheet
  excludes. The design is the workbook's Design sheet; it is never declared
  in the config, and nothing here writes the workbook.

**Save** writes the ``about:`` section and nothing else
(:func:`config.write_about`): every other key is taken from the file as it is
on disk at that moment — ``focuses:``, ``scripts:``, ``exclusions:``,
``omit:``, ``global:`` — and a folder with no config gets one holding
``about:`` alone. Before writing, the window checks whether the file changed
since it read it — a catalogue rewrites the section after filing — and if it
did, asks: reload, overwrite, or cancel. It never overwrites silently.

No Experiment is constructed: loading one creates ``analysis/`` and ``qc/``,
and describing a folder must leave nothing in it but the config. Nothing here
is read by an analysis.
"""

from __future__ import annotations

import copy
import os
import sys
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..gui_env import sanitize_input_method_environment

## Before Qt is imported, not after: the overrides are read when the
## platform plugin initialises.
sanitize_input_method_environment()

from PyQt6.QtCore import QSize, Qt, pyqtSignal  # noqa: E402
from PyQt6.QtWidgets import (  # noqa: E402
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QScrollArea,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .. import about as about_mod  # noqa: E402
from ..domain import config as cfgmod  # noqa: E402
from ..help.window import HelpButton, install_f1  # noqa: E402
from ..ui import ActionButton, Category, TopBar, apply_theme, icon, resolved_mode  # noqa: E402
from ..ui import settings as ui_settings  # noqa: E402

APP_TITLE = "pySurvAnalysis — About Editor"
HELP_TOPIC = "config-about"

ABOUT_INTRO = (
    "What this recording is, in your own words: why it was run, who ran it, "
    "the flies, the protocol and what each level means. Every field is "
    "optional, and no analysis reads any of it. Save writes only the about: "
    "section of survival_config.yaml; Focuses, scripts, exclusions and every "
    "other setting stay as they are.")
RUN_TOOLTIP = (
    "The recording's id in the catalogue that filed it. Written by the "
    "catalogue, never typed here, and never copied to another recording.")
START_FROM_TOOLTIP = (
    "Fill in what recordings of one series share from another recording's "
    "survival_config.yaml: the experimenter, the series, the flies, the "
    "protocol, and each factor's kind and each level's meaning, for the "
    "factors and levels this workbook has. The title, the purpose and the "
    "notes stay this recording's own, and run: is never taken. Nothing is "
    "written until you save.")

#: What the lab's lifespans usually are, already typed into their fields
#: whenever the file gives none: the organism, the age at the start, and the
#: protocol's name. Part of the form as opened, so a folder never looks
#: changed for them; written with the first edit and save, like any field.
FIELD_DEFAULTS: dict[str, str] = {
    "organism": "Drosophila melanogaster",
    "age_at_start": "2-3 days old",
}
DEFAULT_PROTOCOL = "DLife Lifespan"

#: ``about:`` absent from the file — distinct from a section that is blank.
_NO_ABOUT = object()
#: The file is there but cannot be read: equal to nothing this window read,
#: so it always counts as a change.
_UNREADABLE = object()


# ---------------------------------------------------------------------------
# What the folder holds — read, never written
# ---------------------------------------------------------------------------

@dataclass
class FolderDesign:
    """The design of the data file a folder reads, for showing.

    *problem* says why there is none to show; it is ``""`` when *factors*
    were read. *chambers* is one row per Design-sheet chamber of a DLife
    workbook (``Chamber``, ``SampleSize`` and each factor), empty for a CSV.
    *unfinished* is True when the workbook's PrivateData says the lifespan is
    still running.
    """

    data_file: Path | None = None
    referenced: str = ""
    problem: str = ""
    factors: dict[str, list[str]] = field(default_factory=dict)
    chambers: list[dict] = field(default_factory=list)
    excluded: list = field(default_factory=list)
    unfinished: bool = False

    @property
    def declared(self) -> dict[str, list[str]] | None:
        """The factors and levels, or None when there is no design to check
        against."""
        return None if self.problem else dict(self.factors)


def _input_options(directory: Path, config: dict) -> dict:
    """How to read the folder's data file: its own ``input:`` over its
    Project's defaults, when it is a member. Only a CSV needs it."""
    defaults: dict = {}
    project_file = directory.parent / cfgmod.PROJECT_FILENAME
    if project_file.is_file():
        try:
            defaults = cfgmod.read_yaml(project_file).get("defaults") or {}
        except (OSError, ValueError):
            defaults = {}
    return cfgmod.input_options(cfgmod.merge_defaults(config, defaults))


def describe_folder(directory: str | Path, config: dict | None = None) -> FolderDesign:
    """What *directory*'s data file says about the design, read the way the
    classifier reads it (:func:`layout.data_location`) and never by
    constructing an Experiment. Nothing is written."""
    from .. import data_loader
    from ..domain import focus as focusmod
    from ..domain import layout

    directory = Path(directory)
    config = config if isinstance(config, dict) else {}
    out = FolderDesign()
    try:
        location = layout.data_location(directory, config=config)
    except Exception as err:  # noqa: BLE001 — said, never raised
        out.problem = f"The data file could not be found: {err}"
        return out
    if location.problem:
        out.problem = location.problem[:1].upper() + location.problem[1:] + "."
        return out
    if location.path is None:
        if location.candidates:
            names = ", ".join(p.name for p in location.candidates)
            out.problem = (f"{len(location.candidates)} data files ({names}): name "
                           f"the one this recording is with data_file: in "
                           f"{cfgmod.CONFIG_FILENAME}.")
        else:
            out.problem = ("No DLife workbook (.xlsx) or CSV at the folder's root "
                           "or in its data/ folder.")
        return out
    out.data_file = location.path
    if location.external:
        out.referenced = location.describe()
    try:
        design = focusmod.discover_design(location.path,
                                          _input_options(directory, config))
    except Exception as err:  # noqa: BLE001 — said, never raised
        out.problem = f"{location.path.name} could not be read: {err}"
        return out
    out.factors = {str(f): [str(level) for level in design.levels.get(f, ())]
                   for f in design.factors}
    if location.path.suffix.lower() == ".xlsx":
        try:
            frame, factors = data_loader.load_design(location.path)
            columns = ["Chamber", "SampleSize", *factors]
            out.chambers = [{c: row.get(c) for c in columns}
                            for row in frame.to_dict("records")]
        except Exception:  # noqa: BLE001 — the factors are shown without them
            out.chambers = []
        out.excluded = sorted(data_loader.load_chamber_flags(location.path), key=str)
        out.unfinished = data_loader.read_is_completed(location.path) is False
    return out


def _cell(value: Any) -> str:
    if value is None:
        return ""
    try:
        if value != value:                  # NaN: a blank cell
            return ""
    except TypeError:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _fixed_item(text: str) -> QTableWidgetItem:
    item = QTableWidgetItem(text)
    item.setFlags(Qt.ItemFlag.ItemIsEnabled)
    return item


def _fit_rows(table: QTableWidget) -> None:
    """Size *table* to its rows, so the page scrolls rather than the table."""
    table.resizeRowsToContents()
    rows = sum(table.rowHeight(r) for r in range(table.rowCount()))
    spare = 0 if table.rowCount() else 24
    table.setFixedHeight(table.horizontalHeader().sizeHint().height()
                         + rows + spare + 2 * table.frameWidth())


def _section_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setStyleSheet("font-weight: 600;")
    label.setContentsMargins(0, 10, 0, 0)
    return label


def _same_file(a: Path, b: Path) -> bool:
    try:
        return os.path.normcase(os.path.realpath(a)) == os.path.normcase(os.path.realpath(b))
    except OSError:
        return False


class _NoScrollComboBox(QComboBox):
    """A combo the page's scroll wheel passes over."""

    def wheelEvent(self, event):  # noqa: N802 — Qt API
        event.ignore()


# ---------------------------------------------------------------------------
# The About tab
# ---------------------------------------------------------------------------

class AboutForm(QWidget):
    """The ``about:`` section as a form (ADR-0014).

    Writes the section in the shared contract's order (``about.KEY_ORDER``)
    and keeps what it has no field for: ``run:`` — the catalogue's, shown and
    never typed — any key it does not know, and the other keys of a level's
    mapping, where only ``definition`` is this form's to change
    (``about.with_meaning``). A section nobody touched is written back exactly
    as the file had it.

    One row per factor the workbook has, for its kind, and one per level, for
    its meaning. A factor or level the file describes that the workbook does
    not have gets no row: it is not this form's to drop, so it is kept, and
    the checks below the form say it is undeclared.
    """

    #: Any field changed.
    changed = pyqtSignal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        #: The file's ``about:`` as loaded, written back while untouched.
        self._raw: Any = _NO_ABOUT
        #: What the form's edits are laid over: as loaded, or as started from
        #: another recording. Holds what the form has no field for.
        self._base: dict = {}
        #: :meth:`section` right after the load: what "untouched" means.
        self._at_load: dict = {}
        self._other_sex: list[str] = []
        self._factors: dict[str, list[str]] = {}
        #: The workbook's design is unknown: Start from… takes no factors.
        self._design_known = False
        self._config_path: Path | None = None
        self._filling = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        page = QWidget()
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        info_row = QHBoxLayout()
        info = QLabel(ABOUT_INTRO)
        info.setWordWrap(True)
        info_row.addWidget(info, 1)
        info_row.addWidget(HelpButton(HELP_TOPIC))
        layout.addLayout(info_row)

        start_row = QHBoxLayout()
        self.start_button = ActionButton("Start from another recording…",
                                         Category.NEUTRAL, icon_name="open")
        self.start_button.setToolTip(START_FROM_TOOLTIP)
        self.start_button.clicked.connect(self._choose_start_from)
        self.start_note = QLabel("")
        self.start_note.setWordWrap(True)
        self.start_note.setStyleSheet("font-style: italic;")
        start_row.addWidget(self.start_button)
        start_row.addWidget(self.start_note, 1)
        layout.addLayout(start_row)

        def _notes(placeholder: str, height: int) -> QPlainTextEdit:
            edit = QPlainTextEdit()
            edit.setPlaceholderText(placeholder)
            edit.setFixedHeight(height)
            edit.setTabChangesFocus(True)
            return edit

        form = self._form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        layout.addLayout(form)

        form.addRow(_section_label("This recording"))
        self.title = QLineEdit()
        self.title.setPlaceholderText(
            "One line, such as: Lifespan on two diets, InR knockdown, replicate 1")
        self.title_count = QLabel("")
        self.title_count.setToolTip(
            f"A title of up to {about_mod.TITLE_LIMIT} characters fits on one "
            "line in a list of recordings. A longer one is still saved.")
        self.title.textChanged.connect(self._on_title_changed)
        title_row = QHBoxLayout()
        title_row.addWidget(self.title, 1)
        title_row.addWidget(self.title_count)
        form.addRow("Title:", title_row)
        self.purpose = _notes(
            "One or two sentences: what was varied, in which flies, and what "
            "the lifespan should show.", 64)
        form.addRow("Purpose:", self.purpose)
        self.experimenter = QLineEdit()
        self.experimenter.setPlaceholderText("Who ran it, such as your lab handle")
        form.addRow("Experimenter:", self.experimenter)
        self.series = QLineEdit()
        self.series.setPlaceholderText(
            "Shared by recordings of one study, such as diet-inr-2026")
        form.addRow("Series:", self.series)
        self.run_value = QLabel("")
        self.run_value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.run_value.setToolTip(RUN_TOOLTIP)
        form.addRow("Run:", self.run_value)

        form.addRow(_section_label("The flies"))
        self.organism = QLineEdit()
        self.organism.setPlaceholderText("Such as Drosophila melanogaster")
        self.organism.setToolTip(
            f"Filled in as {FIELD_DEFAULTS['organism']} when the file names "
            "none. Change it, or clear it to leave it out.")
        form.addRow("Organism:", self.organism)
        sex_row = QHBoxLayout()
        self.sex_checks: dict[str, QCheckBox] = {}
        for value in about_mod.SEX_CHOICES:
            check = QCheckBox(value)
            check.toggled.connect(self._emit_changed)
            self.sex_checks[value] = check
            sex_row.addWidget(check)
        self.other_sex_label = QLabel("")
        sex_row.addWidget(self.other_sex_label)
        sex_row.addStretch(1)
        form.addRow("Sex:", sex_row)
        self.age_at_start = QLineEdit()
        self.age_at_start.setPlaceholderText(
            "At the start of the lifespan, such as 2-3 days")
        self.age_at_start.setToolTip(
            f"Filled in as {FIELD_DEFAULTS['age_at_start']} when the file says "
            "nothing. Change it, or clear it to leave it out.")
        form.addRow("Age at start:", self.age_at_start)

        form.addRow(_section_label("Protocol and notes"))
        self.protocol_edits = {name: QLineEdit() for name in about_mod.PROTOCOL_FIELDS}
        self.protocol_edits["name"].setPlaceholderText("Such as DLife Lifespan")
        self.protocol_edits["name"].setToolTip(
            f"Filled in as {DEFAULT_PROTOCOL} when the file names no protocol. "
            "Change it, or clear it to leave it out.")
        self.protocol_edits["version"].setPlaceholderText("Such as 4")
        self.protocol_edits["link"].setPlaceholderText(
            "Where the protocol is written down")
        form.addRow("Protocol:", self.protocol_edits["name"])
        form.addRow("Version:", self.protocol_edits["version"])
        form.addRow("Link:", self.protocol_edits["link"])
        self.notes = _notes("Anything else worth knowing about this recording.", 80)
        form.addRow("Notes:", self.notes)

        #: The text fields, by the key each is saved under.
        self._text_widgets: dict[str, QLineEdit | QPlainTextEdit] = {
            "title": self.title, "purpose": self.purpose,
            "experimenter": self.experimenter, "series": self.series,
            "organism": self.organism, "age_at_start": self.age_at_start,
            "notes": self.notes,
        }
        for widget in (*self._text_widgets.values(), *self.protocol_edits.values()):
            widget.textChanged.connect(self._emit_changed)
        #: The keys this form edits. Any other key of the section is kept.
        self._form_keys = {*self._text_widgets, about_mod.SEX_KEY,
                           about_mod.PROTOCOL_KEY, about_mod.FACTORS_KEY}

        layout.addWidget(_section_label("Factors and levels"))
        self.factors_hint = QLabel("")
        self.factors_hint.setWordWrap(True)
        layout.addWidget(self.factors_hint)
        self.kinds_table = QTableWidget(0, 2)
        self.kinds_table.setHorizontalHeaderLabels(["Factor", "Kind"])
        self.meanings_table = QTableWidget(0, 3)
        self.meanings_table.setHorizontalHeaderLabels(
            ["Factor", "Level", "What it means"])
        for table in (self.kinds_table, self.meanings_table):
            header = table.horizontalHeader()
            for column in range(table.columnCount() - 1):
                header.setSectionResizeMode(
                    column, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(table.columnCount() - 1,
                                        QHeaderView.ResizeMode.Stretch)
            table.verticalHeader().setVisible(False)
            table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            layout.addWidget(table)
        self.kinds_table.setMaximumWidth(360)

        layout.addWidget(_section_label("Checks"))
        self.checks = QLabel("")
        self.checks.setWordWrap(True)
        self.checks.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.checks)
        layout.addStretch(1)

        self.load({}, None)

    # -- signals -----------------------------------------------------------

    def _emit_changed(self, *_args) -> None:
        if not self._filling:
            self.changed.emit()

    def _on_title_changed(self, text: str) -> None:
        n = len(text.strip())
        self.title_count.setText(f"{n}/{about_mod.TITLE_LIMIT}" if n else "")
        self.title_count.setStyleSheet(
            "color: #d97706;" if n > about_mod.TITLE_LIMIT else "")

    # -- the factor and level rows ------------------------------------------

    def _kind_combo(self, kind: str) -> QComboBox:
        combo = _NoScrollComboBox()
        combo.addItem("", "")
        for value in about_mod.FACTOR_KINDS:
            combo.addItem(value, value)
        if kind and combo.findData(kind) < 0:
            combo.addItem(kind, kind)          # kept as the file has it
        combo.setCurrentIndex(max(combo.findData(kind), 0))
        combo.setToolTip("What kind of variable this factor is "
                         "(about.factors.<factor>.kind)")
        combo.currentIndexChanged.connect(self._emit_changed)
        return combo

    def _rebuild_rows(self, kinds: dict[str, str],
                      meanings: dict[tuple[str, str], str]) -> None:
        self.kinds_table.setRowCount(0)
        self.meanings_table.setRowCount(0)
        for name, levels in self._factors.items():
            r = self.kinds_table.rowCount()
            self.kinds_table.insertRow(r)
            self.kinds_table.setItem(r, 0, _fixed_item(name))
            self.kinds_table.setCellWidget(r, 1, self._kind_combo(kinds.get(name, "")))
            for level in dict.fromkeys(levels):
                r = self.meanings_table.rowCount()
                self.meanings_table.insertRow(r)
                self.meanings_table.setItem(r, 0, _fixed_item(name))
                self.meanings_table.setItem(r, 1, _fixed_item(level))
                edit = QLineEdit(meanings.get((name, level), ""))
                edit.setFrame(False)
                edit.setToolTip("A few words: the cross, the dose, the diet. "
                                "Optional; saved under about.factors.")
                edit.textChanged.connect(self._emit_changed)
                self.meanings_table.setCellWidget(r, 2, edit)
        _fit_rows(self.kinds_table)
        _fit_rows(self.meanings_table)
        if self._factors:
            self.factors_hint.setText(
                "What kind of variable each factor is, and a few words for each "
                "level: the cross, the dose, the diet. The rows are the "
                "workbook's factors and levels, from its Design sheet.")
        else:
            self.factors_hint.setText(
                "No factors to describe: the data file's design could not be "
                "read (see the Design tab). What the file already says about "
                "factors is kept as it is.")

    def kinds(self) -> dict[str, str]:
        """Each factor's kind as the rows show it (``""`` for none)."""
        return {self.kinds_table.item(r, 0).text():
                self.kinds_table.cellWidget(r, 1).currentData() or ""
                for r in range(self.kinds_table.rowCount())}

    def meanings(self) -> dict[tuple[str, str], str]:
        """Each level's meaning as the rows show it, in row order."""
        return {(self.meanings_table.item(r, 0).text(),
                 self.meanings_table.item(r, 1).text()):
                self.meanings_table.cellWidget(r, 2).text().strip()
                for r in range(self.meanings_table.rowCount())}

    def kind_combo(self, factor: str) -> QComboBox:
        """The kind dropdown of *factor*'s row."""
        for r in range(self.kinds_table.rowCount()):
            if self.kinds_table.item(r, 0).text() == factor:
                return self.kinds_table.cellWidget(r, 1)
        raise KeyError(factor)

    def meaning_edit(self, factor: str, level: str) -> QLineEdit:
        """The meaning field of the row for *level* of *factor*."""
        for r in range(self.meanings_table.rowCount()):
            if (self.meanings_table.item(r, 0).text() == factor
                    and self.meanings_table.item(r, 1).text() == level):
                return self.meanings_table.cellWidget(r, 2)
        raise KeyError((factor, level))

    # -- load / dump ---------------------------------------------------------

    def set_location(self, config_path: Path | None) -> None:
        """Which config this form edits: where **Start from another
        recording…** starts looking, and the one file it refuses."""
        self._config_path = Path(config_path) if config_path else None

    def load(self, config: dict, factors: dict[str, list[str]] | None) -> None:
        """Fill the form from *config*'s ``about:``, with one row per factor
        and level of *factors* (the workbook's; None when unknown)."""
        config = config if isinstance(config, dict) else {}
        self._raw = config.get(about_mod.ABOUT_KEY, _NO_ABOUT)
        self._base = copy.deepcopy(about_mod.read_about(config))
        self._design_known = factors is not None
        self._factors = {str(k): [str(v) for v in levels]
                         for k, levels in (factors or {}).items()}
        self._fill()
        self._at_load = self.section()
        self.start_note.setText("")
        self.refresh_checks()

    def note_saved(self, config: dict) -> None:
        """*config* was just written: its ``about:`` is now what "untouched"
        means. The form is left as it is."""
        config = config if isinstance(config, dict) else {}
        self._raw = config.get(about_mod.ABOUT_KEY, _NO_ABOUT)
        self._base = copy.deepcopy(about_mod.read_about(config))
        self._at_load = self.section()

    def _fill(self) -> None:
        """Set every widget from :attr:`_base`."""
        self._filling = True
        try:
            section = self._base
            for key, widget in self._text_widgets.items():
                text = about_mod._text(section.get(key))
                if isinstance(widget, QPlainTextEdit):
                    widget.setPlainText(text)
                else:
                    widget.setText(text)
            run = about_mod._text(section.get(about_mod.RUN_KEY))
            self.run_value.setText(run)
            self._form.setRowVisible(self.run_value, bool(run))

            sexes = about_mod.sex_values(section.get(about_mod.SEX_KEY))
            lowered = [value.lower() for value in sexes]
            for value, check in self.sex_checks.items():
                check.setChecked(value in lowered)
            self._other_sex = [value for value in sexes
                               if value.lower() not in self.sex_checks]
            self.other_sex_label.setText(
                f"also: {', '.join(self._other_sex)}" if self._other_sex else "")

            protocol = section.get(about_mod.PROTOCOL_KEY)
            if isinstance(protocol, str):
                protocol = {"name": protocol}
            protocol = protocol if isinstance(protocol, Mapping) else {}
            for name, edit in self.protocol_edits.items():
                edit.setText(about_mod._text(protocol.get(name)))

            ## The lab's usual values, where the file gives none. Filled before
            ## load() notes what the form says, so they never make a folder
            ## look changed; a field the file gives keeps the file's value.
            for key, value in FIELD_DEFAULTS.items():
                widget = self._text_widgets[key]
                if not widget.text().strip():
                    widget.setText(value)
            if not self.protocol_edits["name"].text().strip():
                self.protocol_edits["name"].setText(DEFAULT_PROTOCOL)

            notes = about_mod.factor_notes(section)
            kinds = {name: body["kind"] for name, body in notes.items() if body["kind"]}
            meanings = {(name, level): text for name, body in notes.items()
                        for level, text in body["levels"].items() if text}
            self._rebuild_rows(kinds, meanings)
        finally:
            self._filling = False

    def section(self) -> dict:
        """``about:`` as the form describes it, in the order it is written:
        the fields over what the form has no field for. ``{}`` when there is
        nothing to write."""
        section = {key: copy.deepcopy(value) for key, value in self._base.items()
                   if key not in self._form_keys}
        for key, widget in self._text_widgets.items():
            section[key] = (widget.toPlainText() if isinstance(widget, QPlainTextEdit)
                            else widget.text()).strip()
        section[about_mod.SEX_KEY] = [
            value for value, check in self.sex_checks.items() if check.isChecked()
        ] + self._other_sex
        kept = self._base.get(about_mod.PROTOCOL_KEY)
        protocol = ({key: copy.deepcopy(value) for key, value in kept.items()
                     if key not in about_mod.PROTOCOL_FIELDS}
                    if isinstance(kept, Mapping) else {})
        protocol.update({name: edit.text().strip()
                         for name, edit in self.protocol_edits.items()})
        section[about_mod.PROTOCOL_KEY] = protocol
        section[about_mod.FACTORS_KEY] = self._factors_section()
        return about_mod.clean_about(section)

    def _factors_section(self) -> dict:
        """``about.factors`` to write: the base's entries, with the rows laid
        over the factors and levels the workbook has."""
        base = self._base.get(about_mod.FACTORS_KEY)
        base = base if isinstance(base, Mapping) else {}
        kinds = self.kinds()
        meanings = self.meanings()
        out: dict = {}
        described: set[str] = set()
        for raw_name, body in base.items():
            name = str(raw_name).strip()
            described.add(name)
            if name not in self._factors:
                out[raw_name] = copy.deepcopy(body)        # no row: kept
                continue
            entry = self._factor_entry(name, body, kinds, meanings)
            if entry:
                out[name] = entry
        for name in self._factors:
            if name not in described:
                entry = self._factor_entry(name, {}, kinds, meanings)
                if entry:
                    out[name] = entry
        return out

    def _factor_entry(self, name: str, body: Any, kinds: dict,
                      meanings: dict) -> dict:
        body = body if isinstance(body, Mapping) else {}
        entry: dict = {}
        if kinds.get(name):
            entry["kind"] = kinds[name]
        base_levels = body.get("levels")
        base_levels = base_levels if isinstance(base_levels, Mapping) else {}
        declared = list(dict.fromkeys(self._factors.get(name, [])))
        levels: dict = {}
        described: set[str] = set()
        for raw_level, base_entry in base_levels.items():
            level = str(raw_level).strip()
            described.add(level)
            if level not in declared:
                levels[raw_level] = copy.deepcopy(base_entry)    # no row: kept
                continue
            ## Only the meaning is this form's: text stays text, and a
            ## mapping keeps its other keys.
            value = about_mod.with_meaning(base_entry, meanings.get((name, level), ""))
            if value is not None:
                levels[level] = value
        for level in declared:
            if level not in described and meanings.get((name, level)):
                levels[level] = meanings[(name, level)]
        if levels:
            entry["levels"] = levels
        entry.update({key: copy.deepcopy(value) for key, value in body.items()
                      if key not in ("kind", "levels")})
        return entry

    def is_untouched(self) -> bool:
        return self.section() == self._at_load

    def dump(self) -> Any:
        """The ``about:`` value to write, or ``{}`` for none.

        While the form says what it said at load, that is the file's own
        value, untouched: a section in another order, or holding something
        the form would write differently, must not look like an edit.
        """
        section = self.section()
        if section == self._at_load:
            return {} if self._raw is _NO_ABOUT else self._raw
        return section

    def refresh_checks(self) -> None:
        """Say what is odd about the section as the form now describes it."""
        section = self.section()
        declared = self._factors if self._design_known else None
        lines = cfgmod.check_about(section, declared) if section else []
        self.checks.setText("\n".join(f"• {line}" for line in lines)
                            if lines else "Nothing to point out.")
        self.checks.setStyleSheet("color: #d97706;" if lines else "")

    # -- Start from another recording… -----------------------------------------

    def start_from(self, earlier: Any) -> list[str]:
        """Fill in the shared part of *earlier* — another recording's
        ``about:`` — and return the fields taken (none when it has nothing
        this recording can use).

        ``about.start_from`` decides what that is: who ran it, the series,
        the flies, the protocol, and each factor's kind and each level's
        whole entry, for the factors and levels this workbook has. The title,
        the purpose, the notes and ``run:`` are never taken.
        """
        factors = self._factors if self._design_known else {}
        taken = list(about_mod.shared_about(earlier, factors))
        if not taken:
            return []
        self._base = about_mod.start_from(self.section(), earlier, factors)
        self._fill()
        self.refresh_checks()
        self.changed.emit()
        return taken

    def start_from_file(self, path: str | Path) -> bool:
        """:meth:`start_from` the ``about:`` of the config at *path*. What
        happened is said beside the button; True when something was taken."""
        path = Path(path)
        label = f"{path.parent.name}/{path.name}"
        if self._config_path is not None and _same_file(path, self._config_path):
            self.start_note.setText(
                f"{label} is this recording's own config: choose another "
                "recording's.")
            return False
        try:
            config = cfgmod.read_yaml(path)
        except Exception as err:  # noqa: BLE001 — said, never raised in a slot
            self.start_note.setText(f"Could not read {label}: {err}")
            return False
        earlier = about_mod.read_about(config)
        taken = self.start_from(earlier)
        if not taken:
            self.start_note.setText(
                f"{label} has nothing to start from: no about: section, or none "
                "of what recordings share for the factors this workbook has.")
            return False
        everything = about_mod.shared_about(earlier).get(about_mod.FACTORS_KEY)
        kept = about_mod.shared_about(
            earlier, self._factors if self._design_known else {}).get(
                about_mod.FACTORS_KEY)
        left_out = ("" if everything == kept else
                    " What it says of factors or levels this workbook does not "
                    "have was left out.")
        self.start_note.setText(
            f"Started from {label}: {', '.join(taken)}.{left_out} The title, "
            "the purpose and the notes are this recording's own and were left "
            "as they are. Nothing is written until you save.")
        return True

    def _choose_start_from(self) -> None:
        ## Beside this recording's folder is where its earlier ones are.
        start = (str(self._config_path.parent.parent)
                 if self._config_path is not None else os.getcwd())
        chosen, _ = QFileDialog.getOpenFileName(
            self, "Start from another recording's config", start,
            f"Lifespan config ({cfgmod.CONFIG_FILENAME});;"
            "YAML files (*.yaml *.yml);;All files (*)")
        if chosen:
            self.start_from_file(chosen)


# ---------------------------------------------------------------------------
# The Design tab
# ---------------------------------------------------------------------------

class DesignView(QWidget):
    """The workbook's design, read-only: what the About's factor rows follow."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        outer.addWidget(scroll)
        page = QWidget()
        scroll.setWidget(page)
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        intro = QLabel(
            "Read from the data file; nothing here is written. The design is "
            "the workbook's Design sheet — its columns after StartTime are the "
            "factors — so it is changed there, in DLife, never in the config.")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.data_file = QLabel("")
        self.data_file.setWordWrap(True)
        self.data_file.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.data_file)
        self.notice = QLabel("")
        self.notice.setWordWrap(True)
        self.notice.setStyleSheet("color: #d97706;")
        layout.addWidget(self.notice)

        layout.addWidget(_section_label("Factors and levels"))
        self.factors_table = QTableWidget(0, 2)
        self.factors_table.setHorizontalHeaderLabels(["Factor", "Levels"])
        layout.addWidget(self.factors_table)

        layout.addWidget(_section_label("Chambers"))
        self.chambers_table = QTableWidget(0, 0)
        layout.addWidget(self.chambers_table)
        self.excluded = QLabel("")
        self.excluded.setWordWrap(True)
        layout.addWidget(self.excluded)
        for table in (self.factors_table, self.chambers_table):
            table.verticalHeader().setVisible(False)
            table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addStretch(1)
        self.show_design(FolderDesign(problem="No folder open."))

    def show_design(self, design: FolderDesign) -> None:
        if design.data_file is not None:
            text = f"Data file: {design.data_file}"
            if design.referenced:
                text += f"\nRead where it lies ({design.referenced})."
            self.data_file.setText(text)
        else:
            self.data_file.setText("Data file: none")
        notices = [design.problem] if design.problem else []
        if design.unfinished:
            notices.append("The lifespan is still running (PrivateData IsCompleted "
                           "is 0): its survivors are censored at the last census "
                           "until it is complete.")
        self.notice.setText("\n".join(notices))
        self.notice.setVisible(bool(notices))

        self.factors_table.setRowCount(0)
        for name, levels in design.factors.items():
            r = self.factors_table.rowCount()
            self.factors_table.insertRow(r)
            self.factors_table.setItem(r, 0, _fixed_item(name))
            self.factors_table.setItem(r, 1, _fixed_item(", ".join(levels)))
        header = self.factors_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        _fit_rows(self.factors_table)

        columns = list(design.chambers[0]) if design.chambers else []
        excluded = {_cell(c) for c in design.excluded}
        self.chambers_table.clear()
        self.chambers_table.setRowCount(0)
        self.chambers_table.setColumnCount(len(columns) + (1 if columns else 0))
        if columns:
            self.chambers_table.setHorizontalHeaderLabels(
                ["Chamber", "Sample size", *columns[2:], "Excluded"])
        for row in design.chambers:
            r = self.chambers_table.rowCount()
            self.chambers_table.insertRow(r)
            for c, column in enumerate(columns):
                self.chambers_table.setItem(r, c, _fixed_item(_cell(row.get(column))))
            flagged = _cell(row.get("Chamber")) in excluded
            self.chambers_table.setItem(r, len(columns),
                                        _fixed_item("yes" if flagged else ""))
        self.chambers_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents)
        _fit_rows(self.chambers_table)
        self.chambers_table.setVisible(bool(columns))
        if design.chambers:
            total = sum(n for n in (_number(r.get("SampleSize"))
                                    for r in design.chambers) if n is not None)
            flagged = ", ".join(_cell(c) for c in design.excluded)
            self.excluded.setText(
                f"{len(design.chambers)} chambers, {_cell(total)} flies set up. "
                + (f"Excluded by the workbook's ChamberFlags sheet: {flagged}."
                   if flagged else "The workbook's ChamberFlags sheet excludes none."))
        elif design.data_file is not None and not design.problem:
            self.excluded.setText("A CSV cohort has no chambers.")
        else:
            self.excluded.setText("")


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------

class ConfigEditorWindow(QMainWindow):
    """``pysurv-config``: one recording folder's About, and its design."""

    #: The config was written (its path).
    aboutSaved = pyqtSignal(str)

    def __init__(self, directory: str | Path | None = None,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(APP_TITLE)
        self.resize(980, 860)
        self._directory: Path | None = None
        #: The config's bytes as this window last read or wrote them (None:
        #: no file), compared before every save.
        self._as_read: Any = None
        #: The file could not be read: nothing may be written over it.
        self._blocked = ""
        self.design = FolderDesign(problem="No folder open.")
        self._build_ui()
        install_f1(self, lambda: HELP_TOPIC)
        if directory:
            self.open_folder(directory)

    # -- UI ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._top_bar = TopBar("About Editor")
        self.open_button = ActionButton("Open folder…", Category.NEUTRAL,
                                        icon_name="open")
        self.open_button.setToolTip(
            "Open a recording folder: a DLife workbook at its root or in "
            "data/, or the one its survival_config.yaml names with data_file:.")
        self.open_button.clicked.connect(self._choose_folder)
        self._top_bar.add_right(self.open_button)
        self.save_button = ActionButton("Save", Category.LOAD, icon_name="save",
                                        primary=True)
        self.save_button.setToolTip(
            "Write the about: section into survival_config.yaml, and nothing "
            "else. A folder with no config gets one holding about: alone.")
        self.save_button.clicked.connect(self.save)
        self._top_bar.add_right(self.save_button)
        self._top_bar.add_right(HelpButton(HELP_TOPIC))
        self._btn_theme = QToolButton()
        self._btn_theme.setIcon(
            icon("theme_dark" if resolved_mode() == "light" else "theme_light"))
        self._btn_theme.setIconSize(QSize(18, 18))
        self._btn_theme.setAutoRaise(True)
        self._btn_theme.setToolTip("Toggle light / dark theme")
        self._btn_theme.clicked.connect(self._toggle_theme)
        self._top_bar.add_right(self._btn_theme)
        outer.addWidget(self._top_bar)

        status_row = QHBoxLayout()
        status_row.setContentsMargins(16, 6, 16, 6)
        self.path_label = QLabel("No folder open.")
        self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ## A share's paths are long: the label never widens the window, and
        ## its tooltip holds the whole of it.
        self.path_label.setSizePolicy(QSizePolicy.Policy.Ignored,
                                      QSizePolicy.Policy.Preferred)
        self.dirty_label = QLabel("")
        self.dirty_label.setStyleSheet("color: #d97706;")
        status_row.addWidget(self.path_label, 1)
        status_row.addWidget(self.dirty_label)
        outer.addLayout(status_row)

        self.tabs = QTabWidget()
        self.about_form = AboutForm()
        self.about_form.changed.connect(self._on_form_changed)
        self.design_view = DesignView()
        self.design_view.data_file.setSizePolicy(QSizePolicy.Policy.Ignored,
                                                 QSizePolicy.Policy.Preferred)
        self.tabs.addTab(self.about_form, "About")
        self.tabs.addTab(self.design_view, "Design")
        outer.addWidget(self.tabs, 1)
        self.save_button.setEnabled(False)
        self.about_form.setEnabled(False)

    def _toggle_theme(self) -> None:
        ## Applied at once, and remembered for the next launch: this window
        ## owns no tile strip whose colours would need a restart.
        mode = "light" if resolved_mode() == "dark" else "dark"
        apply_theme(QApplication.instance(), mode)
        ui_settings.set_value("theme", mode)
        self._btn_theme.setIcon(icon("theme_dark" if mode == "light" else "theme_light"))

    def _on_form_changed(self) -> None:
        self.about_form.refresh_checks()
        self._refresh_dirty()

    def _refresh_dirty(self) -> None:
        dirty = self._directory is not None and not self.about_form.is_untouched()
        self.dirty_label.setText("●  unsaved changes" if dirty else "")

    def is_dirty(self) -> bool:
        return self._directory is not None and not self.about_form.is_untouched()

    def _status(self, text: str) -> None:
        self.statusBar().showMessage(text, 15000)

    # -- open ----------------------------------------------------------------

    @property
    def directory(self) -> Path | None:
        return self._directory

    @property
    def config_path(self) -> Path | None:
        return cfgmod.config_path(self._directory) if self._directory else None

    def _choose_folder(self) -> None:
        if self.is_dirty() and not self._confirm_discard():
            return
        start = str(self._directory.parent) if self._directory else os.getcwd()
        chosen = QFileDialog.getExistingDirectory(self, "Open a recording folder", start)
        if chosen:
            self.open_folder(chosen)

    def open_folder(self, directory: str | Path) -> bool:
        """Show *directory* — or the folder of a file inside it, such as its
        config or its workbook. True when it could be read; a config that
        cannot be read is said, and nothing may be saved over it."""
        path = Path(directory).expanduser()
        if path.is_file():
            path = path.parent
        if not path.is_dir():
            self._status(f"{path} is not a folder.")
            QMessageBox.warning(self, APP_TITLE, f"{path} is not a folder.")
            return False
        self._directory = path.resolve()
        self.setWindowTitle(f"{APP_TITLE} — {self._directory.name}")
        self.about_form.set_location(self.config_path)
        self._as_read = self._bytes_on_disk()
        self._blocked = ""
        config: dict = {}
        try:
            config = cfgmod.load_config(self._directory)
        except (OSError, ValueError) as err:
            self._blocked = str(err)
        self.design = describe_folder(self._directory, config)
        self.design_view.show_design(self.design)
        self.about_form.load(config, self.design.declared)
        has_config = self.config_path.is_file()
        self.path_label.setToolTip(str(self.config_path))
        if self._blocked:
            self.path_label.setText(
                f"{self.config_path} cannot be read, so nothing will be saved "
                f"over it: {self._blocked}")
        else:
            self.path_label.setText(
                str(self.config_path) if has_config
                else f"{self._directory} — no {cfgmod.CONFIG_FILENAME} yet; "
                     f"Save writes one holding about: alone.")
        self.about_form.setEnabled(not self._blocked)
        self.save_button.setEnabled(not self._blocked)
        self._refresh_dirty()
        return not self._blocked

    # -- changed on disk -----------------------------------------------------

    def _bytes_on_disk(self) -> Any:
        """The config's bytes now; None when there is no file."""
        path = self.config_path
        if path is None:
            return None
        try:
            return path.read_bytes()
        except FileNotFoundError:
            return None
        except OSError:
            return _UNREADABLE

    def changed_on_disk(self) -> bool:
        """The config is not what this window last read or wrote."""
        return self._bytes_on_disk() != self._as_read

    def _what_differs(self, now: Any) -> str:
        """One sentence on how the file differs from what this window read."""
        if now is _UNREADABLE:
            return "It can no longer be read."
        if now is None:
            return "It is no longer there."

        def parse(data):
            if data is None:
                return {}
            try:
                import yaml

                text = data.decode("utf-8-sig", errors="replace")
                value = yaml.safe_load(text)
            except Exception:  # noqa: BLE001
                return None
            return value if isinstance(value, dict) else None

        old, new = parse(self._as_read), parse(now)
        if new is None:
            return "It no longer reads as a config."
        old = old or {}
        missing = object()
        differing = [str(key) for key in dict.fromkeys([*old, *new])
                     if old.get(key, missing) != new.get(key, missing)]
        if not differing:
            return "Its settings read the same as before: only comments or layout differ."
        return "Sections that differ: " + ", ".join(differing) + "."

    def _ask_changed_on_disk(self, now: Any) -> str:
        """Ask what to do about the config having changed on disk:
        ``"reload"``, ``"overwrite"`` or ``"cancel"``."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Warning)
        name = cfgmod.CONFIG_FILENAME
        reload_button = None
        if now is None:
            box.setWindowTitle("The file is gone")
            box.setText(f"{name} is no longer on disk.")
            box.setInformativeText(
                "It was there when this window read it, and has since been "
                "moved, renamed or deleted.\n\nSaving writes it again, here, "
                "holding the about: section this window shows.")
            overwrite_button = box.addButton("Save it again",
                                             QMessageBox.ButtonRole.AcceptRole)
        else:
            box.setWindowTitle("The file changed on disk")
            box.setText(f"{name} has changed on disk since this window read it.")
            box.setInformativeText(
                "Another program or window wrote it: a catalogue that files the "
                "recording rewrites its description, for one.\n\n"
                + self._what_differs(now)
                + "\n\nReload it to see what it holds now: the edits in this "
                "window are lost and nothing is written. Or overwrite its "
                "about: section with what this window shows; the file's other "
                "sections are kept as they are now.")
            reload_button = box.addButton("Reload from disk",
                                          QMessageBox.ButtonRole.ActionRole)
            overwrite_button = box.addButton("Overwrite",
                                             QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = box.addButton(QMessageBox.StandardButton.Cancel)
        ## Enter and Esc both write nothing.
        box.setDefaultButton(cancel_button)
        box.setEscapeButton(cancel_button)
        box.exec()
        clicked = box.clickedButton()
        if clicked is overwrite_button:
            return "overwrite"
        if reload_button is not None and clicked is reload_button:
            return "reload"
        return "cancel"

    # -- save ----------------------------------------------------------------

    def save(self) -> bool:
        """Write the About. True when the file now holds it."""
        if self._directory is None or self._blocked:
            return False
        now = self._bytes_on_disk()
        if now != self._as_read:
            choice = self._ask_changed_on_disk(now)
            if choice == "reload":
                self.open_folder(self._directory)
                self._status("Reloaded from disk; nothing was written.")
                return False
            if choice != "overwrite":
                self._status("Not saved.")
                return False
        elif self.about_form.is_untouched():
            self._status("Nothing has changed; nothing was written.")
            return False
        try:
            written = cfgmod.write_about(self._directory, self.about_form.dump())
        except (OSError, ValueError) as err:
            QMessageBox.warning(self, APP_TITLE,
                                f"{cfgmod.CONFIG_FILENAME} was not written:\n{err}")
            return False
        self._as_read = self._bytes_on_disk()
        config = cfgmod.load_config(self._directory) if written else {}
        self.about_form.note_saved(config)
        self.path_label.setText(str(self.config_path) if written else
                                f"{self._directory} — no {cfgmod.CONFIG_FILENAME}.")
        self._refresh_dirty()
        warnings = cfgmod.check_about(config.get(about_mod.ABOUT_KEY),
                                      self.design.declared)
        if written is None:
            self._status("The About is blank, so no config was written.")
            return False
        self._status(f"Saved about: in {written}"
                     + (f" — {len(warnings)} thing(s) to check below the form."
                        if warnings else "."))
        self.aboutSaved.emit(str(written))
        return True

    # -- close ---------------------------------------------------------------

    def _confirm_discard(self) -> bool:
        """True when unsaved edits may be dropped (after saving them, if the
        person chooses that)."""
        resp = QMessageBox.question(
            self, APP_TITLE, "The About has unsaved changes. Save them?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save)
        if resp == QMessageBox.StandardButton.Save:
            return self.save()
        return resp == QMessageBox.StandardButton.Discard

    def closeEvent(self, event):  # noqa: N802 — Qt API
        if self.is_dirty() and not self._confirm_discard():
            event.ignore()
            return
        event.accept()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

USAGE = """usage: pysurv-config [FOLDER]

Describe one lifespan recording: open FOLDER (a DLife workbook at its root or
in data/, or the one its survival_config.yaml names with data_file:) and edit
the about: section of its survival_config.yaml. Saving writes about: and
nothing else; a folder with no config gets one holding about: alone."""


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        print(USAGE)
        return 0
    app = QApplication.instance() or QApplication(sys.argv[:1] + args)
    apply_theme(app, ui_settings.get("theme", "auto"))
    window = ConfigEditorWindow(args[0] if args else None)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
