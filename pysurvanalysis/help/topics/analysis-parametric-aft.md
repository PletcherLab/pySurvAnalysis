# Parametric AFT models

Kaplan-Meier makes no assumption about the shape of the survival curve. A parametric model instead fits a named lifespan distribution to the data. The app fits three common ones (Weibull, log-normal and log-logistic) to each treatment separately and compares them by AIC. This tells you which distribution describes each treatment's lifespans best, and gives a model-based median lifespan.

## In the app

On the Analyze panel, tick **Parametric AFT models** and click **Run analysis**. This analysis has no Focus requirement: it is offered for every Focus, including a single treatment.

The analysis id for `omit:` is `parametric_aft`. In Experiment Scripts, the `parametric_aft` action fits the same models and writes the results to the log.

## What is computed

For **each treatment on its own**, the app fits three accelerated-failure-time (AFT) models with the **lifelines** library: `WeibullAFTFitter`, `LogNormalAFTFitter` and `LogLogisticAFTFitter`. Each is fitted to that treatment's times and event flags only, with no covariates, so each fit is simply the best two-parameter distribution of that family for that treatment, estimated by maximum likelihood. Censored individuals enter the likelihood correctly: they contribute the probability of surviving past their censoring time.

| Model | Shape of the hazard it can describe |
|---|---|
| Weibull | Hazard that rises (or falls) steadily with age as a power of age |
| Log-normal | Hazard that rises, peaks and then falls |
| Log-logistic | Like the log-normal, with heavier tails |

For each fit the app records:

- **AIC**, the Akaike information criterion: AIC = −2 log L + 2k, where k is the number of parameters. All three models have two parameters, so the ranking by AIC is the same as the ranking by log-likelihood.
- **log-likelihood** of the fit.
- **median survival** predicted by the fitted distribution.

The **best model** for a treatment is the one with the lowest AIC.

Treatments with **fewer than 5 individuals or fewer than 2 deaths are not fitted**, and a model that fails to converge is not fitted either. Neither disappears: each gets a row in the comparison saying why (for example "not fitted: only 3 individual(s) — needs at least 5" or "not fitted: fit failed: …"), and the run log says the same. If the whole step fails, the run continues and the table holds a single row with the reason.

No test is performed, so there are no p-values and no multiple-comparison adjustment. The models do not compare treatments with each other.

## Reading the results

The AIC comparison has one row per treatment and model, treatments in the Focus's display order, plus one row for each treatment that was too small to fit:

| Column | Meaning |
|---|---|
| `treatment` | Treatment label |
| `model` | `Weibull`, `Log-Normal` or `Log-Logistic`; empty for a treatment too small to fit |
| `aic` | AIC of the fit (lower is better), to 2 decimals |
| `delta_aic` | AIC minus the lowest AIC of that treatment, so 0 marks the best fit |
| `log_likelihood` | Maximised log-likelihood |
| `median_survival` | Median lifespan predicted by the fitted distribution |
| `best` | `True` for the treatment's lowest-AIC model |
| `note` | `lowest AIC` for the best model; for a row with no fit, `not fitted:` and the reason |

How to read it:

- Compare AICs **within a treatment**, never across treatments. Each treatment's AIC depends on its own sample size and data.
- A difference of less than about 2 AIC units means the models fit about equally well. A difference of 10 or more is strong support for the lower one.
- Compare the model's `median_survival` with the KM median in [Summary statistics](help:survival-summary). Close agreement is a sign of a good fit. Note that the KM median always falls on a census age, while the model median does not.
- If one family wins for every treatment, it is a reasonable choice for further parametric modelling.

## Where it appears

- **The report**, in the "Data quality" section, as the table **Parametric model fits (AFT)**: Treatment, Model, AIC, ΔAIC, Median (model) and Note. Each treatment's best model is highlighted, and rows that were not fitted are highlighted as warnings.
- **The CSV** `analysis/<focus>/statistics/parametric_aic_<focus>.csv`, with the columns above. A later run that leaves the analysis out deletes it, so it never reads as current.
- **The Run Summary**, as `parametric_models`: the same rows as a list of records. The [Project Report](help:project-report) rebuilds the report's table from it.
- **The run log**, when run as the `parametric_aft` script action, including the AIC comparison table.

The fitted parameters themselves (for example the Weibull scale and shape) are not tabulated.

## Pitfalls

- **Census data is interval data.** Deaths are recorded at census ages, so many share a time. The models treat each recorded age as exact.
- **Assumed censoring adds a block of censored individuals at the last census**, which mostly affects the upper tail of the fit.
- **Per-treatment fits only.** The app does not fit an AFT regression with treatment or factor effects. To model factor effects, use the [Cox](help:cox-factorial) or [RMST](help:rmst-factorial) factorial models.

## See also

- [Summary statistics, median and mean survival](help:survival-summary)
- [Lifespan distribution](help:plot-survival-distribution)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [Censoring policy](help:censoring)
- [The experiment report](help:experiment-report)
