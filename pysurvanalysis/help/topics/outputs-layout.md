# Where results are written

Every analysis is run under a **Focus**, and everything it produces goes into that Focus's own folder, `analysis/<focus>/`, with the Focus's name at the end of every file name. Two Focuses of the same experiment never overwrite each other. A figure copied out of its folder still says which slice of the data it shows. Nothing is written outside the experiment directory except the Project-level files described at the end.

`<focus>` below is the Focus name made safe for file names: any run of characters other than letters, digits, `.`, `_` and `-` becomes `_`. A Focus called `Crowding 20 v 40` writes to `analysis/Crowding_20_v_40/`. The default Focus writes to `analysis/Unfiltered/`.

## An Experiment Directory

```
cohort_a/
├── survival_config.yaml          the experiment's configuration
├── data/
│   └── cohort_a.xlsx             the data file (or at the directory root)
├── qc/
│   └── remove_chambers.csv       Exclusion Groups
├── analysis/
│   └── <focus>/                  one folder per Focus — see below
├── figures/
│   └── <focus>/                  rendered Publication Figures
└── plot_specs.yaml               Publication Figure specs (standalone experiments only)
```

## Inside the analysis/*focus* folder

```
analysis/Crowding20v40/
├── run_summary_Crowding20v40.json
├── cohort_a_report_Crowding20v40.pdf
├── report_Crowding20v40.md
├── report_Crowding20v40_figures/       images used by the Markdown report
├── plots/
├── data_output/
└── statistics/
```

| File | What it is |
|---|---|
| `run_summary_<focus>.json` | The [Run Summary](help:run-summary): counts, the Focus's definition, the Exclusion Group and chambers removed, figures written, Not Applicable and Left Out items, the omnibus test, factorial model headlines. The Hub and the Project Report read this instead of re-analysing. |
| `<experiment>_report_<focus>.pdf` | The [experiment report](help:experiment-report) for this Focus. |
| `report_<focus>.md` | The same report as Markdown. Its images are in `report_<focus>_figures/`. |

### plots/ (PNG, 150 dpi)

| File | Figure |
|---|---|
| `km_with_risk_table_<focus>.png` | KM curves with at-risk table |
| `kaplan_meier_<focus>.png` | Kaplan-Meier curves |
| `cumulative_events_<focus>.png` | Cumulative deaths |
| `survival_distribution_<focus>.png` | Lifespan distribution |
| `mortality_qx_<focus>.png` | Mortality (qx) |
| `hazard_rate_<focus>.png` | Hazard rate |
| `smoothed_hazard_<focus>.png` | Smoothed hazard |
| `nelson_aalen_<focus>.png` | Nelson-Aalen cumulative hazard |
| `number_at_risk_<focus>.png` | Number at risk |
| `hazard_ratio_forest_<focus>.png` | Hazard-ratio forest (2+ treatments) |
| `log_log_diagnostic_<focus>.png` | Log-log diagnostic (2+ treatments) |
| `km_faceted_<focus>.png` | Faceted Kaplan-Meier (Focus varies 2+ factors) |
| `interaction_lifespan_<focus>.png` | Lifespan interaction plot (Focus varies 2+ factors) |
| `defined_<plot name>_<focus>.png` | A [Defined Plot](help:defined-plots) drawn under this Focus |

Only figures that were drawn are present. A figure that is Left Out, Not Applicable, or not offered to this Focus has no file, and a copy left by an earlier run is deleted. The same goes for a Defined Plot's figure that this run did not draw.

### data_output/ (CSV)

| File | Contents |
|---|---|
| `individual_data_<focus>.csv` | One row per individual in the Focus: time, event, chamber, treatment, factors. |
| `lifetables_<focus>.csv` | The life table per treatment (see [Life tables](help:lifetables)). |
| `summary_<focus>.csv` | Summary statistics per treatment. |
| `median_survival_<focus>.csv` | Median survival per treatment, with its 95% confidence interval. |
| `mean_survival_<focus>.csv` | Mean survival (RMST to the common τ) per treatment. |

### statistics/ (CSV)

| File | Written when |
|---|---|
| `survival_quantiles_<focus>.csv` | always |
| `lifespan_treatment_stats_<focus>.csv` | always (when there is data) |
| `lifespan_factor_stats_<focus>.csv` | the Focus varies two or more factors |
| `logrank_pairwise_<focus>.csv` | log-rank pairwise ran |
| `gehan_wilcoxon_pairwise_<focus>.csv` | Gehan-Wilcoxon ran |
| `hazard_ratios_<focus>.csv` | pairwise hazard ratios ran |
| `factorial_01_coefficients_<focus>.csv`, `factorial_01_ph_test_<focus>.csv` | the Cox factorial model ran |
| `factorial_02_coefficients_<focus>.csv` | the RMST factorial model ran |
| `parametric_aic_<focus>.csv` | parametric AFT models ran (one row per treatment × model, including those not fitted and why) |

The omnibus log-rank result is in the Run Summary and the report, not in a CSV. The parametric AFT comparison is in its CSV, the Run Summary and the report.

## Which button writes what

- **Run analysis** (Analyze panel), the `run_analysis` script step, and a Batch Run write everything above for the Focus. Each run also deletes files an earlier run wrote for items now left out or not computable.
- **Generate plots** (Plots panel) redraws only the ticked figures, and the Defined Plots about the Focus, into `plots/`. The statistics, the report and the Run Summary stay as the last full run wrote them.
- **Render publication figures** (Project panel) writes curated Publication Figures to `<experiment>/figures/<focus>/<plot id>_<focus>.svg` (or `.pdf`, `.png`). It writes them only for Focuses whose saved results are current.

## Project level

```
MyProject/
├── project.yaml
├── plot_specs.yaml                   Publication Figure specs and styles
├── MyProject_report.pdf              the Project Report
├── MyProject_report.md
├── MyProject_report_figures/
├── MyProject_narrative.json          the saved AI narrative, when one was written
├── cohort_a/                         a Member Experiment, laid out as above
└── cohort_b/
```

The Project Report and the AI narrative are named after the Project's directory. The narrative's paragraphs are deleted from that file once the Focus they describe is re-analysed (see [The AI narrative](help:ai-narrative)). A Batch folder holds an optional `batch.yaml` — written when you choose a script in the Batch panel's picker — and no results of its own.

## Renaming and deleting Focuses

- Renaming a Focus **in the Focus window** moves its folder and renames the `_<focus>` suffix of every file inside it, so nothing is lost. The Markdown report's image folder (`report_<focus>_figures/`) is renamed with it, and the report's image links are rewritten to match.
- Renaming one **by hand in the YAML**, or deleting one, leaves its folder behind as **Orphaned Results**. The Hub lists these and offers *adopt as…* or *delete*. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).
- `plots`, `statistics` and `data_output` directly under `analysis/`, `analysis/run_summary.json`, `analysis/report.md` and `analysis/*_report.pdf` are results from before Focuses existed. They are shown as legacy results and offered for deletion, never adopted. For this reason, a Focus cannot be named `plots`, `statistics` or `data_output`.

## Pitfalls

- **Re-running replaces.** A new run of a Focus overwrites that Focus's previous files. Copy a folder elsewhere if you want to keep an earlier version.
- **Open files.** If a figure is open in another program when a run tries to delete or overwrite it, the old file can be left in place.
- **Moving the data file** does not move results. Results live under `analysis/`, not next to the data file.

## See also

- [The Run Summary](help:run-summary)
- [The experiment report](help:experiment-report)
- [What a Focus is](help:focus)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [Publication Figures, Specs and Styles](help:publication-figures)
- [The Project Report](help:project-report)
