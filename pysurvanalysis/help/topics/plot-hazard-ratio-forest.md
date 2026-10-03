# Hazard-ratio forest

The forest plot shows every **pairwise hazard ratio** of the Focus on one axis, each with its 95% confidence interval. You can see at a glance which pairs of treatments differ in their risk of death, in which direction and by how much. It draws the table produced by the **Pairwise hazard ratios** analysis.

## In the app

- **Plots panel:** the **Hazard-ratio forest** checkbox (plot id `hazard_ratio_forest`).
- It **draws from Pairwise hazard ratios**. If that box is unticked on the Analyze panel, the forest box is greyed with the tooltip "Draws from Pairwise hazard ratios — tick it on the Analyze panel to draw this figure". Runs then record the forest as **Left Out** ("draws from Pairwise hazard ratios, which is unticked").
- **Generate plots** computes the hazard ratios itself when the forest is ticked, so it does not need a previous run.
- **Scripts:** the **Hazard-ratio forest** action (`forest_plot`).
- **Plot Editor:** `hazard_ratio_forest`. It reads the saved `hazard_ratios_<focus>.csv` from the last run and never computes ratios itself, so run the analysis first.

## What is computed

For every pair of treatments, taken in the Focus's display order (group1 is the one listed earlier), the app estimates the hazard ratio by the **log-rank observed/expected method**. At each observed age, the expected deaths in each group are its share of the at-risk total times the deaths in both groups. Summed over ages:

```
HR      = (O₁ / E₁) / (O₂ / E₂)          group1 is the numerator
SE(log HR) = √(1/E₁ + 1/E₂)
95% CI  = exp( log HR ± 1.96 · SE )
```

O is the observed number of deaths and E the expected number under equal hazards. A pair where the estimate cannot be formed (for example, no deaths in group2) has no ratio and is left off the plot. The table is saved as `statistics/hazard_ratios_<focus>.csv` (columns include `group1`, `group2`, `hazard_ratio`, `hr_ci_lo`, `hr_ci_hi`). See [Pairwise hazard ratios](help:analysis-hazard-ratios).

## What is drawn (analysis figure)

- One row per pair, labelled "group1 vs group2" at the left with the Focus's display names, in table order from top to bottom.
- A **diamond** at the hazard ratio and a horizontal line spanning its 95% CI.
- **Red** where HR > 1 (group1 has the higher hazard) and **blue** where HR ≤ 1.
- The numbers "HR (lower–upper)" to three decimals at the right of each row.
- A dashed vertical line at **HR = 1** (no difference).
- **x axis:** "Hazard Ratio (95% CI)", on a **linear** scale starting at 0.
- Title "Hazard Ratio Forest Plot". The height grows with the number of pairs.

The Publication Figure version uses a **log₁₀ ratio axis**, so 0.5 and 2 sit the same distance from 1. Its rows carry the same display-name labels; it colours each comparison from the Style's cycle and drops any row whose ratio or lower limit is not positive. A new Spec's x label is "Hazard ratio (log scale)".

## Reading it

- **HR > 1:** group1 dies at a higher rate than group2 (shorter-lived). **HR < 1:** group1 dies at a lower rate (longer-lived). HR = 2 means twice the risk of death at any age, if hazards are proportional.
- An interval that **does not cross 1** suggests a difference at about the 5% level for that pair, with no correction for multiple comparisons. For p-values, see the [log-rank pairwise](help:analysis-logrank-pairwise) table and [Reading p-values and multiple comparisons](help:p-values).
- On the linear axis, ratios below 1 are compressed between 0 and 1. A ratio of 0.5 is as large an effect as 2.0.
- The ratio summarises the whole lifespan as one number. If the [Log-log diagnostic](help:plot-log-log) shows crossing lines, the ratio averages effects that change with age.

## Where it appears

- File: `analysis/<focus>/plots/hazard_ratio_forest_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `hazard_ratio_forest` is curated in the Plot Editor.

## When it is offered, Not Applicable or Left Out

- **Not offered** to a Focus that implies only one treatment (it requires a comparison).
- **Not Applicable** when fewer than two of the Focus's treatments hold individuals after exclusions, or when the hazard-ratio table comes out empty ("fewer than two treatments to compare").
- **Left Out** when its own box is unticked, or when **Pairwise hazard ratios** is unticked.

## See also

- [Pairwise hazard ratios](help:analysis-hazard-ratios)
- [Log-log diagnostic](help:plot-log-log)
- [Reading p-values and multiple comparisons](help:p-values)
- [Not Applicable and Left Out](help:not-applicable)
- [The Plots panel and Generate plots](help:plots-panel)
