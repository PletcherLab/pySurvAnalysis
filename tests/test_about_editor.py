"""``pysurv-config`` and the Hub's ways to the ``about:`` section (ADR-0014).

P15's S2 and S3 through the editor, P10's A3–A7 for the writers that live in
windows, and the Hub's **Edit About…**. Domain-level behaviour is
``test_about_config.py``'s. No test here opens a modal: every question the
editor can ask goes through a method the test replaces.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from pysurvanalysis.domain import Project, config as cfgmod
from tests.conftest import write_dlife_workbook
from tests.test_about_config import full_about, make_member, snapshot

#: What the About tab has typed in for a file that gives none of them.
DEFAULTS = {"organism": "Drosophila melanogaster", "age_at_start": "2-3 days old",
            "protocol": {"name": "DLife Lifespan"}}


def with_defaults(about: dict) -> dict:
    """*about* as saved from a form opened on a file that gave no organism,
    age or protocol: the defaults, in the section's written order."""
    from pysurvanalysis import about as about_mod

    return about_mod.clean_about({**DEFAULTS, **about})


@pytest.fixture
def editors(qapp):
    """Open ``ConfigEditorWindow`` s, closed without asking at the end."""
    from pysurvanalysis.apps.config_editor import ConfigEditorWindow

    opened: list = []

    def _open(directory=None):
        window = ConfigEditorWindow(directory)
        window._confirm_discard = lambda: True
        opened.append(window)
        return window

    yield _open
    for window in opened:
        window._confirm_discard = lambda: True
        window.close()


@pytest.fixture
def recording(tmp_path) -> Path:
    """A folder holding a DLife workbook and nothing else."""
    write_dlife_workbook(tmp_path / "R-1" / "data" / "R-1.xlsx", chambers=4,
                         sample_size=20)
    return tmp_path / "R-1"


def _flag_chamber(path: Path, chamber: int) -> None:
    import openpyxl

    book = openpyxl.load_workbook(path)
    sheet = book.create_sheet("ChamberFlags")
    sheet.append(["Chamber", "Excluded"])
    for c in range(1, 5):
        sheet.append([c, 1 if c == chamber else 0])
    book.save(path)


def _column(table, column: int) -> list[str]:
    return [table.item(r, column).text() for r in range(table.rowCount())]


# ---------------------------------------------------------------------------
# S2 — a bare workbook folder
# ---------------------------------------------------------------------------

def test_a_workbook_folder_shows_its_design_and_saves_only_the_about(editors, recording):
    _flag_chamber(recording / "data" / "R-1.xlsx", 3)
    before = snapshot(recording)
    window = editors(recording)
    assert [window.tabs.tabText(i) for i in range(window.tabs.count())] == ["About", "Design"]

    view = window.design_view
    assert _column(view.factors_table, 0) == ["Genotype", "Treatment"]
    ## First appearance in the Design sheet, never alphabetical: chamber 1
    ## is Genotype b.
    assert _column(view.factors_table, 1) == ["b, a", "a, b"]
    assert _column(view.chambers_table, 0) == ["1", "2", "3", "4"]
    assert _column(view.chambers_table, 1) == ["20"] * 4
    assert _column(view.chambers_table, view.chambers_table.columnCount() - 1) == [
        "", "", "yes", ""]
    assert "3" in view.excluded.text() and "80 flies" in view.excluded.text()

    form = window.about_form
    assert form.kinds() == {"Genotype": "", "Treatment": ""}
    assert list(form.meanings()) == [("Genotype", "b"), ("Genotype", "a"),
                                     ("Treatment", "a"), ("Treatment", "b")]
    form.title.setText("Lifespan on two diets")
    form.kind_combo("Treatment").setCurrentText("diet")
    form.meaning_edit("Treatment", "b").setText("15% SY")
    assert window.is_dirty()
    assert window.save()

    assert cfgmod.load_config(recording) == {"about": with_defaults({
        "title": "Lifespan on two diets",
        "factors": {"Treatment": {"kind": "diet", "levels": {"b": "15% SY"}}}})}
    after = snapshot(recording)
    assert set(after) - set(before) == {cfgmod.CONFIG_FILENAME}
    assert not (recording / "analysis").exists() and not (recording / "qc").exists()
    assert not window.is_dirty()


def test_a_blank_about_writes_no_file(editors, recording):
    before = snapshot(recording)
    window = editors(recording)
    assert not window.save()
    window.about_form.title.setText("x")
    window.about_form.title.setText("")
    assert not window.save()
    assert snapshot(recording) == before


def test_a_section_left_blank_is_not_written(editors, recording):
    """No ``sex: []``, no protocol version or link, no ``factors: {}``."""
    window = editors(recording)
    window.about_form.experimenter.setText("tester")
    window.save()
    assert cfgmod.load_config(recording) == {"about": {
        "experimenter": "tester", "organism": "Drosophila melanogaster",
        "age_at_start": "2-3 days old", "protocol": {"name": "DLife Lifespan"}}}


def test_the_lab_defaults_are_typed_in_and_written_only_with_an_edit(editors, recording):
    window = editors(recording)
    form = window.about_form
    assert form.organism.text() == "Drosophila melanogaster"
    assert form.age_at_start.text() == "2-3 days old"
    assert form.protocol_edits["name"].text() == "DLife Lifespan"
    assert not window.is_dirty()
    assert not window.save()                       # nothing typed: nothing written
    assert not cfgmod.config_path(recording).exists()
    form.organism.setText("Drosophila simulans")
    form.age_at_start.setText("")                  # cleared: left out
    assert window.save()
    assert cfgmod.load_config(recording) == {"about": {
        "organism": "Drosophila simulans", "protocol": {"name": "DLife Lifespan"}}}


def test_sex_is_one_of_female_male_or_mixed(editors, recording):
    """One word: the sex every fly is, or mixed for more than one sex."""
    window = editors(recording)
    form = window.about_form
    assert list(form.sex_buttons) == ["female", "male", "mixed"]
    assert form.sex() == ""                       # no Sex factor: not said
    form.sex_buttons["female"].setChecked(True)
    form.sex_buttons["mixed"].setChecked(True)
    assert form.sex() == "mixed"
    assert not form.sex_buttons["female"].isChecked()
    assert window.save()
    assert cfgmod.load_config(recording)["about"]["sex"] == ["mixed"]
    form.sex_buttons["mixed"].setChecked(False)   # cleared: not said
    assert window.save()
    assert "sex" not in cfgmod.load_config(recording)["about"]


def test_a_sex_factor_makes_mixed_the_default(editors, tmp_path):
    folder = tmp_path / "R-sex"
    write_dlife_workbook(folder / "data" / "R.xlsx", factors=("Sex", "Drug"))
    window = editors(folder)
    assert window.about_form.sex() == "mixed"
    assert "the design has a Sex factor" in window.about_form.other_sex_label.text()
    assert not window.is_dirty()
    assert not window.save()                      # a default alone writes nothing
    window.about_form.title.setText("T")
    assert window.save()
    assert cfgmod.load_config(folder)["about"]["sex"] == ["mixed"]
    ## A file that says otherwise keeps its own word.
    cfgmod.write_about(folder, {"sex": ["female"]})
    assert editors(folder).about_form.sex() == "female"


@pytest.mark.parametrize("words", [["female", "male"], ["Female", "MALE"],
                                   ["female", "mixed"], "Mixed"])
def test_more_than_one_sex_in_a_file_reads_as_mixed(editors, tmp_path, words):
    member = make_member(tmp_path / "m", about={"sex": words, "title": "T"})
    path = cfgmod.config_path(member)
    before = path.read_bytes()
    window = editors(member)
    assert window.about_form.sex() == "mixed"
    assert not window.is_dirty()
    assert not window.save()
    assert path.read_bytes() == before            # never rewritten unasked
    window.about_form.title.setText("T2")
    assert window.save()
    assert cfgmod.load_config(member)["about"]["sex"] == ["mixed"]


def test_a_word_that_is_not_a_sex_is_kept_beside_the_choice(editors, tmp_path):
    member = make_member(tmp_path / "m", about={"sex": ["female", "mated"]})
    window = editors(member)
    assert window.about_form.sex() == "female"
    assert "mated" in window.about_form.other_sex_label.text()
    window.about_form.title.setText("T")
    window.save()
    assert cfgmod.load_config(member)["about"]["sex"] == ["female", "mated"]


def test_one_sex_beside_a_sex_factor_is_checked(editors, tmp_path):
    folder = tmp_path / "R-sex"
    write_dlife_workbook(folder / "data" / "R.xlsx", factors=("Sex", "Drug"))
    cfgmod.write_about(folder, {"sex": ["female"]})
    form = editors(folder).about_form
    assert form.sex() == "female"
    assert "the design has a Sex factor" in form.checks.text()


def test_a_factor_of_kind_sex_makes_mixed_the_default(editors, tmp_path, recording):
    cfgmod.write_about(recording, {"factors": {"Genotype": {"kind": "sex"}}})
    form = editors(recording).about_form
    assert form.sex() == "mixed"
    assert "Sex factor" in form.other_sex_label.text()


def test_a_file_that_gives_a_field_keeps_its_own_value(editors, tmp_path):
    member = make_member(tmp_path / "m", about={
        "organism": "Drosophila simulans", "age_at_start": "5 days",
        "protocol": "Another protocol"})
    form = editors(member).about_form
    assert form.organism.text() == "Drosophila simulans"
    assert form.age_at_start.text() == "5 days"
    assert form.protocol_edits["name"].text() == "Another protocol"


def test_blanking_every_field_removes_the_section_and_nothing_else(editors, tmp_path):
    member = make_member(tmp_path / "m", about={"title": "Gone soon"})
    before = cfgmod.load_config(member)
    window = editors(member)
    form = window.about_form
    for edit in (form.title, form.organism, form.age_at_start,
                 form.protocol_edits["name"]):
        edit.setText("")
    assert window.save()
    after = cfgmod.load_config(member)
    assert "about" not in after
    before.pop("about")
    assert after == before


def test_the_title_counts_to_sixty(editors, recording):
    window = editors(recording)
    window.about_form.title.setText("x" * 61)
    assert window.about_form.title_count.text() == "61/60"
    assert "61 characters" in window.about_form.checks.text()


@pytest.mark.parametrize("given", ["data/R-1.xlsx", "data", "."])
def test_the_workbook_or_its_data_folder_opens_the_recording_folder(editors, recording, given):
    """The config belongs at the recording's root, beside data/: the loader
    never reads one inside it."""
    window = editors(recording / given)
    assert window.directory == recording.resolve()
    assert window.design.data_file is not None
    window.about_form.title.setText("T")
    assert window.save()
    assert cfgmod.config_path(recording).is_file()
    assert sorted(os.listdir(recording / "data")) == ["R-1.xlsx"]
    assert window.notice_label.isHidden()


def test_a_workbook_at_the_root_opens_its_own_folder(editors, tmp_path):
    folder = tmp_path / "R-2"
    write_dlife_workbook(folder / "R-2.xlsx")
    assert editors(folder / "R-2.xlsx").directory == folder.resolve()


def test_a_folder_named_data_is_a_recording_when_its_parent_does_not_read_it(editors, tmp_path):
    """Its workbook is in its own data/, so its parent's data/ search finds
    nothing there: it is the recording, not a data/ folder."""
    folder = tmp_path / "data"
    write_dlife_workbook(folder / "data" / "run.xlsx")
    assert editors(folder).directory == folder.resolve()


def test_a_config_saved_inside_data_is_brought_to_the_root(editors, recording):
    """Where an earlier pysurv-config put it when opened on the workbook."""
    stray = recording / "data" / cfgmod.CONFIG_FILENAME
    cfgmod.write_yaml(stray, {"about": {"title": "Typed earlier",
                                        "purpose": "Miglitol and lifespan"}})
    before = stray.read_bytes()
    window = editors(recording / "data" / "R-1.xlsx")
    assert window.directory == recording.resolve()
    assert not window.notice_label.isHidden()
    assert "data/survival_config.yaml" in window.notice_label.text()
    assert "Save writes it to the root" in window.notice_label.text()
    assert window.about_form.title.text() == "Typed earlier"
    assert window.is_dirty()
    assert window.save()
    assert cfgmod.load_config(recording)["about"] == with_defaults(
        {"title": "Typed earlier", "purpose": "Miglitol and lifespan"})
    assert stray.read_bytes() == before                 # never changed here
    reopened = editors(recording)
    assert "The About shown is the root's" in reopened.notice_label.text()
    assert not reopened.is_dirty()


def test_a_member_with_no_about_opens_blank_but_for_the_defaults(editors, tmp_path):
    member = make_member(tmp_path / "m")
    window = editors(member)
    form = window.about_form
    assert form.section() == DEFAULTS
    assert form.title.text() == "" and form.purpose.toPlainText() == ""
    assert not form.run_value.text()
    assert not window.is_dirty()


def test_a_folder_with_no_workbook_still_describes(editors, tmp_path):
    folder = tmp_path / "empty"
    folder.mkdir()
    window = editors(folder)
    assert window.design.problem
    assert window.about_form.kinds() == {}
    window.about_form.title.setText("Planned")
    assert window.save()
    assert cfgmod.load_config(folder) == {"about": with_defaults({"title": "Planned"})}


def test_a_config_that_cannot_be_read_is_never_written_over(editors, tmp_path):
    member = make_member(tmp_path / "m")
    path = cfgmod.config_path(member)
    path.write_bytes(b"about:\n  purpose: \x81\x8d\n")
    window = editors(member)
    assert not window.save_button.isEnabled()
    assert not window.save()
    assert path.read_bytes() == b"about:\n  purpose: \x81\x8d\n"
    assert str(path) in window.path_label.text()


# ---------------------------------------------------------------------------
# S3 and A3 — the editor keeps what it does not edit
# ---------------------------------------------------------------------------

def _member_with_settings(directory: Path, about=None) -> Path:
    member = make_member(
        directory, about=about,
        focuses=[{"name": "Genotype", "factors": {"Genotype": ["a", "b"]},
                  "reference": {"Genotype": "a"}}],
        exclusions={"group": "qc1"}, omit={"analyses": ["parametric_aft"]})
    config = cfgmod.load_config(member)
    config["global"] = {"time_unit": "days"}
    cfgmod.write_yaml(cfgmod.config_path(member), config)
    return member


def test_saving_the_about_leaves_every_other_key_equal(editors, tmp_path):
    member = _member_with_settings(tmp_path / "m")
    before = cfgmod.load_config(member)
    window = editors(member)
    window.about_form.title.setText("A title")
    assert window.save()
    after = cfgmod.load_config(member)
    assert after.pop("about") == with_defaults({"title": "A title"})
    assert after == before
    assert list(cfgmod.load_config(member))[0] == "about"      # new: first


def test_editing_one_meaning_keeps_everything_the_form_has_no_field_for(editors, tmp_path):
    member = _member_with_settings(tmp_path / "m", about=full_about())
    window = editors(member)
    form = window.about_form
    assert form.run_value.text() == "R-20261127-test-01"
    assert form.meaning_edit("Genotype", "b").text() == "da-GAL4 > UAS-RNAi"
    form.meaning_edit("Genotype", "b").setText("da-GAL4 > UAS-RNAi #2")
    form.meaning_edit("Genotype", "a").setText("w1118 (iso)")
    assert window.save()
    expected = full_about()
    expected["factors"]["Genotype"]["levels"]["b"]["definition"] = "da-GAL4 > UAS-RNAi #2"
    expected["factors"]["Genotype"]["levels"]["a"] = "w1118 (iso)"
    assert cfgmod.load_config(member)["about"] == expected


def test_clearing_a_mapped_meaning_keeps_the_catalogues_keys(editors, tmp_path):
    """P10 item 5: a mapping left with no definition keeps its other keys."""
    member = make_member(tmp_path / "m", about=full_about())
    window = editors(member)
    window.about_form.meaning_edit("Genotype", "b").setText("")
    assert window.save()
    assert cfgmod.load_config(member)["about"]["factors"]["Genotype"]["levels"]["b"] == {
        "term": "GEN-0042", "label": "da > RNAi", "role": "treatment", "x_other": "kept"}


def test_an_untouched_about_is_never_rewritten(editors, tmp_path):
    member = _member_with_settings(tmp_path / "m", about=full_about())
    path = cfgmod.config_path(member)
    path.write_text("# a comment a rewrite would lose\n" + path.read_text("utf-8"),
                    encoding="utf-8")
    before = path.read_bytes()
    window = editors(member)
    assert not window.is_dirty()
    assert not window.save()
    assert path.read_bytes() == before


def test_a_level_the_workbook_lacks_is_kept_and_checked(editors, tmp_path):
    about = full_about()
    about["factors"]["Genotype"]["levels"]["zz"] = {"definition": "old", "term": "T-9"}
    about["factors"]["Diet"] = {"kind": "diet"}
    member = make_member(tmp_path / "m", about=about)
    window = editors(member)
    with pytest.raises(KeyError):
        window.about_form.meaning_edit("Genotype", "zz")
    assert "'zz'" in window.about_form.checks.text()
    window.about_form.title.setText("New title")
    window.save()
    saved = cfgmod.load_config(member)["about"]
    assert saved["factors"]["Genotype"]["levels"]["zz"] == {"definition": "old",
                                                            "term": "T-9"}
    assert saved["factors"]["Diet"] == {"kind": "diet"}


def test_a_sex_or_protocol_the_form_has_no_field_for_is_kept(editors, tmp_path):
    about = {"sex": ["female", "mated"], "protocol": {"name": "P", "x": 1},
             "x_lab": {"a": 1}}
    member = make_member(tmp_path / "m", about=about)
    window = editors(member)
    window.about_form.title.setText("T")
    window.save()
    assert cfgmod.load_config(member)["about"] == {
        "title": "T", "organism": "Drosophila melanogaster",
        "sex": ["female", "mated"], "age_at_start": "2-3 days old",
        "protocol": {"name": "P", "x": 1}, "x_lab": {"a": 1}}


# ---------------------------------------------------------------------------
# A5 — a change on disk is never overwritten silently
# ---------------------------------------------------------------------------

def _rewrite_on_disk(member: Path) -> dict:
    """What a catalogue does after filing: rewrite the About in place."""
    rewritten = full_about()
    rewritten["run"] = "R-20261201-test-07"
    rewritten["factors"]["Genotype"]["levels"]["a"] = {
        "definition": "w1118", "term": "GEN-0001", "role": "reference"}
    cfgmod.write_about(member, rewritten)
    return rewritten


def test_a_change_on_disk_is_asked_about_and_cancel_writes_nothing(editors, tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    window = editors(member)
    rewritten = _rewrite_on_disk(member)
    on_disk = cfgmod.config_path(member).read_bytes()
    asked: list[str] = []
    window._ask_changed_on_disk = lambda now: asked.append("asked") or "cancel"
    window.about_form.title.setText("Typed in the window")
    assert not window.save()
    assert asked == ["asked"]
    assert cfgmod.config_path(member).read_bytes() == on_disk
    assert cfgmod.load_config(member)["about"] == rewritten
    assert window.is_dirty()


def test_reload_discards_the_edits_and_writes_nothing(editors, tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    window = editors(member)
    rewritten = _rewrite_on_disk(member)
    on_disk = cfgmod.config_path(member).read_bytes()
    window._ask_changed_on_disk = lambda now: "reload"
    window.about_form.title.setText("Typed in the window")
    assert not window.save()
    assert cfgmod.config_path(member).read_bytes() == on_disk
    assert window.about_form.run_value.text() == "R-20261201-test-07"
    assert window.about_form.title.text() == rewritten["title"]
    assert not window.is_dirty()


def test_overwrite_writes_the_about_and_keeps_the_rest_as_it_is_now(editors, tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    window = editors(member)
    ## Another writer adds a Focus while the editor is open.
    config = cfgmod.load_config(member)
    config["focuses"] = [{"name": "G", "factors": {"Genotype": ["a", "b"]}}]
    cfgmod.write_yaml(cfgmod.config_path(member), config)
    window._ask_changed_on_disk = lambda now: "overwrite"
    window.about_form.title.setText("Typed in the window")
    assert window.save()
    saved = cfgmod.load_config(member)
    assert saved["about"]["title"] == "Typed in the window"
    assert saved["focuses"] == config["focuses"]
    ## Now what the window last wrote: the next save does not ask.
    window._ask_changed_on_disk = lambda now: pytest.fail("asked again")
    window.about_form.notes.setPlainText("More")
    assert window.save()


def test_a_save_with_nothing_changed_anywhere_does_not_ask(editors, tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    window = editors(member)
    window._ask_changed_on_disk = lambda now: pytest.fail("asked")
    window.about_form.title.setText("Mine")
    assert window.save()


# ---------------------------------------------------------------------------
# A6 — Start from another recording…
# ---------------------------------------------------------------------------

def test_start_from_takes_the_shared_about_only(editors, tmp_path, recording):
    earlier = full_about()
    earlier["factors"]["Genotype"]["levels"]["zz"] = "not in this workbook"
    earlier["factors"]["Diet"] = {"kind": "diet", "levels": {"DR": "1% SY"}}
    other = make_member(tmp_path / "earlier", about=earlier)
    cfgmod.write_about(recording, {"title": "Mine", "purpose": "My own",
                                   "notes": "Mine too", "run": "R-mine"})
    window = editors(recording)
    assert window.about_form.start_from_file(cfgmod.config_path(other))
    section = window.about_form.section()
    full = full_about()
    assert section == {
        "run": "R-mine", "title": "Mine", "purpose": "My own",
        **{k: full[k] for k in ("experimenter", "series", "organism", "sex",
                                "age_at_start", "protocol")},
        "notes": "Mine too",
        "factors": full["factors"],
    }
    assert "left out" in window.about_form.start_note.text()
    assert window.is_dirty()
    assert window.save()
    assert cfgmod.load_config(recording)["about"] == section


def test_start_from_refuses_its_own_config(editors, tmp_path):
    member = make_member(tmp_path / "m", about=full_about())
    window = editors(member)
    assert not window.about_form.start_from_file(cfgmod.config_path(member))
    assert "own config" in window.about_form.start_note.text()


def test_start_from_a_config_with_nothing_to_share(editors, tmp_path, recording):
    other = make_member(tmp_path / "earlier", about={"title": "Only a title"})
    window = editors(recording)
    assert not window.about_form.start_from_file(cfgmod.config_path(other))
    assert window.about_form.section() == DEFAULTS
    assert not window.is_dirty()


# ---------------------------------------------------------------------------
# The Hub
# ---------------------------------------------------------------------------

@pytest.fixture
def hub(qapp, tmp_path):
    from pysurvanalysis.apps.hub import HubWindow

    root = tmp_path / "P"
    Project.create(root, name="P")
    make_member(root / "m1", about=full_about())
    make_member(root / "m2")
    window = HubWindow(str(root))
    window._warned = []
    window._warn = lambda message: window._warned.append(message)
    yield window
    for editor in getattr(window, "_about_windows", []):
        editor._confirm_discard = lambda: True
        editor.close()
    window.close()


def test_edit_about_opens_pysurv_config_on_the_member(hub):
    from pysurvanalysis.apps.config_editor import ConfigEditorWindow

    window = hub._action_edit_about(hub._project.directory / "m2")
    assert isinstance(window, ConfigEditorWindow)
    assert window.directory == (hub._project.directory / "m2").resolve()
    assert window.about_form.section() == DEFAULTS     # no About: the defaults
    assert not window.is_dirty()
    window = hub._action_edit_about(hub._project.directory / "m1")
    assert window.about_form.title.text() == full_about()["title"]


def test_the_members_table_offers_edit_about(hub, monkeypatch):
    from PyQt6.QtWidgets import QMenu

    seen: list[str] = []

    def _exec(menu, *_a):
        actions = menu.actions()
        seen.extend(a.text() for a in actions)
        return actions[0]

    monkeypatch.setattr(QMenu, "exec", _exec)
    opened: list = []
    monkeypatch.setattr(hub, "_action_edit_about", lambda d: opened.append(Path(d)))
    rows = [hub._members_table.item(r, 0).text()
            for r in range(hub._members_table.rowCount())]
    row = rows.index("m1")
    point = hub._members_table.visualItemRect(hub._members_table.item(row, 0)).center()
    hub._members_menu(point)
    assert seen == ["Edit About… (m1)"]
    assert opened == [hub._project.directory / "m1"]


def test_copy_config_from_gives_the_shared_about_only(hub, monkeypatch, tmp_path):
    """A7: the new member starts from the first one's shared About."""
    from pysurvanalysis.apps import hub as hub_mod

    source = cfgmod.config_path(hub._project.directory / "m1")
    member = hub._project.add_member("m3")
    write_dlife_workbook(member.directory / "data" / "m3.xlsx")
    monkeypatch.setattr(hub_mod.QFileDialog, "getOpenFileName",
                        lambda *a, **k: (str(source), ""))
    assert hub._copy_member_config("m3", member.directory)
    about = cfgmod.load_config(member.directory)["about"]
    full = full_about()
    assert about == {k: full[k] for k in about_shared_keys()}
    assert not {"title", "purpose", "notes", "run", "x_lab"} & set(about)


def about_shared_keys():
    from pysurvanalysis import about as about_mod

    return about_mod.SHARED_KEYS


def test_copy_config_from_a_config_without_an_about_is_still_a_byte_copy(hub, monkeypatch):
    from pysurvanalysis.apps import hub as hub_mod

    source = cfgmod.config_path(hub._project.directory / "m2")
    member = hub._project.add_member("m4")
    monkeypatch.setattr(hub_mod.QFileDialog, "getOpenFileName",
                        lambda *a, **k: (str(source), ""))
    assert hub._copy_member_config("m4", member.directory)
    assert cfgmod.config_path(member.directory).read_bytes() == source.read_bytes()


def test_validate_yamls_lists_members_that_describe_a_level_differently(hub):
    other = full_about()
    other["factors"]["Treatment"]["levels"]["b"] = "20% SY"
    cfgmod.write_about(hub._project.directory / "m2", other)
    lines: list[str] = []
    hub._log.append_line = lines.append
    hub._action_validate_project()
    assert "Project validation passed." in lines
    assert any(line.startswith("  warning — about: members describe Treatment 'b'")
               for line in lines)


# ---------------------------------------------------------------------------
# A3 and A4 — the writers that live in windows
# ---------------------------------------------------------------------------

def _catalogue_rewrite(member: Path) -> dict:
    rewritten = full_about()
    rewritten["title"] = "Rewritten while the window was open"
    config = cfgmod.load_config(member)
    config["about"] = rewritten
    cfgmod.write_yaml(cfgmod.config_path(member), config)
    return rewritten


def test_the_hubs_exclusion_group_keeps_the_about_on_disk(hub):
    from pysurvanalysis.domain import SurvivalExperiment

    member = hub._project.directory / "m1"
    hub._experiment = SurvivalExperiment(member, defaults=hub._project.defaults,
                                         project=hub._project)
    rewritten = _catalogue_rewrite(member)
    hub._group_combo.addItem("qc1")
    hub._group_combo.setCurrentText("qc1")
    hub._action_set_exclusion_group()
    config = cfgmod.load_config(member)
    assert config["exclusions"] == {"group": "qc1"}
    assert config["about"] == rewritten


def _ambiguous(member: Path) -> None:
    write_dlife_workbook(member / "data" / "second.xlsx")


def test_naming_a_data_file_keeps_the_about(hub):
    from pysurvanalysis.domain import layout

    member = hub._project.directory / "m1"
    _ambiguous(member)
    rewritten = _catalogue_rewrite(member)
    hub._prompt_choice = lambda *a, **k: "run.xlsx"
    hub._name_member_data_file(layout.classify(member))
    config = cfgmod.load_config(member)
    assert config["data_file"] == "data/run.xlsx"
    assert config["about"] == rewritten


def test_the_configs_dialog_and_the_preflight_keep_the_about(qapp, tmp_path, monkeypatch):
    from pysurvanalysis.apps import batch_preflight, project_dialogs
    from pysurvanalysis.domain import layout

    root = tmp_path / "P"
    project = Project.create(root, name="P")
    for name in ("m1", "m2"):
        make_member(root / name, about=full_about())
        _ambiguous(root / name)
    rewritten = {name: _catalogue_rewrite(root / name) for name in ("m1", "m2")}
    for module in (project_dialogs, batch_preflight):
        monkeypatch.setattr(module.QInputDialog, "getItem",
                            staticmethod(lambda *a, **k: ("run.xlsx", True)))

    dialog = project_dialogs.MemberConfigsDialog(None, project)
    try:
        row = [r.name for r in dialog._rows].index("m1")
        dialog._table.selectRow(row)
        dialog._name_data_file()
    finally:
        dialog.close()
    preflight = batch_preflight.BatchPreflightDialog.__new__(
        batch_preflight.BatchPreflightDialog)
    preflight._log = lambda *_a: None
    batch_preflight.BatchPreflightDialog._name_data_file(
        preflight, layout.classify(root / "m2"))
    for name in ("m1", "m2"):
        config = cfgmod.load_config(root / name)
        assert config["data_file"] == "data/run.xlsx"
        assert config["about"] == rewritten[name]


def test_the_script_editor_keeps_the_about_on_disk(qapp, tmp_path, monkeypatch):
    from pysurvanalysis.script_editor import window as editor_mod

    member = make_member(tmp_path / "m", about=full_about())
    monkeypatch.setattr(editor_mod.QMessageBox, "information", lambda *a, **k: None)
    editor = editor_mod.ScriptEditorWindow(str(member))
    try:
        rewritten = _catalogue_rewrite(member)
        editor._scripts.append({"name": "Brand new", "steps": []})
        editor._save()
    finally:
        editor._dirty = False
        editor.close()
    config = cfgmod.load_config(member)
    assert "Brand new" in [s["name"] for s in config["scripts"]]
    assert config["about"] == rewritten


def test_the_editor_module_never_constructs_an_experiment(editors, recording, monkeypatch):
    from pysurvanalysis.domain import experiment

    def boom(*_a, **_k):
        raise AssertionError("an Experiment was constructed")

    monkeypatch.setattr(experiment.SurvivalExperiment, "__init__", boom)
    window = editors(recording)
    window.about_form.title.setText("T")
    assert window.save()
    assert sorted(os.listdir(recording)) == ["data", cfgmod.CONFIG_FILENAME]
