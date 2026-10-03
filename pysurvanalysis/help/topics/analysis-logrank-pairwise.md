# Log-rank pairwise

The pairwise log-rank test asks, for each pair of treatments in turn, whether the two survival curves differ. It is the standard Mantel-Cox log-rank test: it compares the deaths seen in each group with the deaths you would expect if both groups shared one hazard, and it weights every death time equally. The app runs it on every pair of treatments in the Focus and adds a Bonferroni-adjusted p-value.

## In the app

On the Analyze panel, tick **Log-rank pairwise** and click **Run analysis**. The checkbox is offered when the Active Focus implies two or more treatments. If fewer than two of those treatments contain individuals (for example, the exclusions emptied one), the run records "Survival comparisons" as Not Applicable, with the reason.

The analysis id for `omit:` is `logrank_pairwise`. In Experiment Scripts, the `log_rank_pairwise` action runs the same test and prints the table to the log.

## What is computed

The test is the app's own implementation; it does not call lifelines, and the p-value comes from SciPy's χ² distribution. For a pair of treatments A and B, take every distinct time at which at least one individual of A or B died. At each such time tⱼ:

- nA, nB are the numbers at risk in each group (individuals whose time is ≥ tⱼ, so those censored at tⱼ are still at risk), with n = nA + nB.
- dA, dB are the deaths at tⱼ, with d = dA + dB.

Then:

```
O_A = Σ dA                                   observed deaths in A
E_A = Σ nA · d / n                           expected deaths in A
V   = Σ nA · nB · d · (n − d) / (n² (n − 1))  hypergeometric variance
χ²  = (O_A − E_A)² / V        on 1 degree of freedom
p   = P(χ²₁ ≥ χ²)
```

Ties (several deaths at the same census time) are handled by the hypergeometric variance above. Times with only one individual at risk add nothing to V. If V is 0 (for example, no deaths at all), the app reports χ² = 0 and p = 1.

**Which pairs.** Every unordered pair of treatments is tested once: k treatments give k(k − 1)/2 tests. Pairs follow the Focus's display order (the order of its levels, never alphabetical), and within each pair `group1` is the treatment that comes earlier in that order. The χ² and p-value do not depend on which group is called group1.

**Multiple comparisons.** The app adds a **Bonferroni** adjustment over all the pairs in the table: p_bonferroni = min(1, p × number of pairs). The `significant_0.05` column is `True` when the *adjusted* p-value is below 0.05. See [Reading p-values and multiple comparisons](help:p-values).

## Reading the results

Saved as `analysis/<focus>/statistics/logrank_pairwise_<focus>.csv`, one row per pair:

| Column | Meaning |
|---|---|
| `group1`, `group2` | The two treatments compared (group1 earlier in the Focus's order) |
| `observed_1` | O: observed deaths in group1 |
| `expected_1` | E: deaths expected in group1 if the two groups had the same hazard |
| `chi2` | Log-rank χ² statistic (1 df), rounded to 4 decimals |
| `p_value` | Unadjusted p-value |
| `df` | Degrees of freedom (always 1) |
| `p_bonferroni` | Bonferroni-adjusted p-value, capped at 1 |
| `significant_0.05` | `True` when p_bonferroni < 0.05 |

**Direction.** The test has no sign, but `observed_1` and `expected_1` tell you which way the difference goes. If group1 has more deaths than expected (O > E), group1 dies faster than group2. If it has fewer (O < E), group1 lives longer. For a size of effect, see [Pairwise hazard ratios](help:analysis-hazard-ratios).

## Where it appears

- The CSV above.
- The report's "Survival comparisons" section, as the **Pairwise log-rank** table, with the same columns. Rows are highlighted when the *Bonferroni-adjusted* `p_bonferroni` is below 0.05, exactly the rows where `significant_0.05` is `True`. p-values are shown to 4 decimals, or `<0.0001`; other numbers to 3 decimals. Use the CSV for exact values.
- The run log, when it is run as a script action.

## When it is not offered

- A single-treatment Focus is not offered any comparison.
- A Focus that implies two or more treatments but has fewer than two populated records "Survival comparisons" as Not Applicable.

## Pitfalls

- **Crossing curves.** The log-rank test is most powerful when one group's hazard is a constant multiple of the other's (proportional hazards). If the curves cross, early and late differences can cancel out and the test can miss a real difference. Look at the KM curves and the [Log-log diagnostic](help:plot-log-log), and compare with [Gehan-Wilcoxon](help:analysis-gehan-wilcoxon), which weights early deaths more.
- **Bonferroni is conservative** when there are many treatments. With 6 treatments there are 15 pairs, so each raw p-value is multiplied by 15.
- **Individuals, not chambers.** The test treats every individual as independent and pools chambers within a treatment. Strong chamber effects make p-values look more convincing than they are.

## See also

- [Log-rank omnibus](help:analysis-logrank-omnibus)
- [Gehan-Wilcoxon pairwise](help:analysis-gehan-wilcoxon)
- [Pairwise hazard ratios](help:analysis-hazard-ratios)
- [Reading p-values and multiple comparisons](help:p-values)
- [Kaplan-Meier curves](help:plot-km-curves)
