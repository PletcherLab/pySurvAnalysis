# The Project Report

The Project Report binds the saved results of every Focus in every Member Experiment into one document. It **combines nothing**: each Focus keeps its own independent section, built from that Focus's own saved analysis, because a Project never pools data across members. A cover and a Focus Inventory give the reader a map of the whole Project, and a Divergence Note warns when members were processed under different data-source settings.

The report never analyses anything itself. A Focus that has not been analysed, is Blocked, or whose results are Out of Date gets a section saying so, not results.

## In the app

- Project panel → **Actions** card → **Project report**.
- Experiment tile → **AI** → **Project report with narrative** (the same report with the [AI narrative](help:ai-narrative) included).
- The `project_report` step of a Project Script — the last step of the default `batch` script, so every Batch Run ends with it. See [Project Scripts](help:project-scripts).

**View reports** on the Actions card opens the Project Report together with every member report.

Before building it, analyse the members (Run analysis per Focus, or run the `batch` script). Building the report is fast because it only reads files.

## Where it is written

In the Project folder, named after it: `<project>/<project>_report.pdf` and `<project>/<project>_report.md`. Each build overwrites the previous one. If the PDF cannot be produced the Markdown is still written and the log says why.

## What it contains

### Cover

Title `<project> — Project Report`, with the Project's question (from `project.yaml`) as the subtitle, then: Experiment type, Members, Focuses (the total number across members), Generated (date and time) and Path.

**Status line:** "N of M Focus(es) analysed and current." — green when all are, amber otherwise. With no resolvable Focus it reads "No Focus could be resolved for any member."; with no members, "This Project has no Member Experiments yet."

### Focus Inventory

One row per Focus of every member, in member order then the order the Focuses are declared:

| Column | Meaning |
|---|---|
| Member | the Member Experiment |
| Focus | the Focus name |
| Slice | the one-line description: varying factors with levels and Reference Levels, filters, factors pooled over |
| N, Deaths, Censored | from the Run Summary (Censored as count and %); `—` when not analysed |
| Treatments | number of treatments |
| State | `analysed`, `not analysed`, `out of date` or `blocked` |
| Not applicable | the actions recorded as Not Applicable for that Focus |

Rows not in the `analysed` state are highlighted. The caption reminds the reader that nothing is pooled across Focuses or members.

### Divergence Note

Shown only when members differ in **data-source** settings — the censoring policy, the active Exclusion Group, the time unit. A paragraph explains that this is legal but changes how results are computed, followed by a table of each setting and how members differ. Differences in design (factors and levels) are not listed here; the Focus Inventory already shows every design side by side.

### Across Focuses (optional)

When the report is built with the AI narrative and more than one Focus was summarised, an **Across Focuses** paragraph follows, captioned *"Qualitative summary only — no statistic in this report combines Focuses or members."*

### One section per Focus

Each section starts on a new page titled `<member> · <focus>`, with the Focus's description beneath. What follows depends on its state:

- **Blocked** — "Focus … is blocked", with a table of the reasons. The member's other Focuses are unaffected.
- **Not analysed** — "Focus … has not been analysed. Run its analysis and rebuild this report; nothing was computed on its behalf here." If the member has configuration problems they are listed under *Why it cannot be analysed as configured*.
- **Out of date** — the results are not shown; the reasons (what changed since the analysis) are given, with a request to re-run.
- **Analysed and current** — the AI paragraph for this Focus (if any), then the same sections as the [experiment report](help:experiment-report): Focus, Experiment summary, Survivorship figures, Factorial analysis, Lifespan statistics, Survival comparisons, Data quality. They are rebuilt from the saved Run Summary, CSV tables and figure files, and curated Publication Figures replace the default figures exactly as in the member report. If one section cannot be rebuilt, a one-line note replaces it and the rest of the report is still written.

## Differences from the member reports

The per-Focus sections are rebuilt from what is saved on disk, so they show what the run recorded rather than recomputing anything:

- The parametric AFT table is rebuilt from the Run Summary's `parametric_models` records, so it matches the member report row for row.
- Data quality lists the excluded chambers by id from the Run Summary's `excluded_chambers`. A Run Summary written by an earlier version recorded only how many chambers were excluded; for those, the section gives the count alone and asks for a re-run to list them. No chamber id is ever made up.
- Chambers below `global.min_n_per_chamber` and any data-file warnings are the ones the run recorded, not re-checked against the current data.

## Pitfalls

- An old report is not updated automatically. Rebuild it after re-running analyses.
- A Focus analysed before its definition or Exclusion Group was changed is shown as Out of Date, with no numbers. Re-run it.
- Orphaned Results (folders under `analysis/` that no declared Focus names) are never bound into the report.

## See also

- [The experiment report](help:experiment-report)
- [The Run Summary](help:run-summary)
- [The AI narrative](help:ai-narrative)
- [Project actions — reports, figures, Plot Editor](help:project-actions)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [project.yaml and Project Defaults](help:config-project)
