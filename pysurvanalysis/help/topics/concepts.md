# Batches, Projects, Experiments and Focuses

pySurvAnalysis organises work in four nested levels. Each level is a folder, or a named slice inside a folder's data, and each has one job. Knowing which level you are on tells you what a button acts on and where its results go.

```
Batch/                       any folder with Projects beneath it (batch.yaml optional)
└── Sept2026/                grouping folders are transparent
    └── ProjA/               a Project: project.yaml
        ├── plot_specs.yaml  the Project's Plot Specs and Styles
        ├── cohort_a/        a Member Experiment (an Experiment Directory)
        │   ├── survival_config.yaml
        │   ├── data/cohort_a.xlsx
        │   ├── qc/remove_chambers.csv
        │   └── analysis/
        │       ├── Unfiltered/     one folder per Focus
        │       └── FemalesOnly/
        └── cohort_b/
```

## Experiment Directory

One data file's folder. It holds `survival_config.yaml` at its root, the input workbook or CSV either at the root or in `data/`, results in `analysis/<focus>/`, QC state in `qc/` and Publication Figures in `figures/`. The data file may contain several experiments, and the directory holds them all. Its Focuses tell them apart.

An Experiment Directory can stand alone with no Project above it. Opening it in the Hub loads it directly.

## Focus

A **Focus** is a named selection of the factors and levels **discovered** in the data file. You never declare factors: they are read from the Design sheet's columns after `StartTime` (or a CSV's factor columns), with levels in the order they first appear. Each discovered factor plays one of three roles in a Focus:

- named with **two or more levels**, it is **varying**, and its levels label the treatments;
- named with **one level**, it is a **filter** (keep only that level);
- **not named**, it is **pooled over**.

The Focus is the unit of analysis. Each Focus is analysed independently and writes to its own `analysis/<focus>/` folder, and every file in that folder carries the Focus's name as a suffix (`run_summary_<focus>.json`, for example). A config with no `focuses:` block has one Focus anyway, `Unfiltered` (every factor at every level), which is written into the file the first time it is analysed or edited.

What a Focus is offered depends on its **Focus Shape**. Comparisons need two or more treatments, and the interaction analyses need two or more varying factors. See [What a Focus is](help:focus) and [Focus Shape](help:focus-shape).

## Project and Member Experiments

A **Project** is a folder with a `project.yaml` at its root. Its immediate subfolders that hold a `survival_config.yaml` are its **Member Experiments**: separate experiments addressing one question, often with different designs.

- **A Project never pools.** There is no combined analysis or pooled statistic. The Project Report binds one independent section per Focus of every member.
- **Project Defaults** (the `defaults:` section of `project.yaml`) are a seed, not a rule. A member that says nothing about a setting (time unit, censoring policy, input settings, Exclusion Group name) inherits it. A member that states its own value keeps it. Focuses are never inherited.
- **The Experiment Type is the one rule.** Every member must share the Project's Experiment Type. Today there is one, Standard Lifespan.
- When members differ in data-source settings (censoring, active Exclusion Group, time unit), the difference is allowed but declared. The Project Report carries a **Divergence Note**.

A Project also holds the Project Scripts (including the `batch` script every new Project is created with), central Experiment Scripts that serve every member, and `plot_specs.yaml` for Publication Figures.

## Batch

A **Batch** is any folder with at least one Project somewhere beneath it, at any depth. It exists only to run a Project Script in many Projects unattended. It holds no analysis and never combines results. Discovery stops at each Project and never looks inside it. Each Project in a Batch is a **Batch Project**, named by its path relative to the Batch folder (`Sept2026/ProjA`). An optional `batch.yaml` can hold central Project Scripts and a designated script. See [Batch runs](help:batch-panel).

## Blocked, Not Applicable and Left Out

The app separates *what cannot run* from *what you chose not to run*:

- A **Blocked Member** is a member folder a run cannot use as it stands: data but no config, a config but no data, or several candidate data files and no `data_file:` naming one. The other members still run.
- A **Blocked Focus** names a factor or level the data no longer has, or keeps a cell that the active Exclusion Group empties. The member's other Focuses still run.
- **Not Applicable** means an analysis is relevant to the Focus but the data cannot compute it. It is recorded in the log, the Run Summary and the report.
- **Left Out** means you unticked the analysis or figure on the Analyze or Plots panel. It is recorded too, separately from Not Applicable.

See [Not Applicable and Left Out](help:not-applicable).

## How this maps onto the Hub

The Hub's three tiles are the three folder levels: **Batch**, **Project** and **Experiment**. The Focus is chosen at the top of the Experiment panel and applies to everything below it (QC, Analyze, Plots, Scripts, AI). Selecting a folder sets the working level. Double-clicking a member in the Project panel loads that member.

## See also

- [The Analysis Hub](help:hub)
- [What a Focus is](help:focus)
- [project.yaml and Project Defaults](help:config-project)
- [Batch runs](help:batch-panel)
- [Where results are written](help:outputs-layout)
- [Glossary](help:glossary)
