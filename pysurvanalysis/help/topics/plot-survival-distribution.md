# Lifespan distribution

The lifespan-distribution figure shows the **spread of individual lifespans** in each treatment as violin plots: their shape, middle and range. Survival curves show only the cumulative picture. This figure shows whether deaths cluster at one age, spread widely, or fall into two groups. It is in the Standard Lifespan Plot Set and offered to every Focus.

## In the app

- **Plots panel:** the **Lifespan distribution** checkbox (plot id `survival_distribution`). Its caption reads "Distribution of individual lifespans by treatment — recorded deaths only; censored individuals are excluded, since their lifespan is unknown."
- **Plot Editor:** `survival_distribution`. There it is drawn as density curves (see below).

## Which individuals are included

**Only recorded deaths**, in both versions of the figure. A censored individual's lifespan is unknown: the age it was last seen is a lower bound, not a lifespan. Under the default censoring policy, individuals unaccounted for at the last census are censored at that age, so including them would pile weight at the end of the experiment. With heavy censoring the figure therefore describes the individuals whose deaths were seen, which may be the shorter-lived part of the cohort. For censoring-aware medians, see [Summary statistics, median and mean survival](help:survival-summary).

## What is drawn (analysis figure)

- **One violin per treatment**, side by side, in the Focus's order and labelled with its display names. Each violin is filled with that treatment's colour at 70% opacity: the Focus's colour, or the fixed colour cycle in Focus order.
- Each violin shows a kernel density of the treatment's death ages (matplotlib's `violinplot`), with black bars marking the **median**, the minimum and the maximum. The median is the plain median of the death ages, **not** the Kaplan-Meier median.
- If any treatment has one recorded death or fewer, the figure falls back to **box plots** for all treatments (box = quartiles, line = median, whiskers and outlier points in matplotlib's default style).
- **x axis:** "Treatment", with labels slightly rotated.
- **y axis:** `Lifespan — <time label>`, for example "Lifespan — Age (days)".
- Title "Lifespan Distribution". The width grows with the number of treatments.

## The Publication Figure version

In the Plot Editor and in rendered Publication Figures, `survival_distribution` is drawn as one smoothed **density curve** per treatment (plotnine `geom_density`), overlaid on one axis, with the area filled at the Style's **Band opacity**. The **x axis** is lifespan and the **y axis** "Density". It uses the same individuals as the analysis figure: recorded deaths only.

## Reading it

- A **narrow, tall** violin means lifespans are tightly clustered. A **long, thin** one means a few individuals lived much longer or died much earlier than the rest.
- **Two bulges** in one violin suggest a mixed population, such as an early die-off followed by normal ageing.
- Compare medians by eye, but test differences with the [log-rank tests](help:analysis-logrank-pairwise). For censoring-aware medians, see [Summary statistics, median and mean survival](help:survival-summary).

## Where it appears

- File: `analysis/<focus>/plots/survival_distribution_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `survival_distribution` is curated in the Plot Editor.

## When it is not drawn

It has no requirement. Every Focus is offered it, and it is missing only when unticked (**Left Out**).

## See also

- [Summary statistics, median and mean survival](help:survival-summary)
- [Kaplan-Meier curves](help:plot-km-curves)
- [Censoring policy](help:censoring)
- [Lifespan interaction plot](help:plot-interaction-lifespan)
