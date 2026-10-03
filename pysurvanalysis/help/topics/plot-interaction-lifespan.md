# Lifespan interaction plot

The lifespan interaction plot is the classic two-way "interaction plot" for lifespan. It shows the **median lifespan** of every cell of the Focus's crossing, with one factor on the x axis and one line per level of the other. **Parallel lines** mean the factors act independently. **Non-parallel or crossing lines** mean they interact. It is offered whenever the Focus varies two or more factors.

## In the app

- **Plots panel:** the **Lifespan interaction plot** checkbox (plot id `interaction_lifespan`). It appears only for a Focus varying two or more factors.
- **Scripts:** the **Lifespan interaction plot** action, with a **Metric** choice: `median` (default) or `mean`.
- **Plot Editor:** `interaction_lifespan`. It computes the same values as the analysis figure, the same way round.

## What is drawn

Suppose the Focus varies `Sex` (Female, Male) then `Diet` (1x, 20x).

- **x axis:** the levels of the **first** varying factor, here Sex: Female, Male, in the Focus's level order. This is the same factor that makes the panels of the [Faceted Kaplan-Meier](help:plot-km-faceted), so the two figures read the same way round. The axis title is the factor name.
- **Lines:** one per level of the other factor(s), here 1x and 20x. With three or more factors, one line per combination of the other factors' levels, joined by "/". The legend is titled with those factor names and shows the Focus's display names. Line colours are the Focus's colours where it sets them, otherwise the fixed colour cycle in level order.
- **Points:** for each cell, the cell's lifespan statistic, with its 95% confidence interval as error bars, and lines joining a line's points. A cell with no individuals is skipped.
- **y axis:** `Median lifespan — <time label>`, e.g. "Median lifespan — Age (days)".
- Title "Lifespan interaction", 7 × 5 inches.

## How the values are computed

For each cell (one combination of levels), from the individual-level data, **censored individuals included as censored**:

- **Median** (the Plot Set figure, and the default): the **Kaplan-Meier median**, the first age at which the cell's survival falls to 0.5 or below. Its 95% interval is read off the KM curve's own confidence band where it crosses 0.5 (lifelines' exponential-Greenwood band, the way lifelines reports the CI of a median). A cell whose survival never falls to 0.5 has **no median**, so it gets no point. It is never replaced by the plain median of the recorded times, which would count every censored individual as dead.
- **Mean** (script option only): the **restricted mean lifespan** (RMST), the area under the cell's KM curve from 0 to a common τ. τ is the earliest of the cells' last observed ages, so no cell is extrapolated, and it is printed in the y-axis title, e.g. "Restricted mean lifespan (τ = 62) — Age (days)". Its interval is ±1.96 × the standard error of the RMST estimate.
- **Open limits:** when the KM band never falls to 0.5, the upper limit of the median's interval is not reached. That side gets no error bar, rather than one running off the axis or stopping at an invented value.

The intervals describe each cell's own uncertainty. They are a visual guide, not a test: the formal test of interaction is the model, below.

## Reading it

- **Parallel lines:** moving from Female to Male changes median lifespan by the same amount at 1x and 20x. There is no interaction on this scale.
- **Lines that converge, diverge or cross:** the Sex effect depends on Diet. Crossing lines mean the direction of the effect reverses.
- Medians summarise the middle of each survival curve. Two cells can share a median yet differ early or late. Check the [Faceted Kaplan-Meier](help:plot-km-faceted).
- The formal test of interaction is the likelihood-ratio test in the [Cox factorial model](help:cox-factorial). The [RMST factorial model](help:rmst-factorial) tests interaction on the restricted-mean scale without assuming proportional hazards.

## The Publication Figure version

The Plot Editor and rendered Publication Figures draw the same median and interval for each cell, by the same code, with the first varying factor on x and the lines in the Focus's order. Only the median is offered there. A new Spec's x label is the first factor's name and its legend title the other factors' names; the y label is `Median lifespan — <time label>`. Only the y axis can be pinned.

## Where it appears

- File: `analysis/<focus>/plots/interaction_lifespan_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `interaction_lifespan` is curated in the Plot Editor.

## When it is offered, Not Applicable or Left Out

It requires **a figure crossing factors**:

- **Not offered** to a Focus varying fewer than two factors.
- **Not Applicable** when fewer than two of the Focus's treatments hold individuals after exclusions.
- It does **not** need a full crossing. An empty cell is just a missing point.
- **Left Out** when unticked.

## See also

- [Faceted Kaplan-Meier](help:plot-km-faceted)
- [The Cox factorial model](help:cox-factorial)
- [The RMST factorial model](help:rmst-factorial)
- [Interaction analyses (Factorial Battery)](help:analysis-interaction)
- [Focus Shape — what a Focus is offered](help:focus-shape)
