# What a Focus is

A **Focus** is a *named* slice of the factors and levels found in one data file. It is the unit the app analyses: every analysis, figure and statistic in a run groups individuals by the Focus's `treatment` label, every output file carries the Focus's name, and every report says which Focus it describes. One workbook often holds several experiments (a crowding experiment and a genotype experiment sharing the same chambers sheet, say). Each gets its own Focus, each is analysed independently, and their results sit side by side without overwriting each other.

## Factors are discovered, not declared

You never type the factors into the config. The app reads them from the data file:

- **DLife workbook** – the factor columns are the Design sheet's columns after `StartTime`, one row per chamber.
- **CSV/TSV** – the factor columns of the file (see [Input data formats](help:data-formats)).

Each factor's levels are listed in **first-appearance order**, i.e. the order you typed them in the Design sheet. They are never sorted alphabetically, because controls are usually entered first and alphabetical sorting could silently make a mutant the reference.

## The three roles a factor can play

A Focus names some of the discovered factors and, for each one, the levels it keeps. Each discovered factor then plays exactly one role:

| Role | How you get it | What it does |
|---|---|---|
| **Varying** | named with two or more levels | its levels make up the treatment labels (e.g. `Female/20x`) |
| **Filter** | named with exactly one level | keeps only individuals at that level; does not appear in the label |
| **Pooled over** | not named at all | individuals at every level are combined |

Pooling changes every number (N, every curve, every p-value), so the Hub, the Focus window and every report state the role of each factor. The report's Focus section has a "Focus definition" table with Factor, Levels (display order), Role and Reference level columns.

If a Focus varies nothing (every named factor has one level) it is a single treatment. Its label is then built from every named factor so the one curve still has a name.

## A Focus is a rectangular product

A Focus is the **rectangular product** of the levels it names: `Sex: [Female, Male]` × `Density: [20x, 40x]` implies four treatments. If the data never contained one of them (an unbalanced design that ran `Male/40x` nowhere), that cell is **absent**. An absent cell is not an error. The run reports it ("Cells the levels imply but the data never held (absent, not an error)") and carries on with the cells that exist. A diagonal (two of four existing cells, without the other two) cannot be expressed as one Focus. Make two Focuses instead.

Individuals with no recorded level for a factor the Focus names belong to no treatment. The run counts them, writes a line to the log ("N individual(s) have no recorded level of … and belong to no treatment — outside this Focus") and repeats it in the report's Focus section. They are never dropped without a mention.

## How a Focus is written in survival_config.yaml

Focuses live in the `focuses:` block. You normally edit them in [the Focus window](help:focus-window), but the block can also be edited by hand:

```yaml
focuses:
  Crowding20v40:
    factors:                 # levels in display order: legends, facets, cells
      Sex: [Female, Male]
      Density: ["20x", "40x"]
    reference:               # optional; omitted -> first level listed
      Density: "40x"
    display_names: {Female/20x: "F, 20x"}
    colours: {Female/20x: "#b2182b"}
```

- `factors:` – each named factor with its kept levels, **in display order**. The order controls legends, facet panels and plot cells.
- `reference:` – the [Reference Level](help:reference-level) of each varying factor (the Cox baseline). Optional.
- `display_names:` and `colours:` – what each treatment is called and drawn in, keyed by treatment label. These are used by the Publication Figures drawn in the Plot Editor. They never change a number, so editing them never puts results [Out of Date](help:focus-status).

## Unfiltered: the Focus every experiment has

A config with no `focuses:` block still has one Focus, **Unfiltered**: every discovered factor at every level. It is written into the file (with the levels in their discovered order) the first time the experiment is analysed or its Focuses are opened in the Focus window. After that you can see it, edit it and rename it, and re-sorting the Design sheet later cannot move a Reference Level. Its results go to `analysis/Unfiltered/`.

A config written before Focuses existed that still has a top-level `factors:` block is migrated to one Focus named **Interaction** with exactly those factors and level order, so every Reference Level is preserved. No Unfiltered Focus is added next to it.

## Names, folders and files

The Focus name is shown exactly as typed. Folder and file names use a file-system-safe version of it: any run of characters other than letters, digits, `.`, `_` and `-` becomes `_`. A Focus called `Crowding 20v40` writes to `analysis/Crowding_20v40/`, and its files end in `_Crowding_20v40` (for example `plots/kaplan_meier_Crowding_20v40.png` and `run_summary_Crowding_20v40.json`). See [Where results are written](help:outputs-layout).

Two Focuses in one experiment cannot share a name or reduce to the same folder name. A Focus also cannot be named `plots`, `statistics` or `data_output`, because those names are reserved for results from before Focuses existed.

## The Active Focus

The **Active Focus** is the one the Hub currently shows. QC, Analyze, Plots and AI act on it. It is chosen in the Focus card at the top of [the Experiment panel](help:experiment-panel). Switching it is navigation, not configuration: every Focus's outputs coexist under their own names, so switching changes nothing on disk. (The Exclusion Group, by contrast, is configuration, shared by every Focus in the directory.)

Unattended runs have no Active Focus. A Batch Run or an Experiment Script with no `run_in_focuses` step analyses **every** Focus, and `run_in_focuses` lets a script name which ones. See [Experiment and Project Scripts](help:scripts-overview).

## Focuses and Projects

Focuses belong to one Member Experiment. They are **never** inherited from `project.yaml`'s `defaults:`, because members rarely share factors and an inherited Focus would be blocked in every member it did not fit. To reuse a design, use *Copy Focuses from…* in the Focus window. It checks each Focus against the receiving member's data before adding it.

## Pitfalls

- A Focus that pools over a factor (for example sex) mixes those individuals into every curve. If sexes differ, analyse them in separate Focuses, or keep the factor varying.
- Changing a Focus's factors, levels, level order or Reference Level after it has been analysed makes its saved results **Out of Date** until it is re-run.
- Renaming a Focus by hand in the YAML leaves its old results folder behind as **Orphaned Results**. Rename in the Focus window instead, which moves the results with the name.

## See also

- [The Focus window](help:focus-window)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [Reference Levels](help:reference-level)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [Batches, Projects, Experiments and Focuses](help:concepts)
- [Defined Plots](help:defined-plots)
