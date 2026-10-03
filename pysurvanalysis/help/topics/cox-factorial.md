# The Cox factorial model

The Cox factorial model is the hazard-ratio half of the [Factorial Battery](help:analysis-interaction). It fits a Cox proportional-hazards regression with every varying factor of the Focus and every pairwise interaction between them. It reports each term as a hazard ratio relative to the Reference Levels, tests whether the interactions are needed with a likelihood-ratio test, and checks the proportional-hazards assumption term by term.

## In the app

Tick **Interaction analyses** on the Analyze panel and click **Run analysis**. This fits the Cox model together with the [RMST factorial model](help:rmst-factorial). It is offered only when the Active Focus varies two or more factors, and it is computed only when every pair of them is fully crossed in the data. Otherwise the battery is recorded as Not Applicable. In an Experiment Script, the `cox_interaction` step fits it on its own and writes the formula, the LR test and the coefficients to the log.

The baseline of each factor is its **Reference Level**, set in the [Focus window](help:focus-window) or with `reference:` in the Focus's config:

```yaml
focuses:
  Genotype x Diet:
    factors:
      Genotype: [wt, mut]
      Diet: [AL, DR]
    reference:
      Diet: AL
```

A factor with no `reference:` entry uses its first listed level. See [Reference Levels](help:reference-level).

## What is computed

Two Cox models are fitted with the **lifelines** library (`CoxPHFitter`, default settings: no penalty, Efron's method for tied death times) to every individual in the Focus:

1. **Main-effects model**: the dummy-coded factors only.
2. **Interaction model**: the main effects plus every pairwise interaction term (see [the model design](help:analysis-interaction)).

The model for an individual's hazard at age t is

```
h(t) = h₀(t) · exp( β₁x₁ + β₂x₂ + … )
```

where h₀(t) is an unspecified baseline hazard (the hazard of the reference cell) and the x are the 0/1 dummies. **All reported coefficients come from the interaction model.**

**The LR interaction test** compares the two models:

```
LR = 2 · (log L_interaction − log L_main)
df = number of interaction terms
p  = P(χ²_df ≥ LR)
```

It asks whether all the interaction terms together significantly improve the fit. It is one test, so no adjustment is applied. If the design has no interaction terms, the test is not produced.

**The proportional-hazards check** runs a Schoenfeld-residual test on each term of the interaction model; see [Checking proportional hazards](help:ph-check).

## Reading the results

### Model line

The report gives **n** (individuals), **events** (deaths), **concordance** (Harrell's C of the interaction model: the probability that, of two individuals, the model ranks the one that died first as higher-risk; 0.5 is chance, 1 is perfect) and **AIC** (the partial-likelihood AIC of the interaction model, −2 log L + 2 × number of terms). The formula lists every term, for example `Genotype_mut + Diet_DR + Genotype_mut:Diet_DR`.

### Interaction test

The report's interaction table has the row "Interaction (LR, vs main-effects model)", with χ², df, p and a significance marker. The statistic is recorded as `statistic` in the Run Summary, under `factorial_models` → `lr_interaction`, together with `df`, `p_value`, the two log-likelihoods (`ll_main`, `ll_interaction`) and the main-effects model's concordance (`concordance_main`). The same value is also kept under its older name `lr_stat`, so tools written against earlier Run Summaries still find it.

### Coefficients

Saved as `analysis/<focus>/statistics/factorial_01_coefficients_<focus>.csv` and shown in the report's **Coefficients** table, whose caption names the Reference Levels:

| Column | Meaning |
|---|---|
| `covariate` | The term: `Factor_level` (main effect) or `A_a:B_b` (interaction) |
| `coef` | β, the log hazard ratio |
| `HR` | exp(β), the hazard ratio |
| `se` | Standard error of β |
| `coef_lo`, `coef_hi` | 95% Wald confidence interval for β (β ± 1.96 · se) |
| `HR_lo`, `HR_hi` | The same interval on the hazard-ratio scale |
| `z` | Wald statistic, β / se |
| `p_value` | Two-sided Wald p-value for β = 0, unadjusted |
| `-log2(p)` | The p-value as "bits of evidence against the null" (lifelines' S-value) |
| `term_type` | `main_effect` or `interaction` |

Interpretation, with references wt and AL:

- `Genotype_mut` HR = 0.6: on the **AL** diet, mut flies have 40% lower hazard than wt.
- `Diet_DR` HR = 0.5: in **wt** flies, DR halves the hazard compared with AL.
- `Genotype_mut:Diet_DR` HR = 1.3: the DR effect in mut is 1.3 times the DR effect in wt. Equivalently, the hazard ratio of mut/DR against wt/AL is 0.6 × 0.5 × 1.3. An interaction HR of 1 means no interaction.
- HR < 1 means longer life than the reference; HR > 1 means shorter.

The report highlights coefficient rows with an unadjusted p below 0.05. It shows p-values to 4 decimals, or `<0.0001`, and other numbers to 3 decimals; use the CSV for exact values.

### Model warnings

If lifelines warns while fitting either model (for example that the fit did not converge cleanly, or that a column has very low variance), or the PH check cannot be computed, the message is kept with the model. The report lists it in a highlighted **Cox factorial model: warnings** table under the model, and the Run Summary stores it in that model's `warnings` list. Treat the numbers above such a warning with caution.

## Where it appears

- Report, "Factorial analysis" section, under the heading **Cox factorial model**.
- `statistics/factorial_01_coefficients_<focus>.csv` and `statistics/factorial_01_ph_test_<focus>.csv`. The Cox model is always model 01.
- Run Summary: `factorial_models[0]`.
- In an Experiment Script, a `cox_interaction` step after `run_analysis` refits this model and **replaces** the run's copy, so a later `report` step shows it once.

## Pitfalls

- **Read main effects at the reference.** With an interaction in the model, a main effect is a *simple* effect at the other factors' Reference Levels, not an average effect. If the interaction is negligible and you want average effects, the main-effects model would be the one to report. The app fits it for the LR test but tabulates only the interaction model.
- **Proportional hazards.** Every HR assumes the effect is constant across age. Check the PH table and the [Log-log diagnostic](help:plot-log-log). If PH fails, prefer the [RMST model](help:rmst-factorial).
- **Several p-values per model.** The coefficient p-values are not adjusted for each other. The LR test is the one designed to answer "is there any interaction?".
- **Clustering.** Individuals in a chamber share conditions, but the model treats them as independent and has no chamber term, so standard errors can be too small.

## See also

- [Interaction analyses (Factorial Battery)](help:analysis-interaction)
- [The RMST factorial model](help:rmst-factorial)
- [Checking proportional hazards](help:ph-check)
- [Reference Levels](help:reference-level)
- [Reading p-values and multiple comparisons](help:p-values)
