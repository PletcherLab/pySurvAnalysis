# Faceted Kaplan-Meier

The faceted Kaplan-Meier figure splits the survival curves into side-by-side panels: **one panel per level of the first varying factor**, with a curve in each panel for every level (or combination of levels) of the other factors. If one factor's effect differs between panels, that difference is the **interaction**, visible without reading a coefficient. For a Focus that crosses factors, this is the **Headline Figure**.

## In the app

- **Plots panel:** the **Faceted Kaplan-Meier** checkbox (plot id `km_faceted`). It appears only when the Active Focus varies two or more factors.
- **Scripts:** the **Faceted KM** action, with a **Show 95% CI** option (off by default).
- **Plot Editor:** `km_faceted`. Its **Facet by** combo chooses which varying factor becomes the panels. See [Plot Editor — Figure](help:plot-editor-figure).

## What is drawn

Suppose the Focus varies `Sex` (Female, Male) then `Diet` (1x, 20x). Its treatment labels are `Female/1x`, `Female/20x` and so on.

- **Panels:** one per level of the **first** varying factor in the Focus's order, here "Sex: Female" and "Sex: Male". Panels appear in the Focus's level order, and a level with no individuals gets no panel.
- **Curves:** in each panel, one KM step curve per level of the remaining factor(s), here 1x and 20x. With three or more factors, the curves are the combinations of the remaining levels joined by "/". A cell with no individuals is simply a missing curve.
- **Colours:** each curve level keeps the same colour in every panel, so 20x is the same colour under Female and Male. It is the colour the Focus gives that level (set it on the faceted figure in the Plot Editor's Colours card), otherwise the fixed cycle in the Focus's level order. The legend shows the Focus's display name for the level where it has one.
- **Censor ticks** ("|") at ages with censoring. **No CI bands** in the Plot Set figure. The script action can add them.
- **Axes:** every panel shares the y axis "Survival probability" (0 to 1). Each x axis uses your configured time label (for example "Age (days)").
- **Legend:** on the right-hand panel, titled with the curve factor(s), e.g. "Diet".
- **Title:** `Survival by treatment, faceted by <first factor>`. Each panel is about 5.5 × 5 inches.

The curves are the same Kaplan-Meier estimates as the [Kaplan-Meier curves](help:plot-km-curves) figure, computed per treatment from the Focus's lifetable.

## Reading it

- Compare the **gap between curves within each panel**. If 20x lies below 1x by about the same amount in both panels, Diet acts the same way in both sexes (no interaction). If the gap is large in one panel and absent or reversed in the other, the effect of Diet depends on Sex, which is an interaction.
- Compare the **same-coloured curve across panels** to see the effect of the panel factor at each level of the other.
- The formal tests of these patterns are the [Cox factorial model](help:cox-factorial) and the [RMST factorial model](help:rmst-factorial), relative to each factor's [Reference Level](help:reference-level).

## Headline Figure

For a Focus that varies two or more factors and populates two or more treatments, this figure is the Headline Figure. It is placed first in the report's figures section and is the default figure the Plot Editor opens on.

## Where it appears

- File: `analysis/<focus>/plots/km_faceted_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `km_faceted` is curated in the Plot Editor.

## When it is offered, Not Applicable or Left Out

It requires **a figure crossing factors**:

- **Not offered** when the Focus varies fewer than two factors. It has no checkbox, and the Plots panel's "Not offered" line names it.
- **Not Applicable** when the Focus varies two or more factors but fewer than two of its treatments hold individuals after exclusions.
- Unlike the Factorial Battery's models, it does **not** need every combination of levels to be present. A missing cell is a missing curve.
- **Left Out** when unticked.

## See also

- [Lifespan interaction plot](help:plot-interaction-lifespan)
- [Interaction analyses (Factorial Battery)](help:analysis-interaction)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [Kaplan-Meier curves](help:plot-km-curves)
- [Plot Editor — Figure](help:plot-editor-figure)
