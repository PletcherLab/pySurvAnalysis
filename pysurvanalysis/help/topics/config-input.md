# The input: section

The `input:` section of `survival_config.yaml` tells the loader how to read a **CSV or TSV** data file: long or wide layout, which columns hold the time and the event, and which columns are factors. A DLife workbook (`.xlsx`) is self-describing: its Design sheet names the factors, and RawData has fixed column names. So for a workbook this section has no effect beyond the `format` value the app writes when adopting it.

All keys are optional. A missing key takes the default below.

## Keys

| Key | Type | Default | Effect |
|---|---|---|---|
| `format` | `auto` / `excel` / `long` / `wide` | `auto` | For CSV/TSV: `long` or `wide` forces the layout. `auto` (and `excel`) detects it: long if the header holds both `time_col` and `event_col`, wide otherwise. Ignored for `.xlsx`, which is always read as a DLife workbook. |
| `time_col` | string | `Age` | Long format: the column holding each individual's age at death or censoring. Also used by `auto` detection. |
| `event_col` | string | `Event` | Long format: the column holding 1 (death observed) or 0 (censored). Also used by `auto` detection. |
| `factor_cols` | list of strings | `null` (every other column) | Long format: the columns that are treatment factors. Leave `null` to use every column except time and event. List them to ignore extra columns such as an individual ID. |
| `factor_names` | list of two strings | `null` | Wide format: the names of the two factors. Required for wide. |
| `col_mapping` | list of mappings | `null` | Wide format: what each column holds, column by column (see below). Wide needs this or `factor_levels`. |
| `factor_levels` | mapping of factor → list of levels | `null` | Wide format without `col_mapping`: each factor's levels, which the app looks for in the column names (see below). Its factors must be exactly those in `factor_names`. |

## Long format example

A file with columns `Days, Dead, Line, Diet, FlyID`:

```yaml
input:
  format: long
  time_col: Days
  event_col: Dead
  factor_cols: [Line, Diet]     # FlyID is not a factor
```

Without `factor_cols`, `FlyID` would be treated as a factor, and every individual would be its own treatment.

## Wide format example

A file with one column of ages per Sex × Density group and outcome:

```yaml
input:
  format: wide
  factor_names: [Sex, Density]
  col_mapping:
  - {column: F_20x_dead, factor1_level: Female, factor2_level: "20x", event: 1}
  - {column: F_20x_cens, factor1_level: Female, factor2_level: "20x", event: 0}
  - {column: F_40x_dead, factor1_level: Female, factor2_level: "40x", event: 1}
  - {column: F_40x_cens, factor1_level: Female, factor2_level: "40x", event: 0}
  - {column: M_20x_dead, factor1_level: Male,   factor2_level: "20x", event: 1}
  - {column: M_20x_cens, factor1_level: Male,   factor2_level: "20x", event: 0}
  - {column: M_40x_dead, factor1_level: Male,   factor2_level: "40x", event: 1}
  - {column: M_40x_cens, factor1_level: Male,   factor2_level: "40x", event: 0}
```

Each `col_mapping` entry has four keys:

| Key | Meaning |
|---|---|
| `column` | A header in the file. |
| `factor1_level` | The level of the first factor in `factor_names` for every age in this column. |
| `factor2_level` | The level of the second factor. |
| `event` | `1` if the ages in this column are deaths, `0` if they are censorings. |

Every non-empty cell in a mapped column becomes one individual. Columns left out of the mapping are ignored. The order of the entries sets the order of each factor's levels (here `Female` before `Male` and `20x` before `40x`), so put the control level first.

### Without a mapping: factor_levels

When the column names already say what each column holds, list each factor's levels instead of mapping every column:

```yaml
input:
  format: wide
  factor_names: [Sex, Density]
  factor_levels:
    Sex: [Female, Male]
    Density: ["20x", "40x"]
```

Each column name must then mention exactly one level of each factor and an outcome word: `dead`, `death`, `died` or `event` for deaths, `cens`, `censor`, `censored` or `alive` for censorings (`Female_20x_dead`, `Male-40x-censored`). Case and punctuation are ignored, and whole words are matched first, so `Female_20x_dead` is not mistaken for `Male`. Every combination of levels needs both a death column and a censored column; if the names cannot be read that way, loading fails asking for `col_mapping`. The levels are ordered as `factor_levels` lists them, so put the control first.

## Where the format is first written

When the app builds a config around a data file (adopting a workbook or directory into a Project), it writes `input: {format: excel}` for a workbook. For a CSV it writes `format` (long or wide, as detected) together with `time_col: Age` and `event_col: Event`. In a Project, the `input:` block can also live in `defaults:` and is inherited key by key. A member that sets only `time_col` keeps the Project's other input settings.

## Checking it

Validation checks `format` and the wide-format keys:

- `` `input.format` must be auto, excel, long or wide (got '…'). `` — fix the spelling.
- `` `input.format: wide` needs `input.factor_names` (the two factor names). `` and `` `input.factor_names` must name exactly two factors for the wide format. ``
- `` `input.format: wide` needs `input.col_mapping` or `input.factor_levels` to say which cell each column holds. ``
- `` `input.factor_levels` must map each factor to its levels, … ``, `` `input.factor_levels.<factor>` must be a non-empty list of levels. ``, `` … lists a level twice. `` and `` `input.factor_levels` must give levels for exactly the factors in `input.factor_names` (…). ``
- `` `input.col_mapping` must be a list of … entries. ``

Wrong column names show up when the file is loaded (see the error table in [Input data formats](help:data-formats)), not during validation.

## Pitfalls

- **Renamed columns and `auto`.** If your time/event columns are not called `Age`/`Event` and you leave `time_col`/`event_col` unset, `auto` detection will not find them. The file is then treated as wide, and loading fails asking for `factor_names`.
- **ID columns.** In long format every non-time, non-event column is a factor unless you list `factor_cols`.
- **No chambers.** CSV data has no chambers, so Exclusion Groups and the Chamber QC viewer do not apply to it.

## See also

- [Input data formats](help:data-formats)
- [survival_config.yaml reference](help:config-experiment)
- [project.yaml and Project Defaults](help:config-project)
- [Validating configuration](help:validation)
