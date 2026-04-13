"""Generate analysis reports in Markdown and HTML formats.

The Markdown report includes embedded images (base64) when converted to HTML,
making it a self-contained document suitable for sharing.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING

import matplotlib.pyplot as plt
import numpy as np

from . import plotting

if TYPE_CHECKING:
    from .pipeline import AnalysisResult


def _fig_to_base64(fig: plt.Figure) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    encoded = base64.b64encode(buf.read()).decode("utf-8")
    plt.close(fig)
    return encoded


def _fig_to_file(fig: plt.Figure, path: Path) -> None:
    """Save figure to file and close it."""
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def _format_pvalue(p: float) -> str:
    """Format a p-value for display."""
    if p < 0.0001:
        return f"{p:.2e}"
    return f"{p:.4f}"


def _significance_stars(p: float) -> str:
    if p < 0.001:
        return "***"
    if p < 0.01:
        return "**"
    if p < 0.05:
        return "*"
    return "ns"


def generate_markdown(result: "AnalysisResult", output_dir: Path) -> str:
    """Generate a complete Markdown analysis report.

    Plots are saved as PNG files in the output directory and referenced
    by relative path in the Markdown.
    """
    lines: list[str] = []

    lines.append(f"# Survival Analysis Report")
    lines.append(f"")
    lines.append(f"**Input file:** `{result.input_file.name}`  ")
    lines.append(f"**Treatment factors:** {', '.join(result.factors)}  ")
    treatments = sorted(result.individual_data["treatment"].unique())
    lines.append(f"**Number of treatment groups:** {len(treatments)}  ")
    lines.append(f"**Total individuals:** {len(result.individual_data)}  ")
    lines.append("")

    # --- Summary Table ---
    lines.append("## 1. Sample Summary")
    lines.append("")
    lines.append("| Treatment | N | Deaths | Censored | % Censored |")
    lines.append("|-----------|---|--------|----------|------------|")
    for _, row in result.summary.iterrows():
        lines.append(
            f"| {row['treatment']} | {row['n_individuals']} | {row['n_deaths']} "
            f"| {row['n_censored']} | {row['pct_censored']}% |"
        )
    lines.append("")

    # --- Median & Mean Survival ---
    lines.append("## 2. Survival Time Estimates")
    lines.append("")
    lines.append("### Median Survival Time")
    lines.append("")
    lines.append("| Treatment | Median Survival (hours) |")
    lines.append("|-----------|------------------------|")
    for _, row in result.median_surv.iterrows():
        val = f"{row['median_survival']:.1f}" if not np.isnan(row["median_survival"]) else "Not reached"
        lines.append(f"| {row['treatment']} | {val} |")
    lines.append("")

    lines.append("### Restricted Mean Survival Time (RMST)")
    lines.append("")
    if len(result.mean_surv) > 0:
        t_restrict = result.mean_surv["restriction_time"].iloc[0]
        lines.append(f"*Restricted to t = {t_restrict:.1f} hours (common max observed time)*")
        lines.append("")
        lines.append("| Treatment | RMST (hours) |")
        lines.append("|-----------|-------------|")
        for _, row in result.mean_surv.iterrows():
            val = f"{row['rmst']:.1f}" if not np.isnan(row["rmst"]) else "N/A"
            lines.append(f"| {row['treatment']} | {val} |")
    lines.append("")

    # --- KM Plot ---
    lines.append("## 3. Kaplan\u2013Meier Survival Curves")
    lines.append("")
    fig_km = plotting.plot_km_curves(result.lifetables)
    _fig_to_file(fig_km, output_dir / "kaplan_meier.png")
    lines.append("![Kaplan-Meier Survival Curves](kaplan_meier.png)")
    lines.append("")

    # --- Hazard Plot ---
    lines.append("## 4. Hazard Rate Over Time")
    lines.append("")
    fig_hz = plotting.plot_hazard(result.lifetables)
    _fig_to_file(fig_hz, output_dir / "hazard_rate.png")
    lines.append("![Hazard Rate](hazard_rate.png)")
    lines.append("")

    # --- Mortality Plot ---
    lines.append("## 5. Interval Mortality (qx)")
    lines.append("")
    fig_qx = plotting.plot_mortality(result.lifetables)
    _fig_to_file(fig_qx, output_dir / "mortality_qx.png")
    lines.append("![Interval Mortality](mortality_qx.png)")
    lines.append("")

    # --- Number at Risk ---
    lines.append("## 6. Number at Risk")
    lines.append("")
    fig_nr = plotting.plot_number_at_risk(result.lifetables)
    _fig_to_file(fig_nr, output_dir / "number_at_risk.png")
    lines.append("![Number at Risk](number_at_risk.png)")
    lines.append("")

    # --- Omnibus Log-Rank ---
    lines.append("## 7. Omnibus Log-Rank Test")
    lines.append("")
    lr = result.omnibus_lr
    lines.append(f"- **Chi-square statistic:** {lr['chi2']}")
    lines.append(f"- **Degrees of freedom:** {lr['df']}")
    lines.append(f"- **p-value:** {_format_pvalue(lr['p_value'])} {_significance_stars(lr['p_value'])}")
    lines.append("")
    if lr["p_value"] < 0.05:
        lines.append("*The omnibus test indicates statistically significant differences in "
                      "survival among the treatment groups.*")
    else:
        lines.append("*The omnibus test does not indicate statistically significant differences "
                      "in survival among the treatment groups.*")
    lines.append("")

    # --- Pairwise Log-Rank ---
    lines.append("## 8. Pairwise Log-Rank Tests")
    lines.append("")
    if len(result.pairwise_lr) > 0:
        lines.append("| Comparison | Chi\u00b2 | p-value | p (Bonferroni) | Sig. |")
        lines.append("|------------|-------|---------|----------------|------|")
        for _, row in result.pairwise_lr.iterrows():
            lines.append(
                f"| {row['group1']} vs {row['group2']} "
                f"| {row['chi2']:.4f} "
                f"| {_format_pvalue(row['p_value'])} "
                f"| {_format_pvalue(row['p_bonferroni'])} "
                f"| {_significance_stars(row['p_bonferroni'])} |"
            )
    lines.append("")

    # --- Hazard Ratios ---
    lines.append("## 9. Hazard Ratio Estimates")
    lines.append("")
    if len(result.hazard_ratios) > 0:
        lines.append("*Hazard ratios estimated from log-rank O/E method. "
                      "HR > 1 indicates higher risk in the first group.*")
        lines.append("")
        lines.append("| Comparison | HR | 95% CI |")
        lines.append("|------------|-----|--------|")
        for _, row in result.hazard_ratios.iterrows():
            if np.isnan(row["hazard_ratio"]):
                lines.append(f"| {row['group1']} vs {row['group2']} | N/A | N/A |")
            else:
                lines.append(
                    f"| {row['group1']} vs {row['group2']} "
                    f"| {row['hazard_ratio']:.3f} "
                    f"| ({row['hr_ci_lo']:.3f}, {row['hr_ci_hi']:.3f}) |"
                )
    lines.append("")

    # --- Lifetable excerpt ---
    lines.append("## 10. Lifetable (First 10 Rows per Treatment)")
    lines.append("")
    for treatment in treatments:
        grp = result.lifetables[result.lifetables["treatment"] == treatment].head(10)
        lines.append(f"### {treatment}")
        lines.append("")
        lines.append("| Time | n_at_risk | Deaths | Censored | lx | qx | px | hx | SE(KM) |")
        lines.append("|------|-----------|--------|----------|-----|-----|-----|-----|--------|")
        for _, row in grp.iterrows():
            lines.append(
                f"| {row['time']:.1f} | {row['n_at_risk']} | {row['n_deaths']} "
                f"| {row['n_censored']} | {row['lx']:.4f} | {row['qx']:.4f} "
                f"| {row['px']:.4f} | {row['hx']:.6f} | {row['se_km']:.4f} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("*Report generated by pySurvAnalysis*")
    lines.append("")

    return "\n".join(lines)


def generate_report(result: "AnalysisResult", output_dir: Path) -> Path:
    """Generate Markdown report and save to output directory.

    Returns the path to the generated report file.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    md_content = generate_markdown(result, output_dir)
    report_path = output_dir / "report.md"
    report_path.write_text(md_content, encoding="utf-8")

    return report_path
