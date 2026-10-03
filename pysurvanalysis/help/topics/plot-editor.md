# The Plot Editor

The Plot Editor is where you design **Publication Figures**: journal-ready, vector versions of the figures in the Plot Set, drawn with plotnine (a ggplot-style library). On the left you edit one figure's content (its **Plot Spec**) and its look (its **Plot Style**). On the right a live preview redraws as you change things. What you save becomes the Project's curated figure, which **Render publication figures** writes out for every member and the reports show in place of the default figure.

The editor changes presentation only. It never reruns an analysis or changes which treatments a Focus contains. The one thing it writes outside `plot_specs.yaml` is the Active Focus's per-curve colours, into `survival_config.yaml`, because those belong to the Focus.

## Opening it

The editor is opened from the **Project** panel's actions card, with the **Plot editor…** button. It needs one Member Experiment whose data it previews. It picks, in order:

1. the member selected in the members table;
2. otherwise the loaded experiment;
3. otherwise the Project's only member;
4. otherwise it asks which member to use.

The preview draws that member's **Active Focus**, and the window title shows both: `Plot Editor — <member> · Focus <name>`. Press **F1** in the editor to open this page.

## The window

**Top bar** (right-hand side):

- **Save Project default** writes the **current figure's** Spec and its own Style into the container's `plot_specs.yaml`. It also saves any per-curve colours you changed into the Active Focus's definition in `survival_config.yaml`. The status bar confirms the save. Only figures saved this way are rendered and used by the reports.
- **Export SVG** writes the current figure, as previewed, to `<container>/figures/<plot id>_<focus>.svg`, with text kept editable. There is no dialog. If the name is taken, `_1`, `_2`… is appended rather than overwriting, so earlier exports are kept for comparison.
- **?** opens [Publication Figures, Specs and Styles](help:publication-figures).

The **container** is the Project directory. For a standalone experiment with no Project, it is the experiment's own directory.

**Left column**, five cards from top to bottom:

| Card | What it holds | Saved as |
|---|---|---|
| [Figure](help:plot-editor-figure) | which figure; title, axis labels, legend title, facet factor, axis limits, reference line; *Copy style from…* | the Spec |
| [Canvas & type](help:plot-editor-canvas) | size in mm, theme, font, text sizes and colour | the Style |
| [Curves & points](help:plot-editor-curves) | curve and axis weights, line join, markers, censor ticks, CI band | the Style |
| [Panels & legend](help:plot-editor-panels) | panel fill and border, gridlines, facet strips, legend position, At-Risk Band | the Style |
| [Colours](help:plot-editor-colours) | a swatch per curve, the fallback cycle, Refresh preview | Focus colours and the Style's cycle |

Controls that mean nothing for the current figure are **disabled** rather than silently ignored. For example, censor ticks are disabled on a hazard curve, and the At-Risk Band on anything but a KM figure. Controls a figure does use stay enabled even where the name suggests otherwise: **Band opacity** is the distribution's density fill, and the point shape, size, fill and outline style the forest and interaction markers. Scrolling the mouse wheel over the left column scrolls it and never changes a spin box or combo.

A colour swatch showing an automatic value (**curve**, **theme**, **cycle**) can be returned to it after a colour has been picked: **right-click** the swatch and choose **Use curve** (or **Use theme**, **Use cycle**…).

**Right side:** the preview. It is rendered at the screen's full resolution for the figure's size in millimetres, and re-rendered (not stretched) when you resize the window. If a figure cannot be drawn, the preview says why instead, for example "No data for hazard_ratio_forest under this Focus." (a forest needs the saved pairwise hazard ratios, the log-rank observed/expected estimates) or "Preview failed: …".

## Which figures it offers

The **Figure** combo lists:

- every figure already saved in `plot_specs.yaml`; and
- a default for each figure in the Active Focus's Plot Set that is relevant to the Focus's definition: `km_curves`, `cumulative_events`, `survival_distribution`, `mortality`, `hazard`, `smoothed_hazard`, `nelson_aalen`, `number_at_risk`, `hazard_ratio_forest` and `log_log` (the last two only with two or more treatments), plus `km_faceted` and `interaction_lifespan` when the Focus varies two or more factors.

There is no separate `km_risk_table` entry, because in a Publication Figure the at-risk counts are a Style option of `km_curves`. The editor opens on the **Headline Figure**: `km_faceted` when it is offered, otherwise `km_curves` (the publication form of the KM with at-risk table).

## Where the data comes from

The preview uses the Active Focus's **saved results** in `analysis/<focus>/`:

- series figures read `lifetables_<focus>.csv`, or compute the lifetables from the data if there is none;
- the distribution and interaction figures read `individual_data_<focus>.csv`, or load the data;
- the forest reads `hazard_ratios_<focus>.csv` only. The editor never fits a model, so run the analysis (with Pairwise hazard ratios ticked) before curating the forest.

Curves follow the Focus's treatment order and display names. A Spec cannot reorder or rename them (see [Publication Figures, Specs and Styles](help:publication-figures)).

## A typical session

1. Run the analysis for the Focus you want to show.
2. Open the Plot Editor from the Project panel with that member selected.
3. Choose a figure, set its labels, size, fonts and colours, and watch the preview.
4. Click **Save Project default**. Repeat for each figure you want curated.
5. Back on the Project panel, choose a format and click **Render publication figures**.

## See also

- [Publication Figures, Specs and Styles](help:publication-figures)
- [Plot Editor — Figure](help:plot-editor-figure)
- [Plot Editor — Colours](help:plot-editor-colours)
- [Project actions — reports, figures, Plot Editor](help:project-actions)
- [The Plots panel and Generate plots](help:plots-panel)
