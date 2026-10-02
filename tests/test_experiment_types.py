"""Experiment Types: one data-source type, shape-gated figures, the action union.

ADR-0011 retired the Interaction Experiment and Custom types; their keys still
resolve, to the general case, and the 2×2 machinery is gated by Focus Shape.
"""

from __future__ import annotations

import pandas as pd
import pytest

from pysurvanalysis import plot_registry
from pysurvanalysis.domain import focus as fm
from pysurvanalysis.experiment_types import (
    STANDARD, available_types, get_type, type_for_config,
)
from pysurvanalysis.script_editor import actions as action_mod


def _shape(cells):
    """A FocusShape over the given (G, T) cells."""
    f = fm.Focus("F", {"G": ["a", "b"], "T": ["1", "2"]})
    rows = [{"time": 1.0, "event": 1, "G": g, "T": t} for g, t in cells]
    return fm.focus_shape(f, fm.apply_focus(pd.DataFrame(rows), f))


@pytest.mark.parametrize("key", [None, "", "custom", "interaction", "INTERACTION"])
def test_absent_and_retired_keys_are_the_general_case(key):
    assert get_type(key) is STANDARD
    assert type_for_config({"experiment_type": key} if key is not None else {}) is STANDARD


def test_unknown_key_is_an_error_not_a_fallback():
    with pytest.raises(ValueError, match="Unknown experiment_type"):
        get_type("fecundity")


def test_there_is_one_selectable_type():
    assert available_types() == [STANDARD]


def test_every_plot_in_every_plot_set_has_a_builder():
    full = _shape([("a", "1"), ("a", "2"), ("b", "1"), ("b", "2")])
    for exp_type in available_types():
        ids = [p.id for p in exp_type.plot_set_for(full)]
        missing = [p for p in ids if p not in plot_registry.PLOTS]
        assert not missing, f"{exp_type.key} names unbuildable plots: {missing}"


def test_headline_figure_is_in_its_own_plot_set():
    full = _shape([("a", "1"), ("a", "2"), ("b", "1"), ("b", "2")])
    for shape in (None, full):
        ids = [p.id for p in STANDARD.plot_set_for(shape)]
        assert STANDARD.headline_for(shape) in ids


def test_a_populated_2x2_earns_the_faceted_figures():
    full = _shape([("a", "1"), ("a", "2"), ("b", "1"), ("b", "2")])
    ids = [p.id for p in STANDARD.plot_set_for(full)]
    assert "km_faceted" in ids and "interaction_lifespan" in ids
    assert STANDARD.headline_for(full) == "km_faceted"


def test_a_missing_crossing_cell_keeps_the_figures_in_the_set():
    ## Relevance is the definition's: the figures still belong to the run
    ## (a missing cell is a missing curve); only the models need full crossing.
    partial = _shape([("a", "1"), ("a", "2"), ("b", "1")])
    ids = [p.id for p in STANDARD.plot_set_for(partial)]
    assert "km_faceted" in ids
    assert STANDARD.headline_for(partial) == "km_faceted"


def test_one_varying_factor_earns_no_crossing_figures():
    f = fm.Focus("F", {"G": ["a", "b"]})
    rows = [{"time": 1.0, "event": 1, "G": g} for g in ("a", "b")]
    shape = fm.focus_shape(f, fm.apply_focus(pd.DataFrame(rows), f))
    ids = [p.id for p in STANDARD.plot_set_for(shape)]
    assert "km_faceted" not in ids and "interaction_lifespan" not in ids
    assert "hazard_ratio_forest" in ids
    assert STANDARD.headline_for(shape) == STANDARD.headline_plot_id


def test_a_single_treatment_earns_no_comparison_figures():
    f = fm.Focus("F", {"G": ["a"]})
    shape = fm.focus_shape(f, fm.apply_focus(
        pd.DataFrame([{"time": 1.0, "event": 1, "G": "a"}]), f))
    ids = [p.id for p in STANDARD.plot_set_for(shape)]
    assert "hazard_ratio_forest" not in ids and "log_log" not in ids
    assert "km_risk_table" in ids


def test_the_factorial_actions_are_in_the_registry_with_their_requirement():
    registry = action_mod.registry_for(STANDARD)
    for key in ("faceted_km", "interaction_plot"):
        assert registry[key].requires == fm.FACTORIAL_PLOT.key
    for key in ("cox_interaction", "rmst_interaction"):
        assert registry[key].requires == fm.FACTORIAL_MODEL.key
    for key in ("log_rank_pairwise", "log_rank_omnibus", "gehan_wilcoxon", "forest_plot"):
        assert registry[key].requires == fm.COMPARISON.key
    for key in ("km_curves", "nelson_aalen", "mortality", "parametric_aft"):
        assert registry[key].requires is None
    assert "run_in_focuses" in registry


def test_unknown_action_is_still_a_hard_error():
    problems = action_mod.validate_steps([{"action": "nonesuch"}], STANDARD)
    assert problems and "nonesuch" in problems[0]


def test_run_in_focuses_may_appear_once():
    problems = action_mod.validate_steps(
        [{"action": "run_in_focuses"}, {"action": "run_in_focuses"}], STANDARD)
    assert any("more than once" in p for p in problems)


def test_scaffold_names_the_type():
    assert STANDARD.scaffold_config(minimal=True) == {"experiment_type": STANDARD.key}


def test_legacy_factor_block_stringifies_levels():
    assert fm.legacy_factor_block({"factors": {"D": [20, 40]}}) == {"D": ["20", "40"]}


def test_standard_lifespan_validates_its_own_global_key():
    assert STANDARD.validate_config({"global": {"min_n_per_chamber": 5}}) == []
    problems = STANDARD.validate_config({"global": {"min_n_per_chamber": -1}})
    assert problems and "min_n_per_chamber" in problems[0]


def test_time_label_falls_back_to_the_unit():
    assert STANDARD.resolve_time_label({"global": {"time_unit": "weeks"}}) \
        == "Age (weeks)"
    assert STANDARD.resolve_time_label({"global": {"time_label": "Adult age"}}) \
        == "Adult age"
