# The Analyze panel and Run analysis

The Analyze panel is where you choose which statistical analyses a run includes and then start the run. It holds one checkbox per analysis in the experiment's **Analysis Set** that the **Active Focus** is offered, and below them a single **Run analysis** button. Run analysis computes everything under the Active Focus and writes the tables, figures, report and Run Summary to `analysis/<focus>/`.

## In the app

1. Load an experiment. For a Member Experiment, double-click its row in the Project panel's members table; this opens the Experiment panel.
2. On the Experiment panel, choose (or create) the **Active Focus**. The shape line under the selector tells you, before anything runs, which analyses this Focus is offered and whether any of them cannot be computed from its data.
3. Open the **Analyze** sub-tile. Tick the analyses you want and untick the ones you don't.
4. Click **Run analysis**. Progress and results go to the output log; when the run finishes the log reports where it wrote the results.

Each checkbox has a **?** button that opens that analysis's help page.

### The checkboxes

| Checkbox | What it runs | Offered when |
|---|---|---|
| Log-rank pairwise | Mantel-Cox log-rank test for every pair of treatments | the Focus implies 2 or more treatments |
| Log-rank omnibus | One K-sample log-rank test across all treatments | the Focus implies 2 or more treatments |
| Gehan-Wilcoxon pairwise | Gehan-weighted log-rank test for every pair | the Focus implies 2 or more treatments |
| Pairwise hazard ratios | A hazard ratio with 95% CI for every pair (also feeds the hazard-ratio forest) | the Focus implies 2 or more treatments |
| Parametric AFT models | Weibull, log-normal and log-logistic fits per treatment | always |
| Interaction analyses | The Factorial Battery's models: the Cox factorial model and the RMST factorial model together | the Focus varies 2 or more factors |

Analyses that the Focus is not offered get no checkbox. A quiet italic line under the button names them ("Not offered for Focus …"); hover over it to see why. For example, a one-factor Focus is never offered Interaction analyses, and a single-treatment Focus is offered no comparisons.

A checkbox that is offered but **greyed out** means the analysis is relevant but the Focus's data cannot support it. Its tooltip gives the reason, for example an empty cell in the crossing of two factors. See [Not Applicable and Left Out](help:not-applicable).

### What is always computed

The survivorship core is not in the Analysis Set and has no checkbox, because every figure and report section depends on it. Every run computes:

- the life tables and Kaplan-Meier estimates ([Life tables](help:lifetables)),
- the per-treatment summary counts, median survival, mean survival (RMST), the lifespan statistics and the survival quantiles ([Summary statistics](help:survival-summary)).

## Ticks are saved in the config

A tick is not just a setting on the screen. Unticking a box writes the analysis id to the `omit:` block of the experiment's `survival_config.yaml`, and ticking it removes the id again:

```yaml
omit:
  analyses:
    - parametric_aft
    - gehan_wilcoxon
```

The ids are `logrank_pairwise`, `logrank_omnibus`, `gehan_wilcoxon`, `hazard_ratios`, `parametric_aft` and `interaction`. Because the choice is stored in the config, every run of this experiment leaves the same analyses out: Run analysis in the Hub, an Experiment Script's `run_analysis` step, and a Batch Run alike. See [The omit: section](help:config-omit).

An unticked analysis is **Left Out**. It is not computed, and the run records it in the log, in the Run Summary's `left_out` list, and in the report's Focus section under "Left out of this run". Left Out is your choice; Not Applicable is a property of the data.

Unticking **Pairwise hazard ratios** also leaves out the hazard-ratio forest figure, because the forest is drawn from those hazard ratios. On the Plots panel its checkbox greys out and its tooltip says why.

## What Run analysis does

Run analysis runs the whole pipeline once, under the Active Focus:

1. Loads the data file with the experiment's censoring policy ([Censoring policy](help:censoring)) and active Exclusion Group.
2. Applies the Focus: keeps its rows and labels treatments by its varying factors. A Focus that names factors or levels the file lacks, or whose cells the exclusions emptied, is **Blocked**, and nothing is written.
3. Computes the survivorship core, then every ticked analysis the Focus admits.
4. Draws the ticked figures of the Plot Set (the same figures Generate plots draws).
5. Writes the CSV tables, the figures, the experiment report (PDF and Markdown) and the Run Summary.

If one analysis is relevant but cannot be computed, it is recorded as Not Applicable and the run continues. A parametric fit that fails to converge, or a factorial model that fails to fit, does not stop the run either; the report says which and why.

Run analysis does not open figure tabs. To view figures in the Hub, use **Generate plots** on the Plots panel, or open the report.

## Where results are written

Everything goes into the Focus's own folder, and every file name ends with the Focus's name (`_<focus>`), so analysing a second Focus never overwrites the first:

| Location | Contents |
|---|---|
| `analysis/<focus>/data_output/` | `lifetables_<focus>.csv`, `individual_data_<focus>.csv`, `summary_<focus>.csv`, `median_survival_<focus>.csv`, `mean_survival_<focus>.csv` |
| `analysis/<focus>/statistics/` | `logrank_pairwise_<focus>.csv`, `gehan_wilcoxon_pairwise_<focus>.csv`, `hazard_ratios_<focus>.csv`, `survival_quantiles_<focus>.csv`, `lifespan_treatment_stats_<focus>.csv`, `lifespan_factor_stats_<focus>.csv`, `factorial_01_coefficients_<focus>.csv`, `factorial_01_ph_test_<focus>.csv`, `factorial_02_coefficients_<focus>.csv`, `parametric_aic_<focus>.csv` |
| `analysis/<focus>/plots/` | the Plot Set figures |
| `analysis/<focus>/` | `report_<focus>.md`, `<experiment>_report_<focus>.pdf`, `run_summary_<focus>.json` |

A file appears only when its analysis ran and produced rows. When a later run leaves an analysis out, the pipeline deletes the stale comparison, parametric and factorial tables (and figures) an earlier run of the same Focus wrote, so the folder never shows an out-of-date table as if it were current.

The omnibus log-rank result has no CSV of its own: it is stored in the Run Summary and shown in the report. The parametric AFT comparison is in `parametric_aic_<focus>.csv` and also in the Run Summary.

## Pitfalls

- **Check the Active Focus first.** Run analysis always runs under the Active Focus shown on the Experiment panel.
- **One run at a time.** If a task is already running, the Hub refuses to start another.
- **Changing the Focus afterwards** (its levels, filters or Reference Levels) makes the saved results **Out of Date**; re-run to refresh them. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).

## See also

- [Not Applicable and Left Out](help:not-applicable)
- [The omit: section — leaving analyses and figures out](help:config-omit)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [Where results are written](help:outputs-layout)
- [The experiment report](help:experiment-report)
- [Reading p-values and multiple comparisons](help:p-values)
