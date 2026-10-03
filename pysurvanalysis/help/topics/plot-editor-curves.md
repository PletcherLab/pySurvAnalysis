# Plot Editor — Curves & points

The **Curves & points** card styles the data itself: the weight of the curves, how points are joined, optional markers, the Kaplan-Meier censor ticks and the confidence band. These are **Plot Style** settings, saved under the figure's own name in `plot_specs.yaml` by **Save Project default**.

Controls that do not apply to the current figure are greyed out:

| Figure | Markers | Censor ticks | CI band | Band opacity | Line style |
|---|---|---|---|---|---|
| `km_curves`, `km_faceted` | yes | yes | yes | yes | yes |
| `nelson_aalen`, `cumulative_events` | yes | — | yes | yes | yes |
| `mortality`, `hazard`, `smoothed_hazard`, `number_at_risk`, `log_log` | yes | — | — | — | yes |
| `survival_distribution` | — | — | — | yes (the density fill) | — |
| `hazard_ratio_forest`, `interaction_lifespan` | shape, size, fill and outline only | — | — | — | — |

## Fields

**Curve width:** the thickness of the curves and lines (0.1 – 6.0 in plotnine size units; default **0.9**). On the forest and interaction plots it also sets the interval lines, and on the distribution the density outline.

**axes:** the weight of the figure's "furniture": axis lines, tick marks, panel borders and boxed strip outlines (0 – 4.0 pt; default **0.8**). It is kept separate from curve width because a heavy curve on light axes is a common journal style.

**Line style:** how successive values are joined:

- `auto` (default) follows the figure. **Step** for KM, Nelson-Aalen, number at risk and cumulative deaths. **Straight lines** for mortality, hazard, smoothed hazard and the log-log diagnostic (as the analysis figure joins them).
- `step` draws a staircase: each value is held until the next.
- `line` draws straight segments between values.

The CI band follows the same choice, so it always bounds its curve. Not available on the forest, distribution and interaction plots.

## Points on the curve

**Draw points on the curve:** adds a marker at chosen values on every curve. It is **off** by default, because a lifespan cohort has an event at almost every census and a marker per event buries the curve.

**Points at:** which values get a marker:

- `events` (default): values where the curve actually changed. On a survival curve that means every age where survival fell. The age-0 starting point and censoring-only values are skipped.
- `censored`: values at ages with at least one censoring.
- `all`: every observed age (except age 0).

**Shape / size:** the marker shape, one of `o` circle, `s` square, `^` and `v` triangles, `D` diamond, `d` thin diamond, `p` pentagon, `h` hexagon, `*` star, `+`, `x` and `|`. Size ranges from 0.2 to 12 (default **2**). The first nine are *filled* shapes, which can have an outline. On `+`, `x` and `|`, an outline only makes the mark thicker.

**Opacity / fill:**

- **Opacity:** 0 – 1, default 1 (opaque).
- **Fill swatch:** the marker's interior. **curve** (the default, an empty swatch) uses the curve's own colour. Picking a colour uses that colour. Picking with the dialog's alpha at 0 stores `none`, which gives a **hollow** marker when an outline is set (see below). Partial alpha is stored as an `#rrggbbaa` colour. Right-click the swatch and choose **Use curve** to go back to the curve's colour.

**Outline:**

- **Weight:** 0 – 3.0, default **0**. At 0 the marker has no separate edge and is drawn in one colour: the fill colour if one is picked, otherwise the curve colour. Above 0, and on a filled shape, the marker has an edge of this weight with the fill inside.
- **Colour swatch:** the edge colour. Default black. Picking alpha 0 gives an invisible edge. Right-click it and choose **Use curve** for an edge in the curve's own colour.

So for a hollow circle, choose shape `o`, outline weight above 0, and a fill picked with alpha 0.

## Censor ticks

Kaplan-Meier figures only.

**Censor ticks:** marks on the curve at every age where at least one individual was censored. **On** by default.

**Tick shape/size:** the mark, from the same shape list (default `|`, a short vertical tick), size 0.2 – 12 (default **2**), and a colour swatch (default **curve**, the curve's own colour; right-click it to return to **curve**).

## Confidence band

KM, cumulative-deaths and Nelson-Aalen figures only.

**95% CI bands:** shades the 95% confidence interval around each curve. **Off** by default in Publication Figures, although the analysis figures draw it. The intervals are the ones in the lifetable: the log-log (exponential Greenwood) band for KM, reflected for cumulative deaths, and ±1.96·√Σd/n² for Nelson-Aalen (see [Life tables and the Kaplan-Meier estimator](help:lifetables)).

**Band opacity:** 0 – 1, default **0.15**. The band takes each curve's colour.

The [Lifespan distribution](help:plot-survival-distribution) uses this same opacity for its density fill, so the control stays enabled for that figure (the **95% CI bands** box does not).

## Forest and interaction markers

On the forest and interaction plots the marker **is** the estimate, so it is always drawn. Its **shape, size, fill and outline** follow the point settings above, which stay enabled for those figures, at full opacity and a size of at least 2. **Draw points on the curve**, **Points at** and the point opacity do not apply there and are greyed.

## See also

- [The Plot Editor](help:plot-editor)
- [Plot Editor — Canvas & type](help:plot-editor-canvas)
- [Plot Editor — Panels & legend](help:plot-editor-panels)
- [Plot Editor — Colours](help:plot-editor-colours)
- [Kaplan-Meier curves](help:plot-km-curves)
