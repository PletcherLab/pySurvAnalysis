# Reading p-values and multiple comparisons

A run can produce dozens of p-values: one per treatment pair for two different tests, one per model coefficient, one per PH check. This page explains what each p-value tests, which ones the app adjusts for multiple comparisons (only two tables are), and how the report displays them, so you can judge what is genuinely significant.

## What a p-value means here

A p-value is the probability of seeing a difference at least as large as the one observed if there were really no effect. A p below 0.05 is the conventional threshold for "statistically significant". It says nothing about how large or important an effect is. Read it alongside the effect size: the hazard ratio, the difference in RMST or median, or the KM curves themselves. All p-values in the app are two-sided, and the threshold is always 0.05; it cannot be changed.

## Which p-values are adjusted

| Analysis | p-value tests | Adjustment |
|---|---|---|
| [Log-rank pairwise](help:analysis-logrank-pairwise) | two treatments' survival curves are equal | **Bonferroni** across all pairs in the table (`p_bonferroni`) |
| [Gehan-Wilcoxon pairwise](help:analysis-gehan-wilcoxon) | the same, weighting early deaths | **Bonferroni** across all pairs in the table (`p_bonferroni`) |
| [Log-rank omnibus](help:analysis-logrank-omnibus) | all treatments are equal | none needed (a single test) |
| [Pairwise hazard ratios](help:analysis-hazard-ratios) | no p-value; 95% CI per pair | none: each CI is an ordinary 95% interval |
| [Cox factorial model](help:cox-factorial), LR interaction | all interaction terms are zero | none needed (a single test) |
| Cox coefficients | each β = 0 (Wald test) | none |
| [RMST factorial model](help:rmst-factorial) coefficients | each coefficient = 0 (robust z-test) | none |
| [Schoenfeld PH check](help:ph-check) | each term's effect is constant with age | none |
| [Parametric AFT models](help:analysis-parametric-aft) | no p-values (models are compared by AIC) | not applicable |

### Bonferroni, as the app applies it

For the two pairwise tables, with m = the number of pairs (k treatments give m = k(k − 1)/2):

```
p_bonferroni = min(1, p × m)
significant_0.05 = p_bonferroni < 0.05
```

The adjustment is made separately within each table. The log-rank and Gehan-Wilcoxon tables are each corrected for their own pairs, but nothing corrects for running both tests, for running several Focuses, or for looking at both the pairwise tables and the factorial models. Bonferroni controls the chance of *any* false positive among the pairs. It is simple and safe but conservative: with many treatments it can miss real differences.

### Unadjusted p-values

For the model coefficients and PH checks, the p-values are as the fitting library reports them (lifelines for Cox, statsmodels for RMST). If you test many coefficients, expect about one in twenty to fall below 0.05 by chance when nothing is going on. You can apply your own correction to the values in the CSV files. Where a single combined test exists, prefer it: the Cox **LR interaction test** answers "is there any interaction?" in one p-value, instead of reading each interaction coefficient separately.

## How p-values are displayed

**In the CSV files** (`analysis/<focus>/statistics/`), p-values are stored at full precision. Use them for anything you publish.

**In the report:**

- **Single-test tables** (the omnibus log-rank "Overall comparison" and the Cox "Interaction (LR, vs main-effects model)" row) show p to 4 decimals, or `<0.0001`, followed by a marker: `***` for p < 0.001, `**` for p < 0.01, `*` for p < 0.05, `ns` otherwise.
- **Multi-row tables** (pairwise log-rank, pairwise Gehan-Wilcoxon, model coefficients, PH check) print p-value columns (`p_value`, `p_bonferroni`) the same way, to 4 decimals or `<0.0001`, so a tiny p-value is never shown as `0.000`. Other numbers are printed to 3 decimals.
- **Row highlighting.** In the pairwise tables, a row is highlighted when its **Bonferroni-adjusted** `p_bonferroni` is below 0.05, so the highlight always agrees with the `significant_0.05` column. In the coefficient tables, which have no adjusted p-value, a row is highlighted when its unadjusted `p_value` is below 0.05 (never the RMST model's intercept row).
- **Report cover.** The omnibus log-rank p-value appears as a status line: "treatments differ" when p < 0.05, "no overall difference detected" otherwise.

## Pitfalls

- **Individuals are treated as independent.** Every test treats each individual as an independent observation. Individuals in the same chamber share conditions, so if chambers differ, the effective sample size is smaller than the number of individuals and p-values are too small. Check chamber consistency in the [Chamber QC viewer](help:qc-viewer).
- **Choosing a Focus after looking at the data** is a hidden multiple comparison. Decide your main comparisons before you look.
- **Non-significant is not "no effect".** With few deaths, real differences can give large p-values. Look at confidence intervals: a wide interval that includes 1 (for an HR) or 0 (for an RMST difference) means the data cannot tell.
- **Very small p-values in large cohorts** can come with tiny effects. Always check the effect size.

## See also

- [Log-rank pairwise](help:analysis-logrank-pairwise)
- [Gehan-Wilcoxon pairwise](help:analysis-gehan-wilcoxon)
- [The Cox factorial model](help:cox-factorial)
- [Checking proportional hazards](help:ph-check)
- [The experiment report](help:experiment-report)
