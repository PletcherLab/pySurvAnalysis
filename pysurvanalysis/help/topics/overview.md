# What pySurvAnalysis does

pySurvAnalysis analyses lifespan experiments: cohorts of individuals (flies in vials or chambers, for example) scored at each census until death. It reads a DLife census workbook (`.xlsx`) or a CSV/TSV cohort, builds life tables and Kaplan-Meier survivorship, compares treatments with the usual tests (log-rank, Gehan-Wilcoxon, Cox hazard ratios, parametric AFT fits and, for designs that cross two or more factors, Cox and RMST interaction models), draws the standard figures, and writes a PDF report for every analysis it runs.

Everything the app does can also be run headless from the command line, and the same settings drive both, so a report made in the Hub and one made by an unattended Batch Run are the same report.

## The ideas you need

- **Experiment Directory** — one data file's folder: `survival_config.yaml` at its root, the workbook or CSV at the root or in `data/`, results in `analysis/<focus>/`, quality-control state in `qc/`.
- **Focus** — a named slice of the factors and levels found in the data file (for example *Females only, 20x vs 40x density*). Each Focus is analysed on its own, and every output file carries its name. A config with no Focuses has one anyway, called `Unfiltered`.
- **Project** — a folder with a `project.yaml` whose subfolders are **Member Experiments**: separate experiments asking one question in slightly different ways. A Project binds their results into one Project Report but **never pools them**.
- **Batch** — any folder with Projects somewhere beneath it, used to run a script in every Project unattended.
- **Exclusion Group** — a named set of chambers removed from analysis after quality control. The active group is written into the config and stamped on every result.

[Batches, Projects, Experiments and Focuses](help:concepts) explains how these fit together.

## What it will not do

- It never pools members of a Project, or Focuses within one file, into a combined statistic. The Project Report puts independent sections side by side.
- It never analyses silently on your behalf. A report built from saved results says "not analysed" or "out of date" rather than quietly re-running anything.
- It never drops an analysis without saying so. An analysis the data cannot support is recorded as **Not Applicable**, and one you unticked is recorded as **Left Out**. Both appear in the log, the Run Summary and the report.

## The main window

The **Analysis Hub** is the app's main window. Along the top runs a strip of three tiles, **Batch · Project · Experiment**, with a status readout beside them. Below is the Output log, and figures open beside it as tabs. Clicking a tile opens its panel of controls. See [The Analysis Hub](help:hub).

The Hub opens with nothing selected. Use **Project ▸ Open project…** (or **Recent** in the top bar) to choose a folder.

## Getting help in the app

- **Help** in the Hub's top bar, or **F1**, opens this manual at the page for whichever panel is open.
- A **?** button beside a card, control or checkbox opens the page that explains it.
- Most buttons have a tooltip. Hover to read what the button does, and why it is disabled when it is.
- In the manual, use the contents tree or the search box (Ctrl+F) on the left, and **◀ Back** / **Forward ▶** to retrace your steps.

## Where to start

New users should follow [Your first analysis](help:quickstart), which walks through the real UI from an empty Project to a finished report.

## See also

- [Your first analysis](help:quickstart)
- [Batches, Projects, Experiments and Focuses](help:concepts)
- [The Analysis Hub](help:hub)
- [Where results are written](help:outputs-layout)
- [Glossary](help:glossary)
