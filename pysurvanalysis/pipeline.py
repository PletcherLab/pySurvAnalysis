"""Orchestrate the full survival analysis pipeline.

This module ties together data loading, lifetable computation, statistical
tests, plotting, and report generation into a single ``run_analysis`` call.
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
    ):
        self.input_file = input_file
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
) -> AnalysisResult:
    """Run the complete survival analysis pipeline.

    Parameters
    ----------
    input_path : path to the experiment file (.xlsx, .csv, or .tsv)
    output_dir : directory for output files (default: ``<stem>_results/`` next
        to the input file)
    assume_censored : bool
        Excel only.  If True, unaccounted individuals (SampleSize minus
        observed deaths and censored) are added as right-censored at the
        last census time.
    time_col : CSV only.  Column name for survival time (default ``"Age"``).
    event_col : CSV only.  Column name for event indicator (default ``"Event"``).
    factor_cols : CSV long format.  Factor column names; auto-detected if None.
    csv_format : ``"auto"`` (default), ``"long"``, or ``"wide"``.
    col_mapping : CSV wide format.  Explicit column→group mapping list.
    factor_names : CSV wide format.  Factor names.
    factor_levels : CSV wide format.  Factor name → list of levels.

    Returns
    -------
    AnalysisResult with all computed data.
    """
    input_path = Path(input_path)
    if output_dir is None:
        output_dir = input_path.parent / f"{input_path.stem}_results"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"
    plots_dir.mkdir(exist_ok=True)
    data_dir = output_dir / "data_output"
    data_dir.mkdir(exist_ok=True)

    # 0. Excel-only: load chamber exclusions and defined plots before loading data
    excluded_chambers: set = set()
    defined_plots: list[list[str]] = []
    if input_path.suffix.lower() == ".xlsx":
        excluded_chambers = data_loader.load_chamber_flags(input_path)
        defined_plots = data_loader.load_defined_plots(input_path)

    # 1. Load data
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

    # 2. Compute lifetables
    lifetables = lifetable.compute_lifetables(individual_data)

    # 3. Summary statistics
    summary = statistics.summary_statistics(individual_data)
    median_surv = lifetable.median_survival(lifetables)
    mean_surv = lifetable.mean_survival(individual_data)

    # 4. Log-rank tests
    pairwise_lr = statistics.pairwise_logrank(individual_data)
    omnibus_lr = statistics.logrank_multi(individual_data)

    # 5. Hazard ratios
    hazard_ratios = statistics.pairwise_hazard_ratios(individual_data)

    # 5b. Lifespan statistics
    lifespan_stats = lifetable.lifespan_statistics(
        individual_data, factors, assume_censored=assume_censored,
    )

    # 6. Save lifetable CSV
    lifetables.to_csv(data_dir / "lifetables.csv", index=False)

    # 7. Save individual data CSV
    individual_data.to_csv(data_dir / "individual_data.csv", index=False)

    # 8. Generate KM plot
    import matplotlib
    fig_km = plotting.plot_km_curves(lifetables)
    fig_km.savefig(plots_dir / "kaplan_meier.png", dpi=150)

    # 8b. Generate defined plots (Excel only)
    for i, (plot_name, treatment_list) in enumerate(defined_plots, 1):
        valid = [t for t in treatment_list if t in lifetables["treatment"].unique()]
        if not valid:
            continue
        fig_dp = plotting.plot_km_curves(lifetables, treatments=valid, title=plot_name)
        fig_dp.savefig(plots_dir / f"defined_plot_{i:02d}.png", dpi=150)
        matplotlib.pyplot.close(fig_dp)

    # 9. Generate report
    result = AnalysisResult(
        input_file=input_path,
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
    )

    report.generate_report(result, output_dir)

    import matplotlib
    matplotlib.pyplot.close("all")

    return result
