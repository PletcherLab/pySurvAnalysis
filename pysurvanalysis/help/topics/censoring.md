# Censoring policy

An individual is **right-censored** when its death was not observed: we know it was alive up to a certain age, but not when it died. Censored individuals still carry information. They count as "at risk" up to their censoring time and then leave the analysis without counting as a death. Every survival method in the app (Kaplan-Meier, log-rank, Cox, RMST, the parametric fits) uses censored individuals this way. This page explains where censored individuals come from in your data, and the one policy setting that controls them: **Assumed Censoring**.

## Where censored individuals come from

Every input is turned into one row per individual, each with a `time` and an `event` flag (1 = observed death, 0 = censored). You can inspect the result in `analysis/<focus>/data_output/individual_data_<focus>.csv`.

### DLife Excel workbooks (census data)

For each chamber, each census row in the **RawData** sheet contributes:

- `IntDeaths` deaths at that census age (`AgeH`), each an individual with event = 1;
- `Censored` explicitly censored individuals at that age (for example flies that escaped or were lost in handling), each with event = 0.

Then the censoring policy decides what happens to individuals that were never accounted for:

- **Assumed censoring on** (the default): the chamber's starting cohort is its `SampleSize` from the **Design** sheet. Any individuals not accounted for by deaths and explicit censorings (SampleSize − deaths − censored) are added as **censored at that chamber's last census age**. This is the DLife convention: anyone still unaccounted for at the end was alive when scoring stopped.
- **Assumed censoring off**: the cohort is only the individuals that appear in the census (deaths plus explicit censorings). `SampleSize` is ignored and nothing is added.

If a chamber's recorded deaths and censorings already add up to `SampleSize` or more, assumed censoring adds nobody.

### CSV and TSV files

These are already one row per individual, so censoring comes from the data: in long format, from the event column (default name `Event`, 1 = death, 0 = censored); in wide format, from the columns mapped to event 0. **The assumed-censoring setting has no effect on CSV or TSV input.** See [Input data formats](help:data-formats).

## Setting the policy

The policy is the `assume_censored` key of the `global:` section of the experiment's `survival_config.yaml`:

```yaml
global:
  assume_censored: true     # unaccounted individuals are censored at the last census
```

- If the key is absent, the Experiment Type's default applies. For Standard Lifespan, that default is `true`.
- In a Project, `assume_censored` can be set once in the **Project Defaults** (Project panel, **Edit config…**, the Global fields). A member that does not state its own value inherits it. See [project.yaml and Project Defaults](help:config-project).
- When the app first writes a config for a DLife workbook, it copies the workbook's own setting (the `AssumeCensored` flag on the **PrivateData** sheet, 1 = on) into `assume_censored`. From then on, the config is the authority; editing the workbook flag later changes nothing.

The value must be `true` or `false`; [Validate YAMLs](help:validation) reports anything else.

## How it shows in the results

- **Report cover**: the "Censoring policy" line reads *unaccounted individuals censored* (on) or *unaccounted individuals ignored* (off). The cover also gives the total number and percentage censored.
- **Per-treatment summary**: `n_censored` and `pct_censored` for each treatment ([Summary statistics](help:survival-summary)).
- **Run Summary**: `assume_censored` is recorded in `run_summary_<focus>.json`.
- **Project Report**: when members of a Project use different policies, a Divergence Note says so, because the same raw counts give different survival estimates under the two policies.
- **Top-percentile lifespans**: the `top_10pct_mean` and `top_5pct_mean` columns of the lifespan statistics are produced only when assumed censoring is **off**.

## What the choice does to the statistics

With assumed censoring **on**, unscored individuals count as alive until the last census. The KM curve then usually ends above zero, the RMST is restricted to the observation window, and the median can be undefined if too many are censored. Survival estimates are higher than if those individuals were ignored.

With it **off**, the unscored individuals simply do not exist in the analysis. This is appropriate when `SampleSize` is not reliable, or when every individual was scored to death and the difference is only bookkeeping. If individuals really did disappear alive, turning it off biases survival downward.

## Pitfalls

- **Changing the policy does not mark existing results Out of Date.** Out of Date tracks the Focus definition and the Exclusion Group, not the censoring policy. After changing `assume_censored`, re-run every Focus you rely on.
- **A wrong SampleSize becomes censoring.** With the policy on, a typo that makes `SampleSize` too large adds phantom censored individuals at the last census. Check `pct_censored` for any treatment that looks implausible.
- **Censoring must be uninformative.** Every method here assumes that being censored says nothing about when an individual would have died. Escapes due to sickness, or removing the frailest individuals, break this assumption.
- **The last census.** Assumed-censored individuals are placed at each chamber's own last census age, so chambers scored for different lengths of time contribute censorings at different ages.

## See also

- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [Input data formats](help:data-formats)
- [The global: section](help:config-global)
- [Summary statistics, median and mean survival](help:survival-summary)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
