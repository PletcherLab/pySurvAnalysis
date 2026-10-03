"""The manual's table of contents — every topic the in-app help knows.

One page per topic, stored as ``topics/<topic-id>.md``. A ``?`` button names a
topic id from this list; the test suite checks that every id used anywhere in
the app is listed here and that every listed id has a page, so a help button
can never open onto nothing.

Analyses and figures map to topics by id (:func:`analysis_topic`,
:func:`plot_topic`), so a new entry in the Analysis Set or Plot Set needs only
a page, not a wiring change.
"""

from __future__ import annotations

#: (chapter title, ((topic id, page title), ...)), in reading order.
CHAPTERS: tuple[tuple[str, tuple[tuple[str, str], ...]], ...] = (
    ("Getting started", (
        ("overview", "What pySurvAnalysis does"),
        ("installation", "Installing and launching"),
        ("quickstart", "Your first analysis"),
        ("concepts", "Batches, Projects, Experiments and Focuses"),
        ("hub", "The Analysis Hub"),
        ("outputs-layout", "Where results are written"),
    )),
    ("Data and configuration", (
        ("data-formats", "Input data formats"),
        ("config-experiment", "survival_config.yaml reference"),
        ("config-input", "The input: section"),
        ("config-global", "The global: section"),
        ("censoring", "Censoring policy"),
        ("config-omit", "The omit: section — leaving analyses and figures out"),
        ("config-project", "project.yaml and Project Defaults"),
        ("experiment-types", "Experiment Types"),
        ("validation", "Validating configuration"),
    )),
    ("Projects and batches", (
        ("project-create", "Creating and opening a Project"),
        ("project-members", "The Experiments card — members"),
        ("project-actions", "Project actions — reports, figures, Plot Editor"),
        ("project-scripts", "Project Scripts"),
        ("batch-panel", "Batch runs"),
        ("preflight", "The Batch preflight"),
        ("experiment-panel", "The Experiment panel"),
    )),
    ("Focuses", (
        ("focus", "What a Focus is"),
        ("focus-window", "The Focus window"),
        ("reference-level", "Reference Levels"),
        ("focus-shape", "Focus Shape — what a Focus is offered"),
        ("not-applicable", "Not Applicable and Left Out"),
        ("focus-status", "Analysed, Out of Date, Blocked and Orphaned results"),
        ("defined-plots", "Defined Plots"),
    )),
    ("Quality control", (
        ("qc-panel", "The QC panel"),
        ("exclusions", "Exclusion Groups"),
        ("qc-viewer", "The Chamber QC viewer"),
    )),
    ("Statistical analyses", (
        ("analyze-panel", "The Analyze panel and Run analysis"),
        ("lifetables", "Life tables and the Kaplan-Meier estimator"),
        ("survival-summary", "Summary statistics, median and mean survival"),
        ("analysis-logrank-pairwise", "Log-rank pairwise"),
        ("analysis-logrank-omnibus", "Log-rank omnibus"),
        ("analysis-gehan-wilcoxon", "Gehan-Wilcoxon pairwise"),
        ("analysis-hazard-ratios", "Pairwise hazard ratios"),
        ("analysis-parametric-aft", "Parametric AFT models"),
        ("analysis-interaction", "Interaction analyses (Factorial Battery)"),
        ("cox-factorial", "The Cox factorial model"),
        ("rmst-factorial", "The RMST factorial model"),
        ("ph-check", "Checking proportional hazards"),
        ("p-values", "Reading p-values and multiple comparisons"),
    )),
    ("Figures", (
        ("plots-panel", "The Plots panel and Generate plots"),
        ("plot-km-curves", "Kaplan-Meier curves"),
        ("plot-km-risk-table", "KM curves with at-risk table"),
        ("plot-nelson-aalen", "Nelson-Aalen cumulative hazard"),
        ("plot-log-log", "Log-log diagnostic"),
        ("plot-cumulative-events", "Cumulative deaths"),
        ("plot-hazard", "Hazard rate"),
        ("plot-smoothed-hazard", "Smoothed hazard"),
        ("plot-mortality", "Mortality (qx)"),
        ("plot-number-at-risk", "Number at risk"),
        ("plot-survival-distribution", "Lifespan distribution"),
        ("plot-hazard-ratio-forest", "Hazard-ratio forest"),
        ("plot-km-faceted", "Faceted Kaplan-Meier"),
        ("plot-interaction-lifespan", "Lifespan interaction plot"),
        ("plot-editor", "The Plot Editor"),
        ("plot-editor-figure", "Plot Editor — Figure"),
        ("plot-editor-canvas", "Plot Editor — Canvas & type"),
        ("plot-editor-curves", "Plot Editor — Curves & points"),
        ("plot-editor-panels", "Plot Editor — Panels & legend"),
        ("plot-editor-colours", "Plot Editor — Colours"),
        ("publication-figures", "Publication Figures, Specs and Styles"),
    )),
    ("Scripts", (
        ("scripts-overview", "Experiment and Project Scripts"),
        ("experiment-scripts", "Running Experiment Scripts"),
        ("script-editor", "The Script Editor"),
        ("script-actions", "Script action reference"),
    )),
    ("Reports", (
        ("experiment-report", "The experiment report"),
        ("run-summary", "The Run Summary"),
        ("project-report", "The Project Report"),
        ("ai-narrative", "The AI narrative"),
    )),
    ("Reference", (
        ("glossary", "Glossary"),
        ("command-line", "Command-line use"),
        ("troubleshooting", "Troubleshooting"),
    )),
)

TITLES: dict[str, str] = {tid: title for _c, topics in CHAPTERS for tid, title in topics}
CHAPTER_OF: dict[str, str] = {tid: chapter for chapter, topics in CHAPTERS
                              for tid, _t in topics}
HOME = "overview"


def analysis_topic(analysis_id: str) -> str:
    """The page for an Analysis Set id (``logrank_pairwise`` → its page)."""
    return "analysis-" + analysis_id.replace("_", "-")


def plot_topic(plot_id: str) -> str:
    """The page for a Plot Set id (``km_curves`` → its page)."""
    return "plot-" + plot_id.replace("_", "-")
