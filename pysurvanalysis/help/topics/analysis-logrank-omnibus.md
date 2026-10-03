# Log-rank omnibus

The omnibus log-rank test asks one question about the whole Focus: do *any* of the treatments' survival curves differ? It is the K-sample extension of the log-rank test. It gives a single χ² and p-value for all treatments together, so it is the natural first look before you go through the pairwise comparisons.

## In the app

On the Analyze panel, tick **Log-rank omnibus** and click **Run analysis**. The checkbox is offered when the Active Focus implies two or more treatments. If fewer than two treatments contain individuals, the run records "Survival comparisons" as Not Applicable.

The analysis id for `omit:` is `logrank_omnibus`. In Experiment Scripts, the `log_rank_omnibus` action runs the same test and prints the result to the log.

## What is computed

The test is the app's own implementation; the p-value comes from SciPy's χ² distribution. With K treatments, at every distinct death time t in the Focus:

- nₖ is the number at risk in treatment k (time ≥ t), and N = Σ nₖ.
- dₖ is the deaths in treatment k at t, and D = Σ dₖ.
- The expected deaths are eₖ = nₖ · D / N.

The observed-minus-expected deaths are summed over time for K − 1 of the treatments (one is redundant, because the O − E values sum to zero over all K). Their covariance matrix V is also summed over time:

```
Vᵢᵢ += nᵢ (N − nᵢ) D (N − D) / (N² (N − 1))
Vᵢⱼ −= nᵢ nⱼ D (N − D) / (N² (N − 1))      i ≠ j
χ²   = (O − E)ᵀ V⁻¹ (O − E)      on K − 1 degrees of freedom
p    = P(χ²_{K−1} ≥ χ²)
```

Times with one or no individuals at risk, or with no deaths, are skipped. If V cannot be inverted (for example, no deaths at all), the app reports χ² = 0 and p = 1.

This is a single test, so **no multiple-comparison adjustment** applies to it.

## Reading the results

| Value | Meaning |
|---|---|
| χ² | The omnibus log-rank statistic, rounded to 4 decimals |
| df | K − 1, one less than the number of treatments |
| p | Probability of a χ² at least this large if all treatments had the same hazard |

A small p (below 0.05) says that at least one treatment's survival differs from the rest. It does not say which one: use [Log-rank pairwise](help:analysis-logrank-pairwise) for that. With exactly two treatments, the omnibus test is the same as the single pairwise test.

## Where it appears

- **Report cover.** A status line reads "Omnibus log-rank: treatments differ (p = …)" when p < 0.05, or "no overall difference detected" otherwise.
- **Report, "Survival comparisons" section.** The **Overall comparison** table has columns Test, χ², df, p and a significance marker (`***` p < 0.001, `**` p < 0.01, `*` p < 0.05, `ns` otherwise). p-values below 0.0001 are shown as `<0.0001`.
- **Run Summary.** The `omnibus_lr` entry of `analysis/<focus>/run_summary_<focus>.json` holds `chi2`, `p_value`, `df` and `groups`, the treatment labels tested, in the Focus's display order. The Project Report and the Hub read it from there.

There is no separate CSV for the omnibus test.

## When it is not offered

- A single-treatment Focus is not offered any comparison.
- A Focus that implies two or more treatments but has fewer than two populated records "Survival comparisons" as Not Applicable.

## Pitfalls

- **Many treatments dilute one difference.** If a Focus has eight treatments and only one differs, the omnibus test spreads that one difference over 7 df and may miss it. A pairwise test, or a narrower Focus, can find it.
- **The proportional-hazards caveat applies here too.** Curves that cross can cancel out. Check the KM curves and the [Log-log diagnostic](help:plot-log-log).
- **No structure.** The test treats the treatments as unordered categories. It does not use the factorial layout: a 2×2 is tested as four unrelated groups. To separate main effects from an interaction, use the [Interaction analyses](help:analysis-interaction).

## See also

- [Log-rank pairwise](help:analysis-logrank-pairwise)
- [Reading p-values and multiple comparisons](help:p-values)
- [Interaction analyses (Factorial Battery)](help:analysis-interaction)
- [The Run Summary](help:run-summary)
- [The experiment report](help:experiment-report)
