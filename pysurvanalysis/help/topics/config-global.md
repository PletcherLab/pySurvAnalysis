# The global: section

The `global:` section of `survival_config.yaml` holds the data-source settings an Experiment Type supplies defaults for: the time unit and axis label, the censoring policy, and a quality threshold. In a Project these usually live once in `project.yaml` under `defaults: global:` and are inherited key by key by every member that does not state its own value.

## Example

```yaml
global:
  time_unit: days
  time_label: Age (days)
  assume_censored: true
  min_n_per_chamber: 5
```

This is exactly what a Standard Lifespan experiment is scaffolded with.

## Keys

| Key | Type | Default (Standard Lifespan) | Effect |
|---|---|---|---|
| `time_unit` | string | `days` | The unit your ages are recorded in, as a word. It is used to build the axis label when `time_label` is empty (`Age (<unit>)`), and the Project Report's Divergence Note compares it across members. It does **not** convert anything: ages are analysed exactly as they appear in the data file. |
| `time_label` | string | `Age (days)` | The time-axis label on every analysis figure (and the QC viewer), and the default x-axis label of Publication Figures in the Plot Editor. |
| `assume_censored` | true / false | `true` | DLife workbooks only. When true, each chamber starts with its Design-sheet `SampleSize`, and individuals not accounted for by deaths or explicit censorings are right-censored at the chamber's last census. When false, only what RawData records is counted. No effect on CSV data. See [Censoring policy](help:censoring). |
| `min_n_per_chamber` | non-negative integer | `5` | A per-chamber minimum sample size, where `0` means "off". A chamber with fewer individuals is **flagged, never excluded**: the Chamber QC viewer draws it in amber and lists it, and the report's Data quality section names it as a warning. Whether to exclude it is your QC decision. |

Keys the type does not define are kept as they are. The Project editor shows them too, so they are not lost when the project is saved.

## Where to set it

- **For a whole Project:** open the Project panel and choose **Edit config…**. The *Project Defaults* box has a **Global** form, built from the Experiment Type's own keys. A blank text field means "use the type's default", and nothing is written for it. A checkbox is always written as true or false. See [project.yaml and Project Defaults](help:config-project).
- **For one experiment:** add the key under `global:` in its `survival_config.yaml`. Only state the keys you want to differ. Restating a Project default freezes it in this member, so later Project edits stop reaching it.

## Checking it

**Validate YAMLs** reports:

| Message | Fix |
|---|---|
| `` `global:` must be a mapping. `` | `global:` must be followed by indented `key: value` lines, not a list or a single value. |
| `` `global.time_unit` must be a string (e.g. days). `` | Write a word, e.g. `time_unit: days`. |
| `` `global.assume_censored` must be true or false. `` | Write `true` or `false`, without quotes. `"yes"` or `1` are not accepted. |
| `` `global.min_n_per_chamber` must be a non-negative integer (0 turns the check off). `` | Write a whole number ≥ 0, without quotes. |

## Pitfalls

- **Changing the unit does not rescale the data.** If your workbook's `AgeH` column is in hours and you set `time_unit: days`, every number in every table is still in hours. Only the labels change.
- **`time_label` labels every figure's time axis**: the Hub's and the report's figures, the Defined Plots, and a new Publication Figure's x label. A Publication Figure saved earlier keeps the x label stored in its Spec until you change it in the Plot Editor.
- **Censoring differences between members.** If members of a Project use different `assume_censored` values, the Project Report declares it in its Divergence Note. This difference changes how every unscored individual is counted.

## See also

- [Censoring policy](help:censoring)
- [survival_config.yaml reference](help:config-experiment)
- [project.yaml and Project Defaults](help:config-project)
- [Experiment Types](help:experiment-types)
- [Validating configuration](help:validation)
