# Kaplan-Meier curves

The Kaplan-Meier (KM) figure draws one survival curve per treatment of the Focus. Each curve shows the estimated fraction of individuals still alive at each age. A shaded band shows the 95% confidence interval, and tick marks show where individuals were censored. This is the basic survivorship figure and appears in the Standard Lifespan Plot Set for every Focus.

## In the app

- **Plots panel:** the **Kaplan-Meier curves** checkbox (plot id `km_curves`). Tick it and click **Generate plots**, or let **Run analysis** draw it.
- **Scripts:** the **KM curves** action draws the same figure. You can pick treatments, turn the CI band off, or switch to the at-risk-table version.
- **Plot Editor:** `km_curves` is the figure to curate for publication. There the at-risk counts are a Style option, so this one Spec stands in for both KM figures. See [Publication Figures, Specs and Styles](help:publication-figures).

## What is drawn

- **x axis:** age, from 0, labelled with your configured time label: `global: time_label`, or `Age (<time_unit>)` (for example "Age (days)"). The numbers are in your data's own unit.
- **y axis:** "Survival Probability", from 0 to 1.
- **One step curve per treatment**, starting at S(0) = 1 and dropping at every age where deaths were recorded.
- **95% CI band:** a shaded staircase around each curve.
- **Censor ticks:** a short vertical mark "|" on the curve at every age where at least one individual was censored.
- **Legend:** the treatments in the **Focus's order**, labelled with its display names. Each curve takes the colour the Focus gives it (its `colours:`, set in the Focus window or the Plot Editor). A treatment without one takes the fixed 12-colour cycle by its position in the Focus's order, so it keeps the same colour in every figure of the Focus, Publication Figures and [Defined Plots](help:defined-plots) included.
- **Size and title:** 10 × 6 inches, titled "Kaplan–Meier Survival Curves", with a light grid.

## How it is computed

The curves come from the Focus's lifetable (`lifetables_<focus>.csv`), computed separately for each treatment and pooled over chambers:

```
Ŝ(t) = ∏ over observed times tᵢ ≤ t of (1 − dᵢ/nᵢ)
```

where dᵢ is the number of deaths at age tᵢ and nᵢ is the number at risk just before tᵢ. Every distinct observed age (a death or a censoring) is a row of the lifetable.

The confidence band is the **log-log** ("exponential Greenwood") interval, built from Greenwood's sum on the log(−log) scale:

```
σ(t)  = √( Σ dᵢ / (nᵢ (nᵢ − dᵢ)) ) / |ln Ŝ(t)|
CI    = [ Ŝ(t)^exp(+1.96·σ),  Ŝ(t)^exp(−1.96·σ) ]
```

It always lies inside [0, 1] and is asymmetric where survival is near either end, which is where a plain ±1.96·SE interval would have to be clipped. It is the interval lifelines reports, computed in the app's own lifetable code. See [Life tables and the Kaplan-Meier estimator](help:lifetables) for the full lifetable.

Whether individuals unaccounted for at the final census count as censored depends on the [Censoring policy](help:censoring).

## Reading it

- The **vertical drop** at an age is the fraction of the remaining cohort that died then.
- The **median lifespan** is the age where a curve crosses 0.5.
- **Curves that separate early and stay apart** suggest a consistent difference in risk. **Curves that cross** suggest the hazards are not proportional; check the [Log-log diagnostic](help:plot-log-log).
- **Overlapping bands** are a visual guide only. Use the [log-rank tests](help:analysis-logrank-pairwise) to judge differences.
- **Wide bands at old ages** reflect the few individuals still at risk.

## Where it appears

- File: `analysis/<focus>/plots/kaplan_meier_<focus>.png` (150 dpi).
- The experiment report's figures section, titled "Kaplan-Meier curves". If `km_curves` is curated in the Plot Editor, the report shows the curated figure instead, and it also replaces the at-risk-table version.

## When it is not drawn

This figure has no requirement, so every Focus is offered it, even a single-treatment one. It is missing only when it is unticked (**Left Out**).

## See also

- [KM curves with at-risk table](help:plot-km-risk-table)
- [Faceted Kaplan-Meier](help:plot-km-faceted)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [Summary statistics, median and mean survival](help:survival-summary)
- [The Plots panel and Generate plots](help:plots-panel)
