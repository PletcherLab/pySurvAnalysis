# Experiment Types

An **Experiment Type** describes the *data source*: what kind of file an experiment reads, the time unit and axis label, the default censoring policy, the default quality settings, the report's sections, and the base set of figures and analyses a run can produce. It deliberately says nothing about the experimental *design*. One data file can hold several designs, so which analyses apply is decided per Focus by its [Focus Shape](help:focus-shape).

Every Member Experiment of a Project must share the Project's Experiment Type. This is the only value checked across members.

## There is one type: Standard Lifespan

| | |
|---|---|
| Key (in YAML) | `standard_lifespan` |
| Label (in the app) | Standard Lifespan |
| Describes | A census-scored lifespan cohort (DLife workbook): chambers of individuals scored to death, with unaccounted individuals treated as censored. |

Standard Lifespan is the general case. Every analysis the app can do is reachable from it, gated by Focus Shape rather than by type. CSV/TSV cohorts are read under it too (see [Input data formats](help:data-formats)).

### Default global: settings

```yaml
global:
  time_unit: days
  time_label: Age (days)
  assume_censored: true
  min_n_per_chamber: 5
```

See [The global: section](help:config-global) for what each does.

### Base Plot Set, in report order

1. KM curves with at-risk table (`km_risk_table`) — the Headline Figure unless the Focus crosses factors
2. Kaplan-Meier curves (`km_curves`)
3. Cumulative deaths (`cumulative_events`)
4. Lifespan distribution (`survival_distribution`)
5. Mortality (qx) (`mortality`)
6. Hazard rate (`hazard`)
7. Smoothed hazard (`smoothed_hazard`)
8. Nelson-Aalen cumulative hazard (`nelson_aalen`)
9. Number at risk (`number_at_risk`)
10. Hazard-ratio forest (`hazard_ratio_forest`) — only when the Focus implies 2+ treatments
11. Log-log diagnostic (`log_log`) — only when the Focus implies 2+ treatments

A Focus that varies two or more factors also gets the **Faceted Kaplan-Meier** (`km_faceted`, which becomes its Headline Figure) and the **Lifespan interaction plot** (`interaction_lifespan`).

### Analysis Set

Log-rank pairwise, log-rank omnibus, Gehan-Wilcoxon pairwise, pairwise hazard ratios (each offered when the Focus implies 2+ treatments), parametric AFT models (always offered), and the interaction analyses (offered when the Focus varies 2+ factors). Lifetables, summary statistics, median and mean survival always run. See [The Analyze panel and Run analysis](help:analyze-panel).

### Report sections

Each run writes an experiment report for its Focus, with these sections in order: Focus · Experiment summary · Survivorship figures · Factorial analysis · Lifespan statistics · Survival comparisons · Data quality. A section with nothing to show is left out of that report. See [The experiment report](help:experiment-report).

## Where the type is set

- **In a Project:** choose it in the Project editor (**Create project…**, **Initialize existing directory…** or **Edit config…**). It is stored as `defaults: experiment_type:` in `project.yaml`. Members scaffolded by the app also write `experiment_type:` into their own config.
- **For a standalone experiment:** the `experiment_type:` key in its `survival_config.yaml`.

A config with no `experiment_type` key is a Standard Lifespan.

## Retired types

Older configs may name types that no longer exist:

| Old key | What it means now |
|---|---|
| `interaction` | The former "Interaction Experiment" (a 2×2 design). Read as Standard Lifespan. Its 2×2 analyses are now the Factorial Battery, offered to any Focus that varies two or more factors. |
| `custom` | The former "no particular type". Read as Standard Lifespan. |

Both keep working. The key is rewritten to `standard_lifespan` the next time the experiment's Focuses are saved. Any other unknown key is an error rather than a silent fallback. An experiment must not be analysed as though it were something else.

## Validation messages

| Message | Fix |
|---|---|
| `Unknown experiment_type '…'. Known types: standard_lifespan, or omit the key.` | Correct the spelling, or delete the key. |
| `<member> is a <type> but the Project's type is <type>. …` | Make the member match the Project (or remove its `experiment_type` so it inherits). |
| `<file> is a <type> but the Project's type is <type>. Every Member Experiment must share it …` | Shown when copying a config into a member. Nothing was copied; choose a config of the Project's type. |

## See also

- [The global: section](help:config-global)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [project.yaml and Project Defaults](help:config-project)
- [The Plots panel and Generate plots](help:plots-panel)
- [Validating configuration](help:validation)
