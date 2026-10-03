# KM curves with at-risk table

This figure shows the Kaplan-Meier survival curves with a **number-at-risk table** underneath: for each treatment, how many individuals were still alive and uncensored at a few ages along the time axis. The counts show how many individuals each part of a curve rests on. For Standard Lifespan this is the **Headline Figure** of any Focus that does not cross factors, so it leads the Focus's report section.

## In the app

- **Plots panel:** the **KM curves with at-risk table** checkbox (plot id `km_risk_table`). It is the first box in the Plot Set.
- **Scripts:** the **KM curves** action with **With risk table** ticked draws the same figure.
- **Plot Editor:** this figure has no Spec of its own. In a Publication Figure the at-risk counts are a Style option (the **At-Risk Band**) on `km_curves`. A Spec saved under the old id `km_risk_table` is loaded as `km_curves`.

## What is drawn

The figure has two stacked panels that share the time axis (12 inches wide, 7 + 0.35 inches per treatment tall).

**Upper panel: the KM curves.** These are the same estimates as [Kaplan-Meier curves](help:plot-km-curves):

- step curves starting at S(0) = 1, with lines slightly thicker than in the plain KM figure;
- 95% log-log (exponential Greenwood) confidence bands;
- "|" censor ticks;
- legend at upper right; y axis "Survival Probability" from 0 to 1;
- treatments in the Focus's order, with its display names and colours (the fixed colour cycle, in Focus order, for any treatment without one).

**Lower panel: "Number at Risk".**

- One row per treatment, in the same order, labelled at the left with its display name. The numbers are coloured like that treatment's curve.
- Counts are printed at **5 ages: 0, 25, 50, 75 and 100% of the last observed age** of the treatments drawn, evenly spaced in time. These are the same ages the publication [At-Risk Band](help:plot-editor-panels) uses by default.
- The count at age t is the **number at risk at t**: the individuals whose recorded age (death or censoring) is t or later, i.e. alive and uncensored entering age t. It is read from the lifetable: the number at risk of the first observed age at or after t. At age 0 this is the starting group size; after a treatment's last observed age it is 0. The publication band counts the same way, with the same code, so the two always agree.
- The x axis is labelled with your configured time label (for example "Age (days)").

## Reading it

- Read a curve together with the count beneath it. A drop late in the experiment, when only a handful are at risk, is a large step for very few deaths.
- Where a treatment's count reaches 0, its curve has no more information. Any later separation between curves is not supported by data.
- Large differences in starting counts between treatments mean their curves are estimated with different precision. The CI bands show this too.

## Headline Figure

The Headline Figure is this figure for any Focus except one that varies two or more factors and populates at least two treatments. For those Focuses the [Faceted Kaplan-Meier](help:plot-km-faceted) takes over. The Headline Figure is placed first in the report's figures section and marked "— headline figure".

## Where it appears

- File: `analysis/<focus>/plots/km_with_risk_table_<focus>.png` (150 dpi).
- The experiment report's figures section. If `km_curves` is curated in the Plot Editor, the report shows that curated figure in place of **both** KM figures.

## When it is not drawn

It has no requirement, so every Focus is offered it. It is missing only when unticked (**Left Out**).

## Pitfalls

- A count printed at an age between two observed ages is the number entering the **next** observed age, because everyone who died or was censored at the earlier one is no longer at risk. A column at an age with a death shows the number **before** that death.

## See also

- [Kaplan-Meier curves](help:plot-km-curves)
- [Number at risk](help:plot-number-at-risk)
- [Plot Editor — Panels & legend](help:plot-editor-panels)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [The experiment report](help:experiment-report)
