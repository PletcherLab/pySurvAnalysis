# Cumulative deaths

The cumulative-deaths figure shows mortality building up over age for each treatment, as the **cumulative probability of death**, 1 − Ŝ(t). It is the mirror image of the [Kaplan-Meier curves](help:plot-km-curves): where a KM curve falls from 1, this one rises from 0. It is in the Standard Lifespan Plot Set and offered to every Focus.

## In the app

- **Plots panel:** the **Cumulative deaths** checkbox (plot id `cumulative_events`). Its caption reads "Cumulative probability of death, 1 − S(t) from the Kaplan-Meier estimate (so censoring-aware), with its 95% band."
- **Plot Editor:** `cumulative_events`, with the confidence band and point options available.

## What is computed

For each treatment, from the Kaplan-Meier estimate Ŝ(t) in the Focus's lifetable (column `km_lx`):

```
F(t)  = 1 − Ŝ(t)
band  = [1 − upper KM limit, 1 − lower KM limit]
```

The band is the KM confidence band reflected (see [Life tables and the Kaplan-Meier estimator](help:lifetables)). Because it is built on the KM estimate, it accounts for censoring: it estimates the fraction of the cohort that would have died by age t. A raw count of deaths would not. It falls short wherever individuals were censored, and it grows with group size, so treatments of different sizes could not be compared on it. The analysis figure and the Publication Figure draw the same quantity.

## What is drawn

- **x axis:** age from 0, labelled with your configured time label (for example "Age (days)", from `global: time_label` or `time_unit`).
- **y axis:** "Cumulative probability of death", from 0 to 1.
- **One rising step curve per treatment**, starting at 0, with a shaded 95% band.
- Treatments in the Focus's order, with the Focus's display names and colours (the fixed colour cycle, in Focus order, for any treatment without one).
- Legend at upper left. Title "Cumulative Deaths (1 − S(t))", 10 × 6 inches.

In the Plot Editor the y axis has fixed breaks at 0, 0.25, 0.5, 0.75 and 1, and a new Spec starts with the 0.5 reference line ticked, as on the KM figures.

## Reading it

- A steep rise marks ages of heavy mortality.
- The age where a curve crosses 0.5 is the median lifespan.
- The final height is the estimated fraction that died by the last observed age, not a count of deaths.

## Where it appears

- File: `analysis/<focus>/plots/cumulative_events_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `cumulative_events` is curated in the Plot Editor.

## When it is not drawn

It has no requirement. Every Focus is offered it, and it is missing only when unticked (**Left Out**).

## See also

- [Kaplan-Meier curves](help:plot-km-curves)
- [Nelson-Aalen cumulative hazard](help:plot-nelson-aalen)
- [Publication Figures, Specs and Styles](help:publication-figures)
- [The Plots panel and Generate plots](help:plots-panel)
