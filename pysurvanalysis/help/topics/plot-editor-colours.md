# Plot Editor — Colours

The **Colours** card sets the colour of each curve in the current figure and the **fallback cycle** that any curve without its own colour takes. Per-curve colours belong to the **Focus**, not to the figure, so every Publication Figure of that Focus agrees: Females are the same red on the KM curves and on the hazard. The cycle belongs to the figure's Style.

## Fields

**One swatch per curve.** The card lists every curve the current figure will draw, in the order it draws them, each labelled with its display name. The list is rebuilt when you switch figure, because the curves depend on the data and the figure:

- for most figures, one swatch per **treatment** of the Focus;
- for the faceted KM, one per **curve level** (the level, or combination of levels, of the non-panel factors), since the same curve appears in every panel;
- for the interaction plot, one per **line**; for the forest, one per **comparison** ("A vs B").

Click a swatch to pick a colour. The colour dialog includes an alpha (transparency) slider. Partial alpha stores a semi-transparent colour, and alpha 0 stores `none`, which makes the curve invisible.

Each swatch first shows, in order of priority:

1. the colour the Focus already assigns to that curve;
2. a colour from an older Style's own per-label palette, if there is one and the Focus names none;
3. otherwise, the next colour of the fallback cycle by curve position.

**What gets saved.** Only a swatch you changed **away from its cycle colour** becomes an assignment. A swatch still showing its cycle colour is not saved, so opening the editor and touching something does not pin every curve's colour. When you click **Save Project default**, changed assignments are written into the Active Focus's definition (its `colours:`) in `survival_config.yaml`, and the status bar adds `Curve colours saved to Focus <name>.` The same colours can be seen and edited in the Colour column of the [Focus window](help:focus-window).

Because colours are keyed by the Focus's own treatment labels, a colour set under one Focus does not carry over to another, even for the same individuals.

**Fallback cycle.** A row of small swatches, the colours in the order unassigned curves take them. The first curve takes the first colour, the second the second, and so on, wrapping round. The default is an 8-colour, colour-blind-safe palette (`#4C72B0`, `#DD8452`, `#55A868`, `#C44E52`, `#8172B3`, `#937860`, `#DA8BC3`, `#8C8C8C`). Click any swatch to change it. The cycle is part of this figure's Style (`palette_cycle`), saved with the figure and copied by *Copy style from…*. A journal palette can live here without naming any treatment in advance.

To return **one** curve to the cycle, right-click its swatch and choose **Use cycle**.

**Reset curve colours to the cycle.** Clears the per-curve assignments for the curves in this figure, so they fall back to the cycle. The cycle itself is unchanged. The reset is written to the Focus only when you next click **Save Project default**.

**Refresh preview.** Redraws the preview. Changes normally redraw it automatically; use this after editing `plot_specs.yaml` or the Focus elsewhere.

## Notes

- The per-curve colours are the **Focus's**, so they apply to every figure of it: the Publication Figures (the preview, Export SVG, Render publication figures, curated figures in the reports) and the analysis PNGs from Run analysis and Generate plots. Only the fallback differs: a Publication Figure takes this card's cycle, an analysis PNG a fixed cycle, each in the Focus's order.
- Display names (the labels beside the swatches and in legends) also come from the Focus. Change them in the Focus window, not here.

## See also

- [The Plot Editor](help:plot-editor)
- [The Focus window](help:focus-window)
- [Plot Editor — Figure](help:plot-editor-figure)
- [Publication Figures, Specs and Styles](help:publication-figures)
