# Interaction analyses (Factorial Battery)

When a Focus crosses two or more factors (for example Genotype × Diet), the key question is often not just whether each factor matters, but whether they **interact**: does the effect of diet depend on genotype? The **Interaction analyses** checkbox runs the two models of the **Factorial Battery** that answer this:

- the **[Cox factorial model](help:cox-factorial)**, which estimates factor effects as hazard ratios, tests all interactions together with a likelihood-ratio (LR) test, and checks proportional hazards;
- the **[RMST factorial model](help:rmst-factorial)**, which estimates the same factorial design as differences in restricted mean lifespan and does not assume proportional hazards.

Both are fitted relative to each factor's **Reference Level**.

## In the app

1. On the Experiment panel, make the Active Focus one that varies two or more factors. The shape line (for example `2×2`) tells you whether the battery will be offered.
2. Optionally, set each factor's **Reference Level** in the [Focus window](help:focus-window) (the *Reference:* box beside each factor's levels). See [Reference Levels](help:reference-level).
3. On the Analyze panel, tick **Interaction analyses** and click **Run analysis**.

One checkbox runs both models; you cannot run one without the other from the Analyze panel. The analysis id for `omit:` is `interaction`.

The battery's two figures, the [Faceted Kaplan-Meier](help:plot-km-faceted) and the [Lifespan interaction plot](help:plot-interaction-lifespan), are separate Plot Set items on the Plots panel and are not controlled by this checkbox.

In Experiment Scripts, the actions `cox_interaction` and `rmst_interaction` run each model on its own under the step's Focus. `rmst_interaction` has a τ parameter (0 = automatic). They write their results to the log. Placed after a `run_analysis` step, each refitted model **replaces** the run's model of the same name, so a later `report` step shows every model once.

## When it is offered, and when it is Not Applicable

| Situation | What happens |
|---|---|
| The Focus varies fewer than two factors | Not offered: no checkbox, no report section |
| It varies two or more factors, and every pair of them is fully crossed in the populated cells | Both models are fitted |
| It varies two or more factors, but some combination of levels has no individuals | **Not Applicable**: the run records "Factorial Battery" with the empty cells named (for example `Genotype=mut × Diet=DR`), and the checkbox is greyed with that reason |

Any number of levels per factor is allowed. A "factor" here is a *varying* factor of the Focus: one named with two or more levels. A factor the Focus filters to one level, or pools over, does not enter the model.

The crossing must be complete because an interaction term compares a combination of levels with the others. If that combination has no individuals, its term cannot be estimated.

## The model design

Both models use the same design, built from the Focus's varying factors:

- **Main effects**: each factor is dummy-coded with its Reference Level as the baseline. A factor with L levels gets L − 1 terms, named `Factor_level` (for example `Diet_DR`).
- **Pairwise interactions**: for every pair of factors, the product of each of their dummies, named `A_a:B_b` (for example `Genotype_mut:Diet_DR`). A pair with Lᴬ and Lᴮ levels gets (Lᴬ − 1)(Lᴮ − 1) terms.
- **Only pairwise interactions** are included. With three factors, the model has the three two-way interactions but no three-way term.

The design is fitted to individuals, not to treatment means: every individual in the Focus is one row.

## Reading the results

How to interpret the coefficients when interactions are in the model:

- A **main-effect** coefficient is the effect of that level **at the Reference Level of every other factor**. In a Genotype × Diet model with references wt and AL, `Genotype_mut` is the effect of mut *on the AL diet only*. It is not an average over diets.
- An **interaction** coefficient is how much that effect changes at the other level. In the Cox model it is a ratio of hazard ratios; in the RMST model it is a difference of differences in mean lifespan.
- The **Cox LR test** asks whether the interaction terms, taken together, improve the fit. A small p-value means the factors' effects are not additive (on the log-hazard scale).

The [Lifespan interaction plot](help:plot-interaction-lifespan) shows the same idea graphically: lines that are not parallel suggest an interaction.

## Where it appears

- **Report, "Factorial analysis" section**: one subsection per model, giving the formula, the model line (n and events; concordance for Cox; τ, R² and the robust F test for RMST; AIC), the Cox LR interaction table, the coefficient table (captioned with the Reference Levels), the Cox model's Schoenfeld check, and a highlighted table of any warnings raised while fitting that model. If the battery was Not Applicable, the section is a single line, "Factorial Battery: not run", with the reason. If it was unticked, it reads "Interaction analyses: left out of this run".
- **CSV files** in `analysis/<focus>/statistics/`:
  - `factorial_01_coefficients_<focus>.csv`: Cox coefficients
  - `factorial_01_ph_test_<focus>.csv`: Cox Schoenfeld PH check
  - `factorial_02_coefficients_<focus>.csv`: RMST coefficients
- **Run Summary**: `factorial_models` in `run_summary_<focus>.json` lists each model's title, type, formula, any error, n, events, concordance, AIC, Reference Levels, its `warnings`, and, for Cox, the LR interaction test; for RMST, `tau`, `r_squared` and the F test.

If a model fails to fit, the run continues. The report then says "*model* could not be fitted", with the error.

## Pitfalls

- **Changing a Reference Level changes the coefficients, but not the fit.** Main effects then refer to a different baseline cell, and interaction signs can flip. The LR test and the fitted survival do not change. Changing a Reference Level marks the Focus's results Out of Date.
- **Unbalanced or sparse cells** give wide intervals. A cell with very few deaths can make the Cox fit unstable.
- **Display order is not the baseline.** Reordering levels for figures does not change the model unless you also change the Reference Level.

## See also

- [The Cox factorial model](help:cox-factorial)
- [The RMST factorial model](help:rmst-factorial)
- [Checking proportional hazards](help:ph-check)
- [Reference Levels](help:reference-level)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [Lifespan interaction plot](help:plot-interaction-lifespan)
