# Input data formats

pySurvAnalysis reads three kinds of file: a **DLife Excel workbook** (`.xlsx`), which records chambers of individuals scored at each census, and **CSV/TSV files** (`.csv`, `.tsv`) holding one record per individual, in either *long* or *wide* layout. Whatever the format, the loader turns the file into one row per individual with an age (`time`), an outcome (`event`: 1 = death observed, 0 = right-censored), a chamber id, and one column per treatment factor. Every analysis starts from that table.

The file type is decided by its extension. For a workbook, `input.format` in `survival_config.yaml` makes no difference. For a CSV/TSV, `input.format` chooses between long and wide (see [The input: section](help:config-input)).

## Where the data file lives

Each Experiment Directory has exactly one data file. The app looks for it in this order:

1. The file named by `data_file:` in `survival_config.yaml`, if that key is set (a path relative to the experiment directory, or an absolute path).
2. Otherwise, any `.xlsx`, `.csv` or `.tsv` in the `data/` subdirectory.
3. Otherwise, any such file at the directory root.

The search stops at the first place that holds anything. If that place holds **more than one** candidate, the app refuses to guess and the member is *Blocked* until you name one with `data_file:` (the **Set data file…** button in the Project panel's *Experiment configs…* dialog writes this key for you). Excel lock files (`~$…`) and `remove_chambers.csv` are never treated as data.

## The DLife workbook (.xlsx)

A DLife workbook holds a census: for each chamber, how many individuals died (or were censored) between successive census times. The app reads these sheets:

| Sheet | Required | What the app reads |
|---|---|---|
| `Design` | yes | One row per chamber: `Chamber`, `SampleSize`, `StartTime`, then the treatment factors |
| `RawData` | yes | One row per chamber per census: `AgeH`, `Chamber`, `IntDeaths`, `Censored` |
| `ChamberFlags` | no | `Chamber` and `Excluded`; chambers with `Excluded` = 1 are removed from every run |
| `DefinedPlots` | no | Named treatment groupings drawn as extra Kaplan-Meier figures |
| `PrivateData` | no | `AssumeCensored` (1 or 0), read only when a config is first written for the workbook |

Other sheets and extra columns are ignored.

### Design sheet

- `Chamber` — the chamber id, matching `Chamber` in RawData.
- `SampleSize` — how many individuals were placed in the chamber at the start. Used only when assumed censoring is on.
- `StartTime` — marks where the factor columns begin. Its value is not used in any calculation.
- **Every column after `StartTime` is a treatment factor** (for example `Sex`, `Genotype`, `Diet`). You never declare factors anywhere else; they are *discovered* from these columns. There must be at least one.

The levels of each factor are discovered in **order of first appearance** down the Design sheet, not alphabetically. That order becomes the default display order and, through it, the default Reference Level of each factor, so put the control level in the first rows if you want it to be the baseline. A blank factor cell means "no level recorded": those individuals belong to no treatment of any Focus that names that factor, and each run says how many there were.

### RawData sheet

- `AgeH` — the age at that census. It is used as-is as the survival time. No unit conversion is done; `global.time_unit` and `global.time_label` only label the axes.
- `Chamber` — which chamber the row belongs to.
- `IntDeaths` — deaths observed since the previous census; each becomes one individual with `event` = 1 at this age.
- `Censored` — individuals removed alive (escaped, lost, sacrificed) since the previous census; each becomes one individual with `event` = 0 at this age.

RawData rows whose chamber does not appear on the Design sheet are skipped.

### Assumed censoring

With `global.assume_censored: true` (the default), each chamber's starting number is its `SampleSize`. Individuals not accounted for by `IntDeaths` and `Censored` are added as right-censored at that chamber's **last census age**. With `false`, a chamber's cohort is just the deaths plus explicit censorings in RawData, and nothing is added. See [Censoring policy](help:censoring).

The `PrivateData` sheet's `AssumeCensored` value is read only when the app writes a config around a workbook (adding a workbook or directory to a Project). It then seeds `global.assume_censored`. After that, the config decides, and editing the sheet has no effect.

### ChamberFlags sheet

Any chamber with `Excluded` = 1 is dropped before analysis, in every run, whatever Exclusion Group is active. Reports show these as removed "by the workbook" when no group is active. The Chamber QC viewer still shows flagged chambers, because it loads every chamber. To exclude chambers from inside the app, use an [Exclusion Group](help:exclusions).

### DefinedPlots sheet

There is one column per plot. **Row 1** holds the plot's name. From **row 6** down, each cell names one treatment as a full label, with the levels of every Design factor joined by `/` in Design-column order (e.g. `Female/20x`). Only the text before the first comma in a cell is used, and the first empty cell ends that column's list. See [Defined Plots](help:defined-plots).

## CSV/TSV, long format

One row per individual. `.csv` is comma-separated and `.tsv` is tab-separated.

```
Age,Event,Sex,Genotype
52.5,1,F,wCS
61.0,1,F,wCS
70.0,0,M,mDilp235bx
```

- **Time column** — default name `Age`. Change it with `input.time_col`.
- **Event column** — default name `Event`. Change it with `input.event_col`. It must contain only 0 (censored) and 1 (death).
- **Factor columns** — by default every other column. To use only some columns as factors (for example, to ignore an ID column), list them in `input.factor_cols`.

Rows whose time or event is blank or not numeric are dropped, and counted: the run log and the report's Data quality section say how many (`N row(s) dropped: their time or event is blank or not a number.`). Levels are discovered in the order they first appear in the file.

## CSV/TSV, wide format

One column per group, where a group is a combination of two factor levels plus an outcome. Each column lists the ages of the individuals in that group. Columns can have different lengths.

```
F_20x_dead,F_20x_cens,F_40x_dead,F_40x_cens,M_20x_dead,M_20x_cens,M_40x_dead,M_40x_cens
50,70,48,70,44,70,41,70
55,,52,,47,,45,
```

The wide format supports **exactly two factors**. You must give `input.factor_names`, the two factor names, and one way to tell which levels and outcome each column holds (see [The input: section](help:config-input) for both examples):

- `input.col_mapping` – an explicit entry per column. Columns not named in the mapping are ignored. The factor levels are ordered as they first appear in `col_mapping`.
- `input.factor_levels` – each factor's levels. The app then reads each column's name: it must mention exactly one level of each factor and an outcome word (`dead`, `death`, `died` or `event` for deaths; `cens`, `censor`, `censored` or `alive` for censored). Whole words separated by `_`, `-`, spaces or dots are matched first, so `Female_20x_dead` is Female and not Male. Every level combination must have both a death and a censored column, or loading fails asking for `col_mapping`. The levels are ordered as `factor_levels` lists them.

Each non-empty cell becomes one individual.

## Long or wide? (format: auto)

With `input.format: auto` (the default), a CSV/TSV is read as **long** if its header contains both the time column and the event column, and as **wide** otherwise. If you renamed your columns, set `time_col`/`event_col` or set `format: long` explicitly. Otherwise the file will be treated as wide and fail for lack of `factor_names`.

## CSV inputs have no chambers

Individual-level CSV data has no chamber identities (the chamber column reads `N/A`). So an Exclusion Group cannot remove anything from a CSV experiment, and the Chamber QC viewer does not apply. Reports record the group in force with zero chambers removed.

## Error messages from the loader

| Message | Cause and fix |
|---|---|
| `No treatment factor columns found after StartTime in Design sheet` | Add factor columns to the right of `StartTime`. |
| `RawData sheet missing columns: {...}` | RawData needs `AgeH`, `Chamber`, `IntDeaths`, `Censored`. |
| `Long-format CSV missing columns: [...]` | The time/event column names don't match. Set `input.time_col` / `input.event_col`. |
| `No factor columns found in CSV. Specify factor_cols explicitly.` | The file has only time and event columns. |
| `Factor columns not found in CSV: [...]` | A name in `input.factor_cols` is not a column header. |
| `Event column must contain only 0 and 1 values.` | Recode the event column to 0/1. |
| `factor_names is required for wide-format CSV loading.` | Give `input.factor_names` (two names), or fix the column names if the file is really long format. |
| `Wide format requires exactly 2 factor names.` | `input.factor_names` must list exactly two names. |
| `Wide-format column not found: …` | A `column:` in `col_mapping` is not a header in the file. |
| `Wide column '…' must set event to 0 or 1.` | Each `col_mapping` entry needs `event: 0` or `event: 1`. |
| `A wide-format CSV needs input.col_mapping, or input.factor_levels (each factor's levels, matched against the column names).` | Give one of the two. |
| `Could not infer complete wide mapping from column names. Mapped N columns, expected M. Provide explicit col_mapping.` | With `factor_levels`, some column names do not name one level of each factor plus an outcome, or a combination lacks its death or censored column. Rename the columns or give `col_mapping`. |
| `Unsupported file type: …` | Only `.xlsx`, `.csv` and `.tsv` are read. |

## Pitfalls

- **Level order is set by the data.** It is set by the first rows of the Design sheet (or CSV), not by the alphabet. Once a Focus is saved, its level order is frozen in the config, so re-sorting the sheet later does not move a Reference Level.
- **More deaths than `SampleSize`.** If RawData records more deaths and censorings for a chamber than its `SampleSize`, nothing extra is added, N uses the recorded count, and the run warns: `Chamber <id>: RawData records <n> deaths and censorings but its SampleSize is <s> — N uses the <n> recorded; check the Design sheet or RawData.` The warning appears in the run log and the report's Data quality section, whatever the censoring policy.
- **Ages are not adjusted for `StartTime`.** Survival time is `AgeH` exactly as recorded.

## See also

- [The input: section](help:config-input)
- [Censoring policy](help:censoring)
- [Defined Plots](help:defined-plots)
- [Exclusion Groups](help:exclusions)
- [survival_config.yaml reference](help:config-experiment)
