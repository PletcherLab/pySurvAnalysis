"""Orchestrate the full survival analysis pipeline.

This module ties together data loading, lifetable computation, statistical
tests, plotting, and report generation into a single ``run_analysis`` call.

Supports two invocation modes:
  * **Project directory mode** — pass a directory path; the single ``.xlsx``
    file inside is auto-discovered.  Outputs are written to organised
    subdirectories (``plots/``, ``statistics/``, ``data_output/``).
  * **Direct file mode** — pass a path to an ``.xlsx``, ``.csv``, or ``.tsv``
    file directly (original behaviour; backwards-compatible).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import pandas as pd

from . import data_loader, lifetable, statistics, plotting, report


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
        # New analysis results
        self.pairwise_gw: pd.DataFrame = pairwise_gw if pairwise_gw is not None else pd.DataFrame()
        self.parametric_models: dict = parametric_models or {}
        self.surv_quantiles: pd.DataFrame = surv_quantiles if surv_quantiles is not None else pd.DataFrame()
        self.experiment_summary: dict = experiment_summary or {}
        self.nelson_aalen: pd.DataFrame = nelson_aalen if nelson_aalen is not None else pd.DataFrame()


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
    # New: extra chamber ids to exclude on top of any Excel ChamberFlags sheet.
    # Sourced by callers from remove_chambers.csv (see ``pysurvanalysis.exclusions``).
    extra_excluded_chambers: set | None = None,
) -> AnalysisResult:
    """Run the complete survival analysis pipeline.

    Parameters
    ----------
    input_path : path to a project directory (containing one .xlsx file) **or**
        path to an experiment file (.xlsx, .csv, or .tsv) directly.
    output_dir : directory for output files.  Defaults to
        ``<project_dir>/<stem>_results/`` (where ``stem`` comes from the
        discovered or supplied input file).
    assume_censored : bool
        Excel only.  If True, unaccounted individuals are added as
        right-censored at the last census time.
    time_col, event_col, factor_cols, csv_format, col_mapping,
    factor_names, factor_levels : CSV-specific parameters (pass-through).

    Returns
    -------
    AnalysisResult with all computed data.
    """
    input_path = Path(input_path)

    # ── Project directory mode ─────────────────────────────────────────────
    project_dir: Path | None = None
    if input_path.is_dir():
        project_dir = input_path
        input_path = _discover_xlsx(project_dir)

    # ── Output directory setup ─────────────────────────────────────────────
    # Convention: every run writes into <project>/<datafile_stem>_results/ so
    # multiple input files in one project don't clobber each other.
    if output_dir is None:
        output_dir = input_path.parent / f"{input_path.stem}_results"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    data_dir = output_dir / "data_output"
    data_dir.mkdir(exist_ok=True)
    stats_dir = output_dir / "statistics"
    stats_dir.mkdir(exist_ok=True)

    # ── 0. Excel-only: chamber exclusions and defined plots ────────────────
    excluded_chambers: set = set()
    defined_plots: list[list[str]] = []
    if input_path.suffix.lower() == ".xlsx":
        excluded_chambers = data_loader.load_chamber_flags(input_path)
        defined_plots = data_loader.load_defined_plots(input_path)

    # Merge in any extra exclusions sourced from remove_chambers.csv (CSV inputs
    # included — chamber will be "N/A" there and the loader will simply find no
    # matches, which is the correct no-op).
    if extra_excluded_chambers:
        excluded_chambers = set(excluded_chambers) | set(extra_excluded_chambers)

    # ── 1. Load data ───────────────────────────────────────────────────────
    individual_data, factors = data_loader.load_experiment(
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

    # ── 2. Compute lifetables (now with Nelson-Aalen columns) ──────────────
    lifetables = lifetable.compute_lifetables(individual_data)

    # ── 3. Core summary statistics ─────────────────────────────────────────
    summary = statistics.summary_statistics(individual_data)
    median_surv = lifetable.median_survival(lifetables)
    mean_surv = lifetable.mean_survival(individual_data)

    # ── 4. Log-rank tests ──────────────────────────────────────────────────
    pairwise_lr = statistics.pairwise_logrank(individual_data)
    omnibus_lr = statistics.logrank_multi(individual_data)

    # ── 5. Gehan-Wilcoxon tests ────────────────────────────────────────────
    pairwise_gw = statistics.pairwise_gehan_wilcoxon(individual_data)

    # ── 6. Hazard ratios ───────────────────────────────────────────────────
    hazard_ratios = statistics.pairwise_hazard_ratios(individual_data)

    # ── 7. Lifespan statistics ─────────────────────────────────────────────
    lifespan_stats = lifetable.lifespan_statistics(
        individual_data, factors, assume_censored=assume_censored,
    )

    # ── 8. Survival quantiles ──────────────────────────────────────────────
    surv_quantiles = lifetable.survival_quantiles(lifetables)

    # ── 9. Parametric models ───────────────────────────────────────────────
    try:
        parametric_models = statistics.fit_parametric_models(individual_data)
    except Exception:
        parametric_models = {}

    # ── 10. Experiment summary ─────────────────────────────────────────────
    exp_summary = statistics.experiment_summary(individual_data)

    # ── 11. Save CSV outputs ───────────────────────────────────────────────
    lifetables.to_csv(data_dir / "lifetables.csv", index=False)
    individual_data.to_csv(data_dir / "individual_data.csv", index=False)
    surv_quantiles.to_csv(stats_dir / "survival_quantiles.csv", index=False)
    if len(pairwise_lr) > 0:
        pairwise_lr.to_csv(stats_dir / "logrank_pairwise.csv", index=False)
    if len(pairwise_gw) > 0:
        pairwise_gw.to_csv(stats_dir / "gehan_wilcoxon_pairwise.csv", index=False)
    if len(hazard_ratios) > 0:
        hazard_ratios.to_csv(stats_dir / "hazard_ratios.csv", index=False)

    # ── 12. Generate plots ─────────────────────────────────────────────────
    import matplotlib
    import matplotlib.pyplot as mpl_plt

    _plot_and_save(plotting.plot_km_curves(lifetables),
                   plots_dir / "kaplan_meier.png")
    _plot_and_save(plotting.plot_km_with_risk_table(lifetables),
                   plots_dir / "km_with_risk_table.png")
    _plot_and_save(plotting.plot_nelson_aalen(lifetables),
                   plots_dir / "nelson_aalen.png")
    _plot_and_save(plotting.plot_log_log(lifetables),
                   plots_dir / "log_log_diagnostic.png")
    _plot_and_save(plotting.plot_cumulative_events(lifetables),
                   plots_dir / "cumulative_events.png")
    _plot_and_save(plotting.plot_hazard(lifetables),
                   plots_dir / "hazard_rate.png")
    _plot_and_save(plotting.plot_smoothed_hazard(lifetables),
                   plots_dir / "smoothed_hazard.png")
    _plot_and_save(plotting.plot_mortality(lifetables),
                   plots_dir / "mortality_qx.png")
    _plot_and_save(plotting.plot_number_at_risk(lifetables),
                   plots_dir / "number_at_risk.png")
    _plot_and_save(plotting.plot_survival_distribution(individual_data),
                   plots_dir / "survival_distribution.png")
    if len(hazard_ratios) > 0:
        _plot_and_save(plotting.plot_hazard_ratio_forest(hazard_ratios),
                       plots_dir / "hazard_ratio_forest.png")

    # Defined plots (Excel only)
    for i, (plot_name, treatment_list) in enumerate(defined_plots, 1):
        valid = [t for t in treatment_list if t in lifetables["treatment"].unique()]
        if not valid:
            continue
        fig_dp = plotting.plot_km_curves(lifetables, treatments=valid, title=plot_name)
        _plot_and_save(fig_dp, plots_dir / f"defined_plot_{i:02d}.png")

    # ── 13. Build result and generate report ───────────────────────────────
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

    report.generate_report(result, output_dir)

    mpl_plt.close("all")

    return result


def _plot_and_save(fig, path: Path, dpi: int = 150) -> None:
    """Save a matplotlib figure and close it."""
    import matplotlib.pyplot as mpl_plt
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
    mpl_plt.close(fig)
