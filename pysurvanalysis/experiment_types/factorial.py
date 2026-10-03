"""The **Factorial Battery** — the interaction analyses, offered by Focus Shape.

Formerly the whole point of an "Interaction Experiment" type; now ordinary
actions any experiment can reach (ADR-0011). Two requirements govern them
(:mod:`pysurvanalysis.domain.focus`):

* the **models** (Cox and RMST, main effects plus every pairwise interaction)
  are *relevant* when the Focus varies two or more factors, and *computable*
  when every pair of those factors is fully crossed in the populated cells —
  an interaction term with an empty cell is not estimable;
* the **figures** (faceted KM, lifespan interaction plot) are relevant on the
  same two-varying-factor condition and need no full crossing — a missing
  cell is just a missing curve.

A Focus they are not relevant to is simply not offered them: no button, no
figure, no report section. A relevant one the data cannot support records
them as **Not Applicable**, with the reason.

Coefficients are relative to each factor's **Reference Level**, which the
Focus names (``reference:``, defaulting to the first level listed). The model
is fitted on :func:`~pysurvanalysis.domain.focus.model_frame`, which puts the
reference first without touching the display order every figure follows.
"""

from __future__ import annotations

from typing import Any

from ..domain.focus import FACTORIAL_MODEL, FACTORIAL_PLOT, NotApplicable
from ..script_editor.spec import Action, ParamSpec
from ..ui import Category

#: What the battery is called wherever a Not Applicable result names it.
BATTERY = "Factorial Battery"


def factor_levels(focus) -> dict[str, list[str]]:
    """The varying factors and their levels, in display order — the first
    becomes the panels of a faceted figure."""
    return {f: list(focus.factors[f]) for f in focus.varying_factors}


def run_factorial_battery(data, focus, shape) -> list[dict]:
    """The Cox factorial model and its RMST companion for one Focus.

    Raises :class:`NotApplicable` when the Focus does not vary two factors or
    its crossing has an empty cell — the caller decides whether that is worth
    recording (it is only when the battery was relevant to begin with).
    """
    from .. import statistics
    from ..domain.focus import model_frame

    ok, reason = shape.admits(FACTORIAL_MODEL)
    if not ok:
        raise NotApplicable(reason, BATTERY)
    names = list(focus.varying_factors)
    frame = model_frame(data, focus)
    out: list[dict] = []
    for fn, label in ((statistics.cox_interaction_analysis, "Cox factorial model"),
                      (statistics.rmst_interaction_analysis, "RMST factorial model")):
        try:
            model = fn(frame, names, names)
        except Exception as exc:  # noqa: BLE001 - a failed model never kills a run
            model = {"error": str(exc), "model_type": label}
        model.setdefault("title", label)
        model["reference"] = {f: focus.reference_level(f) for f in names}
        out.append(model)
    return out


# ---------------------------------------------------------------------------
# Actions (heavy imports stay inside the functions)
# ---------------------------------------------------------------------------

def _require_data(ctx, action: str):
    if getattr(ctx, "data", None) is None:
        raise RuntimeError(f"{action}: no data loaded — add a 'Load data' step first.")
    if getattr(ctx, "focus", None) is None:
        raise RuntimeError(f"{action}: no Focus — this action runs under one.")


def _figure_options(ctx) -> dict:
    """Time label, colours and display names — the same keywords the Plot
    Set draws with, so a script step's figure matches the run's."""
    from ..plot_registry import figure_options

    return figure_options(getattr(ctx, "experiment", None), getattr(ctx, "focus", None))


def _exec_faceted_km(params: dict, ctx) -> None:
    from .. import lifetable, plotting

    _require_data(ctx, "faceted_km")
    lts = (ctx.lifetables if ctx.lifetables is not None
           else lifetable.compute_lifetables(ctx.data))
    fig = plotting.plot_km_faceted(
        lts, factor_levels(ctx.focus), show_ci=bool(params.get("show_ci", False)),
        **_figure_options(ctx),
    )
    ctx.figure(f"Faceted KM — {ctx.focus.name}", fig)
    ctx.log("Faceted KM rendered.")


def _exec_interaction_plot(params: dict, ctx) -> None:
    from .. import plotting

    _require_data(ctx, "interaction_plot")
    fig = plotting.plot_lifespan_interaction(
        ctx.data, factor_levels(ctx.focus), metric=str(params.get("metric", "median")),
        **_figure_options(ctx),
    )
    ctx.figure(f"Lifespan interaction — {ctx.focus.name}", fig)
    ctx.log("Interaction plot rendered.")


def _exec_cox_interaction(_params: dict, ctx) -> None:
    from .. import statistics
    from ..domain.focus import model_frame

    _require_data(ctx, "cox_interaction")
    names = ctx.focus.varying_factors
    result = statistics.cox_interaction_analysis(model_frame(ctx.data, ctx.focus),
                                                 names, names)
    if result.get("error"):
        ctx.log(f"Cox factorial model: {result['error']}")
        return
    _log_factorial(ctx, result, "Cox factorial model")


def _exec_rmst_interaction(params: dict, ctx) -> None:
    from .. import statistics
    from ..domain.focus import model_frame

    _require_data(ctx, "rmst_interaction")
    names = ctx.focus.varying_factors
    tau = float(params.get("tau") or 0.0) or None
    result = statistics.rmst_interaction_analysis(model_frame(ctx.data, ctx.focus),
                                                  names, names, tau=tau)
    if result.get("error"):
        ctx.log(f"RMST factorial model: {result['error']}")
        return
    _log_factorial(ctx, result, "RMST factorial model")


def _log_factorial(ctx, result: dict[str, Any], title: str) -> None:
    names = list(ctx.focus.varying_factors)
    ref = ", ".join(f"{f} = {ctx.focus.reference_level(f)}" for f in names)
    ctx.log(f"{title}: {result.get('formula', '')}  (reference: {ref})")
    if result.get("tau") is not None:
        ctx.log(f"  Restriction time τ = {result['tau']:.4g}")
    lr = result.get("lr_interaction") or {}
    if lr:
        stat = next((lr[k] for k in ("statistic", "lr_stat", "chi2")
                     if lr.get(k) is not None), float("nan"))
        ctx.log(
            f"  Interaction LR test: chi2={stat:.3f}, "
            f"df={lr.get('df', '?')}, p={lr.get('p_value', float('nan')):.4g}"
        )
    coefs = result.get("coefficients")
    if coefs is not None and len(coefs):
        ctx.log(coefs.to_string(index=False))
    for warning in result.get("warnings") or []:
        ctx.log(f"  Warning: {warning}")
    if getattr(ctx, "result", None) is not None:
        ## Shaped like the run's own battery entry, and REPLACING the model
        ## of the same title: a `cox_interaction` step after `run_analysis`
        ## re-fits the model the run already holds, and appending it would
        ## put the same model in a later report twice.
        result.setdefault("title", title)
        result["reference"] = {f: ctx.focus.reference_level(f) for f in names}
        models = ctx.result.cox_analyses
        for i, existing in enumerate(models):
            if (existing.get("title") or existing.get("model_type")) == result["title"]:
                models[i] = result
                break
        else:
            models.append(result)


FACTORIAL_ACTIONS: dict[str, Action] = {
    "faceted_km": Action(
        key="faceted_km",
        title="Faceted KM",
        description="One panel per level of the first varying factor, curves "
                    "coloured by the others. Offered when the Focus varies two "
                    "or more factors.",
        category=Category.PLOTS,
        icon_name="km",
        params=(ParamSpec("show_ci", "bool", "Show 95% CI", default=False),),
        execute_fn=_exec_faceted_km,
        requires=FACTORIAL_PLOT.key,
    ),
    "interaction_plot": Action(
        key="interaction_plot",
        title="Lifespan interaction plot",
        description="Median lifespan per cell; non-parallel lines indicate "
                    "interaction. Offered when the Focus varies two or more "
                    "factors.",
        category=Category.PLOTS,
        icon_name="interaction",
        params=(
            ParamSpec("metric", "choice", "Metric", default="median",
                      choices=("median", "mean")),
        ),
        execute_fn=_exec_interaction_plot,
        requires=FACTORIAL_PLOT.key,
    ),
    "cox_interaction": Action(
        key="cox_interaction",
        title="Cox factorial model",
        description=(
            "Cox PH main-effects vs pairwise-interaction model, LR omnibus "
            "test, and the Schoenfeld PH check, relative to the Focus's "
            "Reference Levels. Offered when the Focus varies two or more "
            "factors; needs every pair of them fully crossed."
        ),
        category=Category.ANALYZE,
        icon_name="cox",
        params=(),
        execute_fn=_exec_cox_interaction,
        requires=FACTORIAL_MODEL.key,
    ),
    "rmst_interaction": Action(
        key="rmst_interaction",
        title="RMST factorial model",
        description=(
            "RMST pseudo-value regression with the same factorial design — "
            "no proportional-hazards assumption. Offered when the Focus "
            "varies two or more factors; needs every pair of them fully "
            "crossed."
        ),
        category=Category.ANALYZE,
        icon_name="rmst",
        params=(ParamSpec("tau", "float", "τ (0 = auto)", default=0.0,
                          min=0.0, max=1e6),),
        execute_fn=_exec_rmst_interaction,
        requires=FACTORIAL_MODEL.key,
    ),
}
