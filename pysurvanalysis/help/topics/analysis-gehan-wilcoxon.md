# Gehan-Wilcoxon pairwise

The Gehan-Wilcoxon test is a weighted log-rank test. Like the log-rank test, it compares observed and expected deaths between two treatments. The difference is that each death time is weighted by the number of individuals still at risk. Early deaths, when many are alive, count for much more than late deaths, when few are left. It therefore picks up differences early in life that the ordinary log-rank test can dilute. The app runs it on every pair of treatments and adds a Bonferroni-adjusted p-value.

## In the app

On the Analyze panel, tick **Gehan-Wilcoxon pairwise** and click **Run analysis**. The checkbox is offered when the Active Focus implies two or more treatments. If fewer than two of those treatments hold individuals, the run records "Survival comparisons" as Not Applicable.

The analysis id for `omit:` is `gehan_wilcoxon`. In Experiment Scripts, the `gehan_wilcoxon` action runs the same tests and prints the table to the log.

## What is computed

The test is the app's own implementation, with the p-value from SciPy's χ² distribution. For treatments A and B, at each distinct death time tⱼ of the pair, with the same notation as the [log-rank test](help:analysis-logrank-pairwise) (nA, nB at risk, d deaths in total, n = nA + nB), the weight is wⱼ = n, the total number at risk:

```
U  = Σ wⱼ · (dA − nA · d / n)
V  = Σ wⱼ² · nA · nB · d · (n − d) / (n² (n − 1))
χ² = U² / V        on 1 degree of freedom
p  = P(χ²₁ ≥ χ²)
```

This is the Gehan (Breslow) generalisation of the Wilcoxon rank-sum test to censored data. If V is 0, the app reports χ² = 0 and p = 1.

**Pairs and ordering.** Every unordered pair is tested once, in the Focus's display order, and `group1` is the treatment that comes earlier in that order (never alphabetical). The result does not depend on which group is group1.

**Multiple comparisons.** As for the log-rank test, the app adds a **Bonferroni** adjustment over all the pairs: p_bonferroni = min(1, p × number of pairs). `significant_0.05` is `True` when the adjusted p is below 0.05. The Gehan-Wilcoxon and log-rank tables are adjusted separately; nothing corrects for running both. See [Reading p-values and multiple comparisons](help:p-values).

## Reading the results

Saved as `analysis/<focus>/statistics/gehan_wilcoxon_pairwise_<focus>.csv`:

| Column | Meaning |
|---|---|
| `group1`, `group2` | The two treatments compared |
| `chi2` | Gehan-Wilcoxon χ² (1 df), rounded to 4 decimals |
| `p_value` | Unadjusted p-value |
| `df` | Always 1 |
| `p_bonferroni` | Bonferroni-adjusted p-value, capped at 1 |
| `significant_0.05` | `True` when p_bonferroni < 0.05 |

Unlike the log-rank table, this table has no observed/expected columns. To see the direction of a difference, look at the KM curves or the hazard ratios.

**Comparing with the log-rank test:**

- Both significant: the curves differ throughout.
- Gehan-Wilcoxon significant, log-rank not: the difference is concentrated early in life, or the curves converge or cross later.
- Log-rank significant, Gehan-Wilcoxon not: the difference is mainly late in life, where the log-rank test gives deaths more relative weight.

## Where it appears

- The CSV above.
- The report's "Survival comparisons" section, as the **Pairwise Gehan-Wilcoxon** table. As with the log-rank table, rows are highlighted when the *Bonferroni-adjusted* p is below 0.05 (the `significant_0.05` rows), and p-values are shown to 4 decimals, or `<0.0001`.

## When it is not offered

The same as the log-rank test: a single-treatment Focus is not offered it, and one with fewer than two populated treatments records "Survival comparisons" as Not Applicable.

## Pitfalls

- **The weights depend on censoring.** The weight is the number at risk, which falls with censoring as well as death. If two treatments have very different censoring patterns, the Gehan weights can distort the comparison.
- **Late differences carry little weight.** By late life few individuals remain, so a big late separation barely moves this test.

## See also

- [Log-rank pairwise](help:analysis-logrank-pairwise)
- [Reading p-values and multiple comparisons](help:p-values)
- [Checking proportional hazards](help:ph-check)
- [Kaplan-Meier curves](help:plot-km-curves)
