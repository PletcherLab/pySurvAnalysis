"""Action registry for the visual Script Editor.

Each action wraps an existing function in :mod:`pysurvanalysis` and
exposes its parameters via :class:`ParamSpec` for the inspector form.
The registry mirrors PyTrackingAnalysis's pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ..ui import Category


# ---------------------------------------------------------------------------
# Specs
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ParamSpec:
    """Describes one parameter of an action.

    ``kind`` picks the inspector widget:

    * ``"string"`` → QLineEdit
    * ``"int"``    → QSpinBox
    * ``"float"``  → QDoubleSpinBox
    * ``"bool"``   → QCheckBox
    * ``"choice"`` → QComboBox (requires ``choices`` or "factor")
    * ``"path"``   → QLineEdit + browse button
    * ``"list"``   → QLineEdit (comma-separated)
    * ``"factors"``→ QListWidget multi-select of factor names (resolved at runtime)
    """

    name: str
    kind: str
    label: str
    default: Any = None
    help: str = ""
    choices: tuple[str, ...] | None = None
    min: float | None = None
    max: float | None = None
    enabled_when: str | None = None


@dataclass
class RunContext:
    """State threaded through a script run."""

    project_dir: Any = None
    cfg: dict | None = None
    data: Any = None  # individual-level DataFrame
    factors: list[str] | None = None
    lifetables: Any = None
    log: Callable[[str], None] = lambda _msg: None
    figure: Callable[[str, Any], None] = lambda _title, _fig: None
    excluded_chambers: set | None = None
    assume_censored: bool = True


@dataclass
class Action:
    key: str
    title: str
    description: str
    category: Category
    icon_name: str
    params: tuple[ParamSpec, ...]
    execute_fn: Callable[[dict, RunContext], None] | None = None
    applicable_formats: tuple[str, ...] | None = None

    def execute(self, params: dict, ctx: RunContext) -> None:
        if self.execute_fn is None:
            raise NotImplementedError(f"Action {self.key!r} has no execute function")
        merged: dict[str, Any] = {}
        for spec in self.params:
            if spec.name in params:
                merged[spec.name] = params[spec.name]
            elif spec.default is not None:
                merged[spec.name] = spec.default
        self.execute_fn(merged, ctx)


def _parse_list(s: Any) -> list:
    if s is None:
        return []
    if isinstance(s, (list, tuple)):
        return list(s)
    return [x.strip() for x in str(s).split(",") if x.strip()]


def _require_data(ctx: RunContext, action: str) -> None:
    if ctx.data is None:
        raise RuntimeError(
            f"{action}: no data loaded — add a 'Load data' step first."
        )


# ---------------------------------------------------------------------------
# Action implementations
# ---------------------------------------------------------------------------

def _exec_load_data(params: dict, ctx: RunContext) -> None:
    from .. import data_loader

    if ctx.project_dir is None:
        raise RuntimeError("load_data: no project directory in context")
    g = (ctx.cfg or {}).get("global", {}) or {}
    cw = (ctx.cfg or {}).get("csv_wide", {}) or {}
    fmt = g.get("input_format", "excel")
    pdir = ctx.project_dir
    target = None
    if fmt == "excel":
        for f in pdir.glob("*.xlsx"):
            target = f
            break
    else:
        for ext in ("*.csv", "*.tsv"):
            for f in pdir.glob(ext):
                target = f
                break
            if target is not None:
                break
    if target is None:
        raise RuntimeError("load_data: no input file found")
    kwargs = dict(
        assume_censored=ctx.assume_censored,
        excluded_chambers=ctx.excluded_chambers or set(),
        time_col=g.get("time_col", "Age"),
        event_col=g.get("event_col", "Event"),
        factor_cols=g.get("factor_cols"),
    )
    if fmt == "csv_long":
        kwargs["csv_format"] = "long"
    elif fmt == "csv_wide":
        kwargs["csv_format"] = "wide"
        kwargs["factor_names"] = cw.get("factor_names")
        kwargs["factor_levels"] = cw.get("factor_levels")
        kwargs["col_mapping"] = cw.get("col_mapping")
    data, factors = data_loader.load_experiment(target, **kwargs)
    ctx.data = data
    ctx.factors = factors
    ctx.log(
        f"Loaded {len(data)} individuals · {data['treatment'].nunique()} treatments · "
        f"factors={factors}"
    )


def _exec_apply_exclusions(params: dict, ctx: RunContext) -> None:
    from .. import exclusions

    if ctx.project_dir is None:
        raise RuntimeError("apply_exclusions: no project directory in context")
    group = params.get("group", "default")
    chambers = exclusions.chambers_for_group(ctx.project_dir, group)
    ctx.excluded_chambers = (ctx.excluded_chambers or set()) | chambers
    ctx.log(f"Applied {len(chambers)} chamber exclusion(s) from group '{group}'.")
    if ctx.data is not None and "chamber" in ctx.data.columns and chambers:
        before = len(ctx.data)
        ctx.data = ctx.data[~ctx.data["chamber"].isin(chambers)].reset_index(drop=True)
        ctx.log(f"  dropped {before - len(ctx.data)} rows from in-memory data.")


def _exec_filter(params: dict, ctx: RunContext) -> None:
    _require_data(ctx, "filter")
    factor = (params.get("factor") or "").strip()
    value = (params.get("value") or "").strip()
    if not factor:
        raise RuntimeError("filter: 'factor' is required")
    if factor not in ctx.data.columns:
        raise RuntimeError(f"filter: unknown column {factor!r}")
    before = len(ctx.data)
    ctx.data = ctx.data[ctx.data[factor].astype(str) == value].reset_index(drop=True)
    ctx.log(f"filter: kept {len(ctx.data)}/{before} rows where {factor}={value!r}")


def _exec_km(params: dict, ctx: RunContext) -> None:
    from .. import lifetable, plotting

    _require_data(ctx, "km_curves")
    if ctx.lifetables is None:
        ctx.lifetables = lifetable.compute_lifetables(ctx.data)
    treatments = _parse_list(params.get("treatments")) or None
    show_ci = bool(params.get("show_ci", True))
    if params.get("with_risk_table"):
        fig = plotting.plot_km_with_risk_table(
            ctx.lifetables, show_ci=show_ci, treatments=treatments,
        )
    else:
        fig = plotting.plot_km_curves(
            ctx.lifetables, show_ci=show_ci, treatments=treatments,
        )
    ctx.figure("KM curves", fig)


def _exec_nelson_aalen(params: dict, ctx: RunContext) -> None:
    from .. import lifetable, plotting

    _require_data(ctx, "nelson_aalen")
    if ctx.lifetables is None:
        ctx.lifetables = lifetable.compute_lifetables(ctx.data)
    treatments = _parse_list(params.get("treatments")) or None
    fig = plotting.plot_nelson_aalen(ctx.lifetables, treatments=treatments)
    ctx.figure("Nelson-Aalen", fig)


def _exec_hazard(params: dict, ctx: RunContext) -> None:
    from .. import lifetable, plotting

    _require_data(ctx, "hazard")
    if ctx.lifetables is None:
        ctx.lifetables = lifetable.compute_lifetables(ctx.data)
    if params.get("smoothed"):
        fig = plotting.plot_smoothed_hazard(
            ctx.lifetables, sigma=float(params.get("sigma", 2.0)),
        )
    else:
        fig = plotting.plot_hazard(ctx.lifetables)
    ctx.figure("Hazard rate", fig)


def _exec_mortality(_params: dict, ctx: RunContext) -> None:
    from .. import lifetable, plotting

    _require_data(ctx, "mortality")
    if ctx.lifetables is None:
        ctx.lifetables = lifetable.compute_lifetables(ctx.data)
    ctx.figure("Mortality (qx)", plotting.plot_mortality(ctx.lifetables))


def _exec_forest(_params: dict, ctx: RunContext) -> None:
    from .. import plotting, statistics

    _require_data(ctx, "forest_plot")
    hr = statistics.pairwise_hazard_ratios(ctx.data)
    if hr is None or len(hr) == 0:
        ctx.log("forest_plot: no pairwise hazard ratios to display.")
        return
    ctx.figure("Hazard-ratio forest", plotting.plot_hazard_ratio_forest(hr))


def _exec_logrank_pairwise(_params: dict, ctx: RunContext) -> None:
    from .. import statistics

    _require_data(ctx, "log_rank_pairwise")
    res = statistics.pairwise_logrank(ctx.data)
    ctx.log("Pairwise log-rank tests:")
    ctx.log(res.to_string(index=False))


def _exec_logrank_omnibus(_params: dict, ctx: RunContext) -> None:
    from .. import statistics

    _require_data(ctx, "log_rank_omnibus")
    res = statistics.logrank_multi(ctx.data)
    ctx.log("Omnibus log-rank: " + ", ".join(f"{k}={v}" for k, v in res.items()))


def _exec_gehan_wilcoxon(_params: dict, ctx: RunContext) -> None:
    from .. import statistics

    _require_data(ctx, "gehan_wilcoxon")
    res = statistics.pairwise_gehan_wilcoxon(ctx.data)
    ctx.log("Pairwise Gehan-Wilcoxon tests:")
    ctx.log(res.to_string(index=False))


def _exec_cox(params: dict, ctx: RunContext) -> None:
    from .. import statistics

    _require_data(ctx, "cox_ph")
    selected = _parse_list(params.get("factors")) or (ctx.factors or [])
    factors = ctx.factors or selected
    include_inter = bool(params.get("include_interactions", True))
    res = statistics.cox_interaction_analysis(
        ctx.data, factors=factors, selected_factors=selected,
    )
    if "error" in res:
        ctx.log(f"cox_ph: {res['error']}")
        return
    ctx.log(
        f"Cox PH — n={res.get('n_subjects')} events={res.get('n_events')} "
        f"AIC={res.get('AIC'):.2f} C={res.get('concordance'):.3f}"
    )
    coefs = res.get("coefficients")
    if coefs is not None and len(coefs):
        if not include_inter:
            coefs = coefs[~coefs["covariate"].astype(str).str.contains(":", regex=False)]
        ctx.log(coefs.to_string(index=False))
    lr = res.get("lr_interaction")
    if lr:
        ctx.log(f"LR interaction: chi2={lr.get('chi2')}, df={lr.get('df')}, p={lr.get('p_value')}")


def _exec_rmst(params: dict, ctx: RunContext) -> None:
    from .. import statistics

    _require_data(ctx, "rmst")
    selected = _parse_list(params.get("factors")) or (ctx.factors or [])
    factors = ctx.factors or selected
    tau = params.get("tau")
    try:
        tau_val = float(tau) if tau not in (None, "", 0, 0.0) else None
    except (TypeError, ValueError):
        tau_val = None
    res = statistics.rmst_interaction_analysis(
        ctx.data, factors=factors, selected_factors=selected, tau=tau_val,
    )
    if "error" in res:
        ctx.log(f"rmst: {res['error']}")
        return
    ctx.log(f"RMST regression — tau={res.get('tau')}")
    coefs = res.get("coefficients")
    if coefs is not None and len(coefs):
        ctx.log(coefs.to_string(index=False))


def _exec_parametric(_params: dict, ctx: RunContext) -> None:
    from .. import statistics

    _require_data(ctx, "parametric_aft")
    res = statistics.fit_parametric_models(ctx.data)
    if not res:
        ctx.log("parametric_aft: no models fit.")
        return
    for family, summary in res.items():
        ctx.log(f"{family}: {summary}")


def _exec_chamber_qc(params: dict, ctx: RunContext) -> None:
    from .. import lifetable, plotting

    _require_data(ctx, "chamber_overlay_qc")
    if "chamber" not in ctx.data.columns:
        ctx.log("chamber_overlay_qc: data has no chamber column — skipping.")
        return
    treatment = (params.get("treatment") or "").strip()
    pcl = lifetable.compute_lifetables_per_chamber(ctx.data)
    if not treatment:
        treatments = sorted(pcl["treatment"].unique())
        for t in treatments:
            ctx.figure(
                f"QC chamber overlay: {t}",
                plotting.plot_chamber_overlay_km(pcl, t, excluded_chambers=ctx.excluded_chambers),
            )
    else:
        ctx.figure(
            f"QC chamber overlay: {treatment}",
            plotting.plot_chamber_overlay_km(pcl, treatment, excluded_chambers=ctx.excluded_chambers),
        )


def _exec_report(params: dict, ctx: RunContext) -> None:
    from ..pipeline import run_analysis

    if ctx.project_dir is None:
        raise RuntimeError("report: no project directory in context")
    out = params.get("output_dir") or str(ctx.project_dir)
    run_analysis(
        input_path=str(ctx.project_dir),
        output_dir=out,
        assume_censored=ctx.assume_censored,
        extra_excluded_chambers=ctx.excluded_chambers or set(),
    )
    ctx.log(f"Saved: {out}/report.md")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ACTIONS: dict[str, Action] = {
    "load_data": Action(
        key="load_data",
        title="Load data",
        description="Load the project's data file using config settings.",
        category=Category.LOAD,
        icon_name="load",
        params=(),
        execute_fn=_exec_load_data,
    ),
    "apply_exclusions": Action(
        key="apply_exclusions",
        title="Apply exclusions",
        description="Exclude chambers from a remove_chambers.csv group.",
        category=Category.LOAD,
        icon_name="filter",
        params=(
            ParamSpec("group", "string", "Group", default="default"),
        ),
        execute_fn=_exec_apply_exclusions,
    ),
    "filter": Action(
        key="filter",
        title="Filter rows",
        description="Keep only rows where factor == value.",
        category=Category.LOAD,
        icon_name="filter",
        params=(
            ParamSpec("factor", "factor", "Factor"),
            ParamSpec("value", "string", "Value"),
        ),
        execute_fn=_exec_filter,
    ),
    "km_curves": Action(
        key="km_curves",
        title="KM curves",
        description="Plot Kaplan-Meier survival curves.",
        category=Category.PLOTS,
        icon_name="km",
        params=(
            ParamSpec("treatments", "list", "Treatments (blank = all)"),
            ParamSpec("show_ci", "bool", "Show 95% CI", default=True),
            ParamSpec("with_risk_table", "bool", "With risk table", default=False),
        ),
        execute_fn=_exec_km,
    ),
    "nelson_aalen": Action(
        key="nelson_aalen",
        title="Nelson-Aalen",
        description="Cumulative hazard plot.",
        category=Category.PLOTS,
        icon_name="hazard",
        params=(
            ParamSpec("treatments", "list", "Treatments (blank = all)"),
        ),
        execute_fn=_exec_nelson_aalen,
    ),
    "hazard_plot": Action(
        key="hazard_plot",
        title="Hazard rate",
        description="Instantaneous hazard rate (raw or smoothed).",
        category=Category.PLOTS,
        icon_name="hazard",
        params=(
            ParamSpec("smoothed", "bool", "Smoothed", default=False),
            ParamSpec("sigma", "float", "Smoothing σ", default=2.0, min=0.1, max=20.0,
                      enabled_when="smoothed"),
        ),
        execute_fn=_exec_hazard,
    ),
    "mortality": Action(
        key="mortality",
        title="Mortality (qx)",
        description="Interval mortality rate.",
        category=Category.PLOTS,
        icon_name="plot",
        params=(),
        execute_fn=_exec_mortality,
    ),
    "forest_plot": Action(
        key="forest_plot",
        title="Hazard-ratio forest",
        description="Forest plot of pairwise hazard ratios.",
        category=Category.PLOTS,
        icon_name="forest",
        params=(),
        execute_fn=_exec_forest,
    ),
    "log_rank_pairwise": Action(
        key="log_rank_pairwise",
        title="Log-rank pairwise",
        description="Mantel-Cox log-rank test for every treatment pair.",
        category=Category.ANALYZE,
        icon_name="logrank",
        params=(),
        execute_fn=_exec_logrank_pairwise,
    ),
    "log_rank_omnibus": Action(
        key="log_rank_omnibus",
        title="Log-rank omnibus",
        description="K-sample log-rank test across all treatments.",
        category=Category.ANALYZE,
        icon_name="logrank",
        params=(),
        execute_fn=_exec_logrank_omnibus,
    ),
    "gehan_wilcoxon": Action(
        key="gehan_wilcoxon",
        title="Gehan-Wilcoxon pairwise",
        description="Wilcoxon-style weighted log-rank for every pair.",
        category=Category.ANALYZE,
        icon_name="logrank",
        params=(),
        execute_fn=_exec_gehan_wilcoxon,
    ),
    "cox_ph": Action(
        key="cox_ph",
        title="Cox PH (interactions)",
        description="Cox proportional hazards with full-factorial interactions.",
        category=Category.ANALYZE,
        icon_name="cox",
        params=(
            ParamSpec("factors", "factors", "Factors (blank = all)"),
            ParamSpec("include_interactions", "bool", "Include interactions", default=True),
        ),
        execute_fn=_exec_cox,
    ),
    "rmst": Action(
        key="rmst",
        title="RMST regression",
        description="RMST pseudo-value regression with full-factorial interactions.",
        category=Category.ANALYZE,
        icon_name="rmst",
        params=(
            ParamSpec("factors", "factors", "Factors (blank = all)"),
            ParamSpec("include_interactions", "bool", "Include interactions", default=True),
            ParamSpec("tau", "float", "τ (hours, 0 = auto)", default=0.0, min=0.0, max=1e6),
        ),
        execute_fn=_exec_rmst,
    ),
    "parametric_aft": Action(
        key="parametric_aft",
        title="Parametric AFT models",
        description="Fit Weibull, log-normal, and log-logistic AFT models.",
        category=Category.ANALYZE,
        icon_name="parametric",
        params=(),
        execute_fn=_exec_parametric,
    ),
    "chamber_overlay_qc": Action(
        key="chamber_overlay_qc",
        title="Chamber QC overlay",
        description="Per-chamber KM overlay (one figure per treatment).",
        category=Category.QC,
        icon_name="chamber",
        params=(
            ParamSpec("treatment", "string", "Treatment (blank = all)"),
        ),
        execute_fn=_exec_chamber_qc,
    ),
    "report": Action(
        key="report",
        title="Generate report.md",
        description="Run the full analysis pipeline and write report.md.",
        category=Category.TOOLS,
        icon_name="report",
        params=(
            ParamSpec("output_dir", "path", "Output dir (blank = project)"),
        ),
        execute_fn=_exec_report,
    ),
}
