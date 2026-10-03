# Your first analysis

This walk-through takes you from an empty folder to a finished report, using the Analysis Hub. It assumes you have one DLife census workbook (`.xlsx`). Each step names the panel, the card and the button you click. Panels open when you click a tile in the strip across the top, and close again when you click the tile a second time, press Esc, or click elsewhere in the window.

## 1. Open or create a Project

Click the **Project** tile. The first card, **Create/Load**, has the ways in:

- **Open project…** if you already have a folder with a `project.yaml`.
- **Create project…** to start a new one. In the dialog, set **Directory** to the folder the Project should be (it is created if it does not exist), give it a **Project name** (it defaults to the folder name) and a one-line **Question**, which appears on the Project Report's cover. Leave **Experiment type** at *Standard Lifespan* and check the **Global** settings (`time_unit`, `time_label`, `assume_censored` and `min_n_per_chamber`). These are Project Defaults that every member inherits unless it states its own. Click **Save**.
- **Initialize existing directory…** if you already have a folder of experiment subfolders and want it to become a Project in place.

The Project is now open. The Create/Load card shows its name, type and member count, and the **Experiments** card below it becomes usable. You do not need a Project to analyse one workbook (opening a folder that holds a `survival_config.yaml` loads it directly as a standalone experiment), but a Project is the usual way to work. See [Creating and opening a Project](help:project-create).

## 2. Add a member

On the **Experiments** card, under *Bring one in from outside*, click **Add experiment…** and choose your workbook. The app checks that it is a valid DLife workbook (Design and RawData sheets, with at least one factor column after `StartTime`), then:

- creates a member folder named after the file (`cohort_a.xlsx` becomes `cohort_a/`),
- puts the workbook in that folder's `data/` (copied from outside the Project, or moved if it was already loose inside the Project), and
- writes a minimal `survival_config.yaml` that inherits everything else from the Project Defaults.

The member appears in the members table with **Config** = `yes` and **Analysed** = `no`. The other ways to add a member are described in [The Experiments card — members](help:project-members).

## 3. Load the member

**Double-click its row** in the members table. The member loads, the status readout shows it on its *Experiment* row, and the **Experiment** panel opens on its own. Everything you do from here applies to this member.

## 4. Choose or create a Focus

The **Focus** card at the top of the Experiment panel says which slice of the data the next steps act on, the **Active Focus**. A new member has one Focus, `Unfiltered`: every factor found in the Design sheet, at every level. The line under the selector describes the Focus (its varying factors and levels, the Reference Level of each, any filters and anything pooled over), its shape (for example `2×2`), and which comparisons and factorial analyses it offers.

- To analyse everything together, keep `Unfiltered`.
- To analyse a subset, click **New…**. The Focus window opens with a new Focus. Name it, untick the factors you want to pool over, tick the levels to keep (one level makes the factor a filter), choose each factor's Reference Level, then click **Save**. The new Focus becomes the Active Focus. See [The Focus window](help:focus-window).

The selector lists each Focus with its state: `not analysed`, `analysed`, `out of date` or `blocked`.

## 5. Quality control

Click the **QC** sub-tile in the Experiment panel.

1. Click **Chamber QC viewer…**. It draws every chamber's survival curve, panel by panel per treatment. Click a curve to flag that chamber for exclusion, then use **Save Exclusions…** to save the flagged chambers under a group name (for example `default`).
2. Back in the Hub's QC panel, pick that group in **Active group** and click **Set active group**. This writes `exclusions: {group: …}` into `survival_config.yaml`, so every later run drops those chambers and records which group did it. If the new group is not in the list yet, type its name into the box (it accepts typing).

If nothing needs excluding, skip this step. See [The QC panel](help:qc-panel).

## 6. Tick the analyses and run them

Click the **Analyze** sub-tile. There is one checkbox for each analysis the Active Focus is offered (log-rank pairwise, log-rank omnibus, Gehan-Wilcoxon pairwise, pairwise hazard ratios, parametric AFT models and, when the Focus varies two or more factors, *Interaction analyses*). Untick anything you do not want. The ticks are saved in the config's `omit:` block, so scripts and Batch Runs leave out the same things. A greyed box is **Not Applicable**: the Focus asks the question but the data cannot answer it. Hover over the box to see why.

Click **Run analysis**. Progress streams into the **Output** tab, starting with `▶` and ending with `✔` (done) or `✘` (failed). The results, the figures and the report go to `analysis/<focus>/` inside the member's folder. See [The Analyze panel and Run analysis](help:analyze-panel).

## 7. Generate plots

Click the **Plots** sub-tile. There is one checkbox per figure in the Focus's Plot Set. Tick the ones you want, then click **Generate plots**. Each figure opens as a tab beside **Output** and is saved to `analysis/<focus>/plots/`. Run analysis already draws the ticked figures into the report. Generate plots is for looking at them in the Hub. See [The Plots panel and Generate plots](help:plots-panel).

## 8. Read the report

Each run writes `<member>_report_<focus>.pdf` (plus a Markdown `report_<focus>.md`) in `analysis/<focus>/`. To open it, go back to the **Project** tile and click **View reports** on the **Actions** card. It opens the Project Report, if there is one, and every member report in your PDF viewer. To bind all members' Focuses into one document, click **Project report** first. It writes `<project>_report.pdf` in the Project folder from the saved results, without re-analysing anything.

To read a report, see [The experiment report](help:experiment-report) and [The Project Report](help:project-report).

## Next steps

- Add more members, and run every one in a single step with the Project's `batch` script: [Project Scripts](help:project-scripts).
- Curate journal-ready figures in the [Plot Editor](help:plot-editor).

## See also

- [Batches, Projects, Experiments and Focuses](help:concepts)
- [The Analysis Hub](help:hub)
- [The Experiment panel](help:experiment-panel)
- [What a Focus is](help:focus)
- [Where results are written](help:outputs-layout)
- [Troubleshooting](help:troubleshooting)
