"""Orchestrate the full survival analysis pipeline — one Focus per run.

This module ties together data loading, Focus slicing, lifetable computation,
statistical tests, plotting, and report generation into a single
``run_analysis`` call.

Every run is under a **Focus** (ADR-0011): a named slice of the factors and
levels discovered in the data file. There is no unfocused analysis. Outputs
land in the Focus's own directory with its name on every file, so analysing a
second Focus never overwrites the first.

Supports two invocation modes:
  * **Experiment mode** — pass ``experiment`` (and optionally ``focus``); the
    config supplies everything, and outputs go to ``analysis/<focus>/``.
  * **Direct file mode** — pass a path to an ``.xlsx``, ``.csv``, or ``.tsv``
    file directly. The run is under the **Unfiltered** Focus unless one is
    given, and outputs go to ``<stem>_results/<focus>/``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Optional

import pandas as pd

from . import data_loader, lifetable, plotting, statistics

#: Why an item a run left out is missing — in the reader's words.
UNTICKED = "unticked in the Hub (`omit:` in survival_config.yaml)"


class AnalysisResult:
    """Container for all analysis outputs."""

    def __init__(
        self,
        input_file: Path,
        output_dir: Path,
        factors: list[str],
        individual_data: pd.DataFrame,
        lifetables: pd.DataFrame,
        summary: pd.DataFrame,
        median_surv: pd.DataFrame,
        mean_surv: pd.DataFrame,
        pairwise_lr: pd.DataFrame,
        omnibus_lr: dict,
        hazard_ratios: pd.DataFrame,
        lifespan_stats: dict | None = None,
        assume_censored: bool = True,
        excluded_chambers: set | None = None,
        defined_plots: list[list[str]] | None = None,
        # New fields
        pairwise_gw: pd.DataFrame | None = None,
        parametric_models: dict | None = None,
        surv_quantiles: pd.DataFrame | None = None,
        experiment_summary: dict | None = None,
        nelson_aalen: pd.DataFrame | None = None,
    ):
        self.input_file = input_file
        self.output_dir = output_dir
        self.factors = factors
        self.individual_data = individual_data
        self.lifetables = lifetables
        self.summary = summary
        self.median_surv = median_surv
        self.mean_surv = mean_surv
        self.pairwise_lr = pairwise_lr
        self.omnibus_lr = omnibus_lr
        self.hazard_ratios = hazard_ratios
        self.lifespan_stats = lifespan_stats or {}
        self.assume_censored = assume_censored
        self.excluded_chambers: set = excluded_chambers or set()
        self.defined_plots: list[list[str]] = defined_plots or []
        self.cox_analyses: list[dict] = []
        #: The Experiment Directory this run belongs to, when there is one.
        self.experiment: Any = None
        #: The Experiment Type that chose the base battery and Plot Set.
        self.experiment_type: Any = None
        #: The active Exclusion Group's name, stamped on every output.
        self.exclusion_group: str | None = None
        #: plot id → saved figure path, in the Plot Set's order.
        self.figure_paths: dict[str, Path] = {}
        #: Defined Plot name → saved figure path.
        self.defined_plot_paths: dict[str, Path] = {}
        #: The Focus this run is under, its Shape, and the data file's design.
        self.focus: Any = None
        self.focus_shape: Any = None
        self.design: Any = None
        #: Where this run's files live (a FocusOutputs).
        self.outputs: Any = None
        #: The Headline Figure for this Focus's shape.
        self.headline_plot_id: str | None = None
        #: ``{"action", "reason"}`` for every real action this Focus does not
        #: admit — recorded, never fatal, never silent.
        self.not_applicable: list[dict] = []
        #: ``{"id", "item", "reason"}`` for every analysis or figure this run
        #: left out by choice (the config's ``omit:``) — a choice, not a gap.
        self.left_out: list[dict] = []
        #: Individuals with no recorded level for a factor the Focus names —
        #: in no treatment, so outside the slice, and said so rather than
        #: silently dropped.
        self.unassigned: int = 0
        # New analysis results
        self.pairwise_gw: pd.DataFrame = pairwise_gw if pairwise_gw is not None else pd.DataFrame()
        self.parametric_models: dict = parametric_models or {}
        self.surv_quantiles: pd.DataFrame = surv_quantiles if surv_quantiles is not None else pd.DataFrame()
        self.experiment_summary: dict = experiment_summary or {}
        self.nelson_aalen: pd.DataFrame = nelson_aalen if nelson_aalen is not None else pd.DataFrame()

    def has_chambers(self) -> bool:
        """True when the input carries real chamber identities.

        CSV cohorts do not, so an Exclusion Group naming chambers cannot have
        removed anything from them — and must not be reported as if it had.
        """
        if self.individual_data is None or "chamber" not in self.individual_data:
            return False
        return not self.individual_data["chamber"].astype(str).eq("N/A").all()

    def n_excluded_applied(self) -> int:
        """How many excluded chambers this input could actually have."""
        return len(self.excluded_chambers or set()) if self.has_chambers() else 0

    @property
    def focus_record(self) -> dict:
        """The Focus as the Run Summary records it and every report describes
        it — the same dict whether the report is built live or from disk."""
        focus, shape, design = self.focus, self.focus_shape, self.design
        if focus is None:
            return {}
        return {
            "name": focus.name,
            "slug": focus.slug,
            "definition": focus.analytic_definition(),
            "description": focus.describe(design),
            "filters": focus.filter_factors,
            "pooled_over": focus.pooled_over(design),
            "shape": shape.describe() if shape is not None else None,
            "treatments": list(shape.populated) if shape is not None else [],
            "absent_cells": list(shape.absent) if shape is not None else [],
            "headline": self.headline_plot_id,
            "unassigned": int(self.unassigned or 0),
        }


def _discover_xlsx(project_dir: Path) -> Path:
    """Find the single .xlsx file in a project directory.

    Raises
    ------
    FileNotFoundError
        If no .xlsx file is found.
    ValueError
        If more than one .xlsx file is found.
    """
    xlsx_files = list(project_dir.glob("*.xlsx"))
    if len(xlsx_files) == 0:
        raise FileNotFoundError(
            f"No .xlsx file found in project directory: {project_dir}"
        )
    if len(xlsx_files) > 1:
        raise ValueError(
            f"Multiple .xlsx files found in {project_dir}: "
            f"{[f.name for f in xlsx_files]}. "
            "Place exactly one .xlsx file in the project directory."
        )
    return xlsx_files[0]


def run_analysis(
    input_path: str | Path,
    output_dir: Optional[str | Path] = None,
    assume_censored: bool = True,
    # CSV-specific parameters
    time_col: str = "Age",
    event_col: str = "Event",
    factor_cols: list[str] | None = None,
    csv_format: str = "auto",
    col_mapping: list[dict] | None = None,
    factor_names: list[str] | None = None,
    factor_levels: dict[str, list] | None = None,
    # Extra chamber ids to exclude on top of any Excel ChamberFlags sheet.
    extra_excluded_chambers: set | None = None,
    # An Experiment Directory drives everything from its config.
    experiment: "Any" = None,
    # The Focus this run is under; default the experiment's Active Focus, or
    # Unfiltered in direct mode.
    focus: "Any" = None,
    # Analysis and plot ids to leave out; default the config's `omit:` block.
    omit_analyses: Optional[Iterable[str]] = None,
    omit_plots: Optional[Iterable[str]] = None,
    log=None,
) -> AnalysisResult:
    """Run the complete survival analysis pipeline under one Focus.

    Two ways in:

    * **Experiment mode** — pass ``experiment`` (a
      :class:`~pysurvanalysis.domain.experiment.SurvivalExperiment`). Its
      ``survival_config.yaml`` supplies the input format, the censoring policy,
      the active Exclusion Group, the **Experiment Type** and the Focuses.
      Outputs go to ``analysis/<focus>/``.
    * **Direct mode** — pass a file (or a directory holding one ``.xlsx``) and
      the explicit keyword arguments. The run is under **Unfiltered** unless a
      Focus is given; outputs go to ``<stem>_results/<focus>/``.

    A Focus that names factors or levels the file lacks, or whose cells the
    exclusions emptied, raises
    :class:`~pysurvanalysis.domain.experiment.BlockedFocusError` before
    anything is written.

    Analyses and figures the config's ``omit:`` block names (the boxes
    unticked in the Hub) are not computed, and the run records each as
    **left out** — in the log, the Run Summary and the report — so a missing
    table reads as a choice, never as a gap (ADR-0012).

    Returns an :class:`AnalysisResult` with everything computed.
    """
    from .domain import config as cfgmod, focus as fm
    from .domain.experiment import BlockedFocusError
    from .experiment_types import STANDARD

    emit = log or (lambda _m: None)
    exp_type = experiment.type if experiment is not None else STANDARD
    config = dict(experiment.config) if experiment is not None else {}

    # ── Resolve the input file ─────────────────────────────────────────────
    if experiment is not None:
        input_path = experiment.data_file()
    else:
        input_path = Path(input_path)
        if input_path.is_dir():
            input_path = _discover_xlsx(input_path)
    input_path = Path(input_path)

    # ── Exclusions ─────────────────────────────────────────────────────────
    excluded_chambers: set = set()
    defined_plots: list[list[str]] = []
    if input_path.suffix.lower() == ".xlsx":
        excluded_chambers = data_loader.load_chamber_flags(input_path)
        defined_plots = data_loader.load_defined_plots(input_path)
    if extra_excluded_chambers:
        excluded_chambers = set(excluded_chambers) | set(extra_excluded_chambers)

    exclusion_group = None
    if experiment is not None:
        from .domain import config as cfgmod

        exclusion_group = cfgmod.exclusion_group(config)

    # ── Load ───────────────────────────────────────────────────────────────
    if experiment is not None:
        from .domain import config as cfgmod

        opts = cfgmod.input_options(config)
        fmt = str(opts.get("format", "auto"))
        assume_censored = exp_type.resolve_assume_censored(config)
        time_col = str(opts.get("time_col") or time_col)
        event_col = str(opts.get("event_col") or event_col)
        factor_cols = opts.get("factor_cols", factor_cols)
        factor_names = opts.get("factor_names", factor_names)
        col_mapping = opts.get("col_mapping", col_mapping)
        csv_format = "auto" if fmt in {"auto", "excel"} else fmt

    emit(f"Loading {input_path.name}…")
    raw_data, discovered_factors = data_loader.load_experiment(
        input_path,
        assume_censored=assume_censored,
        excluded_chambers=excluded_chambers,
        time_col=time_col,
        event_col=event_col,
        factor_cols=factor_cols,
        csv_format=csv_format,
        col_mapping=col_mapping,
        factor_names=factor_names,
        factor_levels=factor_levels,
    )

    # ── The Focus ──────────────────────────────────────────────────────────
    # The design comes from the file before any exclusion — the Design sheet
    # for a workbook — so an emptied cell can be told from one that was never
    # there.
    if experiment is not None:
        design = experiment.design()
    else:
        design = fm.discover_design(input_path, {
            "format": csv_format, "time_col": time_col, "event_col": event_col,
            "factor_cols": factor_cols, "col_mapping": col_mapping,
            "factor_names": factor_names,
        })
    if focus is None:
        focus = (experiment.active() if experiment is not None else None) \
            or fm.unfiltered(design)

    stale = fm.stale_reasons(focus, design)
    if stale:
        raise BlockedFocusError(focus, stale)
    individual_data = fm.apply_focus(raw_data, focus)
    named = [f for f in focus.factors if f in raw_data.columns]
    unassigned = int(raw_data[named].isna().any(axis=1).sum()) if named else 0
    if unassigned:
        emit(f"  {unassigned} individual(s) have no recorded level of "
             f"{', '.join(named)} and belong to no treatment — outside this Focus.")
    populated = fm.populated_labels(individual_data)
    _raise_if_empty(focus, design, individual_data)
    shape = fm.focus_shape(focus, individual_data)
    factors = list(focus.varying_factors)
    emit(f"Focus {focus.name!r}: {focus.describe(design)} — "
         f"{len(individual_data)} individuals, {len(populated)} treatment(s), "
         f"shape {shape.describe()}")

    # ── Output directory ───────────────────────────────────────────────────
    # Every run writes into its Focus's own directory, every file carrying the
    # Focus's name; direct mode keeps the legacy <stem>_results/ parent.
    if output_dir is None:
        output_dir = (experiment.focus_dir(focus) if experiment is not None
                      else input_path.parent / f"{input_path.stem}_results" / focus.slug)
    outs = fm.FocusOutputs.at(output_dir, focus).ensure()
    output_dir = outs.root

    not_applicable: list[dict] = []

    def _not_applicable(action: str, reason: str) -> None:
        not_applicable.append({"action": action, "reason": reason})
        emit(f"  Not applicable — {action}: {reason}")

    # ── The selection: what this run leaves out ────────────────────────────
    if omit_analyses is None:
        omit_analyses = cfgmod.omitted(config, "analyses")
    if omit_plots is None:
        omit_plots = cfgmod.omitted(config, "plots")
    omit_analyses, omit_plots = frozenset(omit_analyses), frozenset(omit_plots)
    left_out: list[dict] = []

    def _left_out(item_id: str, label: str, reason: str = UNTICKED) -> None:
        left_out.append({"id": item_id, "item": label, "reason": reason})
        emit(f"  Left out — {label}: {reason}")

    ## Only what this Focus is offered can be left out of it: an unticked
    ## interaction analysis means nothing to a one-factor Focus.
    wanted: set[str] = set()
    for analysis in exp_type.analysis_set_for(shape):
        if analysis.id in omit_analyses:
            _left_out(analysis.id, analysis.label)
        else:
            wanted.add(analysis.id)

    # ── Compute ────────────────────────────────────────────────────────────
    emit("Computing lifetables and summary statistics…")
    lifetables = lifetable.compute_lifetables(individual_data)
    summary = statistics.summary_statistics(individual_data)
    median_surv = lifetable.median_survival(lifetables)
    mean_surv = lifetable.mean_survival(individual_data)

    ## Comparisons need two treatments. A single-treatment Focus is not asked
    ## them at all; one whose second treatment the data never populated is
    ## asked, and told why there is no answer.
    comparable, why = shape.admits(fm.COMPARISON)
    pairwise_lr = pairwise_gw = hazard_ratios = pd.DataFrame()
    omnibus_lr: dict = {}
    comparisons = wanted & {"logrank_pairwise", "logrank_omnibus",
                            "gehan_wilcoxon", "hazard_ratios"}
    if comparable and comparisons:
        emit("Running survival comparisons…")
        if "logrank_pairwise" in comparisons:
            pairwise_lr = statistics.pairwise_logrank(individual_data)
        if "logrank_omnibus" in comparisons:
            omnibus_lr = statistics.logrank_multi(individual_data)
        if "gehan_wilcoxon" in comparisons:
            pairwise_gw = statistics.pairwise_gehan_wilcoxon(individual_data)
        if "hazard_ratios" in comparisons:
            hazard_ratios = statistics.pairwise_hazard_ratios(individual_data)
    elif comparisons and shape.relevant(fm.COMPARISON)[0]:
        _not_applicable("Survival comparisons", why)
    ## Pooled per-factor-level statistics only mean something when two or more
    ## factors vary; with one they repeat the per-treatment table.
    lifespan_stats = lifetable.lifespan_statistics(
        individual_data, factors if len(factors) >= 2 else [],
        assume_censored=assume_censored,
    )
    surv_quantiles = lifetable.survival_quantiles(lifetables)
    parametric_models: dict = {}
    if "parametric_aft" in wanted:
        try:
            parametric_models = statistics.fit_parametric_models(individual_data)
        except Exception:  # noqa: BLE001 - a non-converging AFT fit never kills a run
            parametric_models = {}
    exp_summary = statistics.experiment_summary(individual_data)

    result = AnalysisResult(
        input_file=input_path,
        output_dir=output_dir,
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
        assume_censored=assume_censored,
        excluded_chambers=excluded_chambers,
        defined_plots=defined_plots,
        pairwise_gw=pairwise_gw,
        parametric_models=parametric_models,
        surv_quantiles=surv_quantiles,
        experiment_summary=exp_summary,
    )
    result.experiment = experiment
    result.experiment_type = exp_type
    result.exclusion_group = exclusion_group
    result.figure_paths = {}
    result.focus = focus
    result.focus_shape = shape
    result.design = design
    result.outputs = outs
    result.headline_plot_id = exp_type.headline_for(shape)
    result.not_applicable = not_applicable
    result.left_out = left_out
    result.unassigned = unassigned

    # ── The Factorial Battery, by Focus Shape ──────────────────────────────
    from .experiment_types.factorial import BATTERY, run_factorial_battery

    ## Offered only when the Focus varies two or more factors (and the
    ## interaction analyses are ticked); then run, or recorded as Not
    ## Applicable when the crossing has an empty cell.
    if "interaction" in wanted:
        try:
            models = run_factorial_battery(individual_data, focus, shape)
            emit("Running the Factorial Battery…")
            result.cox_analyses.extend(models)
        except fm.NotApplicable as exc:
            _not_applicable(BATTERY, exc.reason)

    # ── Save tabular outputs ───────────────────────────────────────────────
    lifetables.to_csv(outs.data("lifetables"), index=False)
    individual_data.to_csv(outs.data("individual_data"), index=False)
    summary.to_csv(outs.data("summary"), index=False)
    median_surv.to_csv(outs.data("median_survival"), index=False)
    mean_surv.to_csv(outs.data("mean_survival"), index=False)
    for key, frame in (lifespan_stats or {}).items():
        if hasattr(frame, "to_csv") and len(frame):
            frame.to_csv(outs.stats(f"lifespan_{key}"), index=False)
    for i, model in enumerate(result.cox_analyses, 1):
        coefs = model.get("coefficients")
        if coefs is not None and hasattr(coefs, "to_csv") and len(coefs):
            coefs.to_csv(outs.stats(f"factorial_{i:02d}_coefficients"), index=False)
        ph = model.get("ph_test")
        if ph is not None and hasattr(ph, "to_csv") and len(ph):
            ph.to_csv(outs.stats(f"factorial_{i:02d}_ph_test"), index=False)
    surv_quantiles.to_csv(outs.stats("survival_quantiles"), index=False)
    if len(pairwise_lr) > 0:
        pairwise_lr.to_csv(outs.stats("logrank_pairwise"), index=False)
    if len(pairwise_gw) > 0:
        pairwise_gw.to_csv(outs.stats("gehan_wilcoxon_pairwise"), index=False)
    if len(hazard_ratios) > 0:
        hazard_ratios.to_csv(outs.stats("hazard_ratios"), index=False)

    # ── Figures: the Plot Set this Focus earns, in order ──────────────────
    _draw_plot_set(result, omit_plots, omit_analyses,
                   not_applicable=_not_applicable, left_out=_left_out, emit=emit)
    _drop_stale_outputs(result)

    # ── Defined Plots: all of a plot's curves, or none and a reason ────────
    for plot_name, treatment_list in defined_plots:
        label = f"Defined Plot {plot_name!r}"
        if not fm.defined_plot_relevant(focus, design, list(treatment_list)):
            continue                    # about another slice of the file
        matched, why = fm.defined_plot_match(focus, design, list(treatment_list),
                                             populated)
        if why:
            _not_applicable(label, why)
            continue
        fig_dp = plotting.plot_km_curves(lifetables, treatments=matched, title=plot_name)
        path = outs.plot(f"defined_{fm.slugify(plot_name)}.png")
        _plot_and_save(fig_dp, path)
        result.defined_plot_paths[plot_name] = path

    # ── Report and run summary ─────────────────────────────────────────────
    from . import report_builder

    report_builder.write_experiment_report(result, output_dir)
    _write_run_summary(result, output_dir)

    import matplotlib.pyplot as mpl_plt

    mpl_plt.close("all")
    emit(f"Analysis complete — {output_dir}")
    return result


def render_plots(experiment, focus=None, log=None) -> list[tuple[str, Any]]:
    """Draw the ticked figures of *focus*'s Plot Set — the Plots panel's
    **Generate plots**.

    The same figures, from the same slice, that a full run draws, saved to the
    same files under ``analysis/<focus>/plots/``; the statistics, the report
    and the Run Summary stay as the last run wrote them. *focus* defaults to
    the Active Focus. Returns ``(title, figure)`` pairs, left open for display.
    """
    from .domain import focus as fm
    from .domain.experiment import BlockedFocusError, ExperimentError

    emit = log or (lambda _m: None)
    if isinstance(focus, str):
        focus = experiment.focus(focus)
    focus = focus or experiment.active()
    if focus is None:
        raise ExperimentError(f"{experiment.name}: no Focus could be resolved — "
                              f"is the data file readable?")
    if experiment.materialize_focuses():
        focus = experiment.focus(focus.name)
    design = experiment.design()
    stale = fm.stale_reasons(focus, design)
    if stale:
        raise BlockedFocusError(focus, stale)
    data, _factors = experiment.load(focus=focus)
    _raise_if_empty(focus, design, data)
    shape = fm.focus_shape(focus, data)
    omit_plots, omit_analyses = experiment.omitted("plots"), experiment.omitted("analyses")

    outs = experiment.outputs(focus).ensure()
    result = AnalysisResult(
        input_file=experiment.data_file(), output_dir=outs.root,
        factors=list(focus.varying_factors), individual_data=data,
        lifetables=lifetable.compute_lifetables(data),
        summary=pd.DataFrame(), median_surv=pd.DataFrame(), mean_surv=pd.DataFrame(),
        pairwise_lr=pd.DataFrame(), omnibus_lr={}, hazard_ratios=pd.DataFrame(),
        assume_censored=experiment.type.resolve_assume_censored(experiment.config),
    )
    result.experiment, result.experiment_type = experiment, experiment.type
    result.focus, result.focus_shape, result.design, result.outputs = focus, shape, design, outs
    ## Only what the ticked figures draw from: the forest needs the hazard
    ## ratios, and no other figure needs a statistic.
    wanted = {need for p in experiment.type.plot_set_for(shape)
              if p.id not in omit_plots for need in p.needs} - omit_analyses
    if "hazard_ratios" in wanted and shape.admits(fm.COMPARISON)[0]:
        result.hazard_ratios = statistics.pairwise_hazard_ratios(data)

    figures = _draw_plot_set(
        result, omit_plots, omit_analyses,
        not_applicable=lambda label, reason: emit(f"  Not applicable — {label}: {reason}"),
        left_out=lambda _id, label, reason=UNTICKED: emit(f"  Left out — {label}: {reason}"),
        emit=emit, keep=True)
    emit(f"{len(figures)} figure(s) saved to {outs.plots_dir}")
    return figures


def _raise_if_empty(focus, design, individual_data) -> None:
    """Block a Focus whose cells the exclusions emptied, or that selects no
    one — before anything is written."""
    from .domain import focus as fm
    from .domain.experiment import BlockedFocusError

    empty = fm.empty_reasons(focus, design, fm.populated_labels(individual_data))
    if empty:
        raise BlockedFocusError(focus, empty)
    if not len(individual_data):
        raise BlockedFocusError(focus, [fm.BlockReason(
            fm.EMPTY, f"Focus {focus.name!r} selects no individuals", "edit the Focus")])


def _draw_plot_set(result: AnalysisResult, omit_plots, omit_analyses, *,
                   not_applicable, left_out, emit, keep: bool = False) -> list:
    """Draw and save the figures of the run's Plot Set that the selection keeps.

    Shared by a full run and by Generate plots, so the two cannot disagree
    about which figures a Focus gets or why one is missing. With *keep* the
    figures stay open and come back as ``(title, figure)`` pairs; otherwise
    each is closed once saved.
    """
    import matplotlib.pyplot as mpl_plt

    from . import plot_registry
    from .domain import focus as fm
    from .experiment_types.base import ALL_ANALYSIS_DEFS

    labels = {a.id: a.label for a in ALL_ANALYSIS_DEFS}
    shape = result.focus_shape
    plot_defs = result.experiment_type.plot_set_for(shape)
    drawn: list = []
    emit(f"Rendering {sum(p.id not in omit_plots for p in plot_defs)} figure(s)…")
    for plot_def in plot_defs:
        if plot_def.id in omit_plots:
            left_out(plot_def.id, plot_def.label)
            continue
        missing = [labels.get(a, a) for a in plot_def.needs if a in omit_analyses]
        if missing:
            left_out(plot_def.id, plot_def.label,
                     f"draws from {', '.join(missing)}, which is unticked")
            continue
        ## The Plot Set holds only figures relevant to this Focus; a relevant
        ## one the populated cells cannot support is said, not skipped.
        ok, reason = shape.admits(plot_def.requires)
        if not ok:
            not_applicable(plot_def.label, reason)
            continue
        try:
            fig = plot_registry.build(plot_def.id, result)
        except fm.NotApplicable as exc:
            not_applicable(plot_def.label, exc.reason)
            continue
        except Exception as exc:  # noqa: BLE001 - one bad figure never kills a run
            not_applicable(plot_def.label, f"could not be drawn ({exc})")
            continue
        if fig is None:
            not_applicable(plot_def.label, "the data cannot support it")
            continue
        path = result.outputs.plot(plot_registry.get(plot_def.id).filename)
        fig.savefig(path, dpi=150, bbox_inches="tight")
        result.figure_paths[plot_def.id] = path
        if keep:
            drawn.append((f"{plot_def.label} — {result.focus.name}", fig))
        else:
            mpl_plt.close(fig)
    return drawn


def _drop_stale_outputs(result: AnalysisResult) -> None:
    """Delete what an earlier run of this Focus wrote and this one did not —
    a figure or table since left out reads as current in the folder.

    Only names this pipeline writes are touched (a Plot Set figure, a
    comparison table, a factorial model's tables), never a file someone else
    put there.
    """
    from . import plot_registry

    def _unlink(path: Path) -> None:
        try:
            path.unlink(missing_ok=True)
        except OSError:                 # open in a viewer — stale, not fatal
            pass

    outs = result.outputs
    for plot_id in plot_registry.available():
        if plot_id not in result.figure_paths:
            _unlink(outs.plot(plot_registry.get(plot_id).filename))
    for stem, frame in (("logrank_pairwise", result.pairwise_lr),
                        ("gehan_wilcoxon_pairwise", result.pairwise_gw),
                        ("hazard_ratios", result.hazard_ratios)):
        if frame is None or not len(frame):
            _unlink(outs.stats(stem))
    n_models = len(result.cox_analyses or [])
    for path in outs.stats_dir.glob(f"factorial_*_{outs.slug}.csv"):
        index = path.stem.split("_")[1]
        if index.isdigit() and int(index) > n_models:
            _unlink(path)


def _jsonable(value):
    """Reduce a stats dict to JSON-safe scalars (DataFrames are saved as CSV)."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()
                if not hasattr(v, "to_csv")}
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:  # noqa: BLE001 - a numpy array is not a scalar
            return str(value)
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _write_run_summary(result: AnalysisResult, output_dir: Path) -> None:
    """A small JSON the Hub and the Project Report read instead of re-analysing.

    The Exclusion Group and the number of chambers it removed are stamped here
    and on every report, so a saved result always says what was excluded. So is
    the Focus's **analytic definition** — factors, ordered levels, Reference
    Levels — which is what lets a later reader notice the Focus has changed
    since and call these results **Out of Date** rather than present them.
    """
    import json
    from datetime import datetime

    es = result.experiment_summary or {}
    design = result.design
    payload = {
        "analyzed_at": datetime.now().isoformat(timespec="seconds"),
        "input_file": result.input_file.name,
        "experiment_type": getattr(result.experiment_type, "key", "standard_lifespan"),
        "focus": result.focus_record,
        "factors": list(result.factors),
        "discovered_factors": list(getattr(design, "factors", ()) or ()),
        "n_total": es.get("n_total"),
        "n_deaths": es.get("n_deaths"),
        "n_censored": es.get("n_censored"),
        "n_treatments": es.get("n_treatments"),
        "n_chambers": es.get("n_chambers"),
        "time_min": es.get("time_min"),
        "time_max": es.get("time_max"),
        "assume_censored": bool(result.assume_censored),
        "exclusion_group": getattr(result, "exclusion_group", None),
        "n_excluded": result.n_excluded_applied(),
        "n_excluded_listed": len(result.excluded_chambers or set()),
        "figures": {k: str(v.name) for k, v in
                    getattr(result, "figure_paths", {}).items()},
        "defined_plots": {k: str(v.name) for k, v in
                          getattr(result, "defined_plot_paths", {}).items()},
        "not_applicable": list(result.not_applicable or []),
        "left_out": list(getattr(result, "left_out", None) or []),
        "omnibus_lr": _jsonable(result.omnibus_lr),
        # Enough of each factorial model to rebuild its report section from
        # disk; the coefficient tables sit beside it as CSVs.
        "factorial_models": [
            {
                "title": mdl.get("title") or mdl.get("model_type"),
                "model_type": mdl.get("model_type"),
                "formula": mdl.get("formula"),
                "error": mdl.get("error"),
                "n_subjects": mdl.get("n_subjects"),
                "n_events": mdl.get("n_events"),
                "concordance": mdl.get("concordance"),
                "AIC": mdl.get("AIC"),
                "reference": mdl.get("reference"),
                "lr_interaction": _jsonable(mdl.get("lr_interaction")),
            }
            for mdl in (result.cox_analyses or [])
        ],
    }
    target = result.outputs.summary if result.outputs is not None \
        else Path(output_dir) / "run_summary.json"
    target.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def _plot_and_save(fig, path: Path, dpi: int = 150) -> None:
    """Save a matplotlib figure and close it."""
    import matplotlib.pyplot as mpl_plt
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    mpl_plt.close(fig)
