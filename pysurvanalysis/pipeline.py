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
        self.cox_analyses: list[dict] = []


def run_analysis(
    excel_path: str | Path,
    output_dir: Optional[str | Path] = None,
    assume_censored: bool = True,
) -> AnalysisResult:
    """Run the complete survival analysis pipeline.

    Parameters
    ----------
    excel_path : path to the experiment Excel file
    output_dir : directory for output files (default: same as input file)
    assume_censored : bool
        If True, unaccounted individuals (SampleSize minus observed deaths
        and censored) are added as right-censored at the last census time.
        If False, cohort size is just the sum of deaths + censored.

    Returns
    -------
    AnalysisResult with all computed data.
    """
    excel_path = Path(excel_path)
    if output_dir is None:
        output_dir = excel_path.parent / f"{excel_path.stem}_results"
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    individual_data, factors = data_loader.load_experiment(
        excel_path, assume_censored=assume_censored,
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
    lifetables.to_csv(output_dir / "lifetables.csv", index=False)

    # 7. Save individual data CSV
    individual_data.to_csv(output_dir / "individual_data.csv", index=False)

    # 8. Generate KM plot
    fig_km = plotting.plot_km_curves(lifetables)
    fig_km.savefig(output_dir / "kaplan_meier.png", dpi=150)

    # 9. Generate report
    result = AnalysisResult(
        input_file=excel_path,
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
    )

    report.generate_report(result, output_dir)

    import matplotlib
    matplotlib.pyplot.close("all")

    return result
