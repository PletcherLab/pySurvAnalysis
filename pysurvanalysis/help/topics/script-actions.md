# Script action reference

Every action a script step can name, with its parameters. In YAML a step is the action key plus its parameters:

```yaml
- action: hazard_plot
  smoothed: true
  sigma: 3.0
```

A parameter left out takes its default. "List" parameters accept either a YAML list or a comma-separated string (`treatments: A, B`); blank means "all". Actions marked **Requires** are offered only when the Focus Shape admits them; reached anyway, the step is **Not Applicable** for that Focus — logged, recorded, and the script carries on (see [Not Applicable and Left Out](help:not-applicable)). A step naming an action not listed for its level stops the script before it starts.

## Experiment actions

These are available in Experiment Scripts and central experiment scripts. The Standard Lifespan type offers all of them.

### Summary

| Action | Title in the editor | Category | Parameters | Requires | Writes files? |
|---|---|---|---|---|---|
| `load_data` | Load data | Load | — | — | no |
| `apply_exclusions` | Apply exclusions | Load | `group` | — | no |
| `filter` | Filter rows | Load | `factor`, `value` | — | no |
| `run_in_focuses` | Run in focuses | Scripts | `only` | — | no |
| `run_analysis` | Run analysis | Analyze | — | — | yes |
| `report` | Generate report | Tools | `output_dir` | — | yes |
| `render_publication_figures` | Render publication figures | Plots | `format` | — | yes |
| `chamber_overlay_qc` | Chamber QC overlay | QC | `treatment` | — | no |
| `km_curves` | KM curves | Plots | `treatments`, `show_ci`, `with_risk_table` | — | no |
| `nelson_aalen` | Nelson-Aalen | Plots | `treatments` | — | no |
| `hazard_plot` | Hazard rate | Plots | `smoothed`, `sigma` | — | no |
| `mortality` | Mortality (qx) | Plots | — | — | no |
| `forest_plot` | Hazard-ratio forest | Plots | — | comparison | no |
| `faceted_km` | Faceted KM | Plots | `show_ci` | factorial plot | no |
| `interaction_plot` | Lifespan interaction plot | Plots | `metric` | factorial plot | no |
| `log_rank_pairwise` | Log-rank pairwise | Analyze | — | comparison | no |
| `log_rank_omnibus` | Log-rank omnibus | Analyze | — | comparison | no |
| `gehan_wilcoxon` | Gehan-Wilcoxon pairwise | Analyze | — | comparison | no |
| `parametric_aft` | Parametric AFT models | Analyze | — | — | no |
| `cox_ph` | Cox PH (interactions) | Analyze | `factors`, `include_interactions` | — | no |
| `rmst` | RMST regression | Analyze | `factors`, `tau` | — | no |
| `cox_interaction` | Cox factorial model | Analyze | — | factorial model | no |
| `rmst_interaction` | RMST factorial model | Analyze | `tau` | factorial model | no |

The requirements: **comparison** needs at least two populated treatments in the Focus; **factorial plot** needs a Focus that varies two or more factors (with at least two populated treatments); **factorial model** additionally needs every pair of those factors fully crossed in the populated cells. See [Focus Shape](help:focus-shape).

"Writes files? no" means a quick look: tests print to the log, figures open as tabs in the Hub's plot area (and are discarded in unattended runs). Nothing is saved, nothing goes into the report, and the `omit:` block is not consulted. Only `run_analysis`, `report` and `render_publication_figures` produce lasting output.

### Data steps

**`load_data` — Load data.** No parameters. Loads the experiment's data file exactly as its `survival_config.yaml` describes it (format, columns, censoring policy), with the config's active Exclusion Group and any chambers added by earlier `apply_exclusions` steps removed. Factors are discovered from the file. Under a Focus the in-memory data is that Focus's slice; otherwise it is the whole file. Logs the number of individuals and treatments. Needed before the quick-look analysis and plot steps; `run_analysis` does not need it.

**`apply_exclusions` — Apply exclusions.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `group` | text | `default` | Name of a group in `qc/remove_chambers.csv` |

Adds that group's chambers to the set this run excludes, *in addition to* the config's active Exclusion Group. Every later `load_data`, `run_analysis` and `report` step leaves them out. If data is already loaded and has a chamber column, the chambers are also dropped from it — from the whole loaded file as well as the current Focus's slice, so a Focus cut later under `run_in_focuses` does not get them back. Logs how many chambers the group lists; a name with no saved group excludes nothing.

The report and Run Summary of every analysis the script then runs name **both** groups, joined with `+` (for example `default + extra`), and count the chambers of both. Because the config's active group alone would not reproduce that run, the Hub shows its results as **Out of Date** ("analysed under exclusion group 'default + extra' …"). To make a group part of every run, set it as the active group on the QC panel instead. See [Exclusion Groups](help:exclusions).

**`filter` — Filter rows.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `factor` | factor (drop-down) | none — required | Column to filter on |
| `value` | text | none | Value to keep (compared as text) |

Keeps only the rows where the column equals the value, and logs how many rows remain. Fails if `factor` is blank or not a column of the loaded data. Needs loaded data. It affects only the quick-look steps after it in the same Focus; `run_analysis` reloads from the file and ignores it. To analyse a subset with saved results, declare a Focus instead.

### Structure

**`run_in_focuses` — Run in focuses.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `only` | list | blank = every Focus | Focus names to run |

Splits the script: steps before it run once, steps after it run once per Focus (continue-on-error). Names in `only` that the experiment does not declare are logged and skipped. At most one per script. See [Running Experiment Scripts](help:experiment-scripts).

### Saved analysis and outputs

**`run_analysis` — Run analysis.** No parameters. The same run as the Hub's **Run analysis** button: the Analysis Set and Plot Set for the Focus, the Factorial Battery when the Focus varies two or more factors, less whatever the config's `omit:` block leaves out. Writes `analysis/<focus>/` — tables, figures, the report and `run_summary_<focus>.json`. Later quick-look steps in the same Focus reuse its data and life tables. Placed where no Focus is in force (before `run_in_focuses` in an unattended run), it analyses **every** declared Focus; a Focus that fails makes the step fail after the others have run. See [The Analyze panel and Run analysis](help:analyze-panel).

**`report` — Generate report.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `output_dir` | folder | blank | A folder to write a copy of each report into as well; blank = only `analysis/<focus>/` |

If an earlier `run_analysis` in this Focus produced a result, rewrites that Focus's report (PDF and Markdown) from it. Otherwise it runs the full analysis — which writes the report — for the step's Focus, or for every Focus when none is in force. The report always goes to `analysis/<focus>/`; with `output_dir`, each report is also written there, under the same Focus-suffixed names (`report_<focus>.md`, `<member>_report_<focus>.pdf`), so several Focuses can share the folder. The analysis outputs themselves stay in `analysis/<focus>/`.

**`render_publication_figures` — Render publication figures.**

| Parameter | Type | Default | Choices |
|---|---|---|---|
| `format` | choice | `svg` | `svg`, `pdf`, `png` |

Renders the curated Publication Figures (those saved in `plot_specs.yaml` from the Plot Editor) into `figures/<focus>/<plot>_<focus>.<format>`, for the step's Focus — or, with no Focus in force, for each Focus whose saved results are current (not analysed and Out of Date Focuses are named and skipped). With nothing curated it renders nothing and says so. svg and pdf keep text editable. See [Publication Figures, Specs and Styles](help:publication-figures).

### Quality control

**`chamber_overlay_qc` — Chamber QC overlay.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `treatment` | text | blank = every treatment | One treatment to draw |

Draws one figure per treatment, in the Focus's display order, overlaying the Kaplan-Meier curve of each chamber, so an aberrant vial stands out. The time axis carries the experiment's time label. Chambers excluded by earlier `apply_exclusions` steps are marked. If the data has no chamber column (long-format CSV), it logs that and does nothing. See [The Chamber QC viewer](help:qc-viewer).

### Quick-look figures

These draw a Focus the way the saved figures do: the experiment's time-axis label (`global.time_label`, or `Age (<unit>)`), and the Focus's treatment order, display names and colours. The forest uses the display names too.

**`km_curves` — KM curves.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `treatments` | list | blank = all | Treatments to draw |
| `show_ci` | on/off | on | Draw 95% confidence bands |
| `with_risk_table` | on/off | off | Add the number-at-risk table beneath |

See [Kaplan-Meier curves](help:plot-km-curves).

**`nelson_aalen` — Nelson-Aalen.** `treatments` (list, blank = all). Cumulative hazard by treatment. See [Nelson-Aalen cumulative hazard](help:plot-nelson-aalen).

**`hazard_plot` — Hazard rate.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `smoothed` | on/off | off | Kernel-smoothed hazard instead of the raw interval hazard |
| `sigma` | number, 0.1–20 | 3.0 | Smoothing width (the same default as the Plot Set's smoothed hazard figure); used only when `smoothed` is on |

See [Hazard rate](help:plot-hazard) and [Smoothed hazard](help:plot-smoothed-hazard).

**`mortality` — Mortality (qx).** No parameters. Interval mortality probability. See [Mortality (qx)](help:plot-mortality).

**`forest_plot` — Hazard-ratio forest.** No parameters. Requires comparison. Computes the pairwise hazard ratios and draws them; if there are none, logs that and draws nothing.

**`faceted_km` — Faceted KM.** `show_ci` (on/off, default off). Requires factorial plot. One panel per level of the Focus's first varying factor, curves coloured by the others. Needs a Focus. See [Faceted Kaplan-Meier](help:plot-km-faceted).

**`interaction_plot` — Lifespan interaction plot.** `metric` (choice `median` or `mean`, default `median`). Requires factorial plot. Kaplan-Meier median (or restricted mean) lifespan per cell with its 95% interval, censoring-aware, the first varying factor on x; non-parallel lines suggest interaction. Needs a Focus. See [Lifespan interaction plot](help:plot-interaction-lifespan).

### Quick-look statistics

These print their result tables to the log.

- **`log_rank_pairwise`** — Mantel-Cox log-rank test for every pair of treatments. Requires comparison. See [Log-rank pairwise](help:analysis-logrank-pairwise).
- **`log_rank_omnibus`** — one k-sample log-rank test across all treatments. Requires comparison. See [Log-rank omnibus](help:analysis-logrank-omnibus).
- **`gehan_wilcoxon`** — Gehan-Wilcoxon (early-weighted) test for every pair. Requires comparison. See [Gehan-Wilcoxon pairwise](help:analysis-gehan-wilcoxon).
- **`parametric_aft`** — fits Weibull, log-normal and log-logistic accelerated-failure-time models to each treatment and logs the AIC table (one row per treatment × model, with ΔAIC, log-likelihood, the model's median and why a treatment or model was not fitted), then the best model per treatment. See [Parametric AFT models](help:analysis-parametric-aft).

**`cox_ph` — Cox PH (interactions).**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `factors` | list of factors | blank = the Focus's varying factors | Factors in the model |
| `include_interactions` | on/off | on | Fit the pairwise interaction terms; off fits main effects only |

Fits a Cox proportional-hazards model on the Focus's data, with each factor's Reference Level as baseline — main effects plus every pairwise interaction, or main effects alone with `include_interactions` off. Logs n, events, AIC, concordance and the coefficient table, and, when interactions are fitted, the likelihood-ratio interaction test (main-effects model against the interaction model). See [The Cox factorial model](help:cox-factorial).

**`rmst` — RMST regression.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `factors` | list of factors | blank = the Focus's varying factors | Factors in the model |
| `tau` | number ≥ 0 | 0 (= chosen automatically) | Restriction time τ, in the data's time unit |

Restricted mean survival time pseudo-value regression with full-factorial interactions; logs τ and the coefficient table. The model always includes every pairwise interaction. (Older scripts may carry an `include_interactions` key on this step; it never had an effect and is now ignored.) See [The RMST factorial model](help:rmst-factorial).

**`cox_interaction` — Cox factorial model.** No parameters. Requires factorial model. The Factorial Battery's Cox model on the Focus's varying factors: main effects plus every pairwise interaction, relative to the Reference Levels. Logs the formula, the Reference Levels, the interaction likelihood-ratio test and the coefficients.

**`rmst_interaction` — RMST factorial model.** `tau` (number ≥ 0, default 0 = automatic). Requires factorial model. The RMST companion to the Cox factorial model, with no proportional-hazards assumption. See [Interaction analyses](help:analysis-interaction).

## Project actions

These are available only in Project Scripts (`project.yaml` → `scripts:`).

| Action | Title in the editor | Parameters |
|---|---|---|
| `validate_project` | Validate project | — |
| `run_in_experiments` | Run in experiments | `script`, `only` |
| `render_publication_figures` | Render publication figures | `format` |
| `project_report` | Project report | `formats`, `with_narrative`, `provider` |
| `generate_ai_narrative` | Generate AI narrative | `provider` |

**`validate_project` — Validate project.** No parameters. Checks the Project and every member: that all members share the Project's Experiment Type, each member's own configuration problems, and `defaults:` keys the Project should no longer carry. Any problem **stops the Project Script**, listing the problems. Otherwise logs how many members were validated and any divergence in data-source settings, which is reported but not a failure.

**`run_in_experiments` — Run in experiments.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `script` | text | none — required | Name of the Experiment Script to run |
| `only` | list | blank = every member | Member names to run |

Runs the named Experiment Script in each member, continue-on-error, with each log line prefixed `[member]`. The name is looked up in the Project's central `experiment_scripts:`, then the member's own `scripts:`, then the built-ins. A member with no script of that name, or a name in `only` that is not a member, is logged, counted as a failure and skipped; a member whose run fails is counted and the next member runs. A script that names an action the member's type does not provide is a hard error that **stops the Project Script**. Ends with `n/m member(s) completed`.

**`render_publication_figures` — Render publication figures.** `format` (choice `svg`, `pdf`, `png`; default `svg`). For each member with curated figure specs, renders them for each of its current Focuses into the member's `figures/<focus>/`. Members with nothing curated are skipped; a Project with nothing curated renders nothing and says so.

**`project_report` — Project report.**

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `formats` | list | `pdf,md` | Which files to write (`pdf`, `md`) |
| `with_narrative` | on/off | off | Generate the AI narrative first (saving it) and include it |
| `provider` | choice: blank, `anthropic`, `openai` | blank (first configured provider) | The narrative's provider; used only when `with_narrative` is on |

Writes `<project>_report.pdf` and/or `<project>_report.md` in the Project folder from each Focus's saved results. Fails if nothing was written. See [The Project Report](help:project-report).

**`generate_ai_narrative` — Generate AI narrative.**

| Parameter | Type | Default | Choices |
|---|---|---|---|
| `provider` | choice | blank (first configured provider) | blank, `anthropic`, `openai` |

Asks the AI provider for a paragraph per current Focus and an across-Focuses paragraph, saves them to `<project>_narrative.json` in the Project folder, and logs how many sections were written and where. Never fails the script: a provider problem is logged and the script continues. It does not put the text in a report; to include the narrative in the Project Report, use `project_report` with `with_narrative: true`. See [The AI narrative](help:ai-narrative).

## See also

- [Experiment and Project Scripts](help:scripts-overview)
- [The Script Editor](help:script-editor)
- [Running Experiment Scripts](help:experiment-scripts)
- [Project Scripts](help:project-scripts)
- [Focus Shape — what a Focus is offered](help:focus-shape)
