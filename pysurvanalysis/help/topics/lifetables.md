# Life tables and the Kaplan-Meier estimator

Every run starts by building a life table for each treatment in the Focus. The life table holds the Kaplan-Meier (KM) survivorship estimate with its confidence band, the interval mortality and hazard, and the Nelson-Aalen cumulative hazard. Almost everything else in the app is computed from it: the KM, hazard, mortality, cumulative-hazard and number-at-risk figures, median survival, mean survival (RMST) and the survival quantiles.

## In the app

There is nothing to tick. The life tables are part of the survivorship core, so **Run analysis** on the Analyze panel always computes them, and **Generate plots** recomputes them for the figures. They are computed separately for each treatment of the Active Focus, after the Exclusion Group has removed its chambers. All the chambers of a treatment are pooled.

## How it works

The data are first expanded to one row per individual, each with a time and an event flag: 1 means an observed death, 0 means right-censored. See [Censoring policy](help:censoring) for how censored individuals arise. The calculation is the app's own code; it does not call a survival library, though its survival estimate and band agree with lifelines'. Treatments appear in the Focus's display order.

For each treatment, the table has **one row for each distinct time at which any individual of that treatment died or was censored**. At each such time t:

- nᵢ is the number at risk: everyone still alive and uncensored just before t.
- dᵢ is the number of deaths at t, and cᵢ is the number censored at t.
- Individuals censored at t are counted as at risk at t and removed afterwards, so nᵢ₊₁ = nᵢ − dᵢ − cᵢ.

The Kaplan-Meier estimate is the running product of the interval survival probabilities:

```
qᵢ = dᵢ / nᵢ            probability of dying at tᵢ
pᵢ = 1 − qᵢ             probability of surviving tᵢ
Ŝ(t) = ∏ pᵢ   over all tᵢ ≤ t
```

**Confidence band.** The variance uses Greenwood's formula, and the 95% band is the **log-log** ("exponential Greenwood") interval, built on the log(−log Ŝ) scale and transformed back:

```
G(t)     = Σ dᵢ / (nᵢ (nᵢ − dᵢ))          Greenwood sum, over tᵢ ≤ t
SE(Ŝ(t)) = Ŝ(t) · √G(t)
v        = log Ŝ(t)
95% CI   = exp( −exp( log(−v) ± 1.96 · √G(t) / v ) )
```

The interval always lies between 0 and 1 without clipping, and it is asymmetric where Ŝ is close to either end, which is where the tail is read. It is the interval R's `survfit` uses with `conf.type = "log-log"` and the one lifelines' `KaplanMeierFitter` reports, and the app's values match lifelines exactly. Where Ŝ = 1 (before the first death) the band is 1, and where Ŝ = 0 it is 0. A time at which everyone at risk dies (nᵢ = dᵢ) adds nothing to the Greenwood sum.

**Interval hazard.** The hazard in each interval uses the actuarial approximation, where Δt is the gap to the next time in the table (for the last row, the gap from the previous time):

```
hᵢ = 2 qᵢ / ((1 + pᵢ) · Δt)
```

**Nelson-Aalen cumulative hazard**, with a normal-approximation 95% interval (the lower bound is clipped at 0):

```
H(t)    = Σ dᵢ / nᵢ
Var H   = Σ dᵢ / nᵢ²
95% CI  = H ± 1.96 · √Var H
```

## Reading the results

The life table is saved as `analysis/<focus>/data_output/lifetables_<focus>.csv`, with one block of rows per treatment:

| Column | Meaning |
|---|---|
| `treatment` | Treatment label (levels of the Focus's varying factors joined with `/`) |
| `time` | A distinct death or censoring time, in the data's time unit |
| `n_at_risk` | Number at risk at this time (before its deaths and censorings are removed) |
| `n_deaths` | Deaths at this time |
| `n_censored` | Individuals censored at this time |
| `qx` | Interval probability of death, d/n |
| `px` | Interval probability of survival, 1 − qx |
| `lx` | Survivorship: the cumulative product of px (identical to `km_lx`) |
| `hx` | Interval hazard, actuarial approximation adjusted for interval width |
| `km_lx` | Kaplan-Meier survival estimate Ŝ(t) |
| `se_km` | Greenwood standard error of Ŝ(t) (0 before the first death) |
| `km_ci_lo`, `km_ci_hi` | 95% log-log confidence band for Ŝ(t) |
| `na_H` | Nelson-Aalen cumulative hazard H(t) |
| `na_se` | Standard error of H(t) |
| `na_ci_lo`, `na_ci_hi` | 95% confidence band for H(t) |

The same folder holds `individual_data_<focus>.csv`, the one-row-per-individual data the life tables were built from (`time`, `event`, `chamber`, `treatment` and the factor columns), so you can check any number by hand or reanalyse it in other software.

## Where it appears

- `data_output/lifetables_<focus>.csv`, as above. The life table itself is not printed in the report.
- The figures drawn from it: [Kaplan-Meier curves](help:plot-km-curves), [KM curves with at-risk table](help:plot-km-risk-table), [Nelson-Aalen cumulative hazard](help:plot-nelson-aalen), [Hazard rate](help:plot-hazard), [Mortality (qx)](help:plot-mortality) and [Number at risk](help:plot-number-at-risk).
- The report's "Lifespan statistics" section, through the median, mean and quantile tables derived from it ([Summary statistics](help:survival-summary)).

## Pitfalls

- **Census data has coarse time.** With census-scored chambers, many deaths share each census time, so the table has one row per census age, and the KM curve drops in steps at those ages.
- **The tail is noisy.** Late in the experiment few individuals are at risk, so `qx` and `hx` jump about and the confidence band is wide. The log-log band stays inside 0…1 but becomes lopsided there, wider on the side away from the boundary.
- **Censoring at the end.** With assumed censoring on, individuals unaccounted for are censored at their chamber's last census. The KM curve then stays above zero at the end of the experiment, and the band does not close.
- **Pooling.** Chambers are pooled within a treatment; the life table does not model chamber-to-chamber variation. Use the [Chamber QC viewer](help:qc-viewer) to look for outlying chambers.

## See also

- [Summary statistics, median and mean survival](help:survival-summary)
- [Censoring policy](help:censoring)
- [Kaplan-Meier curves](help:plot-km-curves)
- [Nelson-Aalen cumulative hazard](help:plot-nelson-aalen)
- [Mortality (qx)](help:plot-mortality)
