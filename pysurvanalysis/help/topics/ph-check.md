# Checking proportional hazards

Hazard ratios, the Cox model, and to a degree the log-rank test all rest on the **proportional-hazards (PH) assumption**: the ratio of two groups' hazards stays the same at every age. If treatment A halves the risk of death at 10 days, it should also halve it at 60 days. When the assumption fails (curves that cross, or an effect that fades or appears late), a single hazard ratio is an average of an effect that changes with age. The app gives you one formal test and one visual check.

## The formal test: Schoenfeld residuals

### Where it is run

The test is part of the [Cox factorial model](help:cox-factorial), so it runs whenever **Interaction analyses** is ticked on the Analyze panel and the Focus admits the [Factorial Battery](help:analysis-interaction) (two or more varying factors, fully crossed). It is not run for the pairwise hazard ratios, the log-rank tests, or one-factor Focuses.

### What is computed

The app calls the **lifelines** function `proportional_hazard_test` on the fitted Cox **interaction** model, with `time_transform="rank"`. For each term of the model, this tests whether the term's scaled Schoenfeld residuals trend with the rank of the death times. A trend means the term's effect, its log hazard ratio, drifts with age. Each term gets a χ² statistic on 1 degree of freedom and a p-value.

There is **one row per model term**: every main-effect dummy and every interaction dummy. No global (whole-model) test is reported, and **no multiple-comparison adjustment** is applied across the rows.

### Reading the results

Saved as `analysis/<focus>/statistics/factorial_01_ph_test_<focus>.csv` and shown in the report's "Factorial analysis" section, under the Cox model, as **Proportional-hazards check (Schoenfeld residuals)**:

| Column | Meaning |
|---|---|
| `covariate` | The model term, e.g. `Diet_DR` or `Genotype_mut:Diet_DR` |
| `test_statistic` | χ² statistic (1 df) for a time trend in that term's effect |
| `p_value` | p-value for that trend |

How to read it:

- **A small p-value (below 0.05)** means that term's hazard ratio is not constant with age, so the PH assumption is doubtful for it. The report caption says the same: small p-values indicate violation.
- **A large p-value** means no evidence against PH. It does not prove PH holds, especially with few deaths.
- With large samples, the test can flag departures too small to matter. Look at the curves before deciding.
- With many rows, expect about one in twenty to fall below 0.05 by chance.

If the test itself fails to run, the PH table is missing from the report and no `ph_test` CSV is written for that run. The failure is not silent: the report lists it, as "PH assumption test failed: …", in the highlighted **Cox factorial model: warnings** table under the model, and the Run Summary keeps it in that model's `warnings` list. Warnings lifelines raises while running the test are listed there too.

## The visual check: the log-log plot

The [Log-log diagnostic](help:plot-log-log) on the Plots panel plots log(−log Ŝ(t)) against log time for each treatment. Under proportional hazards the curves are roughly **parallel**, a constant vertical distance apart. Curves that converge, diverge or cross suggest non-proportional hazards. The plot is offered whenever the Focus has two or more treatments, so it is the check to use for one-factor Focuses, and for the pairwise hazard ratios, which have no formal test. The [Kaplan-Meier curves](help:plot-km-curves) help too: KM curves that cross are a clear sign that hazards are not proportional.

## What to do when PH fails

- Use the **[RMST factorial model](help:rmst-factorial)**. It estimates effects as differences in mean lifespan up to τ and needs no PH assumption. It is fitted alongside the Cox model.
- For pairwise comparisons, compare the **log-rank** test with **Gehan-Wilcoxon**, which weights early deaths more. If they disagree, the difference is concentrated at one end of life. See [Gehan-Wilcoxon pairwise](help:analysis-gehan-wilcoxon).
- Report hazard ratios as averages over the observed period, or describe the curves directly: medians, survival quantiles and RMST ([Summary statistics](help:survival-summary)).

## Pitfalls

- **Census data have many ties.** Many deaths share each census age, which makes the residual trend coarse. Treat borderline p-values with caution.
- **Interaction terms are tested too.** A PH failure in an interaction row means the *interaction* changes with age, not necessarily either factor alone.

## See also

- [The Cox factorial model](help:cox-factorial)
- [The RMST factorial model](help:rmst-factorial)
- [Log-log diagnostic](help:plot-log-log)
- [Pairwise hazard ratios](help:analysis-hazard-ratios)
- [Reading p-values and multiple comparisons](help:p-values)
