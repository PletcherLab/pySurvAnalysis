# The Run Summary

The Run Summary is a small JSON file written at the end of every analysis run, one per Focus. It records what the run analysed and how: the counts, the exact Focus definition, the Exclusion Group, the figures written, what was Not Applicable or Left Out, and the headline test results. The Hub and the Project Report read it instead of re-analysing, which is what makes "not analysed" and "Out of Date" visible states, and what makes building a Project Report fast.

You rarely need to open it, but it is plain text and is the authoritative record of a run.

## Where it is written

`<experiment>/analysis/<focus>/run_summary_<focus>.json` — for example `Exp12/analysis/diet/run_summary_diet.json`. It is written by every **Run analysis**, every `run_analysis` script step and every Batch Run, after the report. Re-running the Focus overwrites it. Because there is one per Focus, analysing a second Focus never overwrites the first.

## What it contains

| Key | Meaning |
|---|---|
| `analyzed_at` | date and time of the run (to the second) |
| `input_file` | name of the data file |
| `data_sha256` | the SHA-256 hash of the data file's contents, so an edited data file can be told from the one analysed |
| `experiment_type` | the Experiment Type key, e.g. `standard_lifespan` |
| `focus` | the Focus record (see below) |
| `factors` | the Focus's varying factors |
| `discovered_factors` | every factor found in the data file |
| `n_total` | individuals in this Focus |
| `n_deaths` | deaths |
| `n_censored` | censored individuals |
| `n_treatments` | number of treatments |
| `n_chambers` | number of chambers |
| `time_min`, `time_max` | the observation window |
| `assume_censored` | the censoring policy: `true` when individuals unaccounted for at the last census are censored |
| `exclusion_group` | name of the config's active Exclusion Group, or `null` |
| `excluded_chambers` | the chambers actually removed, as a sorted list of ids (text): those the exclusions listed **and** the data file holds. Empty for data with no chamber identities |
| `n_excluded` | how many chambers were actually removed (the length of `excluded_chambers`) — `0` for data with no chamber identities, whatever the group lists |
| `n_excluded_listed` | chambers the exclusions listed, including any the data file never had |
| `omit` | the `omit:` selection the run applied: `{analyses: [...], plots: [...]}`, sorted ids |
| `load_warnings` | what the loader reported about the data file without refusing it (for example a chamber recording more deaths and censorings than its SampleSize) |
| `min_n_per_chamber` | the `global.min_n_per_chamber` threshold in force (`0` = off) |
| `small_chambers` | list of `{chamber, treatment, n}` for each chamber of this Focus with fewer individuals than the threshold — flagged, not excluded |
| `figures` | figure id → file name in `plots/`, for each figure drawn |
| `defined_plots` | Defined Plot name → file name, for each drawn |
| `not_applicable` | list of `{action, reason}` — real actions this Focus could not support |
| `left_out` | list of `{id, item, reason}` — analyses and figures left out by the config's `omit:` |
| `omnibus_lr` | the omnibus log-rank result (`chi2`, `p_value`, `df`, `groups`), or `{}` when it did not run |
| `parametric_models` | the parametric AFT comparison, one record per treatment × model with `treatment`, `model`, `aic`, `delta_aic`, `log_likelihood`, `median_survival`, `best` and `note` (the reason, for a treatment or model not fitted); `[]` when the analysis was left out. See [Parametric AFT models](help:analysis-parametric-aft) |
| `factorial_models` | one entry per Factorial Battery model (see below); empty when the battery did not run |

### The `focus` record

| Key | Meaning |
|---|---|
| `name`, `slug` | the Focus name and the form used in file names |
| `definition` | the **analytic definition**: `factors` (each with its ordered levels) and `reference` (each factor's Reference Level) |
| `description` | the one-line description of the slice shown in reports |
| `filters` | factors held at a single level |
| `pooled_over` | factors in the data that the Focus does not name |
| `shape` | the Focus Shape, e.g. `2×2`, `2×2 (3 of 4 cells)` or `single cell` |
| `treatments` | the populated treatments |
| `absent_cells` | cells the levels imply but the data never held |
| `headline` | the Headline Figure's id |
| `unassigned` | individuals with no level for a factor the Focus names, so outside the analysis |

### Each `factorial_models` entry

`title`, `model_type`, `formula`, `error` (set when the model could not be fitted), `n_subjects`, `n_events`, `concordance`, `AIC`, `reference` (the Reference Levels), `warnings` (anything the fit or the PH test warned about; an empty list when nothing did), and `lr_interaction` — for the Cox model, the likelihood-ratio test of the interaction model against the main-effects model: `statistic` (the χ² statistic, also kept as `lr_stat` for older readers), `df`, `p_value`, the two log-likelihoods (`ll_main`, `ll_interaction`), `concordance_main` and the interaction terms tested (`interaction_cols`). For the RMST model, `tau` (the restriction time used), `rmst_overall` (the pooled RMST θ), `r_squared`, `f_statistic` and `f_p_value`; these are `null` for the Cox model. The coefficient tables are saved beside it as CSVs in `statistics/`.

Summaries written by earlier versions lack some of these keys (`excluded_chambers`, `parametric_models`, `statistic`, `tau`, …). Readers fall back: a missing χ² `statistic` is read from `lr_stat`, and a report built from a summary with no `excluded_chambers` gives the count of excluded chambers only.

## How it is used

- **Out of Date.** The Hub compares the recorded `focus.definition` and `exclusion_group` with what the config declares now, and, where this file recorded them, `data_sha256`, `excluded_chambers`, `assume_censored` and `omit` with the data file, exclusions and settings as they are now. If any of them changed, the Focus is **Out of Date**: the Hub says so, and the Project Report shows no results for it until it is re-run. Display names and colours are not part of the comparison. A summary with no recorded definition (from before Focuses existed) is always Out of Date. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).
- **Not analysed.** A Focus with no Run Summary is "not analysed"; the report never analyses it on your behalf.
- **The Project Report** rebuilds each Focus's section from this file plus the saved CSVs and figures, and fills the Focus Inventory from it.
- **The AI narrative** reads the same saved numbers.

## Not Applicable entries from scripts

When an Experiment Script runs `run_analysis` for a Focus and a later step in the same Focus is Not Applicable (say, a `cox_interaction` step on a Focus with an empty cell), that step is added to this file's `not_applicable` list. Duplicates are not added. A script that did not analyse the Focus itself never edits its Run Summary.

## Pitfalls

- Do not edit the file by hand: a changed definition will be compared against the config, and hand-edited counts will appear in the Project Report as if computed.
- Renaming a Focus by hand in the YAML leaves its folder, and this file, behind as Orphaned Results. Rename Focuses in the Focus window instead.

## See also

- [The experiment report](help:experiment-report)
- [The Project Report](help:project-report)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [Not Applicable and Left Out](help:not-applicable)
- [Where results are written](help:outputs-layout)
