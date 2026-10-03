# Log-log diagnostic

The log-log diagnostic is a visual check of the **proportional-hazards (PH)** assumption behind the hazard ratios and the Cox models. For each treatment it plots log(−log Ŝ(t)) against log(t). If the hazards are proportional, the curves are **parallel**, separated by a constant vertical distance.

## In the app

- **Plots panel:** the **Log-log diagnostic** checkbox (plot id `log_log`). Its caption reads "Parallel lines support the proportional-hazards assumption."
- **Plot Editor:** `log_log`. The x label defaults to `log(<time label>)`.

## What is computed

From each treatment's Kaplan-Meier estimate Ŝ(t) (the lifetable column `km_lx`):

```
x = ln(t)
y = ln(−ln Ŝ(t))
```

Logarithms are natural logs. Only ages where t > 0 and 0 < Ŝ(t) < 1 are used, because the transform is infinite at Ŝ = 1 (before the first death) and at Ŝ = 0 (after the last). A treatment with fewer than two such points is not drawn.

## What is drawn

- **x axis:** `log(<time label>)`, for example "log(Age (days))": the natural log of age in your data's time unit.
- **y axis:** "log(−log S(t))".
- One line with small markers per treatment, joining the transformed KM values. Treatments are in the Focus's order, with its display names and colours (the fixed colour cycle, in Focus order, for any treatment without one).
- In the Plot Editor the values are joined with straight lines too, by default (**Line style** `auto`).
- A dashed grey horizontal line at y = 0. This is where Ŝ(t) = e⁻¹ ≈ 0.37.
- Title "Log(−log S(t)) vs Log(t) — PH Assumption Check", 10 × 6 inches.

## Reading it

- **Roughly parallel lines** support proportional hazards: one treatment's hazard is a constant multiple of the other's at every age. The vertical gap is approximately the log hazard ratio.
- **Lines that converge, diverge or cross** suggest the hazard ratio changes with age, for example a treatment that protects early but not late. Hazard ratios and Cox coefficients then describe an average effect. The [log-rank test](help:analysis-logrank-pairwise) loses power, and the [Gehan-Wilcoxon](help:analysis-gehan-wilcoxon) test or [RMST](help:rmst-factorial) may describe the difference better.
- **Straight lines** suggest a Weibull distribution of lifespans. The slope is the Weibull shape parameter. See [Parametric AFT models](help:analysis-parametric-aft).
- The early part of each line rests on very few deaths and is noisy. Judge parallelism over the bulk of the data.

This is a visual check. For a formal test of PH in a factorial Focus, see [Checking proportional hazards](help:ph-check).

## Where it appears

- File: `analysis/<focus>/plots/log_log_diagnostic_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `log_log` is curated in the Plot Editor.

## When it is offered, Not Applicable or Left Out

This figure **requires a comparison between treatments**:

- **Not offered** to a Focus that implies only one treatment. There is nothing to compare, so the box does not appear.
- **Not Applicable** when the Focus implies two or more treatments but fewer than two hold individuals after exclusions. The box is greyed with the reason, and a run records it under "Not applicable to this Focus".
- **Left Out** when unticked.

## See also

- [Checking proportional hazards](help:ph-check)
- [Pairwise hazard ratios](help:analysis-hazard-ratios)
- [Nelson-Aalen cumulative hazard](help:plot-nelson-aalen)
- [Kaplan-Meier curves](help:plot-km-curves)
- [Focus Shape — what a Focus is offered](help:focus-shape)
