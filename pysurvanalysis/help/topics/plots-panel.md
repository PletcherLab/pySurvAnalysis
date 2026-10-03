# The Plots panel and Generate plots

The Plots panel lists the **Plot Set** of the Active Focus — every standard figure this Focus can get — with one checkbox per figure, and one **Generate plots** button below them. A ticked box means "draw this figure"; an unticked box means "leave it out of every run". The same ticks govern **Generate plots**, **Run analysis** on the Analyze panel, Experiment Scripts and Batch runs.

## In the app

Open the Experiment tile and choose the **Plots** sub-tile. With no experiment loaded the panel only says "Load an experiment to see its plots."

- **The checkboxes.** One per figure in the Plot Set, in the order the report uses. Hover over a box to see its caption. Each box has a **?** button that opens that figure's page in this manual.
- **Ticking and unticking** saves at once. An unticked figure is written to the `omit:` block of `survival_config.yaml` (under `plots:`), and the log says so, e.g. `Log-log diagnostic: left out of <experiment>'s runs — survival_config.yaml omit:`. Ticking it again removes it from the block.
- **Generate plots** draws the ticked figures for the Active Focus. Each figure opens in its own tab, titled `<figure> — <Focus name>`, and is saved as a PNG under `analysis/<focus>/plots/`.
- **The "Not offered" line.** Under the button, a grey italic line names figures this Focus is not offered (for example "Not offered for Focus Females: Faceted Kaplan-Meier, Lifespan interaction plot."). Hover over it to see why.

## Which figures are listed

The Standard Lifespan Plot Set, in order:

| Figure | Plot id | Needs |
|---|---|---|
| KM curves with at-risk table | `km_risk_table` | — |
| Kaplan-Meier curves | `km_curves` | — |
| Cumulative deaths | `cumulative_events` | — |
| Lifespan distribution | `survival_distribution` | — |
| Mortality (qx) | `mortality` | — |
| Hazard rate | `hazard` | — |
| Smoothed hazard | `smoothed_hazard` | — |
| Nelson-Aalen cumulative hazard | `nelson_aalen` | — |
| Number at risk | `number_at_risk` | — |
| Hazard-ratio forest | `hazard_ratio_forest` | a comparison; Pairwise hazard ratios ticked |
| Log-log diagnostic | `log_log` | a comparison |
| Faceted Kaplan-Meier | `km_faceted` | a figure crossing factors |
| Lifespan interaction plot | `interaction_lifespan` | a figure crossing factors |

A figure's requirement decides how it appears (see [Focus Shape](help:focus-shape)):

- **Not offered.** The Focus's definition does not ask the question. A single-treatment Focus gets no forest and no log-log diagnostic. A Focus that varies fewer than two factors gets no faceted KM and no interaction plot. These figures have no checkbox and are not recorded anywhere.
- **Not Applicable (greyed).** The figure is relevant but the data, after exclusions, cannot support it. For example, the Focus implies two treatments but only one holds individuals. The box is greyed and its tooltip gives the reason. The Hub works this out from the Design sheet and the active Exclusion Group before anything runs.
- **Greyed because an analysis is unticked.** The hazard-ratio forest draws from **Pairwise hazard ratios**. If that box is unticked on the Analyze panel, the forest box is greyed and its tooltip says "Draws from Pairwise hazard ratios — tick it on the Analyze panel to draw this figure." Runs record the forest as Left Out with the reason "draws from Pairwise hazard ratios, which is unticked".

## What Generate plots does, and does not do

- It loads the Active Focus's slice, with exclusions applied, and computes the lifetables afresh.
- If the forest is ticked (and Pairwise hazard ratios is ticked), it computes the pairwise hazard ratios. It computes no other statistic.
- It writes each figure to `analysis/<focus>/plots/<file>_<focus>.png` at 150 dpi, overwriting the earlier version. The file names are listed on each figure's page.
- It does **not** rewrite the statistics, the report or the Run Summary. They stay as the last **Run analysis** left them. To get new figures into the report, run the analysis again.
- It also draws the workbook's [Defined Plots](help:defined-plots) that are about the Active Focus, each in its own tab titled `Defined Plot — <name> — <Focus name>`, exactly as a full run does.
- It logs every figure it leaves out or finds Not Applicable ("Left out — …", "Not applicable — …") and ends with "N figure(s) saved to …".

A Blocked Focus (one that names factors or levels the data file lacks, or whose cells were all excluded) cannot be drawn. Generate plots stops with the reason.

## In a full run

**Run analysis** draws the same ticked figures the same way, because both buttons share one drawing routine. A full run also:

- records each left-out figure under "Left out of this run" in the report and under `left_out` in the Run Summary, and each Not Applicable figure under "Not applicable to this Focus";
- deletes a Plot Set or Defined Plot PNG that an earlier run wrote and this run did not, so a folder never shows a stale figure as if it were current;
- places the figures in the report's figures section with the **Headline Figure** first. That is the [KM curves with at-risk table](help:plot-km-risk-table), or the [Faceted Kaplan-Meier](help:plot-km-faceted) when the Focus crosses factors and the data can draw it. Where a figure has been curated in the [Plot Editor](help:plot-editor), the report shows the curated version in its place.

If one figure fails to draw, it is recorded as Not Applicable ("could not be drawn (…)") and the other figures are still drawn.

## How the figures look

- Treatments are drawn in the **Focus's order**, labelled with its **display names**, in its **colours**: the same order, names and per-curve colours the Publication Figures use. A treatment the Focus gives no colour takes a fixed colour cycle by its position in the Focus's order, so it keeps one colour across every analysis figure of the Focus. (A Publication Figure's fallback is its Style's own cycle instead.)
- The time axis carries your configured time label (`global: time_label`, or `Age (<time_unit>)`).

## See also

- [The omit: section — leaving analyses and figures out](help:config-omit)
- [Not Applicable and Left Out](help:not-applicable)
- [The Analyze panel and Run analysis](help:analyze-panel)
- [Defined Plots](help:defined-plots)
- [Where results are written](help:outputs-layout)
- [The Plot Editor](help:plot-editor)
