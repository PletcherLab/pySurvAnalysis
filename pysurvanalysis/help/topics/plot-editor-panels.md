# Plot Editor — Panels & legend

The **Panels & legend** card controls everything around the curves: the panel background and border, gridlines, the title strips of a faceted figure, where the legend sits, and the **At-Risk Band** of number-at-risk counts under a Kaplan-Meier figure. These are **Plot Style** settings, saved under the figure's own name in `plot_specs.yaml` by **Save Project default**.

## Fields

**Panel:**

- **Swatch:** the plotting area's background. **theme** (the default, an empty swatch) keeps the theme's own fill. Pick a colour to override it.
- **Border:** draws a box around each panel in the text colour, at the **axes** weight from [Curves & points](help:plot-editor-curves). Off by default. A boxed facet strip turns the border on regardless.

**Gridlines:** `none` (default), `y` or `both`.

- `none` removes all gridlines.
- `y` draws light grey horizontal lines at the y-axis breaks, and no vertical ones.
- `both` draws light grey lines at the breaks of both axes.

Minor gridlines are always off. The lines are drawn whatever the theme, including the default `theme_classic`, which has none of its own. With the At-Risk Band on, `both` keeps the vertical lines out of the band, so they do not read as table rulings. The default is `none` because a survivorship curve is read against its own steps, and rules at 0.25, 0.5 and 0.75 compete with them.

**Facet strips:** the panel titles of a faceted figure (`km_faceted`, or a distribution given a `facet_by:` by hand in `plot_specs.yaml`).

- `plain` (default): the level name as bare text.
- `boxed`: the level name in a filled, outlined box, ggplot style. The panels get a border too, so the strip does not look detached.
- **Swatch:** the box fill for `boxed` (default light grey `#d9d9d9`). Not used with `plain`.

**Legend:** where the curve legend goes: `right` (default), `left`, `top`, `bottom` or `none` (no legend). The forest plot never shows a legend.

## The At-Risk Band

Kaplan-Meier figures only (`km_curves`, `km_faceted`). The band is the Publication Figure's version of the number-at-risk table. The counts are drawn as text **inside the same plot**, in space reserved below the curves, so the figure stays one object for faceting and vector export.

**At-risk band below the curves:** turns the band on. **On** by default, so a curated `km_curves` is "KM with at-risk counts" unless you untick it.

**Band size:**

- **Font size:** 3 – 20 (default **7**), the size of the count numbers.
- **row:** the vertical space given to each curve's row of counts, 0.02 – 0.4 (default **0.075**), in **y-axis units**. On a survival axis running 0 to 1, 0.075 is 7.5% of the axis height. The first curve's counts sit at −0.075, the second at −0.15 and so on, and the y axis is extended down to make room. The band has no axis labels. Each row's numbers are coloured like its curve, which identifies the row.

**Band times:** the ages the counts are printed at, as numbers separated by commas or spaces in your time unit (e.g. `0, 20, 40, 60`). Anything that is not a number is ignored. **Empty** (the default) prints at five evenly spaced ages: 0%, 25%, 50%, 75% and 100% of the last observed age. Pin the times when figures must line up side by side.

**What the count means:** for each curve and each band time t, the **number at risk at t**: the individuals whose recorded age (death or censoring) is t or later, i.e. alive and uncensored entering age t. It is the number at risk of the first observed age at or after t; at age 0 it is the starting group size, and after a curve's last observed age it is 0. In a faceted figure each panel gets its own rows. The counts are read from the same data as the curve above them, so the two cannot disagree, and by the same code as the analysis figure's [at-risk table](help:plot-km-risk-table), at the same default ages, so the two print the same numbers.

**Pitfall:** if you pin **Y limits** on the Figure card, the pinned range replaces the room reserved for the band. Set the lower limit below 0 (for two treatments at the default row height, about −0.2) to keep it visible.

## See also

- [The Plot Editor](help:plot-editor)
- [KM curves with at-risk table](help:plot-km-risk-table)
- [Plot Editor — Canvas & type](help:plot-editor-canvas)
- [Plot Editor — Figure](help:plot-editor-figure)
- [Publication Figures, Specs and Styles](help:publication-figures)
