# The RMST factorial model

The RMST factorial model is the companion to the [Cox factorial model](help:cox-factorial) in the [Factorial Battery](help:analysis-interaction). It fits the same factorial design (main effects plus every pairwise interaction, relative to the Reference Levels), but on the **restricted mean survival time (RMST)**: the average lifespan up to a cut-off age τ. Its coefficients are differences in mean lifespan, in your time unit, and it **does not assume proportional hazards**. Use it when the Cox model's PH check fails, or whenever "days of life gained" is easier to explain than a hazard ratio.

## In the app

Tick **Interaction analyses** on the Analyze panel and click **Run analysis**. The RMST model is fitted alongside the Cox model. It has the same requirement: the Focus must vary two or more factors, every pair fully crossed. In a full run, τ is always chosen automatically.

In an Experiment Script, the `rmst_interaction` step fits this model on its own under the step's Focus. Its **τ** parameter lets you set the restriction time yourself (0 = automatic). Its results go to the log. After a `run_analysis` step, the refitted model also **replaces** the run's RMST model, so a later `report` step shows it once, with the τ the step used.

## What is computed

This is the pseudo-value regression method (Andersen and colleagues). It turns a censored outcome into one number per individual, which can then go into an ordinary regression.

**1. Choose τ.** By default, τ is the smallest of the treatments' last observed times: τ = min over treatments of (the largest time, death or censoring, in that treatment). Every treatment is therefore followed for at least τ. This is the same rule as the `restriction_time` in the [Mean survival](help:survival-summary) table, and on the same data it gives the same τ. The report prints the τ used on the model line and in a sentence under it, and the Run Summary records it as `tau`.

**2. RMST of the whole Focus.** θ is the area under the Kaplan-Meier curve of **all individuals in the Focus pooled**, from 0 to τ. The curve is a step function, flat between death times, and the area is computed exactly: each step's height times its width, with the last step cut off at τ itself (the same calculation as the Mean survival table, and the same number as lifelines' `restricted_mean_survival_time`).

**3. Jackknife pseudo-values.** For each individual i, θ₋ᵢ is recomputed with that individual left out, and

```
pseudoᵢ = n · θ − (n − 1) · θ₋ᵢ
```

Pseudo-values average to the RMST of the group they come from, and censored individuals get sensible values without being treated as deaths.

**4. Regression.** The pseudo-values are regressed on the factorial design with ordinary least squares (**statsmodels** `OLS`), with an intercept, and with **heteroskedasticity-robust (HC1) standard errors**:

```
pseudoᵢ = β₀ + Σ β·(main-effect dummies) + Σ β·(interaction dummies) + error
```

z-statistics, two-sided p-values and 95% confidence intervals use the normal distribution with the robust standard errors. No multiple-comparison adjustment is applied.

## Reading the results

Saved as `analysis/<focus>/statistics/factorial_02_coefficients_<focus>.csv` and shown in the report's **Coefficients** table under **RMST factorial model**:

| Column | Meaning |
|---|---|
| `covariate` | `const` (intercept), `Factor_level` (main effect) or `A_a:B_b` (interaction) |
| `coef` | Estimate, in the data's time unit |
| `HR`, `HR_lo`, `HR_hi` | Always blank: not applicable to an RMST model (kept so the table matches the Cox table's layout) |
| `se` | Robust (HC1) standard error |
| `z` | coef / se |
| `p_value` | Two-sided p-value for coef = 0, unadjusted |
| `coef_lo`, `coef_hi` | 95% confidence interval for coef |
| `term_type` | `intercept`, `main_effect` or `interaction` |

Interpretation, with Reference Levels wt and AL and time in days:

- `const` = 46: the estimated mean lifespan up to τ in the **reference cell** (wt on AL).
- `Genotype_mut` = +11: on **AL**, mut lives on average 11 days longer than wt, within the window up to τ.
- `Diet_DR` = +14: in **wt**, DR adds 14 days.
- `Genotype_mut:Diet_DR` = −8: the DR benefit is 8 days smaller in mut than in wt (difference of differences). So mut/DR is estimated at 46 + 11 + 14 − 8 = 63 days. An interaction of 0 means the effects add up.

The report highlights coefficient rows whose unadjusted p is below 0.05, except the intercept: its test (is the reference cell's mean lifespan zero?) answers no question anyone asked.

The model line in the report gives n, events, **τ**, **R²** (the share of the pseudo-values' variance the design explains), AIC and the **robust F** test of all terms together, with its p-value. This AIC belongs to the least-squares fit of the pseudo-values: it is not comparable with the Cox model's AIC and has no direct survival interpretation. There is no concordance, no LR interaction test and no PH check for this model. Use the interaction coefficients and their p-values; with more than one interaction term, judge them together.

If statsmodels warns while fitting, the message is listed under the model in a highlighted **RMST factorial model: warnings** table and stored in the model's `warnings` list in the Run Summary.

## Where it appears

- Report, "Factorial analysis" section, under the heading **RMST factorial model**.
- `statistics/factorial_02_coefficients_<focus>.csv`. The RMST model is always model 02.
- Run Summary: `factorial_models[1]` (title, formula, n, events, AIC, Reference Levels, `tau`, `rmst_overall` (θ), `r_squared`, `f_statistic`, `f_p_value` and `warnings`).

## Pitfalls

- **Everything is "up to τ".** The RMST says nothing about survival after τ. If one treatment ends early, τ is short for every treatment, and differences late in life are not seen. Check `restriction_time` in `mean_survival_<focus>.csv`.
- **Main effects are simple effects** at the other factors' Reference Levels, exactly as in the Cox model.
- **Large Focuses take longer.** The jackknife refits the Kaplan-Meier curve once for each distinct (age, died or censored) pair, since leaving out either of two identical individuals gives the same curve. Census data has few distinct ages, so this is usually quick, but a Focus with thousands of distinct exact ages takes noticeably longer.
- **Clustering.** The robust standard errors allow unequal variances, but they do not account for chambers. Individuals are still treated as independent.

## See also

- [Interaction analyses (Factorial Battery)](help:analysis-interaction)
- [The Cox factorial model](help:cox-factorial)
- [Summary statistics, median and mean survival](help:survival-summary)
- [Checking proportional hazards](help:ph-check)
- [Reference Levels](help:reference-level)
