# Mortality (qx)

The mortality figure plots **qx**, the probability of dying in each interval, against age for every treatment. It is the classic demographic view of a life table. It is in the Standard Lifespan Plot Set and offered to every Focus.

## In the app

- **Plots panel:** the **Mortality (qx)** checkbox (plot id `mortality`). Its caption reads "Interval mortality probability."
- **Scripts:** the **Mortality (qx)** action.
- **Plot Editor:** `mortality`, labelled "Mortality (qx)" on the y axis.

## What is computed

The lifetable has one row per distinct observed age (an age at which at least one death or censoring was recorded) for each treatment, pooled over chambers. At each row:

```
qx = dx / nx
```

where dx is the number of deaths at that age and nx is the number alive and uncensored just before it. This is the lifetable column `qx` in `lifetables_<focus>.csv`. In a census design, each row normally corresponds to one census, so qx is the fraction of the survivors that died since the previous census.

qx is a probability **per interval**, not per unit time. It depends on the gap between observed ages. If censuses are irregular, a longer gap gives a larger qx at the same underlying death rate. For a rate per unit time, see the [Hazard rate](help:plot-hazard) and [Smoothed hazard](help:plot-smoothed-hazard).

## What is drawn

- **x axis:** age from 0, labelled with your configured time label (for example "Age (days)").
- **y axis:** "Probability of Death (qx)", from 0.
- One line with small dot markers per treatment, joining the per-row qx values. It is not smoothed. Treatments are in the Focus's order, with its display names and colours (the fixed colour cycle, in Focus order, for any treatment without one).
- Title "Interval Mortality (qx)", 10 × 6 inches.

## Reading it

- qx usually rises with age in an ageing cohort.
- **Late points are noisy.** When only a few individuals remain, one death can give qx = 0.5 or 1.0. The last row of a treatment in which everyone died has qx = 1.
- Rows with censoring but no deaths have qx = 0. These pull the line to the axis between deaths, which is common when censoring happens at times other than deaths.
- For a smoother view of the same information, use the [Smoothed hazard](help:plot-smoothed-hazard).

## Where it appears

- File: `analysis/<focus>/plots/mortality_qx_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `mortality` is curated in the Plot Editor.

## When it is not drawn

It has no requirement. Every Focus is offered it, and it is missing only when unticked (**Left Out**).

## See also

- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [Hazard rate](help:plot-hazard)
- [Smoothed hazard](help:plot-smoothed-hazard)
- [Number at risk](help:plot-number-at-risk)
- [The Plots panel and Generate plots](help:plots-panel)
