# Summary statistics, median and mean survival

Alongside the life tables, every run computes descriptive statistics for each treatment: how many individuals, deaths and censored individuals it has, its median survival, its mean survival (as a restricted mean, RMST), its survival quantiles, and a lifespan table that can also pool by factor level. These are part of the survivorship core, so they are always computed and have no checkbox.

## In the app

Click **Run analysis** on the Analyze panel. All of the tables below are computed for every treatment of the Active Focus. The results go to CSV files under `analysis/<focus>/` and to the report's "Experiment summary" and "Lifespan statistics" sections.

## What is computed

### Per-treatment summary

Counts of the individuals each treatment contributes after the Focus and the Exclusion Group are applied. Saved as `data_output/summary_<focus>.csv` and shown in the report as **Per-treatment summary**:

| Column | Meaning |
|---|---|
| `treatment` | Treatment label |
| `n_individuals` | Individuals in the treatment |
| `n_deaths` | Observed deaths (event = 1) |
| `n_censored` | Right-censored individuals (event = 0) |
| `pct_censored` | 100 × n_censored / n_individuals, to one decimal |

The report cover also gives the Focus-wide totals (treatments, individuals, deaths, censored and % censored), and the summary section gives the observation window (the earliest and latest time in the data) and the number of chambers.

### Median survival

The median is read off the Kaplan-Meier curve: it is the **first time at which Ŝ(t) ≤ 0.5**. When the curve never reaches 0.5, for example because many individuals are censored, the median is undefined and shown as blank or "—".

Its **95% confidence interval** is read off the KM curve's 95% confidence band the same way: the lower limit is the first time the band's lower edge reaches 0.5, and the upper limit the first time its upper edge does. The band is the log-log interval described in [Life tables](help:lifetables), so this is the interval R's `survfit` and lifelines report. When the upper edge never falls to 0.5, the upper limit is "not reached" and shown as blank or "—", even when the median itself exists.

Saved as `data_output/median_survival_<focus>.csv` and shown in the report as **Median survival**:

| Column | Meaning |
|---|---|
| `treatment` | Treatment label |
| `median_survival` | First time Ŝ(t) ≤ 0.5 |
| `median_ci_lo`, `median_ci_hi` | The 95% confidence interval for the median |

### Mean survival (RMST, common restriction time)

A plain mean of death times is biased when some individuals are censored. The app therefore reports the **restricted mean survival time (RMST)**: the area under the KM curve from 0 up to a restriction time τ. You can read it as the average lifespan over the window from 0 to τ.

- **τ is common to all treatments**, so their RMSTs can be compared. It is the smallest of the treatments' last observed times: τ = min over treatments of (the largest time, death or censoring, in that treatment).
- **The area** is the exact area under the KM **step function**: Ŝ is 1 from 0 to the first death, then holds each value until the next death, and the last step is cut off at τ itself. This is the same number as lifelines' `restricted_mean_survival_time`.

Saved as `data_output/mean_survival_<focus>.csv` and shown in the report as **Mean survival**:

| Column | Meaning |
|---|---|
| `treatment` | Treatment label |
| `rmst` | Area under the KM curve up to the restriction time |
| `restriction_time` | τ, the same for every row |

The same τ rule is used by the [RMST factorial model](help:rmst-factorial), so `restriction_time` here also tells you which τ that model used.

### Lifespan statistics

A second table gives each group's mean and median, and can also pool by factor level. Saved as `statistics/lifespan_treatment_stats_<focus>.csv` and, when the Focus varies two or more factors, `statistics/lifespan_factor_stats_<focus>.csv`. In the report they are **Lifespan statistics by treatment** and **Lifespan statistics by factor level**.

| Column | Meaning |
|---|---|
| `group` | A treatment, or `Factor=level` in the factor-level table |
| `n`, `n_deaths`, `n_censored` | Counts for the group |
| `mean_rmst` | Area under the group's KM step function from 0 to the common τ, computed as above |
| `tau` | The common τ: the same restriction time as the Mean survival table, in every row of both tables |
| `median` | First time the group's KM curve is at or below 0.5 |
| `t_max` | The group's own last observed time |
| `top_10pct_mean`, `top_5pct_mean` | Mean age at death of the longest-lived 10% / 5% of the individuals that died |

Notes:

- **`mean_rmst` uses the common τ**, so for a treatment it is the same number as the `rmst` in the Mean survival table (rounded to 2 decimals), and rows observed for different lengths of time are still compared over the same window.
- **The factor-level rows pool across the other factors.** For example, `Genotype=wt` combines every wt treatment of the Focus, whatever its diet. The factor-level table is produced only when the Focus varies two or more factors; with one, it would repeat the treatment table.
- **The top-percentile columns appear only when assumed censoring is off** (`assume_censored: false`) **and the group has more than 10 deaths.** They use deaths only, so they are meaningful only when there is little censoring. The number kept is the fraction of deaths rounded up, and at least one.

### Survival quantiles

The time at which each treatment's KM curve first falls to or below a set of survival levels. Saved as `statistics/survival_quantiles_<focus>.csv` and shown in the report as **Survival quantiles**:

| Column | Meaning |
|---|---|
| `treatment` | Treatment label |
| `S=90%` | First time Ŝ(t) ≤ 0.90 (10% have died) |
| `S=75%` | First time Ŝ(t) ≤ 0.75 |
| `S=50%` | First time Ŝ(t) ≤ 0.50 (the median) |
| `S=25%` | First time Ŝ(t) ≤ 0.25 |
| `S=10%` | First time Ŝ(t) ≤ 0.10 (90% have died) |

A blank cell means the curve never fell that far.

## Reading the results

- All times are in the data's time unit (`global.time_unit`, for example days).
- Every table lists treatments in the Focus's display order (the order of its levels), never alphabetically.
- With census data, medians, their confidence limits and quantiles always fall on census ages, because the KM curve and its band only drop at those times. Two treatments can share a median even though their curves differ.
- The report rounds numbers to 3 decimal places. For full precision, use the CSV files.

## Pitfalls

- **Heavy censoring.** If a treatment's curve stays above 0.5, its median is missing. Its RMST still exists, but it describes survival only up to τ.
- **A short treatment shortens everyone's τ.** One treatment observed for less time pulls the common restriction time down for every treatment, in the Mean survival table and the lifespan tables alike.
- **Results from before this version.** Earlier versions joined the KM points with straight lines (trapezoids) and stopped at the last time before τ, which gave slightly lower means, and restricted each lifespan-table row to its own last time. Re-run the analysis to get the exact values.

## See also

- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [The RMST factorial model](help:rmst-factorial)
- [Censoring policy](help:censoring)
- [Lifespan distribution](help:plot-survival-distribution)
- [The experiment report](help:experiment-report)
