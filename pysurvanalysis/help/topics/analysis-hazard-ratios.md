# Pairwise hazard ratios

A hazard ratio (HR) says how much faster one treatment dies than another. HR = 2 means that, at any age, an individual of the first group has twice the risk of dying of one in the second. The app estimates an HR with a 95% confidence interval for every pair of treatments in the Focus. These are the numbers the [Hazard-ratio forest](help:plot-hazard-ratio-forest) draws.

## In the app

On the Analyze panel, tick **Pairwise hazard ratios** and click **Run analysis**. The checkbox is offered when the Active Focus implies two or more treatments. If fewer than two treatments hold individuals, the run records "Survival comparisons" as Not Applicable.

The analysis id for `omit:` is `hazard_ratios`. **Unticking it also leaves out the hazard-ratio forest**, because the forest has nothing else to draw. When only the plots are regenerated (**Generate plots**), the hazard ratios are recomputed for the forest if it is ticked.

## What is computed

The estimate is the **log-rank observed/expected (O/E) hazard ratio**, computed by the app's own code from the same quantities as the [log-rank test](help:analysis-logrank-pairwise). It is not fitted by a Cox regression. For treatments A (`group1`) and B (`group2`), at each distinct death time of the pair:

```
O_A = Σ dA         E_A = Σ nA · d / n
O_B = Σ dB         E_B = Σ nB · d / n

HR         = (O_A / E_A) / (O_B / E_B)
SE(log HR) = √(1/E_A + 1/E_B)
95% CI     = exp( log HR ± 1.96 · SE )
```

Here n is the number at risk in both groups together, and d the deaths in both. The HR is reported as missing when E_A, E_B or O_B is zero.

- **Direction.** `group1` is the numerator. HR > 1 means group1 has the higher hazard: it dies faster and lives shorter than group2. HR < 1 means group1 lives longer.
- **Which group is group1.** Within each pair, group1 is the treatment that comes earlier in the Focus's display order (the order of its levels), never the alphabetically first label. It is not necessarily the Reference Level: reordering the levels in the Focus window changes which treatment is group1. The report's table caption says so. To read a pair the other way round, take 1/HR and swap and invert the CI limits.
- **No p-value and no adjustment.** The table has no p-value column, and the confidence intervals are ordinary (unadjusted) 95% intervals for each pair. With many pairs, some intervals will exclude 1 by chance. For a test of each pair, use the [log-rank table](help:analysis-logrank-pairwise), which carries a Bonferroni-adjusted p-value.
- **Unadjusted.** Each HR compares two treatments on their own, ignoring the rest of the design. For effects of each factor relative to its Reference Level, with interactions, see [The Cox factorial model](help:cox-factorial).

## Reading the results

Saved as `analysis/<focus>/statistics/hazard_ratios_<focus>.csv`, one row per pair:

| Column | Meaning |
|---|---|
| `group1` | Numerator treatment (earlier in the Focus's order) |
| `group2` | Denominator treatment |
| `hazard_ratio` | O/E hazard ratio of group1 relative to group2, to 4 decimals |
| `hr_ci_lo` | Lower 95% confidence limit |
| `hr_ci_hi` | Upper 95% confidence limit |

An interval that excludes 1 (both limits above 1, or both below) shows a difference at roughly the 5% level for that pair on its own. Because the scale is multiplicative, HR = 0.5 is as large an effect as HR = 2.

## Where it appears

- The CSV above.
- The report's "Survival comparisons" section, as the **Pairwise hazard ratios** table.
- The [Hazard-ratio forest](help:plot-hazard-ratio-forest) figure, one line per pair.

## When it is not offered

The same as the other comparisons: not offered to a single-treatment Focus, and Not Applicable when fewer than two treatments hold individuals.

## Pitfalls

- **One number assumes proportional hazards.** A single HR summarises the whole lifespan only if the ratio of hazards stays roughly constant with age. If the KM curves cross or converge, the HR is an average of an effect that changes with age. Check the [Log-log diagnostic](help:plot-log-log) and [Checking proportional hazards](help:ph-check), and consider [RMST](help:rmst-factorial) as a summary that does not need the assumption.
- **The O/E estimate is approximate.** It agrees closely with a Cox estimate when the effect is modest, but it can differ for large effects or very unequal censoring. For publication-grade HRs, fit a Cox model.
- **Independence.** Like the tests, the CI treats individuals as independent and ignores chamber clustering, so it can be too narrow.

## See also

- [Hazard-ratio forest](help:plot-hazard-ratio-forest)
- [Log-rank pairwise](help:analysis-logrank-pairwise)
- [The Cox factorial model](help:cox-factorial)
- [Checking proportional hazards](help:ph-check)
- [Reading p-values and multiple comparisons](help:p-values)
