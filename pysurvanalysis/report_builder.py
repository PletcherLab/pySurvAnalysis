"""Build report blocks from analysis results.

This module is the only place that turns numbers into a document. It emits the
backend-agnostic blocks of :mod:`pysurvanalysis.report_pkg.model`, so the PDF
and the markdown are provably the same report — and an Experiment Type's
``report_sections()`` decides which sections appear and in what order.

Every report is about one **Focus**, and says so: the cover names it, and the
Focus section describes the slice — its varying factors and Reference Levels,
its filters, what it pools over, which cells exist — and lists every action
that was **Not Applicable** to it, with the reason (ADR-0011). A figure or
model that did not run is stated, never just absent.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from .report_pkg import model as m
from .report_pkg.render import render


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def format_pvalue(p: Any) -> str:
    try:
        value = float(p)
    except (TypeError, ValueError):
        return "—"
    if pd.isna(value):
        return "—"
    if value < 0.0001:
        return "<0.0001"
    return f"{value:.4f}"


def significance_stars(p: Any) -> str:
    try:
        value = float(p)
    except (TypeError, ValueError):
        return ""
    if pd.isna(value):
        return ""
    if value < 0.001:
        return "***"
    if value < 0.01:
        return "**"
    if value < 0.05:
        return "*"
    return "ns"


def _num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if pd.isna(f):
        return "—"
    return f"{f:.{digits}f}"


def _level_for_p(p: Any) -> m.Level:
    try:
        value = float(p)
    except (TypeError, ValueError):
        return m.Level.NEUTRAL
    if pd.isna(value):
        return m.Level.NEUTRAL
    return m.Level.OK if value < 0.05 else m.Level.NEUTRAL


def is_pvalue_column(name: Any) -> bool:
    """True for a column holding p-values (``p``, ``p_value``, ``p_bonferroni``,
    ``f_p_value``…) — never for a transform of one such as ``-log2(p)``."""
    text = str(name).strip().lower()
    return (text in {"p", "pvalue", "p-value", "p_value"}
            or text.startswith("p_") or text.endswith("_p")
            or text.endswith("_p_value"))


def _p_for_level(df: pd.DataFrame, max_rows: int = 200) -> pd.Series | None:
    """The p-value a row's highlight follows: the multiplicity-adjusted one
    when the table has it, so the tint and the ``significant_0.05`` column
    can never disagree; otherwise the plain ``p_value``."""
    for column in ("p_bonferroni", "p_adjusted", "p_value"):
        if column in getattr(df, "columns", []):
            return df[column].head(max_rows)
    return None


def dataframe_table(df: pd.DataFrame, title: str | None = None,
                    caption: str | None = None, digits: int = 3,
                    max_rows: int = 200) -> m.Table | None:
    """A Table block from a DataFrame, cells pre-stringified.

    p-value columns go through :func:`format_pvalue` — a fixed three
    decimals would print a highly significant result as "0.000".
    """
    if df is None or len(df) == 0:
        return None
    frame = df.head(max_rows)
    columns = [str(c) for c in frame.columns]
    pcols = [is_pvalue_column(c) for c in frame.columns]
    rows: list[list[str]] = []
    for _, row in frame.iterrows():
        cells = []
        for value, is_p in zip(row, pcols):
            if is_p:
                cells.append(format_pvalue(value))
            elif isinstance(value, float):
                cells.append(_num(value, digits))
            else:
                cells.append("—" if value is None else str(value))
        rows.append(cells)
    note = caption
    if len(df) > max_rows:
        extra = f"Showing the first {max_rows} of {len(df)} rows."
        note = f"{caption} {extra}" if caption else extra
    return m.Table(columns=columns, rows=rows, title=title, caption=note)


def figure_block(path: Path, title: str | None = None,
                 caption: str | None = None) -> m.Figure | None:
    """Load a saved PNG into a Figure block (``None`` when it is missing)."""
    p = Path(path)
    if not p.is_file():
        return None
    return m.Figure(data=p.read_bytes(), fmt=p.suffix.lstrip(".").lower() or "png",
                    width_in=6.5, height_in=4.2, title=title, caption=caption)


# ---------------------------------------------------------------------------
# Experiment-level sections
# ---------------------------------------------------------------------------

def focus_record(result) -> dict:
    """The run's Focus as a plain dict — live result or saved one alike."""
    return dict(getattr(result, "focus_record", None) or {})


def not_applicable(result) -> list[dict]:
    return [dict(item) for item in (getattr(result, "not_applicable", None) or [])
            if isinstance(item, dict)]


def left_out(result) -> list[dict]:
    """What the run left out by choice — the config's ``omit:`` (ADR-0012)."""
    return [dict(item) for item in (getattr(result, "left_out", None) or [])
            if isinstance(item, dict)]


def _chamber_sort_key(chamber: str):
    """Chamber ids in numeric order where they are numbers (2 before 10)."""
    text = str(chamber)
    return (0, int(text), "") if text.lstrip("-").isdigit() else (1, 0, text)


def exclusion_facts(result) -> tuple[int, int, list[str] | None]:
    """``(removed, listed, ids)`` for the run's exclusions — live result or
    saved one alike.

    *removed* counts the chambers the exclusions actually took out of this
    data; *listed* what the group and the workbook named; *ids* the removed
    chambers' identities, or ``None`` when the record predates saving them —
    then only the count is known, and no identity is invented for it.
    """
    listed_fn = getattr(result, "n_excluded_listed", None)
    listed = (listed_fn() if callable(listed_fn)
              else len(getattr(result, "excluded_chambers", None) or ()))
    applied_fn = getattr(result, "excluded_applied", None)
    ids = applied_fn() if callable(applied_fn) else None
    count_fn = getattr(result, "n_excluded_applied", None)
    removed = count_fn() if callable(count_fn) else (len(ids) if ids is not None else 0)
    if ids is not None:
        ids = sorted((str(c) for c in ids), key=_chamber_sort_key)
    return int(removed or 0), int(listed or 0), ids


def _cover(result, name: str) -> m.Cover:
    exp_type = result.experiment_type
    es = result.experiment_summary or {}
    rec = focus_record(result)
    meta: list[tuple[str, str]] = [
        ("Focus", rec.get("name") or "—"),
        ("Slice", rec.get("description") or "—"),
        ("Experiment type", getattr(exp_type, "label", "Standard Lifespan")),
        ("Data file", result.input_file.name),
        ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
        ("Varying factors", ", ".join(result.factors) or "none"),
        ("Treatments", str(es.get("n_treatments", "?"))),
        ("Individuals", str(es.get("n_total", "?"))),
        ("Deaths", str(es.get("n_deaths", "?"))),
        ("Censored", f"{es.get('n_censored', '?')} ({es.get('pct_censored', '?')}%)"),
    ]
    group = getattr(result, "exclusion_group", None)
    applied, listed, _ids = exclusion_facts(result)
    if group and applied:
        exclusion_text = f"{group} — {applied} chamber(s) removed"
    elif group:
        exclusion_text = (f"{group} — no chambers removed "
                          f"({listed} listed, none present in this data)"
                          if listed else f"{group} — nothing listed")
    elif applied:
        exclusion_text = f"none declared ({applied} removed by the workbook)"
    else:
        exclusion_text = "none"
    meta.append(("Exclusion group", exclusion_text))
    meta.append(("Censoring policy",
                 "unaccounted individuals censored" if result.assume_censored
                 else "unaccounted individuals ignored"))

    status: list[m.StatusLine] = []
    omnibus = result.omnibus_lr or {}
    p = omnibus.get("p_value")
    if p is not None:
        level = m.Level.OK if _level_for_p(p) is m.Level.OK else m.Level.NEUTRAL
        verdict = ("treatments differ" if _level_for_p(p) is m.Level.OK
                   else "no overall difference detected")
        status.append(m.StatusLine(
            f"Omnibus log-rank: {verdict} (p = {format_pvalue(p)}).", level))
    skipped = not_applicable(result)
    if skipped:
        status.append(m.StatusLine(
            f"{len(skipped)} action(s) not applicable to this Focus — listed in "
            f"the Focus section.", m.Level.WARN))
    omitted = left_out(result)
    if omitted:
        status.append(m.StatusLine(
            f"{len(omitted)} analysis or figure(s) left out of this run by "
            f"choice — listed in the Focus section.", m.Level.NEUTRAL))
    title_name = f"{name} · {rec['name']}" if rec.get("name") else name
    return m.Cover(
        title=getattr(exp_type, "report_title", lambda n: n)(title_name),
        subtitle=exp_type.report_intro() or "",
        metadata=meta,
        status=status or None,
    )


def _section_focus(result) -> list:
    """Name the slice, describe it, and state what did not apply to it."""
    rec = focus_record(result)
    if not rec:
        return []
    blocks: list = [m.Paragraph(
        f"This analysis is under the Focus **{rec.get('name')}**: "
        f"{rec.get('description') or 'a slice of the data file'}.")]
    definition = rec.get("definition") or {}
    factors = definition.get("factors") or {}
    reference = definition.get("reference") or {}
    if factors:
        rows = []
        for factor, levels in factors.items():
            levels = list(levels or [])
            role = ("varying" if len(levels) >= 2 else "filter")
            rows.append([factor, ", ".join(map(str, levels)), role,
                         str(reference.get(factor) or "—") if role == "varying" else "—"])
        for factor in rec.get("pooled_over") or []:
            rows.append([factor, "all levels", "pooled over", "—"])
        blocks.append(m.Table(
            columns=["Factor", "Levels (display order)", "Role", "Reference level"],
            rows=rows, title="Focus definition",
            caption=("Levels are discovered from the data file. A varying factor "
                     "labels the treatments; a filter keeps one level; a factor "
                     "the Focus does not name is pooled over. Model coefficients "
                     "are relative to each Reference Level.")))
    treatments = rec.get("treatments") or []
    absent = rec.get("absent_cells") or []
    shape = rec.get("shape")
    line = f"Shape {shape}" if shape else "Shape unknown"
    line += f"; {len(treatments)} treatment(s): {', '.join(map(str, treatments))}."
    if absent:
        line += (f" Cells the levels imply but the data never held (absent, "
                 f"not an error): {', '.join(map(str, absent))}.")
    blocks.append(m.Paragraph(line))
    if rec.get("unassigned"):
        blocks.append(m.Paragraph(
            f"{rec['unassigned']} individual(s) in the data file have no recorded "
            f"level for a factor this Focus names, so they belong to no "
            f"treatment and are outside this analysis."))
    skipped = not_applicable(result)
    if skipped:
        blocks.append(m.Table(
            columns=["Not applicable", "Why"],
            rows=[[str(i.get("action", "")), str(i.get("reason", ""))] for i in skipped],
            row_levels=[m.Level.WARN] * len(skipped),
            title="Not applicable to this Focus",
            caption=("Real actions this slice does not admit. Recorded rather "
                     "than omitted, so a missing figure or model is never "
                     "mistaken for a result.")))
    omitted = left_out(result)
    if omitted:
        blocks.append(m.Table(
            columns=["Left out", "Why"],
            rows=[[str(i.get("item", "")), str(i.get("reason", ""))] for i in omitted],
            title="Left out of this run",
            caption=("Analyses and figures this Focus is offered that the run "
                     "was asked to leave out. A choice, not a property of the "
                     "data — tick them again and re-run to include them.")))
    return blocks


def _section_summary(result) -> list:
    blocks: list = []
    table = dataframe_table(result.summary, title="Per-treatment summary")
    if table:
        blocks.append(table)
    es = result.experiment_summary or {}
    if es:
        blocks.append(m.Paragraph(
            f"Observation window {_num(es.get('time_min'))}–"
            f"{_num(es.get('time_max'))}, {es.get('n_chambers', 'N/A')} chamber(s)."
        ))
    return blocks


#: Raster resolution for a curated figure placed in the report — the sister
#: app's report figures render at the same, and a page needs more than the
#: preview's screen resolution.
_REPORT_FIGURE_DPI = 200


def _curated_figure(result, plot_id: str, specs, title: str,
                    caption: str | None):
    """The Publication Figure curated for *plot_id*, as a report block — or
    ``None`` when nothing is curated for it, or rendering it failed.

    A curated figure outranks the analysis's own matplotlib PNG: the whole
    point of curating in the Plot Editor is that THIS is the figure the
    experiment is meant to be seen through, and a report showing a different
    one beside it would be two figures disagreeing about one result. The
    default stays as the fallback, never the other way round.
    """
    from . import pubfigures

    experiment = getattr(result, "experiment", None)
    if experiment is None or specs is None:
        return None
    spec = specs.get(pubfigures._SPEC_ALIASES.get(plot_id, plot_id))
    if spec is None:
        return None
    focus = getattr(result, "focus", None)
    try:
        style = pubfigures.effective_style(
            pubfigures.resolve_style(spec.style, experiment), focus, spec)
        frame = pubfigures.data_for(experiment, spec, focus=focus)
        if frame.empty:
            return None
        figure = pubfigures.build_ggplot(frame, spec, style)
        data = pubfigures.render_png_bytes(figure, style, dpi=_REPORT_FIGURE_DPI)
    except Exception:  # noqa: BLE001 - a broken curation must not sink the report
        return None
    return m.Figure(
        data=data, fmt="png",
        width_in=float(style.width_mm) / 25.4,
        height_in=float(style.height_mm) / 25.4,
        title=f"{title} — curated figure",
        caption=caption,
    )


def _section_figures(result) -> list:
    from . import plot_registry, pubfigures

    blocks: list = []
    paths = getattr(result, "figure_paths", {}) or {}
    exp_type = result.experiment_type
    headline = (getattr(result, "headline_plot_id", None)
                or getattr(exp_type, "headline_plot_id", None))
    order = [headline] + [pid for pid in paths if pid != headline] if headline in paths \
        else list(paths)

    ## What the Plot Editor curated for this experiment's container, read
    ## once. None (not {}) when there is no experiment to ask, so the loop
    ## below cannot mistake "unknown" for "nothing curated".
    experiment = getattr(result, "experiment", None)
    specs = None
    if experiment is not None:
        try:
            specs = pubfigures.adopt_legacy_member_specs(experiment).plots
        except Exception:  # noqa: BLE001
            specs = None

    placed: set[str] = set()
    for plot_id in order:
        path = paths.get(plot_id)
        if path is None:
            continue
        try:
            registry_spec = plot_registry.get(plot_id)
        except KeyError:
            continue
        label = registry_spec.label + (" — headline figure" if plot_id == headline else "")

        ## The two default KM figures are one curated figure (the at-risk band
        ## is a Style toggle there), so a curated km_curves stands in for BOTH
        ## and the second default is dropped rather than shown beside it.
        curated_id = pubfigures._SPEC_ALIASES.get(plot_id, plot_id)
        if curated_id in placed:
            continue
        block = _curated_figure(result, plot_id, specs, label,
                                registry_spec.caption)
        if block is not None:
            placed.add(curated_id)
        else:
            block = figure_block(path, title=label, caption=registry_spec.caption)
        if block:
            blocks.append(block)
    for name, path in (getattr(result, "defined_plot_paths", {}) or {}).items():
        block = figure_block(path, title=f"Defined Plot — {name}",
                             caption="Treatments the experimenter listed in the "
                                     "workbook's DefinedPlots sheet.")
        if block:
            blocks.append(block)
    return blocks


def _tau_of(*frames) -> str | None:
    """The restriction time a mean-survival table used, for its caption."""
    for frame, column in frames:
        if isinstance(frame, pd.DataFrame) and column in frame.columns and len(frame):
            value = frame[column].dropna()
            if len(value):
                return _num(value.iloc[0])
    return None


def _section_lifespan(result) -> list:
    blocks: list = []
    median_caption = (
        "Kaplan-Meier median: the first age at which survival is at or below "
        "50%. The 95% interval is where the curve's log-log confidence band "
        "reaches 50% (as R's survfit and lifelines); — means not reached.")
    tau = _tau_of((result.mean_surv, "restriction_time"))
    mean_caption = (
        "Restricted mean survival time: the exact area under each treatment's "
        "Kaplan-Meier step function from 0 to the common restriction time "
        f"τ{f' = {tau}' if tau else ''} — the shortest follow-up of any "
        "treatment, so every mean covers the same window.")
    for df, title, caption in ((result.median_surv, "Median survival", median_caption),
                               (result.mean_surv, "Mean survival", mean_caption)):
        table = dataframe_table(df, title=title, caption=caption)
        if table:
            blocks.append(table)
    stats = result.lifespan_stats or {}
    if isinstance(stats, dict):
        tau = _tau_of((stats.get("treatment_stats"), "tau"))
        caption = (f"mean_rmst is restricted to the same common τ"
                   f"{f' = {tau}' if tau else ''} as the Mean survival table; "
                   f"t_max is each group's own last observed age.")
        for key, title in (("treatment_stats", "Lifespan statistics by treatment"),
                           ("factor_stats", "Lifespan statistics by factor level")):
            table = dataframe_table(stats.get(key), title=title, caption=caption)
            if table:
                blocks.append(table)
    table = dataframe_table(result.surv_quantiles, title="Survival quantiles")
    if table:
        blocks.append(table)
    return blocks


def _section_tests(result) -> list:
    blocks: list = []
    omnibus = result.omnibus_lr or {}
    if omnibus:
        blocks.append(m.Table(
            columns=["Test", "chi²", "df", "p", ""],
            rows=[[
                "Omnibus log-rank",
                _num(omnibus.get("chi2") or omnibus.get("test_statistic")
                     or omnibus.get("statistic")),
                str(omnibus.get("df") or omnibus.get("degrees_of_freedom") or "—"),
                format_pvalue(omnibus.get("p_value")),
                significance_stars(omnibus.get("p_value")),
            ]],
            title="Overall comparison",
        ))
    adjusted = ("Pairs are in the Focus's treatment order. Highlighted rows are "
                "significant after the Bonferroni adjustment (p_bonferroni < 0.05, "
                "the significant_0.05 column); p_value is unadjusted.")
    for df, title, caption in (
            (result.pairwise_lr, "Pairwise log-rank", adjusted),
            (result.pairwise_gw, "Pairwise Gehan-Wilcoxon", adjusted),
            (result.hazard_ratios, "Pairwise hazard ratios",
             "hazard_ratio is group1 / group2, group1 being the treatment "
             "earlier in the Focus's order: below 1, group1 dies at the lower "
             "rate. Log-rank O/E estimate with an approximate 95% interval.")):
        table = dataframe_table(df, title=title, caption=caption)
        if table:
            p = _p_for_level(df)
            if p is not None:
                table.row_levels = [_level_for_p(v) for v in p]
            blocks.append(table)
    return blocks


def _section_interaction(result) -> list:
    """The Factorial Battery's models — or the one line saying why it did not
    apply to this Focus."""
    blocks: list = []
    if not (result.cox_analyses or []):
        for item in not_applicable(result):
            if item.get("action") == "Factorial Battery":
                blocks.append(m.Paragraph(
                    f"**Factorial Battery: not run** — {item.get('reason')}."))
        for item in left_out(result):
            if item.get("id") == "interaction":
                blocks.append(m.Paragraph(
                    f"**Interaction analyses: left out of this run** — "
                    f"{item.get('reason')}."))
        return blocks
    for model in result.cox_analyses or []:
        title = model.get("title") or model.get("model_type", "Factorial model")
        if model.get("error"):
            blocks.append(m.Paragraph(f"**{title}** could not be fitted: "
                                      f"{model['error']}"))
            continue
        blocks.append(m.Heading(title, level=2))
        formula = model.get("formula")
        if formula:
            blocks.append(m.Paragraph(f"Model: `{formula}`"))
        meta = []
        for key, label, digits in (("n_subjects", "n", 0), ("n_events", "events", 0),
                                   ("tau", "τ", 2), ("concordance", "concordance", 3),
                                   ("r_squared", "R²", 3), ("AIC", "AIC", 2)):
            if model.get(key) is not None:
                meta.append(f"{label} = {_num(model[key], digits)}")
        if model.get("f_statistic") is not None:
            meta.append(f"robust F = {_num(model['f_statistic'])} "
                        f"(p = {format_pvalue(model.get('f_p_value'))})")
        if meta:
            blocks.append(m.Paragraph(", ".join(meta) + "."))
        if model.get("tau") is not None:
            blocks.append(m.Paragraph(
                f"Coefficients are differences in mean lifespan up to τ = "
                f"{_num(model['tau'])}, the restriction time — the shortest "
                f"follow-up of any treatment unless a script step set it."))

        lr = model.get("lr_interaction") or {}
        if lr:
            p = lr.get("p_value")
            ## "statistic" since the rename; older Run Summaries say lr_stat,
            ## and anything older still chi2.
            stat = next((lr[k] for k in ("statistic", "lr_stat", "chi2")
                         if lr.get(k) is not None), None)
            blocks.append(m.Table(
                columns=["Test", "chi²", "df", "p", ""],
                rows=[["Interaction (LR, vs main-effects model)",
                       _num(stat), str(lr.get("df", "—")),
                       format_pvalue(p), significance_stars(p)]],
                row_levels=[_level_for_p(p)],
                caption=("A significant interaction means the effect of one "
                         "factor depends on the level of the other."),
            ))
        coefs = model.get("coefficients")
        ref = model.get("reference") or {}
        ref_text = (", ".join(f"{f} = {lv}" for f, lv in ref.items())
                    if isinstance(ref, dict) and ref else "each factor's reference level")
        table = dataframe_table(coefs, title="Coefficients",
                                caption=f"Relative to the Reference Levels: {ref_text}.")
        if table is not None:
            if isinstance(coefs, pd.DataFrame) and "p_value" in coefs.columns:
                ## The intercept's test (is the reference cell's mean zero?)
                ## answers no question anyone asked; it is never highlighted.
                kinds = (coefs["term_type"].head(200).astype(str).tolist()
                         if "term_type" in coefs.columns else [""] * min(len(coefs), 200))
                table.row_levels = [m.Level.NEUTRAL if kind == "intercept" else _level_for_p(v)
                                    for v, kind in zip(coefs["p_value"].head(200), kinds)]
            blocks.append(table)
        ph = model.get("ph_test")
        table = dataframe_table(
            ph, title="Proportional-hazards check (Schoenfeld residuals)",
            caption="Small p-values indicate the PH assumption is violated.")
        if table is not None:
            blocks.append(table)
        ## A fit that warned (a convergence problem, a PH test that could not
        ## run) printed numbers as confident as any other; the warning is
        ## part of the result.
        notes = [str(w) for w in model.get("warnings") or [] if str(w).strip()]
        if notes:
            blocks.append(m.Table(
                columns=["Model warning"], rows=[[w] for w in notes],
                row_levels=[m.Level.WARN] * len(notes),
                title=f"{title}: warnings",
                caption="Raised while fitting this model. Read its numbers "
                        "with these in mind."))
    return blocks


def _parametric_block(models) -> m.Table | None:
    """The AFT comparison: per treatment × model AIC, the best marked, and a
    row with the reason for every treatment or family that was not fitted."""
    from . import statistics

    if not models:
        return None
    table = statistics.parametric_table(models)
    if table is None or not len(table):
        return None
    rows: list[list[str]] = []
    levels: list[m.Level] = []
    for rec in table.to_dict("records"):
        note = rec.get("note")
        note = "" if note is None or (isinstance(note, float) and pd.isna(note)) else str(note)
        model = rec.get("model")
        treatment = rec.get("treatment")
        rows.append([
            "—" if treatment is None or pd.isna(treatment) else str(treatment),
            "—" if model is None or (isinstance(model, float) and pd.isna(model)) else str(model),
            _num(rec.get("aic")), _num(rec.get("delta_aic")),
            _num(rec.get("median_survival")), note or "",
        ])
        if note.startswith("not fitted"):
            levels.append(m.Level.WARN)
        elif bool(rec.get("best")) is True:
            levels.append(m.Level.OK)
        else:
            levels.append(m.Level.NEUTRAL)
    return m.Table(
        columns=["Treatment", "Model", "AIC", "ΔAIC", "Median (model)", "Note"],
        rows=rows, row_levels=levels, title="Parametric model fits (AFT)",
        caption=("Each treatment fitted on its own by Weibull, log-normal and "
                 "log-logistic AFT models. Compare AIC within a treatment only; "
                 "ΔAIC is the distance from that treatment's best (lowest AIC, "
                 "highlighted). A treatment with fewer than 5 individuals or 2 "
                 "deaths is not fitted, and a family whose fit failed is listed "
                 "with the reason."))


def _section_quality(result) -> list:
    blocks: list = []
    removed, listed, ids = exclusion_facts(result)
    group = getattr(result, "exclusion_group", None)
    via = f" via group **{group}**" if group else ""
    if removed and ids:
        blocks.append(m.Paragraph(
            f"{removed} chamber(s) excluded{via}: {', '.join(ids)}."))
    elif removed:
        ## A Run Summary from before the identities were saved: the count
        ## is all that is known, and inventing ids for it would be worse.
        blocks.append(m.Paragraph(
            f"{removed} chamber(s) excluded{via}. This run recorded only the "
            f"count — re-run the analysis to list which chambers."))
    elif listed:
        blocks.append(m.Paragraph(
            f"No chambers were excluded from this analysis: the {listed} "
            f"chamber(s) listed{via} are not in this data file."))
    else:
        blocks.append(m.Paragraph("No chambers were excluded from this analysis."))

    warnings_ = [str(w) for w in getattr(result, "load_warnings", None) or []]
    if warnings_:
        blocks.append(m.Table(
            columns=["Data file warning"], rows=[[w] for w in warnings_],
            row_levels=[m.Level.WARN] * len(warnings_),
            title="Warnings from loading the data file",
            caption="Reported by the loader, which read the file as it stands "
                    "— check the data file where they point."))

    threshold = int(getattr(result, "min_n_per_chamber", 0) or 0)
    small = [dict(c) for c in getattr(result, "small_chambers", None) or []
             if isinstance(c, dict)]
    if threshold and small:
        small.sort(key=lambda c: _chamber_sort_key(c.get("chamber", "")))
        blocks.append(m.Table(
            columns=["Chamber", "Treatment", "Individuals"],
            rows=[[str(c.get("chamber", "")), str(c.get("treatment", "")),
                   str(c.get("n", ""))] for c in small],
            row_levels=[m.Level.WARN] * len(small),
            title=f"Chambers with fewer than {threshold} individuals",
            caption=(f"Below global.min_n_per_chamber = {threshold}. Flagged "
                     f"for review, not excluded — exclude a chamber in the QC "
                     f"viewer if it should not count.")))

    models = getattr(result, "parametric_models", None) or {}
    block = _parametric_block(models)
    if block is not None:
        blocks.append(block)
    return blocks


_SECTION_BUILDERS = {
    "focus": _section_focus,
    "summary": _section_summary,
    "figures": _section_figures,
    "lifespan": _section_lifespan,
    "tests": _section_tests,
    "interaction": _section_interaction,
    "quality": _section_quality,
}


def build_experiment_report(result, name: str | None = None) -> m.Report:
    """The block document for one Experiment Directory's analysis."""
    exp = getattr(result, "experiment", None)
    label = name or (exp.name if exp is not None else result.input_file.stem)
    exp_type = result.experiment_type
    report = m.Report(title=label)
    report.add(_cover(result, label))

    for section in exp_type.report_sections():
        builder = _SECTION_BUILDERS.get(section.key)
        if builder is None:
            continue
        blocks = builder(result)
        if not blocks:
            continue
        report.add(m.SectionDivider(section.title))
        report.extend(blocks)
    return report


def write_experiment_report(result, output_dir: str | Path,
                            formats: tuple[str, ...] = ("pdf", "md")) -> dict[str, Path]:
    """Render the experiment report. Returns ``{format: path}``."""
    from .domain.focus import FocusOutputs

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    exp = getattr(result, "experiment", None)
    stem = exp.name if exp is not None else result.input_file.stem
    report = build_experiment_report(result)
    outs = getattr(result, "outputs", None)
    focus = getattr(result, "focus", None)
    if outs is None and focus is not None:
        outs = FocusOutputs.at(out, focus)

    def _target(suffix: str) -> Path:
        if outs is not None:
            return outs.report(stem, suffix)
        return out / (f"{stem}_report.pdf" if suffix == ".pdf" else "report.md")

    written: dict[str, Path] = {}
    if "pdf" in formats:
        target = _target(".pdf")
        try:
            render(report, str(target), backend="reportlab")
            written["pdf"] = target
        except Exception:  # noqa: BLE001 - markdown must still be written
            pass
    if "md" in formats:
        target = _target(".md")
        render(report, str(target), backend="markdown")
        written["md"] = target
    return written
