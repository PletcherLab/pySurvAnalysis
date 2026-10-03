# The Experiment panel

The **Experiment** panel is where you work on one loaded experiment. At the top, the **Focus** card chooses which slice of the data everything else acts on. Below it, five sub-tiles (**QC · Analyze · Plots · Scripts · AI**) open the panels that do the work.

The panel opens by itself when you double-click a member in the Project panel's members table. You can also open it by clicking the **Experiment** tile once an experiment is loaded, either a member or a standalone Experiment Directory. With nothing loaded, the tile is dimmed and clicking it only logs *Load an experiment first*.

The Experiment tile's summary shows `loaded: <experiment>` and `focus: <Active Focus>`.

## The Focus card

### The Active Focus selector

The drop-down lists every Focus of the experiment as `name — state`, where the state is one of:

- `not analysed`: no saved results under this Focus;
- `analysed`: saved results that match the current definition;
- `out of date`: saved results produced from something that has since changed: the definition (factors, levels, Reference Levels), the Exclusion Group or its chambers, the data file, the censoring policy, or the analyses and plots left out (the reasons are listed);
- `blocked`: the Focus cannot run as declared (it names a level the data lacks, or the active Exclusion Group empties one of its cells).

A config with no `focuses:` block shows one Focus, `Unfiltered`. The Focus you pick is the **Active Focus**: the one the Analyze, Plots and QC viewer act on, and the one a script with no `run_in_focuses` step runs under. Switching it is navigation only. Nothing is written to disk, and every Focus's results stay where they are. The log records `Active Focus: <name>`. When you first load an experiment, the Active Focus is its first Focus.

### New… and Edit…

- **New…** opens the [Focus window](help:focus-window) with a new Focus (named `New focus`) over every discovered factor, ready to narrow down.
- **Edit…** opens the same window on the Active Focus, where you can edit, rename, duplicate or delete Focuses, import them from the workbook's DefinedPlots sheet, or copy them from another member.

Nothing is written until you click **Save** in that window. After a save, the Focus that was selected there becomes the Active Focus. If the data file cannot be read, the window does not open and a message says why.

### The shape line

Under the selector, one line describes the Active Focus before anything runs. Its parts are separated by `·`:

- the definition: each varying factor with its levels in display order and its Reference Level (`Density: 20x, 40x (reference 40x)`), joined by `×`, then `; only Sex = Female` for filters and `; pooled over Genotype` for factors left out;
- `shape 2×2`: the number of levels of each varying factor. When some implied cells hold no individuals, it adds `(3 of 4 cells)`;
- what the Focus is **offered**, for example `offers a comparison between treatments; a figure crossing factors; the Factorial Battery`. Each item is marked `(not computable: …)` when the data cannot support it. A single-treatment Focus reads *offers the survivorship battery only*;
- when they apply: `not applicable last run: …`, `BLOCKED — <reasons>`, or `out of date — <reasons>`.

If no Focus can be resolved, typically because the member has no data file yet or the file cannot be read, the line says *No Focus could be resolved — is the data file readable?*. See [Focus Shape](help:focus-shape).

### Orphaned and pre-Focus results

A row appears under the shape line only when `analysis/` holds results no declared Focus names:

- *Orphaned results (no Focus names them): …*: left behind when a Focus was renamed or removed by hand in the YAML (renaming in the Focus window moves its results with it);
- *Pre-Focus results in analysis/ — never adopted and never replaced by a re-run; Delete… removes them.*: output from before Focuses existed. A re-run writes under `analysis/<focus>/` and leaves these files where they are.

| Button | What it does |
|---|---|
| **Adopt…** | Pick an orphaned result folder, then a declared Focus that has no results yet. The folder becomes that Focus's results, and is judged against it like any other result (it may show as out of date). It refuses if there are no orphans (pre-Focus results cannot be adopted) or if every Focus already has results. |
| **Delete…** | Pick an orphaned folder or *pre-Focus results*, confirm, and it is deleted from `analysis/`. This cannot be undone. |

Orphaned results are never bound into a report. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).

## The sub-tiles

Each sub-tile opens its own panel under the Experiment tile. The tiles show only their titles. Hover over one to read its live summary.

| Sub-tile | Opens | Hover summary |
|---|---|---|
| **QC** | [The QC panel](help:qc-panel): the active Exclusion Group and the Chamber QC viewer | `group: <name or none>`, `N chamber(s) excluded` — the chambers of this data file that the active group and the workbook's ChamberFlags remove from every Focus's next run (chambers a group lists that the file does not have are not counted; a CSV has none to remove) |
| **Analyze** | [The Analyze panel](help:analyze-panel): a checkbox per analysis, and **Run analysis** | `focus: <name>`, then `N individuals · <state>` once analysed |
| **Plots** | [The Plots panel](help:plots-panel): a checkbox per figure, and **Generate plots** | `focus shape: <shape>`, `headline: <figure id>` — the Active Focus's Headline Figure: `km_faceted` when it crosses factors, `km_risk_table` otherwise |
| **Scripts** | [Running Experiment Scripts](help:experiment-scripts) | numbers of experiment scripts and Project Scripts |
| **AI** | [The AI narrative](help:ai-narrative) | provider count, or `no API key` |

QC, Analyze, Plots and Scripts are dimmed with nothing loaded. The AI sub-tile is dimmed until a Project is open *and* an API key for a provider is configured, because the narrative is written per Project. A dimmed sub-tile still opens its panel, but the cards inside are dimmed too.

QC comes first on purpose: decide which chambers to exclude before you analyse.

## Pitfalls

- **The Active Focus is not saved.** It resets to the first Focus when the experiment is loaded again. Scripts run unattended analyse every Focus regardless.
- **A fresh member with no data has no Focus.** Add its data file (or use Experiment configs… to fix an ambiguous one) before anything here works.
- **Out of date is not an error.** Re-run the Focus with **Run analysis** on the Analyze panel.

## See also

- [What a Focus is](help:focus)
- [The Focus window](help:focus-window)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [The Analyze panel and Run analysis](help:analyze-panel)
- [The Experiments card — members](help:project-members)
