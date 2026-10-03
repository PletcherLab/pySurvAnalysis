# Defined Plots

A **Defined Plot** is a named group of treatments that you write into the DLife workbook's `DefinedPlots` sheet while designing the experiment. For example, "Diet series" might list the four diets fed to females. Each analysis run draws every Defined Plot that is about the Focus being analysed, as a Kaplan-Meier figure with exactly the curves you listed and titled with the plot's name. A Defined Plot is a **figure**, not an analysis. It adds no statistics, though it can be turned into a Focus (see below).

## The DefinedPlots sheet

Defined Plots are read only from an Excel (`.xlsx`) DLife workbook with a sheet named exactly `DefinedPlots`. CSV inputs have none.

- **One column per plot.**
- **Row 1:** the plot's name. It is used as the figure title, the report heading and in the file name.
- **Rows 2–5:** ignored.
- **Row 6 downward:** one treatment per cell. Only the text **before the first comma** is used, so `Female/20x, high-dose group` reads as `Female/20x`. The first empty cell ends the list for that column.
- A column with no treatments from row 6 is ignored. If the sheet cannot be read, there are simply no Defined Plots.

Each treatment must be written as a **full treatment of the data file**: one level of **every** factor in the file, in the file's factor order, joined by `/`, e.g. `Female/20x` for a file whose factors are Sex then Diet. Spaces around each part are ignored.

## Which Focus draws it

Defined Plots are matched against the Focus of each run:

- **Drawn** when the Focus pools over no factor, and every listed treatment that the data file contains falls inside the Focus. Every listed treatment must also hold individuals in this Focus after exclusions. The curves are relabelled with the Focus's own treatment names and drawn in the Focus's order.
- **Not drawn, and not mentioned**, when the plot is about a different slice. A plot comparing the sexes is not about a females-only Focus, so it does not appear there or in its report. The same goes for any Focus that pools over a factor.
- **Not Applicable** when the plot is about this Focus but a listed treatment is missing from it. The treatment may be absent from the data, emptied by the active Exclusion Group, or a typo the file never had. The run records `Defined Plot '<name>'` with the reason, e.g. "not in Focus 'Females': Female/40x", in the log, the Run Summary and the report's "Not applicable to this Focus" table. A Defined Plot is **all or nothing**: it is never drawn with fewer curves than you listed.

Every factor in a file must be named in a label. A plot that cannot be about **any** Focus is a mistake in the sheet, so rather than vanishing it is recorded as **Not Applicable under every Focus**, with the reason:

- a label with the wrong number of `/`-separated parts (for example, only the diet in a Sex × Diet file): "Female — not a full treatment of this data file (one level of each of Sex/Diet, joined by '/')";
- labels none of which is a treatment the file contains (every one a typo): "none of … is a treatment of this data file".

## What is drawn

The same figure as [Kaplan-Meier curves](help:plot-km-curves), restricted to the listed treatments:

- KM step curves with 95% confidence bands and "|" censor ticks;
- the plot's name as the title; y axis "Survival Probability"; x axis labelled with your configured time label (for example "Age (days)");
- the curves in the Focus's order, with its display names and colours. A treatment without a Focus colour takes the fixed cycle by its position among **all** the Focus's treatments, so it keeps the same colour as in the Focus's main KM figure.

## Where it appears

- File: `analysis/<focus>/plots/defined_<name>_<focus>.png` (150 dpi). In `<name>`, any run of characters other than letters, digits, `.`, `_` and `-` becomes `_`.
- The experiment report's figures section, after the Plot Set figures, titled `Defined Plot — <name>` with the caption "Treatments the experimenter listed in the workbook's DefinedPlots sheet."
- The Run Summary's `defined_plots` entry.

Defined Plots are drawn by **Run analysis**, by scripts and Batch runs that run the analysis, and by **Generate plots** on the Plots panel. They have no checkbox there, and the `omit:` block does not affect them. A full run deletes a `defined_*` PNG an earlier run wrote that this run did not draw (the plot was renamed or removed from the sheet, or is now Not Applicable), so the folder never shows a stale one.

## Promoting a Defined Plot to a Focus

Experimenters often use Defined Plots to mark the separate experiments within one file. The [Focus window](help:focus-window) offers **Import from DefinedPlots…**:

1. It reads the sheet and, for each plot, proposes a Focus with the plot's name that selects exactly the listed treatments.
2. A proposal is possible only when the listed treatments form a **rectangular product of levels**. For example, Female and Male × 1x and 20x, all four listed. If the product of the levels used would also include a treatment you did not list, the plot is shown as not importable with the reason ("its treatments are not a rectangular product of levels (the product would also include …)"). The same happens for a level the data file does not contain.
3. You tick the proposals you want. They are added as new Focuses (renamed if the name is taken) and saved when you close the Focus window with OK.

Import is offered rather than automatic because a Focus is an **analysis**, with its own statistics, report section and output folder, whereas a Defined Plot is only a figure.

## See also

- [What a Focus is](help:focus)
- [The Focus window](help:focus-window)
- [Kaplan-Meier curves](help:plot-km-curves)
- [Not Applicable and Left Out](help:not-applicable)
- [Input data formats](help:data-formats)
- [The experiment report](help:experiment-report)
