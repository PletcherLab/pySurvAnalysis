"""The Focus core: discovery, slicing, shape, blocking, migration (ADR-0011)."""

from __future__ import annotations

import pandas as pd
import pytest

from pysurvanalysis.domain import focus as fm


def _frame(rows):
    return pd.DataFrame(rows, columns=["time", "event", "Genotype", "Density", "Sex"])


@pytest.fixture
def frame():
    rows = []
    t = 1.0
    for g in ("wCS", "mDilp235bx"):            # appearance order, not alphabetical
        for d in ("20x", "40x"):
            for s in ("F", "M"):
                for _ in range(3):
                    rows.append((t, 1, g, d, s))
                    t += 1.0
    return _frame(rows)


@pytest.fixture
def design(frame):
    return fm.design_from_frame(frame, ["Genotype", "Density", "Sex"])


# ── discovery ──────────────────────────────────────────────────────────────

def test_levels_are_discovered_in_first_appearance_order(design):
    ## Alphabetical would put mDilp235bx first and silently make it the
    ## reference, flipping every coefficient.
    assert design.levels["Genotype"] == ("wCS", "mDilp235bx")
    assert design.factors == ("Genotype", "Density", "Sex")
    assert len(design.cells) == 8


def test_unfiltered_names_every_factor_at_every_level(design):
    f = fm.unfiltered(design)
    assert f.name == fm.UNFILTERED
    assert f.factors == {"Genotype": ["wCS", "mDilp235bx"],
                         "Density": ["20x", "40x"], "Sex": ["F", "M"]}
    assert f.reference_level("Genotype") == "wCS"


def test_config_without_a_block_resolves_to_unfiltered(design):
    focuses = fm.resolve_focuses({}, design)
    assert [f.name for f in focuses] == [fm.UNFILTERED]
    assert fm.resolve_focuses({}, None) == []


def test_legacy_factor_block_migrates_verbatim():
    cfg = {"experiment_type": "interaction",
           "factors": {"Genotype": ["wCS", "mDilp235bx"], "Diet": ["AL", "DR"]}}
    [f] = fm.resolve_focuses(cfg, None)
    assert f.name == fm.MIGRATED_NAME and f.origin == "migrated"
    assert f.factors == {"Genotype": ["wCS", "mDilp235bx"], "Diet": ["AL", "DR"]}
    assert f.reference_level("Genotype") == "wCS"


def test_declared_focuses_win_over_a_legacy_block(design):
    cfg = {"factors": {"Genotype": ["wCS", "mDilp235bx"]},
           "focuses": {"Mine": {"factors": {"Sex": ["F"]}}}}
    assert [f.name for f in fm.resolve_focuses(cfg, design)] == ["Mine"]


# ── labels, filters, pooling ───────────────────────────────────────────────

def test_single_level_factor_filters_without_labelling():
    f = fm.Focus("X", {"Sex": ["F"], "Density": ["20x", "40x"]})
    assert f.varying_factors == ["Density"]
    assert f.filter_factors == {"Sex": "F"}
    assert f.implied_labels() == ["20x", "40x"]


def test_unnamed_factor_is_pooled_and_said(design):
    f = fm.Focus("Dens", {"Density": ["20x", "40x"]})
    assert f.pooled_over(design) == ["Genotype", "Sex"]
    assert "pooled over Genotype, Sex" in f.describe(design)


def test_single_cell_focus_still_has_a_label():
    f = fm.Focus("One", {"Sex": ["F"], "Density": ["20x"]})
    assert f.implied_labels() == ["F/20x"]


def test_apply_focus_filters_relabels_and_orders(frame):
    f = fm.Focus("S", {"Density": ["40x", "20x"], "Sex": ["F"]})
    out = fm.apply_focus(frame, f)
    assert set(out["Sex"].astype(str)) == {"F"}
    assert list(out["treatment"].cat.categories) == ["40x", "20x"]
    assert out["treatment"].astype(str).iloc[0] == "40x"
    assert len(out) == 12          # 2 genotypes × 2 densities × 3, females only


# ── reference level ────────────────────────────────────────────────────────

def test_explicit_reference_is_separate_from_display_order(frame):
    f = fm.Focus("R", {"Density": ["20x", "40x"]}, reference={"Density": "40x"})
    assert f.reference_level("Density") == "40x"
    applied = fm.apply_focus(frame, f)
    assert list(applied["Density"].cat.categories) == ["20x", "40x"]   # display
    model = fm.model_frame(applied, f)
    assert list(model["Density"].cat.categories) == ["40x", "20x"]     # baseline


def test_a_reference_naming_no_level_falls_back_to_the_first():
    f = fm.Focus("R", {"Density": ["20x", "40x"]}, reference={"Density": "80x"})
    assert f.reference_level("Density") == "20x"


# ── shape ──────────────────────────────────────────────────────────────────

# ── requirements: relevance by definition, computability by data ──────────

def test_a_crossed_2x2_admits_everything(frame):
    f = fm.Focus("G", {"Genotype": ["wCS", "mDilp235bx"], "Density": ["20x", "40x"]})
    shape = fm.focus_shape(f, fm.apply_focus(frame, f))
    for req in (fm.COMPARISON, fm.FACTORIAL_PLOT, fm.FACTORIAL_MODEL):
        assert shape.admits(req) == (True, "")


def test_an_empty_crossing_cell_is_relevant_but_not_computable(frame):
    f = fm.Focus("G", {"Genotype": ["wCS", "mDilp235bx"], "Density": ["20x", "40x"]})
    unbalanced = frame[~((frame.Genotype == "mDilp235bx") & (frame.Density == "40x"))]
    shape = fm.focus_shape(f, fm.apply_focus(unbalanced, f))
    assert shape.absent == ("mDilp235bx/40x",)
    assert fm.FACTORIAL_MODEL.relevant(f)[0]          # the question is asked…
    ok, reason = fm.FACTORIAL_MODEL.computable(shape)
    assert not ok and "Genotype=mDilp235bx × Density=40x" in reason
    ## …but a missing cell is only a missing curve for the figures.
    assert fm.FACTORIAL_PLOT.computable(shape)[0]


def test_more_than_two_levels_is_still_factorial(frame):
    extra = pd.concat([frame, _frame([(1.0, 1, "InR", d, "F") for d in ("20x", "40x")])],
                      ignore_index=True)
    f = fm.Focus("G3", {"Genotype": ["wCS", "mDilp235bx", "InR"], "Density": ["20x", "40x"]})
    shape = fm.focus_shape(f, fm.apply_focus(extra, f))
    assert shape.describe() == "3×2"
    assert shape.admits(fm.FACTORIAL_MODEL) == (True, "")


def test_three_varying_factors_need_every_pair_crossed(frame):
    f = fm.unfiltered(fm.design_from_frame(frame, ["Genotype", "Density", "Sex"]))
    assert fm.focus_shape(f, fm.apply_focus(frame, f)).admits(fm.FACTORIAL_MODEL)[0]
    thinned = frame[~((frame.Density == "40x") & (frame.Sex == "M"))]
    ok, reason = fm.focus_shape(f, fm.apply_focus(thinned, f)).admits(fm.FACTORIAL_MODEL)
    assert not ok and "Density=40x × Sex=M" in reason


def test_one_varying_factor_is_not_offered_the_factorial_analyses(frame):
    f = fm.Focus("D", {"Density": ["20x", "40x"]})
    assert [r.key for r in fm.offered(f)] == ["comparison"]
    ok, reason = fm.FACTORIAL_MODEL.relevant(f)
    assert not ok and "varies only Density" in reason


def test_a_single_treatment_is_offered_no_comparison():
    f = fm.Focus("One", {"Sex": ["F"], "Density": ["20x"]})
    assert fm.offered(f) == []
    assert "survivorship battery only" in fm.describe_offer(f)


def test_a_relevant_comparison_with_one_populated_treatment_is_not_computable(frame):
    f = fm.Focus("D", {"Density": ["20x", "40x"]})
    only = frame[frame.Density == "20x"]
    ok, reason = fm.focus_shape(f, fm.apply_focus(only, f)).admits(fm.COMPARISON)
    assert not ok and "only 1 treatment(s)" in reason


# ── blocked focuses ────────────────────────────────────────────────────────

def test_stale_level_is_blocked_with_a_close_match(design):
    f = fm.Focus("Old", {"Genotype": ["wCS", "mDilp"]})
    [reason] = fm.block_reasons(f, design)
    assert reason.kind == fm.STALE and "mDilp235bx" in reason.fix


def test_stale_factor_is_blocked(design):
    [reason] = fm.block_reasons(fm.Focus("X", {"Diet": ["AL"]}), design)
    assert reason.kind == fm.STALE and "Diet" in reason.detail


def test_extra_levels_in_the_data_are_normal(design):
    assert fm.block_reasons(fm.Focus("X", {"Genotype": ["wCS"]}), design) == []


def test_never_populated_cell_is_absent_not_blocked(frame):
    unbalanced = frame[~((frame.Genotype == "mDilp235bx") & (frame.Density == "40x"))]
    design = fm.design_from_frame(unbalanced, ["Genotype", "Density", "Sex"])
    f = fm.Focus("G", {"Genotype": ["wCS", "mDilp235bx"], "Density": ["20x", "40x"]})
    populated = fm.populated_labels(fm.apply_focus(unbalanced, f))
    assert fm.block_reasons(f, design, populated) == []


def test_cell_emptied_by_exclusion_is_blocked(design, frame):
    f = fm.Focus("G", {"Genotype": ["wCS", "mDilp235bx"], "Density": ["20x", "40x"]})
    emptied = frame[~((frame.Genotype == "wCS") & (frame.Density == "40x"))]
    populated = fm.populated_labels(fm.apply_focus(emptied, f))
    [reason] = fm.block_reasons(f, design, populated)
    assert reason.kind == fm.EMPTY and "wCS/40x" in reason.detail


# ── out of date ────────────────────────────────────────────────────────────

def test_out_of_date_compares_definition_and_group():
    f = fm.Focus("F", {"Density": ["20x", "40x"]})
    payload = {"focus": {"definition": f.analytic_definition()}, "exclusion_group": None}
    assert fm.out_of_date_reasons(f, payload, None) == []
    assert fm.out_of_date_reasons(f, payload, "bad")          # group changed
    narrowed = f.copy(factors={"Density": ["20x"]})
    assert fm.out_of_date_reasons(narrowed, payload, None)    # redefined
    rebased = f.copy(reference={"Density": "40x"})
    assert "Reference" in fm.out_of_date_reasons(rebased, payload, None)[0]


def test_display_names_and_colours_do_not_make_results_out_of_date():
    f = fm.Focus("F", {"Density": ["20x", "40x"]})
    payload = {"focus": {"definition": f.analytic_definition()}}
    dressed = f.copy(display_names={"20x": "low"}, colours={"20x": "#000000"})
    assert fm.out_of_date_reasons(dressed, payload, None) == []


def test_results_with_no_recorded_definition_are_out_of_date():
    assert fm.out_of_date_reasons(fm.Focus("F", {"D": ["a"]}), {"n_total": 3}, None)


# ── config ─────────────────────────────────────────────────────────────────

def test_round_trip_through_config():
    f = fm.Focus("Crowding 20v40", {"Sex": ["F", "M"], "Density": ["20x", "40x"]},
                 reference={"Density": "40x"}, display_names={"F/20x": "F low"},
                 colours={"F/20x": "#112233"})
    [back] = fm.parse_focuses({"focuses": fm.focuses_to_config([f])})
    assert back.factors == f.factors and back.reference == f.reference
    assert back.display_names == f.display_names and back.colours == f.colours
    assert back.slug == "Crowding_20v40"


@pytest.mark.parametrize("block, needle", [
    ({"A": {"factors": {}}}, "names no factors"),
    ({"A": {"factors": {"D": ["x", "x"]}}}, "twice"),
    ({"A": {"factors": {"D": ["x", "y"]}, "reference": {"D": "z"}}}, "not one of"),
    ({"A": {"factors": {"D": ["x"]}, "reference": {"E": "x"}}}, "does not name"),
    ({"a b": {"factors": {"D": ["x"]}}, "a_b": {"factors": {"D": ["x"]}}}, "same output"),
])
def test_focus_block_validation(block, needle):
    problems = fm.validate_focus_block({"focuses": block})
    assert any(needle in p for p in problems), problems


# ── defined plots ──────────────────────────────────────────────────────────

def test_defined_plot_renders_only_when_every_curve_is_present(design, frame):
    f = fm.unfiltered(design)
    populated = fm.populated_labels(fm.apply_focus(frame, f))
    labels, why = fm.defined_plot_match(f, design, ["wCS/20x/F", "wCS/40x/F"], populated)
    assert labels == ["wCS/20x/F", "wCS/40x/F"] and why == ""
    labels, why = fm.defined_plot_match(f, design, ["wCS/20x/F", "InR/20x/F"], populated)
    assert labels == [] and "InR/20x/F" in why


def test_defined_plot_does_not_match_a_pooling_focus(design, frame):
    f = fm.Focus("D", {"Density": ["20x", "40x"]})
    populated = fm.populated_labels(fm.apply_focus(frame, f))
    labels, why = fm.defined_plot_match(f, design, ["wCS/20x/F"], populated)
    assert labels == [] and "pools over" in why


def test_rectangular_defined_plot_becomes_a_focus(design):
    f, why = fm.focus_from_defined_plot(
        "Females", ["wCS/20x/F", "wCS/40x/F", "mDilp235bx/20x/F", "mDilp235bx/40x/F"],
        design)
    assert why == "" and f.factors == {"Genotype": ["wCS", "mDilp235bx"],
                                       "Density": ["20x", "40x"], "Sex": ["F"]}


def test_diagonal_defined_plot_is_not_a_focus(design):
    f, why = fm.focus_from_defined_plot("Diag", ["wCS/20x/F", "mDilp235bx/40x/F"], design)
    assert f is None and "rectangular" in why


# ── copying ────────────────────────────────────────────────────────────────

def test_copy_check_rejects_what_would_be_blocked_here(design):
    ok, rejected = fm.copy_check(
        [fm.Focus("Good", {"Sex": ["F", "M"]}), fm.Focus("Bad", {"Diet": ["AL"]}),
         fm.Focus("Dup", {"Sex": ["F"]})],
        design, existing=["Dup"])
    assert [f.name for f in ok] == ["Good"]
    assert len(rejected) == 2


def test_output_names_carry_the_focus():
    f = fm.Focus("Crowding 20v40", {"D": ["a"]})
    assert fm.output_name("kaplan_meier", f, ".png") == "kaplan_meier_Crowding_20v40.png"
    assert fm.summary_filename(f) == "run_summary_Crowding_20v40.json"


def test_csv_discovery_keeps_file_order(tmp_path):
    ## The loader sorts individuals by treatment; discovery must not see that
    ## order, or the alphabetically-first level silently becomes the reference.
    path = tmp_path / "c.csv"
    pd.DataFrame({"Age": [5, 6, 7, 8], "Event": [1, 1, 1, 1],
                  "Genotype": ["wCS", "wCS", "mDilp235bx", "mDilp235bx"]}).to_csv(path, index=False)
    design = fm.discover_design(path, {"format": "auto"})
    assert design.levels["Genotype"] == ("wCS", "mDilp235bx")
    assert fm.unfiltered(design).reference_level("Genotype") == "wCS"
