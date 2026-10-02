"""Report block assembly, the Project Report binder, and output stamping."""

from __future__ import annotations

import json

import pytest

from pysurvanalysis import project_report, report_builder as rb
from pysurvanalysis.report_pkg import model as m

from conftest import FACTORIAL


@pytest.fixture
def analysed(analysed_project):
    project, _results = analysed_project
    return project


@pytest.fixture
def result_a(analysed_project):
    _project, results = analysed_project
    return results["rep_a"]


def _blocks_of(report, kind):
    return [b for b in report.blocks if isinstance(b, kind)]


def test_experiment_report_leads_with_the_headline_figure(result_a):
    report = rb.build_experiment_report(result_a)

    figures = _blocks_of(report, m.Figure)
    assert figures and "headline figure" in (figures[0].title or "")


def test_report_sections_follow_the_type(result_a):
    report = rb.build_experiment_report(result_a)
    titles = [b.title for b in _blocks_of(report, m.SectionDivider)]
    assert titles[0] == "Focus"                    # every report names its slice
    assert "Factorial analysis" in titles          # a 2×2 Focus ran the battery
    assert titles.index("Experiment summary") < titles.index("Factorial analysis")


def test_every_report_names_and_describes_its_focus(result_a):
    report = rb.build_experiment_report(result_a)
    cover = _blocks_of(report, m.Cover)[0]
    stamped = dict(cover.metadata)
    assert stamped["Focus"] == FACTORIAL
    assert "reference wt" in stamped["Slice"]
    assert FACTORIAL in cover.title
    definition = next(t for t in _blocks_of(report, m.Table)
                      if t.title == "Focus definition")
    assert [row[0] for row in definition.rows] == ["Genotype", "Treatment"]
    assert definition.rows[0][3] == "wt"           # the Reference Level column


def test_cover_stamps_the_exclusion_group(project):
    member = project.member("rep_a")
    config = dict(member.raw_config)
    config["exclusions"] = {"group": "review_v2"}
    from pysurvanalysis.domain import config as cfgmod

    cfgmod.save_config(member.directory, config)

    from pysurvanalysis.domain import Project

    member = Project(project.directory).member("rep_a")
    result = member.run_analysis()
    cover = _blocks_of(rb.build_experiment_report(result), m.Cover)[0]
    stamped = dict(cover.metadata)
    assert "review_v2" in stamped["Exclusion group"]

    payload = json.loads(
        member.outputs(FACTORIAL).summary.read_text(encoding="utf-8"))
    assert payload["exclusion_group"] == "review_v2"


def test_significant_rows_are_tinted_semantically(result_a):
    tables = _blocks_of(rb.build_experiment_report(result_a), m.Table)
    tinted = [t for t in tables if t.row_levels]
    assert tinted, "no table carried semantic row levels"
    assert all(isinstance(lv, m.Level) for t in tinted for lv in t.row_levels)


def test_both_backends_write_from_the_same_blocks(result_a, tmp_path):
    written = rb.write_experiment_report(result_a, tmp_path)
    assert written["pdf"].is_file() and written["md"].is_file()
    assert written["pdf"].stat().st_size > 1000
    text = written["md"].read_text(encoding="utf-8")
    assert "# rep_a" in text
    assert "![" in text                      # figures linked, not inlined


def test_project_report_binds_one_section_per_focus(analysed):
    report = project_report.build_project_report(analysed)
    dividers = [b.title for b in _blocks_of(report, m.SectionDivider)]
    for member in analysed.members():
        assert project_report.section_key(member.name, FACTORIAL) in dividers


def test_project_report_carries_the_focus_inventory(analysed):
    report = project_report.build_project_report(analysed)
    tables = {t.title: t for t in _blocks_of(report, m.Table)}
    inventory = tables["Focus inventory"]
    assert [row[:2] for row in inventory.rows] == [["rep_a", FACTORIAL],
                                                  ["rep_b", FACTORIAL]]
    ## The members' designs differ in level order — shown in the inventory,
    ## and not a "divergence": that note is for data-source settings.
    assert "reference wt" in inventory.rows[0][2]
    assert "reference mut" in inventory.rows[1][2]
    assert "Divergence note" not in tables


def test_differing_censoring_earns_the_divergence_note(project):
    from pysurvanalysis.domain import Project, config as cfgmod

    member = project.member("rep_b")
    config = dict(member.raw_config)
    config["global"] = {"assume_censored": False}
    cfgmod.save_config(member.directory, config)
    report = project_report.build_project_report(Project(project.directory))
    tables = {t.title: t for t in _blocks_of(report, m.Table)}
    assert [r[0] for r in tables["Divergence note"].rows] == ["censoring"]


def test_an_unanalysed_focus_says_so_and_is_not_analysed(project):
    project.member("rep_a").run_analysis()
    report = project_report.build_project_report(project)
    paragraphs = " ".join(p.text for p in _blocks_of(report, m.Paragraph))
    assert f"Focus {FACTORIAL} has not been analysed" in paragraphs
    assert not project.member("rep_b").outputs(FACTORIAL).summary.is_file()


def test_an_out_of_date_focus_shows_no_numbers(project):
    from pysurvanalysis.domain import Project

    member = project.member("rep_a")
    member.run_analysis()
    [focus] = member.focuses()
    member.save_focuses([focus.copy(reference={"Treatment": "drug"})])
    report = project_report.build_project_report(Project(project.directory))
    paragraphs = " ".join(p.text for p in _blocks_of(report, m.Paragraph))
    assert "results are out of date" in paragraphs
    assert "Reference Level changed" in paragraphs
    ## Neither member's figures are bound: rep_a is out of date, rep_b unrun.
    assert not _blocks_of(report, m.Figure)


def test_a_blocked_focus_is_reported_and_its_siblings_still_bind(project):
    from pysurvanalysis.domain import Project
    from pysurvanalysis.domain.focus import Focus

    member = project.member("rep_a")
    member.save_focuses(member.focuses() + [Focus("Stale", {"Genotype": ["wild"]})])
    member.run_all()
    report = project_report.build_project_report(Project(project.directory))
    paragraphs = " ".join(p.text for p in _blocks_of(report, m.Paragraph))
    assert "Focus Stale is blocked" in paragraphs
    assert _blocks_of(report, m.Figure)            # the healthy Focus still binds


def test_saved_analysis_rebuilds_sections_without_recomputing(analysed):
    member = analysed.member("rep_a")
    saved = project_report.SavedAnalysis(member, member.focus(FACTORIAL))
    assert saved.exists
    assert saved.focus_record["name"] == FACTORIAL
    assert len(saved.summary) > 0
    assert saved.omnibus_lr.get("p_value") is not None
    assert len(saved.cox_analyses) == 2          # Cox + RMST companions
    assert saved.figure_paths                      # figures found on disk


def test_project_report_writes_both_formats(analysed):
    written = project_report.write_project_report(analysed)
    assert written["pdf"].is_file() and written["md"].is_file()
    assert written["pdf"].parent == analysed.directory


def test_a_section_divider_is_not_asked_to_break_twice(analysed):
    """A ``SectionDivider`` starts its own page, so a ``PageBreak`` in front of
    one produces a page holding nothing but the running header and footer.

    Asserted on the model, where the mistake is made: every member used to get
    an explicit break before its divider, and the reader got a blank page per
    member.
    """
    report = project_report.build_project_report(analysed)
    kinds = [type(b) for b in report.blocks]
    for i, kind in enumerate(kinds[:-1]):
        if kind is m.PageBreak:
            assert kinds[i + 1] is not m.SectionDivider, (
                f"block {i} breaks the page immediately before a "
                f"SectionDivider, which breaks it again")


def test_the_pdf_backend_collapses_consecutive_page_breaks(tmp_path):
    """The rule lives in the backend too: a caller cannot see from the model
    that a divider starts its own page, so writing the break by hand has to be
    harmless rather than merely discouraged."""
    from reportlab.platypus import PageBreak

    from pysurvanalysis.report_pkg.backends import reportlab_backend as rl

    report = m.Report(title="doubled")
    report.add(m.Paragraph("before"))
    report.add(m.PageBreak())
    report.add(m.PageBreak())
    report.add(m.SectionDivider("A section"))
    report.add(m.Paragraph("after"))

    flow = rl._blocks_to_flowables(report, rl._styles())
    breaks = [i for i, f in enumerate(flow) if isinstance(f, PageBreak)]
    assert all(b + 1 not in breaks for b in breaks), \
        "two PageBreaks in a row would render an empty page"


# ── curated Publication Figures in the report ──────────────────────────────

def _figure_blocks(report):
    return [b for b in report.blocks if isinstance(b, m.Figure)]


def test_a_curated_figure_replaces_the_default_in_the_report(project):
    """As in the sister app: a plot the Plot Editor curated is shown in the
    report through THAT figure and its style; a plot with nothing curated
    keeps the analysis's own matplotlib figure."""
    from pysurvanalysis import pubfigures as pf

    member = project.member("rep_a")
    result = member.run_analysis()

    ## Nothing curated yet: every figure is the default, at its fixed size.
    before = _figure_blocks(rb.build_experiment_report(result))
    assert before
    assert all(f.width_in == 6.5 and f.height_in == 4.2 for f in before)
    assert not any("curated" in (f.title or "") for f in before)

    spec = pf.default_spec("km_faceted")
    spec.facet_by = "Genotype"
    pf.save_specs(project.directory, {"km_faceted": spec})
    pf.save_styles(project.directory,
                   {"default": pf.PlotStyle(name="default", width_mm=127.0,
                                            height_mm=76.2)})

    after = _figure_blocks(rb.build_experiment_report(result))
    curated = [f for f in after if "curated" in (f.title or "")]
    assert len(curated) == 1
    ## Rendered from the curated Spec + Style — the block carries the style's
    ## size, not the default's.
    assert round(curated[0].width_in, 2) == 5.0
    assert round(curated[0].height_in, 2) == 3.0
    assert curated[0].data[:8] == b"\x89PNG\r\n\x1a\n"
    ## The rest are untouched defaults, and the count is the same.
    assert len(after) == len(before)
    others = [f for f in after if "curated" not in (f.title or "")]
    assert all(f.width_in == 6.5 for f in others)


def test_a_curated_km_stands_in_for_both_default_km_figures(tmp_path):
    """The analysis writes two KM figures (with and without the at-risk
    table); in the publication renderer the table is a Style toggle, so one
    curated km_curves supersedes both rather than sitting beside a
    near-duplicate."""
    from pysurvanalysis import pubfigures as pf
    from pysurvanalysis.domain import SurvivalExperiment
    from tests.conftest import make_experiment_dir

    directory = make_experiment_dir(tmp_path / "lone", type_key="standard_lifespan")
    experiment = SurvivalExperiment(directory)
    result = experiment.run_analysis()
    assert {"km_curves", "km_risk_table"} <= set(result.figure_paths)

    before = _figure_blocks(rb.build_experiment_report(result))
    pf.save_specs(directory, {"km_curves": pf.default_spec("km_curves")})
    after = _figure_blocks(rb.build_experiment_report(result))

    curated = [f for f in after if "curated" in (f.title or "")]
    assert len(curated) == 1
    assert len(after) == len(before) - 1                  # one KM, not two
    assert not any("at-risk" in (f.title or "").lower() and "curated" not in
                   (f.title or "") for f in after)


def test_a_broken_curation_falls_back_to_the_default(project, monkeypatch):
    """A curation that cannot render must not sink the report — the default
    figure stands in, silently, and the report is whole."""
    from pysurvanalysis import pubfigures as pf

    member = project.member("rep_a")
    result = member.run_analysis()
    spec = pf.default_spec("km_faceted")
    spec.facet_by = "Genotype"
    pf.save_specs(project.directory, {"km_faceted": spec})

    def _boom(*_a, **_k):
        raise RuntimeError("cannot render")

    monkeypatch.setattr(pf, "build_ggplot", _boom)
    figures = _figure_blocks(rb.build_experiment_report(result))
    assert figures
    assert not any("curated" in (f.title or "") for f in figures)
    assert all(f.width_in == 6.5 for f in figures)
