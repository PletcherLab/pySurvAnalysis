"""The Project Report — one bound document, one section per **Focus**.

A Project never pools (ADR-0001), so this binder combines nothing: it reads
each Focus's *saved* analysis outputs and lays them out one after another,
behind a cover carrying the **Focus Inventory** and, when members' data-source
settings differ, the **Divergence Note**. The Focus, not the directory, is the
unit of independent analysis (ADR-0011), so a member whose file holds three
experiments contributes three sections.

A declared Focus that has not been analysed yields a "not analysed" section —
the report never silently analyses on the user's behalf. By the same rule it
never silently presents results for something they no longer describe: a
Focus whose saved results predate a change to its definition, its data file
or its exclusions is **Out of Date**, and its section says so instead of
showing them. What a section does show is what the run recorded — the
chambers it excluded, the AFT table, the model warnings — never a stand-in.

Sections are built by the same ``report_builder`` section functions the
per-Focus report uses, fed by :class:`SavedAnalysis` — a read-only view of
``analysis/<focus>/`` shaped like an ``AnalysisResult``. One set of section
builders, two sources.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from . import report_builder as rb
from .domain.focus import FocusOutputs
from .report_pkg import model as m
from .report_pkg.render import render


def section_key(member_name: str, focus_name: str) -> str:
    """How one Focus's section is keyed — in the AI Narrative and the report."""
    return f"{member_name} · {focus_name}"


class SavedAnalysis:
    """One Focus's saved ``analysis/<focus>/`` directory, shaped like an
    AnalysisResult.

    Only the attributes the report sections actually read are provided; each is
    loaded lazily so binding a ten-member Project doesn't read forty CSVs it
    will not use.
    """

    def __init__(self, experiment, focus=None):
        self.experiment = experiment
        self.experiment_type = experiment.type
        if focus is None:
            focus = experiment.active()
        self.focus = focus
        self.outputs = FocusOutputs(experiment.analysis_dir, focus) if focus is not None \
            else None
        self.analysis_dir = self.outputs.root if self.outputs else experiment.analysis_dir
        self.summary_path = self.outputs.summary if self.outputs else None
        self.payload: dict[str, Any] = {}
        if self.summary_path is not None and self.summary_path.is_file():
            try:
                self.payload = json.loads(self.summary_path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001 - a corrupt summary reads as "not analysed"
                self.payload = {}

    # ── availability ───────────────────────────────────────────────────────

    @property
    def exists(self) -> bool:
        return bool(self.payload)

    # ── AnalysisResult-shaped attributes ───────────────────────────────────

    @property
    def input_file(self) -> Path:
        return Path(self.payload.get("input_file") or self.experiment.name)

    @property
    def factors(self) -> list[str]:
        return list(self.payload.get("factors") or [])

    @property
    def focus_record(self) -> dict:
        return dict(self.payload.get("focus") or {})

    @property
    def not_applicable(self) -> list[dict]:
        return [dict(i) for i in self.payload.get("not_applicable") or []
                if isinstance(i, dict)]

    @property
    def left_out(self) -> list[dict]:
        return [dict(i) for i in self.payload.get("left_out") or []
                if isinstance(i, dict)]

    @property
    def headline_plot_id(self) -> str | None:
        return self.focus_record.get("headline")

    @property
    def assume_censored(self) -> bool:
        return bool(self.payload.get("assume_censored", True))

    @property
    def exclusion_group(self) -> str | None:
        return self.payload.get("exclusion_group")

    @property
    def excluded_chambers(self) -> set:
        """The chambers the run removed, as saved — empty for a summary
        written before identities were recorded (only the count survives
        there, and no identity is invented for it)."""
        return set(self.excluded_applied() or ())

    def excluded_applied(self) -> list[str] | None:
        """The removed chambers' ids, or ``None`` when the summary predates
        saving them."""
        ids = self.payload.get("excluded_chambers")
        if not isinstance(ids, list):
            return None
        return [str(c) for c in ids]

    def n_excluded_applied(self) -> int:
        ids = self.excluded_applied()
        return len(ids) if ids is not None else int(self.payload.get("n_excluded") or 0)

    def n_excluded_listed(self) -> int:
        listed = self.payload.get("n_excluded_listed")
        return int(listed) if listed is not None else self.n_excluded_applied()

    @property
    def load_warnings(self) -> list[str]:
        return [str(w) for w in self.payload.get("load_warnings") or []]

    @property
    def min_n_per_chamber(self) -> int:
        return int(self.payload.get("min_n_per_chamber") or 0)

    @property
    def small_chambers(self) -> list[dict]:
        return [dict(c) for c in self.payload.get("small_chambers") or []
                if isinstance(c, dict)]

    @property
    def experiment_summary(self) -> dict:
        keys = ("n_total", "n_deaths", "n_censored", "n_treatments", "n_chambers",
                "time_min", "time_max")
        out = {k: self.payload.get(k) for k in keys}
        total, censored = out.get("n_total"), out.get("n_censored")
        if total and censored is not None:
            out["pct_censored"] = round(100.0 * censored / total, 1)
        return out

    @property
    def omnibus_lr(self) -> dict:
        return self.payload.get("omnibus_lr") or {}

    def _csv(self, path: Path | None) -> pd.DataFrame:
        if path is not None and path.is_file():
            try:
                return pd.read_csv(path)
            except Exception:  # noqa: BLE001 - an unreadable CSV is an empty table
                return pd.DataFrame()
        return pd.DataFrame()

    def _data(self, stem: str) -> pd.DataFrame:
        return self._csv(self.outputs.data(stem) if self.outputs else None)

    def _stats(self, stem: str) -> pd.DataFrame:
        return self._csv(self.outputs.stats(stem) if self.outputs else None)

    @property
    def summary(self) -> pd.DataFrame:
        return self._data("summary")

    @property
    def median_surv(self) -> pd.DataFrame:
        return self._data("median_survival")

    @property
    def mean_surv(self) -> pd.DataFrame:
        return self._data("mean_survival")

    @property
    def surv_quantiles(self) -> pd.DataFrame:
        return self._stats("survival_quantiles")

    @property
    def pairwise_lr(self) -> pd.DataFrame:
        return self._stats("logrank_pairwise")

    @property
    def pairwise_gw(self) -> pd.DataFrame:
        return self._stats("gehan_wilcoxon_pairwise")

    @property
    def hazard_ratios(self) -> pd.DataFrame:
        return self._stats("hazard_ratios")

    @property
    def lifespan_stats(self) -> dict:
        return {
            "treatment_stats": self._stats("lifespan_treatment_stats"),
            "factor_stats": self._stats("lifespan_factor_stats"),
        }

    @property
    def parametric_models(self) -> dict:
        """The AFT comparison as the run saved it (``{"table": DataFrame}``),
        or ``{}`` when the run left it out or predates saving it."""
        from .statistics import PARAMETRIC_COLUMNS

        records = self.payload.get("parametric_models")
        if not isinstance(records, list) or not records:
            return {}
        rows = [r for r in records if isinstance(r, dict)]
        return {"table": pd.DataFrame(rows, columns=list(PARAMETRIC_COLUMNS))} if rows else {}

    @property
    def cox_analyses(self) -> list[dict]:
        models: list[dict] = []
        for i, meta in enumerate(self.payload.get("factorial_models") or [], 1):
            model = dict(meta)
            coefs = self._stats(f"factorial_{i:02d}_coefficients")
            if len(coefs):
                model["coefficients"] = coefs
            ph = self._stats(f"factorial_{i:02d}_ph_test")
            if len(ph):
                model["ph_test"] = ph
            models.append(model)
        return models

    def _plot_files(self, key: str) -> dict[str, Path]:
        if self.outputs is None:
            return {}
        plots = self.outputs.plots_dir
        return {
            name: plots / filename
            for name, filename in (self.payload.get(key) or {}).items()
            if (plots / filename).is_file()
        }

    @property
    def figure_paths(self) -> dict[str, Path]:
        return self._plot_files("figures")

    @property
    def defined_plot_paths(self) -> dict[str, Path]:
        return self._plot_files("defined_plots")


# ---------------------------------------------------------------------------
# Cover, inventory, divergence
# ---------------------------------------------------------------------------

def _focus_rows(project) -> list[tuple]:
    """``(member, FocusStatus, Focus)`` for every Focus of every member, in
    member then declaration order."""
    rows = []
    for member in project.members():
        st = member.status()
        focuses = {f.name: f for f in member.focuses()}
        for fs in st.focuses:
            rows.append((member, fs, focuses.get(fs.name)))
    return rows


def _inventory_table(rows) -> m.Table:
    """One row per Focus — the reader's map of the Project."""
    columns = ["Member", "Focus", "Slice", "N", "Deaths", "Censored",
               "Treatments", "State", "Not applicable"]
    body: list[list[str]] = []
    levels: list[m.Level | None] = []
    for member, fs, _focus in rows:
        censored = (f"{fs.n_censored} ({round(100.0 * fs.n_censored / fs.n_total, 1)}%)"
                    if fs.analyzed and fs.n_total and fs.n_censored is not None else "—")
        na = "; ".join(action for action, _ in fs.not_applicable) or "—"
        body.append([
            member.name, fs.name, fs.description or "—",
            str(fs.n_total or "—") if fs.analyzed else "—",
            str(fs.n_deaths or "—") if fs.analyzed else "—",
            censored,
            str(fs.n_treatments or "—") if fs.analyzed else "—",
            fs.state, na,
        ])
        levels.append(m.Level.NEUTRAL if fs.state == "analysed" else m.Level.WARN)
    return m.Table(columns=columns, rows=body, title="Focus inventory",
                   row_levels=levels,
                   caption="Each Focus is analysed independently — a slice of one "
                           "member's data file, named and declared in its config. "
                           "Nothing here is pooled across Focuses or members.")


def _divergence_blocks(project) -> list:
    """The Divergence Note: data-source settings only.

    Design divergence is shown by the Focus Inventory instead — members rarely
    share factors, so a note saying so on every Project would teach readers to
    skip it, and with it the one line that mattered.
    """
    divergences = project.divergences()
    if not divergences:
        return []
    blocks: list = [m.Paragraph(
        "Members of this Project differ in the data-source settings listed "
        "below. That is legal — but it changes how every result is computed, "
        "and no result in this report combines across them. Assumed censoring "
        "on in one member and off in another, for instance, changes how every "
        "death is counted and can flip a comparison's conclusion."
    )]
    blocks.append(m.Table(
        columns=["Setting", "How members differ"],
        rows=[[d.aspect, d.detail] for d in divergences],
        title="Divergence note",
        row_levels=[m.Level.WARN] * len(divergences),
    ))
    return blocks


def build_project_report(project, narrative: dict[str, str] | None = None) -> m.Report:
    """The bound document: cover, inventory, divergence, then Focus sections."""
    rows = _focus_rows(project)
    current = [r for r in rows if r[1].state == "analysed"]

    report = m.Report(title=project.name)
    if rows:
        status = [m.StatusLine(
            f"{len(current)} of {len(rows)} Focus(es) analysed and current.",
            m.Level.OK if len(current) == len(rows) else m.Level.WARN)]
    elif project.members():
        status = [m.StatusLine("No Focus could be resolved for any member.",
                               m.Level.WARN)]
    else:
        status = [m.StatusLine("This Project has no Member Experiments yet.",
                               m.Level.WARN)]
    report.add(m.Cover(
        title=f"{project.name} — Project Report",
        subtitle=project.question,
        metadata=[
            ("Experiment type", project.type.label),
            ("Members", str(len(project.members()))),
            ("Focuses", str(len(rows))),
            ("Generated", datetime.now().strftime("%Y-%m-%d %H:%M")),
            ("Path", str(project.directory)),
        ],
        status=status,
    ))

    report.add(m.SectionDivider("Focuses"))
    if rows:
        report.add(_inventory_table(rows))
    report.extend(_divergence_blocks(project))

    if narrative and narrative.get("__across__"):
        report.add(m.Heading("Across Focuses", level=2))
        report.add(m.Paragraph(narrative["__across__"]))
        report.add(m.Paragraph(
            "*Qualitative summary only — no statistic in this report combines "
            "Focuses or members.*"
        ))

    for member, fs, focus in rows:
        key = section_key(member.name, fs.name)
        ## No PageBreak of its own: a SectionDivider already starts on a
        ## fresh page, and asking for one here put an empty page — header and
        ## footer only — in front of every section.
        report.add(m.SectionDivider(key, subtitle=fs.description or member.type.label))
        if fs.blocked:
            report.add(m.Paragraph(
                f"**Focus {fs.name} is blocked** — it cannot run as declared, "
                f"so nothing was analysed for it. {member.name}'s other "
                f"Focuses are unaffected."))
            report.add(m.Table(columns=["Why it is blocked"],
                               rows=[[r] for r in fs.blocked],
                               row_levels=[m.Level.ERROR] * len(fs.blocked)))
            continue
        if not fs.analyzed:
            report.add(m.Paragraph(
                f"**Focus {fs.name} has not been analysed.** Run its analysis "
                f"and rebuild this report; nothing was computed on its behalf "
                f"here."))
            problems = member.validate()
            if problems:
                report.add(m.Table(
                    columns=["Problem"], rows=[[p] for p in problems],
                    row_levels=[m.Level.ERROR] * len(problems),
                    title="Why it cannot be analysed as configured",
                ))
            continue
        if fs.out_of_date:
            report.add(m.Paragraph(
                f"**Focus {fs.name}'s results are out of date** — they predate a "
                f"change and are not shown: "
                f"{'; '.join(fs.out_of_date_reasons)}. Re-run its analysis and "
                f"rebuild this report."))
            continue

        saved = SavedAnalysis(member, focus)
        if narrative and narrative.get(key):
            report.add(m.Paragraph(narrative[key]))
        for section in member.type.report_sections():
            builder = rb._SECTION_BUILDERS.get(section.key)
            if builder is None:
                continue
            try:
                blocks = builder(saved)
            except Exception as exc:  # noqa: BLE001 - one bad section, not one bad report
                blocks = [m.Paragraph(f"*{section.title} could not be rebuilt from "
                                      f"the saved analysis: {exc}*")]
            if not blocks:
                continue
            report.add(m.Heading(section.title, level=1))
            report.extend(blocks)

    return report


def write_project_report(project, formats: tuple[str, ...] = ("pdf", "md"),
                         narrative: dict[str, str] | None = None,
                         log=None) -> dict[str, Path]:
    """Render the Project Report into the Project root. Returns ``{fmt: path}``."""
    emit = log or (lambda _m: None)
    report = build_project_report(project, narrative=narrative)
    written: dict[str, Path] = {}
    stem = project.directory.name

    if "pdf" in formats:
        target = project.directory / f"{stem}_report.pdf"
        try:
            render(report, str(target), backend="reportlab")
            written["pdf"] = target
            emit(f"Wrote {target}")
        except Exception as exc:  # noqa: BLE001 - markdown must still be written
            emit(f"PDF report failed ({exc}); writing markdown only.")
    if "md" in formats:
        target = project.directory / f"{stem}_report.md"
        render(report, str(target), backend="markdown")
        written["md"] = target
        emit(f"Wrote {target}")
    return written
