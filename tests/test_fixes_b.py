"""Figures: the fixes found while writing the manual (brief section B).

Each test names the behaviour it pins. Most draw synthetic data straight
through :mod:`plotting` and :mod:`pubfigures`; the few that need a real run
use the small fixtures in ``conftest``.
"""

from __future__ import annotations

import copy
import inspect
import os

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.text as mtext  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pytest  # noqa: E402

from pysurvanalysis import lifetable, plot_registry, plotting, pubfigures as pf  # noqa: E402
from pysurvanalysis.experiment_types import STANDARD  # noqa: E402

from tests.conftest import make_experiment_dir, write_dlife_workbook  # noqa: E402

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

#: A Focus order that is NOT alphabetical, so a figure that sorts shows it.
ORDER = ["wt/drug", "wt/ctrl", "mut/drug", "mut/ctrl"]
FACTORS = {"G": ["wt", "mut"], "T": ["drug", "ctrl"]}


@pytest.fixture(autouse=True)
def _close_figures():
    yield
    plt.close("all")


@pytest.fixture(scope="module")
def cohort() -> pd.DataFrame:
    """A 2×2 cohort with censoring, its treatment an ordered Categorical in
    a non-alphabetical display order — what ``apply_focus`` produces."""
    rng = np.random.default_rng(7)
    rows = []
    for label in ORDER:
        g, t = label.split("/")
        times = rng.gamma(6.0, 6.0 + 2.0 * ORDER.index(label), 40).round(2)
        events = (rng.random(40) > 0.25).astype(int)
        rows += [{"time": ti, "event": ei, "G": g, "T": t, "treatment": label}
                 for ti, ei in zip(times, events)]
    frame = pd.DataFrame(rows)
    frame["treatment"] = pd.Categorical(frame["treatment"], categories=ORDER,
                                        ordered=True)
    return frame


@pytest.fixture(scope="module")
def lifetables(cohort) -> pd.DataFrame:
    return lifetable.compute_lifetables(cohort)


def _legend(ax) -> list[str]:
    return [t.get_text() for t in ax.get_legend().get_texts()]


def _line_colours(ax) -> dict[str, str]:
    return {line.get_label(): matplotlib.colors.to_hex(line.get_color())
            for line in ax.get_lines() if not line.get_label().startswith("_")}


# ── 1. time labels ─────────────────────────────────────────────────────────

LIFETABLE_FIGURES = (
    plotting.plot_km_curves, plotting.plot_hazard, plotting.plot_mortality,
    plotting.plot_number_at_risk, plotting.plot_km_with_risk_table,
    plotting.plot_nelson_aalen, plotting.plot_cumulative_events,
    plotting.plot_smoothed_hazard,
)


@pytest.mark.parametrize("draw", LIFETABLE_FIGURES, ids=lambda f: f.__name__)
def test_every_time_axis_takes_the_time_label(draw, lifetables):
    """A day-scaled census used to be labelled "Time (hours)" on every
    lifetable figure; ``time_label`` reaches them all, and None keeps the old
    text (the contract the QC viewer relies on)."""
    fig = draw(lifetables, time_label="Age (days)")
    assert fig.axes[-1].get_xlabel() == "Age (days)"
    assert draw(lifetables).axes[-1].get_xlabel() == "Time (hours)"


def test_the_other_time_axes_take_it_too(cohort, lifetables):
    assert plotting.plot_log_log(lifetables, time_label="Age (days)") \
        .axes[0].get_xlabel() == "log(Age (days))"
    assert plotting.plot_log_log(lifetables).axes[0].get_xlabel() == "log(Time)"
    assert "Age (days)" in plotting.plot_survival_distribution(
        cohort, time_label="Age (days)").axes[0].get_ylabel()
    per_chamber = lifetable.compute_lifetables_per_chamber(cohort.assign(chamber=1))
    assert plotting.plot_chamber_overlay_km(
        per_chamber, "wt/drug", time_label="Age (days)").axes[0].get_xlabel() \
        == "Age (days)"
    faceted = plotting.plot_km_faceted(lifetables, FACTORS, time_label="Age (days)")
    assert faceted.axes[0].get_xlabel() == "Age (days)"
    for draw in (*LIFETABLE_FIGURES, plotting.plot_log_log,
                 plotting.plot_survival_distribution, plotting.plot_km_faceted,
                 plotting.plot_lifespan_interaction, plotting.plot_chamber_overlay_km):
        param = inspect.signature(draw).parameters["time_label"]
        assert param.default is None, draw.__name__


def test_the_registry_draws_with_the_experiments_time_label(analysed_project):
    project, results = analysed_project
    result = results["rep_a"]
    label = result.experiment.type.resolve_time_label(result.experiment.config)
    for plot_id in ("km_curves", "mortality", "number_at_risk", "cumulative_events"):
        fig = plot_registry.build(plot_id, result)
        assert fig.axes[-1].get_xlabel() == label, plot_id


# ── 2. the Focus's order, display names and colours ─────────────────────────

def test_figures_follow_the_focus_order_not_the_alphabet(cohort, lifetables):
    for draw, frame in ((plotting.plot_km_curves, lifetables),
                        (plotting.plot_mortality, lifetables),
                        (plotting.plot_nelson_aalen, lifetables)):
        assert _legend(draw(frame).axes[0]) == ORDER
    ticks = plotting.plot_survival_distribution(cohort).axes[0].get_xticklabels()
    assert [t.get_text() for t in ticks] == ORDER


def test_focus_colours_and_display_names_reach_the_analysis_figures(lifetables):
    fig = plotting.plot_km_curves(
        lifetables, colours={"mut/drug": "#123456"},
        display_names={"wt/drug": "Wild type, drug"})
    ax = fig.axes[0]
    assert _legend(ax)[0] == "Wild type, drug"
    colours = _line_colours(ax)
    assert colours["mut/drug"] == "#123456"
    ## A treatment with no Focus colour takes the cycle by its place in the
    ## Focus's order — position 1 here, not its alphabetical rank.
    assert colours["wt/ctrl"] == plotting.COLORS[1]


def test_a_subset_keeps_each_treatments_colour(lifetables):
    """A Defined Plot draws some of the treatments; each keeps the colour it
    has in the Focus's main KM figure."""
    full = _line_colours(plotting.plot_km_curves(lifetables).axes[0])
    subset = _line_colours(plotting.plot_km_curves(
        lifetables, treatments=["mut/ctrl"]).axes[0])
    assert subset == {"mut/ctrl": full["mut/ctrl"]}


def test_the_registry_draws_with_the_focus_colours(analysed_project):
    _project, results = analysed_project
    result = copy.copy(results["rep_a"])
    label = str(result.lifetables["treatment"].iloc[0])
    result.focus = result.focus.copy(colours={label: "#abcdef"},
                                     display_names={label: "Shown name"})
    fig = plot_registry.build("km_curves", result)
    assert _line_colours(fig.axes[0])["Shown name"] == "#abcdef"
    opts = plot_registry.figure_options(result.experiment, result.focus)
    assert opts["colours"] == {label: "#abcdef"}


def test_publication_legends_follow_the_focus_order(lifetables):
    """A discrete plotnine scale sorts string levels; the legend has to be
    told the order, or it is alphabetical beside curves that are not."""
    spec = pf.default_spec("km_curves")
    spec.treatments = ORDER
    spec.display_names = {"wt/drug": "Wild type, drug"}
    fig = pf.build_ggplot(pf.curve_data(lifetables, spec), spec,
                          pf.PlotStyle(risk_table=False)).draw()
    texts = [t.get_text() for t in fig.findobj(mtext.Text)]
    shown = ["Wild type, drug", "wt/ctrl", "mut/drug", "mut/ctrl"]
    assert [t for t in texts if t in shown] == shown


def test_the_publication_forest_uses_display_names():
    hr = pd.DataFrame({"group1": ["a"], "group2": ["b"], "hazard_ratio": [2.0],
                       "hr_ci_lo": [1.0], "hr_ci_hi": [4.0]})
    spec = pf.default_spec("hazard_ratio_forest")
    spec.display_names = {"a": "Alpha"}
    assert pf.forest_data(hr, spec)["label"].tolist() == ["Alpha vs b"]


# ── 3. cumulative deaths, the raw hazard, one smoothing constant ───────────

def test_cumulative_deaths_is_one_minus_km_in_both_renderers(lifetables):
    group = lifetables[lifetables["treatment"].astype(str) == "wt/ctrl"]
    ax = plotting.plot_cumulative_events(lifetables).axes[0]
    [line] = [ln for ln in ax.get_lines() if ln.get_label() == "wt/ctrl"]
    assert np.allclose(line.get_ydata()[1:], 1.0 - group["km_lx"].to_numpy())

    kind = pf.kind_for("cumulative_events")
    data = pf.series_data(lifetables, pf.default_spec("cumulative_events"), kind)
    pub = data[data["treatment"] == "wt/ctrl"].iloc[1:]
    assert np.allclose(pub["value"], 1.0 - group["km_lx"].to_numpy())
    assert np.allclose(pub["ci_hi"], 1.0 - group["km_ci_lo"].to_numpy())
    assert "probability" in kind.y_label.lower()
    caption = plot_registry.get("cumulative_events").caption
    assert "1 − S(t)" in caption and "count" not in caption.lower()


def test_the_raw_hazard_and_cumulative_deaths_are_in_the_plot_set():
    ids = STANDARD.plot_ids()
    assert "cumulative_events" in ids and "hazard" in ids


def test_the_smoothed_hazard_has_one_bandwidth(lifetables):
    from scipy.ndimage import gaussian_filter1d

    sigma = plotting.SMOOTHED_HAZARD_SIGMA
    assert inspect.signature(plotting.plot_smoothed_hazard) \
        .parameters["sigma"].default == sigma
    group = lifetables[lifetables["treatment"].astype(str) == "wt/ctrl"]
    derived = pf._derived(group, pf.kind_for("smoothed_hazard"))
    assert np.allclose(derived["hx_smooth"],
                       gaussian_filter1d(group["hx"].to_numpy(float), sigma=sigma))


# ── 4. the lifespan interaction plot ───────────────────────────────────────

def test_the_interaction_plot_puts_the_first_factor_on_x(cohort):
    ax = plotting.plot_lifespan_interaction(cohort, FACTORS).axes[0]
    assert ax.get_xlabel() == "G"
    assert [t.get_text() for t in ax.get_xticklabels()] == ["wt", "mut"]
    assert _legend(ax) == ["drug", "ctrl"]


def test_both_interaction_plots_draw_the_km_median_and_its_interval(cohort):
    spec = pf.default_spec("interaction_lifespan")
    spec.treatments = ORDER
    data = pf.interaction_data(cohort, spec)
    assert list(data["x"].cat.categories) == ["wt", "mut"]
    for _i, row in data.iterrows():
        cell = cohort[cohort["treatment"].astype(str) == f"{row['x']}/{row['series']}"]
        expected = lifetable.km_median_ci(cell)
        assert row["value"] == pytest.approx(expected["median"])
        if np.isfinite(expected["ci_lo"]):
            assert row["ci_lo"] == pytest.approx(expected["ci_lo"])
    ## The analysis figure plots the same numbers.
    ax = plotting.plot_lifespan_interaction(cohort, FACTORS).axes[0]
    drawn = sorted(round(float(y), 6) for bars in ax.containers
                   for y in bars.lines[0].get_ydata())
    assert drawn == sorted(round(float(v), 6) for v in data["value"])


def test_a_cell_whose_survival_never_halves_has_no_median():
    cell = pd.DataFrame({"time": [5.0, 6.0, 7.0, 8.0], "event": [1, 0, 0, 0]})
    assert plotting.cell_lifespan(cell) is None


def test_the_mean_metric_is_the_restricted_mean(cohort):
    from lifelines import KaplanMeierFitter
    from lifelines.utils import restricted_mean_survival_time

    cell = cohort[cohort["treatment"].astype(str) == "wt/ctrl"]
    tau = 30.0
    value, low, high = plotting.cell_lifespan(cell, "mean", tau)
    kmf = KaplanMeierFitter().fit(cell["time"], cell["event"])
    assert value == pytest.approx(restricted_mean_survival_time(kmf, t=tau))
    assert low < value < high


def test_the_rmst_standard_error_is_the_classical_one():
    ## S = .75, .5, .25 at t = 1, 2, 3; to tau = 4 the areas right of each
    ## death are 1.5, .75 and .25, so Var = 1.5²/12 + .75²/6 + .25²/2.
    se = plotting.rmst_se([1, 2, 3, 4], [1, 1, 1, 0], 4.0)
    assert se == pytest.approx(np.sqrt(0.3125))


# ── 5. the lifespan distribution ───────────────────────────────────────────

def test_the_distribution_leaves_censored_individuals_out(cohort):
    late = cohort.copy()
    late.loc[late["event"] == 0, "time"] = 5000.0
    ax = plotting.plot_survival_distribution(late).axes[0]
    assert ax.dataLim.y1 < 1000
    assert pf.distribution_data(late, pf.default_spec("survival_distribution")) \
        ["value"].max() < 1000
    assert "censored" in plot_registry.get("survival_distribution").caption


# ── 6. the at-risk counts ──────────────────────────────────────────────────

def test_the_at_risk_table_and_band_print_the_same_counts(lifetables):
    fig = plotting.plot_km_with_risk_table(lifetables)
    risk_ax = fig.axes[1]
    table = {(round(t.get_position()[0], 6), int(round(t.get_position()[1]))): int(t.get_text())
             for t in risk_ax.texts}
    spec = pf.default_spec("km_curves")
    band = pf.risk_band_data(pf.curve_data(lifetables, spec), pf.PlotStyle(), spec)
    t_max = float(lifetables["time"].max())
    assert sorted({x for x, _row in table}) == \
        [round(t, 6) for t in plotting.default_risk_times(t_max)]
    for row, label in enumerate(ORDER):
        printed = [table[(round(t, 6), row)] for t in plotting.default_risk_times(t_max)]
        banded = band[band["label"] == label].sort_values("time")["count"].tolist()
        assert printed == banded, label


def test_at_risk_means_a_recorded_time_at_or_after_t():
    times, at_risk = [10.0, 20.0, 30.0], [5, 3, 1]
    ## Entering a knot counts it; between knots, the next knot's number.
    assert plotting.at_risk_counts(times, at_risk, [0, 10, 15, 20, 30, 31]) \
        == [5, 5, 3, 3, 1, 0]


# ── 7. the Plot Editor ─────────────────────────────────────────────────────

def test_new_specs_label_the_axes_they_have():
    assert pf.default_spec("hazard_ratio_forest", "Age (days)").x_label \
        == "Hazard ratio (log scale)"
    assert pf.default_spec("interaction_lifespan", "Age (days)").x_label == ""
    assert pf.default_spec("survival_distribution", "Age (days)").x_label == "Age (days)"
    assert pf.default_spec("cumulative_events").reference_line == 0.5


def test_the_interaction_spec_is_named_for_the_first_factor(project):
    spec = pf.specs_for(project.member("rep_a"))["interaction_lifespan"]
    assert spec.x_label == "Genotype"
    assert spec.series_label == "Treatment"


def test_the_log_log_publication_figure_joins_its_points():
    assert pf.effective_geom(pf.PlotStyle(), pf.kind_for("log_log")) == "line"


@pytest.fixture(scope="module")
def qapp():
    pytest.importorskip("PyQt6")
    from PyQt6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _one_factor_experiment(directory):
    """A standalone experiment whose Focus varies Genotype only."""
    from pysurvanalysis.domain import SurvivalExperiment

    make_experiment_dir(directory, factors={"Genotype": ["wt", "mut"],
                                            "Treatment": ["ctrl"]})
    return SurvivalExperiment(directory)


def test_the_editor_opens_on_the_headline_and_enables_what_a_figure_uses(qapp, tmp_path):
    from pysurvanalysis.apps.plot_editor import PlotEditorWindow

    editor = PlotEditorWindow(_one_factor_experiment(tmp_path / "one"))
    try:
        ## The type's headline is km_risk_table, which a Publication Figure
        ## folds into km_curves; looked up raw it never matched.
        assert editor._current_id == "km_curves"

        editor._plot_combo.setCurrentText("survival_distribution")
        assert editor._ci_alpha.isEnabled() and not editor._ci_band.isEnabled()

        editor._plot_combo.setCurrentText("hazard_ratio_forest")
        for widget in (editor._point_shape, editor._point_size, editor._point_fill,
                       editor._point_stroke, editor._point_stroke_color):
            assert widget.isEnabled()
        assert not editor._show_points.isEnabled()
        assert editor.spec.x_label == "Hazard ratio (log scale)"
    finally:
        editor.close()


def test_a_colour_swatch_can_return_to_auto(qapp):
    from pysurvanalysis.apps.plot_editor import ColorButton

    swatch = ColorButton("#000000", auto_text="curve")
    fired: list[bool] = []
    swatch.changed.connect(lambda: fired.append(True))
    swatch.reset()
    assert swatch.color() == "" and fired == [True]


# ── 8. gridlines ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("grid,x_on,y_on", [("none", False, False),
                                            ("y", False, True),
                                            ("both", True, True)])
def test_gridlines_are_drawn_on_theme_classic(lifetables, grid, x_on, y_on):
    spec = pf.default_spec("km_curves")
    style = pf.PlotStyle(theme="theme_classic", grid=grid, risk_table=False)
    ax = pf.build_ggplot(pf.curve_data(lifetables, spec), spec, style).draw().axes[0]
    assert any(line.get_visible() for line in ax.get_xgridlines()) == x_on
    assert any(line.get_visible() for line in ax.get_ygridlines()) == y_on


# ── 9. rendering only what the Focus is offered ────────────────────────────

def test_render_all_skips_a_curated_figure_the_focus_is_not_offered(tmp_path):
    experiment = _one_factor_experiment(tmp_path / "render")
    experiment.run_analysis()
    pf.save_specs(experiment.directory, {
        "km_curves": pf.default_spec("km_curves"),
        "km_faceted": pf.default_spec("km_faceted"),
    })
    logs: list[str] = []
    written = pf.render_all(experiment, fmt="svg", log=logs.append)
    assert [p.name.split("_Factorial")[0] for p in written] == ["km_curves"]
    assert any("km_faceted: not offered" in line for line in logs)


# ── 10. Defined Plots ──────────────────────────────────────────────────────

def test_defined_plots_never_vanish_and_never_go_stale(tmp_path):
    from pysurvanalysis import pipeline
    from pysurvanalysis.domain import SurvivalExperiment, config as cfgmod

    directory = tmp_path / "dp"
    write_dlife_workbook(directory / "data" / "dp.xlsx", defined_plots={
        "Bs": ["b/a", "b/b"],
        "Short": ["a", "b"],           # a level of one factor, not a treatment
    })
    cfgmod.save_config(directory, {"input": {"format": "excel"}})
    experiment = SurvivalExperiment(directory)
    stale = experiment.outputs("Unfiltered").ensure().plot("defined_Gone.png")
    stale.write_bytes(b"old")

    result = experiment.run_analysis()
    assert list(result.defined_plot_paths) == ["Bs"]
    reason = next(i["reason"] for i in result.not_applicable
                  if i["action"] == "Defined Plot 'Short'")
    assert "not a full treatment" in reason
    assert not stale.exists()

    ## Generate plots draws them too.
    titles = [title for title, _fig in pipeline.render_plots(experiment)]
    assert any(title.startswith("Defined Plot — Bs") for title in titles)
