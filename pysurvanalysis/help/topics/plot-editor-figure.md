# Plot Editor — Figure

The **Figure** card is the top card of the Plot Editor. It chooses which figure you are editing and holds that figure's **content decisions**: the **Plot Spec**. Everything on this card except *Copy style from…* is saved in the figure's entry under `plots:` in the container's `plot_specs.yaml` when you click **Save Project default**.

Text fields update the preview when you press Enter or leave the field. Every other control updates it at once.

## Fields

**Figure:** the plot id of the figure being edited (`km_curves`, `mortality`, `km_faceted`, …). Switching loads that figure's Spec and Style into all the cards and disables the controls that do not apply to it. Unsaved edits to the previous figure stay in the editor's working copy until you close it, but they are written to the file only by **Save Project default** while that figure is selected.

**Title:** the figure title. It is empty by default, and an empty title draws no title, which suits a journal figure whose caption carries it.

**X label:** the x-axis title. The default follows what the axis shows. Where it is age, it is your configured time label, e.g. "Age (days)" from `global: time_label` (also the distribution, whose x axis is lifespan). For the log-log diagnostic it is "log(Age (days))". For the forest plot it is "Hazard ratio (log scale)", which is also what a cleared field gives. For the interaction plot it is the name of the first varying factor, whose levels are on that axis.

**Y label:** the y-axis title. The default is set per figure: "Survival probability" (KM and faceted KM), "Cumulative probability of death" (cumulative deaths), "Cumulative hazard" (Nelson-Aalen), "Individuals at risk", "Mortality (qx)", "Hazard rate", "Smoothed hazard", "log(−log S(t))", "Density" (distribution), "Comparison" (forest) or `Median lifespan — <time label>` (interaction). An empty field falls back to the figure's own label.

**Legend title:** the title over the curve legend. The default is "Treatment". For the faceted KM it is the second varying factor, because there the curves are that factor's levels, not whole treatments; for the interaction plot, the factor(s) after the first, whose levels make the lines. The forest plot shows no legend. Legend entries follow the Focus's order and show its display names.

**Facet by:** a list of the Active Focus's **varying factors**, plus "(none)". The factor you pick becomes the **panels**, one per level. The other factor(s) become the curves within each panel. It is enabled only for `km_faceted`, and it defaults to the first varying factor. With "(none)" the faceted KM draws as one panel of whole-treatment curves.

**X limits:** a checkbox and two numbers (low – high, two decimals). Unchecked, the axis fits the data. Checked, the axis is pinned to that range, which you need when two figures must sit side by side on the same scale. The two numbers are sorted when saved, so typing them the wrong way round still works. The units are those of the x axis: your time unit, or natural-log time for the log-log diagnostic. On the forest plot the limits are ratios and must both be greater than 0, otherwise they are ignored. On the interaction plot x is a list of levels and cannot be pinned.

**Y limits:** the same, for the y axis (three decimals; default range 0 – 1 when first ticked). Units are those of the y axis: probability, cumulative hazard, count, density or lifespan. On the forest plot y is the list of comparisons and cannot be pinned. On a KM figure, pinning y replaces the room the editor otherwise reserves below 0 for the At-Risk Band, so set the lower limit below 0 (e.g. −0.3) if you want the band to stay visible.

**Reference line:** a checkbox and a value (three decimals). Checked, a dashed grey horizontal line is drawn at that y value. The default is **checked at 0.5** for the KM figures and cumulative deaths, marking median survival, and unchecked elsewhere. Negative values are allowed, which is useful on the log-log diagnostic. It is drawn on the series figures (KM, cumulative deaths, Nelson-Aalen, hazard, mortality, number at risk, log-log) but not on the forest, distribution or interaction plots.

**Style: Copy style from…** opens a list of every other figure's working style ("mortality (figure)") and every named style already in `plot_specs.yaml` ("km_curves (saved style)"). The one you pick is copied over the current figure's **whole Style**: all of Canvas & type, Curves & points, Panels & legend and the colour cycle. Each figure owns its style, so this is the deliberate way to make figures match. The copy is not saved until you click **Save Project default**. The **?** beside it opens [Publication Figures, Specs and Styles](help:publication-figures).

## What the Spec cannot do here

- **Treatment order and display names** come from the Focus. Set them in the [Focus window](help:focus-window).
- A Spec can **narrow** a figure to some of the Focus's treatments, but there is no control for it in the editor. Add a `treatments:` list to the figure's entry in `plot_specs.yaml` by hand. Names not in the Focus are ignored, and if none match, all treatments are shown.
- **Facet order** (`facet_order:`) can likewise only be set in the file.

## See also

- [The Plot Editor](help:plot-editor)
- [Publication Figures, Specs and Styles](help:publication-figures)
- [Plot Editor — Panels & legend](help:plot-editor-panels)
- [Faceted Kaplan-Meier](help:plot-km-faceted)
- [The Focus window](help:focus-window)
