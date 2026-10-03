# The omit: section — leaving analyses and figures out

The `omit:` section of `survival_config.yaml` lists the optional analyses and figures that **every run of this experiment leaves out**. It is what the unticked boxes on the Hub's Analyze and Plots panels are saved as. Because it is configuration rather than a setting of the Hub window, **Run analysis** in the Hub, an Experiment Script's `run_analysis` step, and a Batch Run all leave out the same things and produce the same report.

The block records what is left *out*, not what is included. A config nobody has touched runs everything, and an analysis added by a later version of the app is included until someone unticks it.

## Example

```yaml
omit:
  analyses: [parametric_aft, gehan_wilcoxon]
  plots: [number_at_risk, survival_distribution]
```

A single id may be written without brackets (`analyses: parametric_aft`). An empty or missing list leaves nothing out.

## Keys

| Key | Type | Default | Effect |
|---|---|---|---|
| `analyses` | list of analysis ids | `[]` | These optional analyses are not computed, and each is recorded as Left Out. |
| `plots` | list of plot ids | `[]` | These figures are not drawn, and each is recorded as Left Out. |

Any other key under `omit:` is a validation error.

### Analysis ids

| Id | Hub label | Offered when |
|---|---|---|
| `logrank_pairwise` | Log-rank pairwise | the Focus implies 2+ treatments |
| `logrank_omnibus` | Log-rank omnibus | the Focus implies 2+ treatments |
| `gehan_wilcoxon` | Gehan-Wilcoxon pairwise | the Focus implies 2+ treatments |
| `hazard_ratios` | Pairwise hazard ratios | the Focus implies 2+ treatments |
| `parametric_aft` | Parametric AFT models | always |
| `interaction` | Interaction analyses (Cox + RMST factorial models) | the Focus varies 2+ factors |

Lifetables, summary statistics, median and mean survival are the survivorship core. They always run and cannot be omitted.

### Plot ids

| Id | Figure | In the Standard Lifespan Plot Set |
|---|---|---|
| `km_risk_table` | KM curves with at-risk table | yes (the Headline Figure unless the Focus crosses factors) |
| `km_curves` | Kaplan-Meier curves | yes |
| `cumulative_events` | Cumulative deaths | yes |
| `survival_distribution` | Lifespan distribution | yes |
| `mortality` | Mortality (qx) | yes |
| `hazard` | Hazard rate | yes |
| `smoothed_hazard` | Smoothed hazard | yes |
| `nelson_aalen` | Nelson-Aalen cumulative hazard | yes |
| `number_at_risk` | Number at risk | yes |
| `hazard_ratio_forest` | Hazard-ratio forest | yes, with 2+ treatments |
| `log_log` | Log-log diagnostic | yes, with 2+ treatments |
| `km_faceted` | Faceted Kaplan-Meier | added when the Focus varies 2+ factors |
| `interaction_lifespan` | Lifespan interaction plot | added when the Focus varies 2+ factors |

## In the app

On the Hub, load an experiment and open **Analyze** or **Plots** under the Experiment tile. Each item the Active Focus is offered has a checkbox:

- **Unticking** a box adds its id to `omit:` immediately. **Ticking** it removes the id. The output log confirms the change (`… left out of <experiment>'s runs — survival_config.yaml omit:`).
- A box that is **greyed** is either Not Applicable to this Focus's data (the tooltip gives the reason), or a figure that draws from an unticked analysis.
- Items the Focus is not offered at all are not shown as boxes. One quiet line ("Not offered for Focus …") names them.

The `omit:` block belongs to the **experiment**, not to a Focus. Unticking an analysis leaves it out of every Focus that would have been offered it.

## What a run does with it

- Each left-out item is written in the run log (`Left out — <label>: unticked in the Hub (omit: in survival_config.yaml)`), in the Run Summary's `left_out` list, and in a **Left out of this run** table in the Focus's report section.
- **The forest follows the hazard ratios.** If `hazard_ratios` is omitted, the Hazard-ratio forest is left out too, with the reason "draws from Pairwise hazard ratios, which is unticked". Its Plots box is greyed until you tick the analysis again.
- Files an earlier run wrote for an item that is now left out (its PNG, or its statistics CSV) are **deleted**, so the folder never shows an old figure as if it were current.
- Only items the Focus is offered can be left out of it. Omitting `interaction` means nothing to a one-factor Focus and is not reported there.
- Left Out is not the same as **Not Applicable**. Left Out is your choice. Not Applicable means the data could not support the item. See [Not Applicable and Left Out](help:not-applicable).

## In a Project

`omit:` can be set under `defaults:` in `project.yaml`, and members inherit it. Inheritance is per list: a member that states `omit: {plots: [...]}` keeps the Project's `analyses:` list but replaces its `plots:` list entirely (the lists are not combined). When you tick a box in a member that inherits an omission, the app writes the member's own list, an empty `[]` if necessary, to override the Project's.

## Checking it

| Message | Fix |
|---|---|
| `` `omit:` must be a mapping, e.g. `{analyses: [parametric_aft]}`. `` | Put `analyses:` and/or `plots:` under `omit:`. |
| `` `omit.<key>` is not something a run can leave out (use analyses or plots). `` | Only `analyses` and `plots` are allowed. |
| `` `omit.<kind>` must be a list of ids. `` | Write a list, e.g. `[parametric_aft]`. |
| `` `omit.<kind>` names '<id>', which no run produces. Known: … `` | A misspelt id omits nothing. Copy the id from the list in the message. |

## See also

- [The Analyze panel and Run analysis](help:analyze-panel)
- [The Plots panel and Generate plots](help:plots-panel)
- [Not Applicable and Left Out](help:not-applicable)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [survival_config.yaml reference](help:config-experiment)
