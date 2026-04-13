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

    # --- Lifespan Statistics ---
    ls = result.lifespan_stats
    if ls:
        ts = ls.get("treatment_stats")
        fs = ls.get("factor_stats")
        has_top_pct = ts is not None and "top_10pct_mean" in ts.columns

        if ts is not None and len(ts) > 0:
            lines.append("### Lifespan by Treatment")
            lines.append("")
            if has_top_pct:
                lines.append("| Treatment | N | Deaths | Mean (RMST) | Median | Top 10% Mean | Top 5% Mean |")
                lines.append("|-----------|---|--------|-------------|--------|--------------|-------------|")
            else:
                lines.append("| Treatment | N | Deaths | Mean (RMST) | Median |")
                lines.append("|-----------|---|--------|-------------|--------|")
            for _, row in ts.iterrows():
                mean_s = f"{row['mean_rmst']:.1f}" if not np.isnan(row["mean_rmst"]) else "N/A"
                med_s = f"{row['median']:.1f}" if not np.isnan(row["median"]) else "Not reached"
                base = f"| {row['group']} | {int(row['n'])} | {int(row['n_deaths'])} | {mean_s} | {med_s}"
                if has_top_pct:
                    t10 = f"{row['top_10pct_mean']:.1f}" if not np.isnan(row.get("top_10pct_mean", np.nan)) else "N/A"
                    t5 = f"{row['top_5pct_mean']:.1f}" if not np.isnan(row.get("top_5pct_mean", np.nan)) else "N/A"
                    lines.append(f"{base} | {t10} | {t5} |")
                else:
                    lines.append(f"{base} |")
            lines.append("")

        if fs is not None and len(fs) > 0:
            has_top_pct_f = "top_10pct_mean" in fs.columns
            lines.append("### Lifespan by Factor Level (pooled)")
            lines.append("")
            if has_top_pct_f:
                lines.append("| Factor Level | N | Deaths | Mean (RMST) | Median | Top 10% Mean | Top 5% Mean |")
                lines.append("|--------------|---|--------|-------------|--------|--------------|-------------|")
            else:
                lines.append("| Factor Level | N | Deaths | Mean (RMST) | Median |")
                lines.append("|--------------|---|--------|-------------|--------|")
            for _, row in fs.iterrows():
                mean_s = f"{row['mean_rmst']:.1f}" if not np.isnan(row["mean_rmst"]) else "N/A"
                med_s = f"{row['median']:.1f}" if not np.isnan(row["median"]) else "Not reached"
                base = f"| {row['group']} | {int(row['n'])} | {int(row['n_deaths'])} | {mean_s} | {med_s}"
                if has_top_pct_f:
                    t10 = f"{row['top_10pct_mean']:.1f}" if not np.isnan(row.get("top_10pct_mean", np.nan)) else "N/A"
                    t5 = f"{row['top_5pct_mean']:.1f}" if not np.isnan(row.get("top_5pct_mean", np.nan)) else "N/A"
                    lines.append(f"{base} | {t10} | {t5} |")
                else:
                    lines.append(f"{base} |")
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


def _render_coef_table_md(coefs: "pd.DataFrame", section_type: str, is_rmst: bool) -> list[str]:
    """Render a coefficient table section in markdown."""
    import pandas as pd

    subset = coefs[coefs["term_type"] == section_type]
    if len(subset) == 0:
        return []

    label_map = {
        "intercept": "Intercept",
        "main_effect": "Main Effects",
        "interaction": "Interaction Effects",
    }
    lines: list[str] = []
    lines.append(f"#### {label_map.get(section_type, section_type)}")
    lines.append("")

    if is_rmst:
        lines.append("| Covariate | Coef (hours) | SE | t | p-value | 95% CI (hours) |")
        lines.append("|-----------|-------------|----|----|---------|----------------|")
        for _, row in subset.iterrows():
            p_str = _format_pvalue(row["p_value"])
            sig = _significance_stars(row["p_value"])
            lines.append(
                f"| {row['covariate']} "
                f"| {row['coef']:.2f} "
                f"| {row['se']:.2f} "
                f"| {row['z']:.3f} "
                f"| {p_str} {sig} "
                f"| ({row['coef_lo']:.2f}, {row['coef_hi']:.2f}) |"
            )
    else:
        lines.append("| Covariate | Coef | HR | SE | z | p-value | 95% CI (HR) |")
        lines.append("|-----------|------|----|----|---|---------|-------------|")
        for _, row in subset.iterrows():
            p_str = _format_pvalue(row["p_value"])
            sig = _significance_stars(row["p_value"])
            lines.append(
                f"| {row['covariate']} "
                f"| {row['coef']:.4f} "
                f"| {row['HR']:.4f} "
                f"| {row['se']:.4f} "
                f"| {row['z']:.3f} "
                f"| {p_str} {sig} "
                f"| ({row['HR_lo']:.3f}, {row['HR_hi']:.3f}) |"
            )
    lines.append("")
    return lines


def generate_cox_markdown(cox_analyses: list[dict]) -> str:
    """Generate markdown sections for Cox and RMST interaction analyses."""
    if not cox_analyses:
        return ""

    lines: list[str] = []
    lines.append("## 11. Factorial Interaction Analyses")
    lines.append("")

    for i, result in enumerate(cox_analyses, 1):
        model_type = result.get("model_type", "cox_ph")
        is_rmst = model_type == "rmst_pseudo"
        type_label = "RMST Pseudo-Value Regression" if is_rmst else "Cox Proportional Hazards"
        factors_str = ", ".join(result.get("factors_used", []))

        lines.append(f"### Analysis {i} [{type_label}]: {factors_str}")
        lines.append("")

        if "error" in result:
            lines.append(f"**Error:** {result['error']}")
            lines.append("")
            continue

        lines.append(f"**Model formula:** `{result.get('formula', 'N/A')}`  ")
        lines.append(f"**N subjects:** {result.get('n_subjects', 'N/A')}  ")
        lines.append(f"**N events (deaths):** {result.get('n_events', 'N/A')}  ")

        if is_rmst:
            lines.append(f"**Restriction time (tau):** {result.get('tau', 'N/A')} hours  ")
            lines.append(f"**Overall RMST:** {result.get('rmst_overall', 'N/A')} hours  ")
            lines.append(f"**R-squared:** {result.get('r_squared', 'N/A')}  ")
            if result.get("f_statistic") is not None:
                lines.append(f"**F-statistic:** {result['f_statistic']}  ")
            if result.get("f_p_value") is not None:
                p = result["f_p_value"]
                lines.append(
                    f"**F-test p-value:** "
                    f"{_format_pvalue(p)} {_significance_stars(p)}  "
                )
        else:
            if result.get("concordance") is not None:
                lines.append(f"**Concordance index:** {result['concordance']}  ")
            if result.get("AIC") is not None:
                lines.append(f"**AIC (partial):** {result['AIC']}  ")
            if result.get("log_likelihood") is not None:
                lines.append(f"**Log-likelihood:** {result['log_likelihood']}  ")
            if result.get("log_likelihood_ratio_p") is not None:
                p = result["log_likelihood_ratio_p"]
                lines.append(
                    f"**Likelihood ratio test p-value:** "
                    f"{_format_pvalue(p)} {_significance_stars(p)}  "
                )
        lines.append("")

        coefs = result.get("coefficients")
        if coefs is not None and len(coefs) > 0:
            for section_type in ("intercept", "main_effect", "interaction"):
                lines.extend(_render_coef_table_md(coefs, section_type, is_rmst))

        if result.get("warnings"):
            lines.append("**Warnings:**")
            for w in cox["warnings"]:
                lines.append(f"- {w}")
            lines.append("")

    return "\n".join(lines)


def append_cox_to_report(cox_analyses: list[dict], output_dir: Path) -> None:
    """Append Cox analysis results to an existing report.md."""
    report_path = Path(output_dir) / "report.md"
    if not report_path.exists():
        return

    cox_md = generate_cox_markdown(cox_analyses)
    if not cox_md:
        return

    content = report_path.read_text(encoding="utf-8")
    # Replace the footer and append cox section before it
    footer = "---\n*Report generated by pySurvAnalysis*\n"
    if footer in content:
        content = content.replace(footer, cox_md + "\n" + footer)
    else:
        content += "\n" + cox_md + "\n"

    report_path.write_text(content, encoding="utf-8")


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
