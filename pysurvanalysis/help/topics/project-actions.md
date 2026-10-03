# Project actions — reports, figures, Plot Editor

The **Actions** card is the third card in the Project panel. Its buttons act on the open Project as a whole: they build and open reports, author Publication Figures, and render them for every member. The card is dimmed until a Project is open. Every action reads **saved** results. None of them analyses anything.

## Project report

Builds the **Project Report** from each member's saved results and writes two files to the Project folder: `<project-folder>_report.pdf` and `<project-folder>_report.md`. If the PDF cannot be rendered, the Markdown is still written and the log says why.

The report has a cover with the Project's question, a **Focus Inventory** listing every Focus of every member with its state, a **Divergence Note** when members' data-source settings (censoring, active Exclusion Group, time unit) differ, and then one independent section per Focus. A Focus that has never been analysed gets a "not analysed" section. An Out of Date Focus is named as such and its old numbers are not shown. Nothing is pooled across members or Focuses, and nothing is re-run. See [The Project Report](help:project-report).

The button runs in the background, like every task. Watch the Output tab for `Wrote …` lines. With no Project open it warns *No Project selected.* The AI panel's **Project report with narrative** builds the same report with an [AI narrative](help:ai-narrative).

## View reports

Opens the Project Report PDF and **every member report PDF** (one per analysed Focus: `analysis/<focus>/<member>_report_<focus>.pdf`) in your system's PDF viewer, all at once. The Output log says how many were opened.

| State | Button |
|---|---|
| no Project open | disabled, with the tooltip *Select a Project first.* |
| no Project Report and no member report on disk | disabled, with the tooltip *No reports yet — run Project report first.* |
| either kind exists | enabled. The tooltip says how many of each will open |

Member reports are written by **Run analysis** (on the experiment's Analyze panel) or by any script that runs the analysis. You do not need a Project Report to open them.

## Plot editor…

Opens the [Plot Editor](help:plot-editor), where you author Publication Figures: each figure's Spec (labels, axis limits, a narrowing of treatments) and its Style. A Spec belongs to one experiment, so the editor always opens on one member, chosen in this order:

1. the member **selected** (single-clicked) in the members table on the Experiments card;
2. otherwise the **loaded** member;
3. otherwise the only member, if there is just one;
4. otherwise it asks *Author which member's figures?*

With no members it warns that there is nothing to author. The editor is the only way into Publication Figure authoring.

## Render publication figures

Renders the Project's **curated** Publication Figures (those saved into the Project's `plot_specs.yaml` from the Plot Editor) for every member, in the format chosen in the box beside the button:

- `svg` (default) or `pdf`: vector output with editable text, the point of a publication figure;
- `png`: for a slide.

Files go to each member's `figures/<focus>/` folder, one set per Focus, each file named for its Focus. A member with nothing curated is skipped (`nothing curated — skipped`). Within a member, a Focus that is not analysed, or whose results are Out of Date, is named in the log and skipped, because a figure of it would describe a slice the config no longer declares. If no member has curated figures, the log says *nothing rendered. Curate figures in the Plot Editor first.*

This button runs the same `render_publication_figures` action a Project Script step does, so the button and a Batch Run render the same figures. See [Publication Figures, Specs and Styles](help:publication-figures).

## Pitfalls

- **Reports never refresh themselves.** After re-running members, click **Project report** again. Otherwise the PDF still shows the earlier results.
- **The Project Report file is named after the folder**, not the Project's `name:`.
- **Render needs current results.** Re-run Out of Date Focuses first, or they are skipped.

## See also

- [The Project Report](help:project-report)
- [The experiment report](help:experiment-report)
- [The Plot Editor](help:plot-editor)
- [Publication Figures, Specs and Styles](help:publication-figures)
- [Project Scripts](help:project-scripts)
- [Where results are written](help:outputs-layout)
