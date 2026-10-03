# Validating configuration

Validation checks your YAML files for mistakes before a run depends on them: a misspelt key value, a Focus that names a level twice, an `omit:` id that no run produces, or a member whose Experiment Type differs from its Project's. It reads **only the configuration and the directory layout**. It does not load your data. Problems that need the data, such as a Focus naming a level the workbook lacks, are reported as Blocked Focuses (below).

## In the app

- **Validate YAMLs** (Project panel, Create/Load card) checks `project.yaml` and every member's `survival_config.yaml` in the open Project, re-reading them from disk, so an edit made since the Project was opened is checked too. The output log shows:
  - `Project validation problems:` followed by one line per problem, or `Project validation passed.`
  - `divergence — …` for each data-source difference between members (legal, but declared).
  - `blocked — <member>: <status> — <detail>` for each subdirectory a run cannot use.
  - A closing count: `[validate] N file(s) checked, N problem(s), N blocked member(s).`
- With a **standalone experiment** loaded (no Project), the same button checks that one config: `<name> config problems:` and a list, or `<name>: config is valid.`
- The Project card's summary shows `N problem(s) — run Validate YAMLs.` whenever the open Project has problems.
- A Project Script step `validate_project` runs the same check and **stops the script** if anything is wrong.
- The Project Report lists a member's problems under "Why it cannot be analysed as configured" for any Focus that has not been analysed.

Member problems are prefixed with the member's name (`cohort_a: …`).

## survival_config.yaml problems

| Message | What to do |
|---|---|
| `survival_config.yaml, line N: not valid YAML — <problem>. (<path>)` | The file is not YAML at all, so none of the checks below can run (see *YAML syntax errors* below). |
| `Config must be a YAML mapping.` / `… must contain a YAML mapping, got list.` | The file must be `key: value` lines at the top level, not a list or a single value. |
| `Unknown experiment_type '…'. Known types: standard_lifespan, or omit the key.` | Correct or delete `experiment_type`. When this appears, the other checks are skipped until it is fixed. |
| `` `input.format` must be auto, excel, long or wide (got '…'). `` | Fix the value. See [The input: section](help:config-input). |
| `` `input.format: wide` needs … `` / `` `input.factor_names` … `` / `` `input.factor_levels` … `` / `` `input.col_mapping` … `` | A wide-format CSV's keys are missing or malformed. See [The input: section](help:config-input). |
| `` `exclusions:` must be a mapping, e.g. `{group: default}`. `` | Write `exclusions:` then an indented `group: <name>`. |
| `` `global:` must be a mapping. `` | See [The global: section](help:config-global). |
| `` `global.time_unit` must be a string (e.g. days). `` | Write a word. |
| `` `global.assume_censored` must be true or false. `` | Use unquoted `true` or `false`. |
| `` `global.min_n_per_chamber` must be a non-negative integer (0 turns the check off). `` | A whole number ≥ 0. |
| `No input data file found in <dir> (looked in data/ and the directory root).` | Put the `.xlsx`/`.csv`/`.tsv` in `data/` or the directory root, or fix `data_file:`. |

### focuses: problems

| Message | What to do |
|---|---|
| `` `focuses:` must be a mapping of Focus name → {factors: …}. `` | Each Focus is a name followed by an indented body. |
| `A Focus has an empty name.` | Give it a name. |
| `Focus '…' would write to analysis/<slug>/, which is reserved for pre-Focus results; rename it.` | `plots`, `statistics` and `data_output` cannot be Focus names. |
| `Focus '…' and Focus '…' would write to the same output directory (<slug>); rename one.` | Two names that differ only in characters replaced in folder names (spaces, slashes, etc.) clash. Rename one. |
| `` Focus '…' must be a mapping with a `factors:` key. `` | Add a `factors:` block. |
| `` Focus '…' names no factors — give `factors:` at least one factor with its levels. `` | List at least one factor. |
| `Focus '…': factor '…' lists no levels.` | Give the factor at least one level. |
| `Focus '…': factor '…' lists a level twice.` | Remove the duplicate. |
| `` Focus '…': `reference:` must map factor → level. `` | e.g. `reference: {Density: "40x"}`. |
| `Focus '…': reference names factor '…', which the Focus does not name.` | Remove it, or add the factor to `factors:`. |
| `Focus '…': reference level '…' is not one of <factor>'s levels (…).` | Choose one of the listed levels. Watch quoting: `40x` and `"40x"` are the same, but `20` and `"20"` may not be. |
| `` Focus '…': `display_names:` must map treatment → value. `` (or `colours:`) | Use `treatment label: value` pairs. |

### omit: problems

| Message | What to do |
|---|---|
| `` `omit:` must be a mapping, e.g. `{analyses: [parametric_aft]}`. `` | See [The omit: section](help:config-omit). |
| `` `omit.<key>` is not something a run can leave out (use analyses or plots). `` | Only `analyses` and `plots` are allowed. |
| `` `omit.<kind>` must be a list of ids. `` | Write a list. |
| `` `omit.<kind>` names '…', which no run produces. Known: … `` | A misspelt id omits nothing. Use one of the listed ids. |

## project.yaml problems

| Message | What to do |
|---|---|
| `` project.yaml: `defaults: focuses:` is ignored — a member never inherits Focuses. … `` | Remove it. Copy Focuses into members with **Copy Focuses from…**. |
| `` project.yaml: `defaults: factors:` predates Focuses. … `` | Analyse each member once, then remove it. |
| `project.yaml: Unknown experiment_type '…'. …` | Fix `defaults: experiment_type`. Members are not checked until it is fixed. |
| `<member> is a <type> but the Project's type is <type>. …` | Make the member's type match the Project's. |
| `<path> is not a Project — no project.yaml. …` | Shown when opening a folder without one. Use **Create project…** or **Initialize existing directory…**. |

## Blocked members (layout)

A subdirectory of a Project that a run cannot use is a **Blocked Member**. It is listed by Validate YAMLs and the Batch preflight. The rest of the Project still runs.

| Status and detail | Fix |
|---|---|
| `no config — holds <file> but no survival_config.yaml` | Scaffold one: double-click its row in the members table, or **Create config** in *Experiment configs…*. |
| `no config — holds N data files but no survival_config.yaml` | Scaffold the config first, then name the data file. |
| `no data — survival_config.yaml but no .xlsx/.csv/.tsv in data/ or the directory root` | Add the data file. |
| `` no data — `data_file: …` does not exist (looked at …) `` | Correct the path in `data_file:`. |
| `ambiguous — N data files in data/ (…) — which is the experiment?` | **Set data file…** in *Experiment configs…* (or the preflight) writes `data_file:` for you. |
| `unreadable — cannot be listed (permissions?)` | Fix the folder's permissions. |
| `bad config — survival_config.yaml, line N: not valid YAML — …` | Fix the YAML at that line (see *YAML syntax errors* below). |

When loading, the same conditions appear as `<name>: N data files in data (…). Name one with data_file: in survival_config.yaml.` and `<name>: no .xlsx/.csv/.tsv found in … or its data/ subdirectory.`

## Blocked Focuses (need the data)

These are not part of Validate YAMLs. They appear in the Hub's members table (red row, reasons in the tooltip), in the Batch preflight, and as `Focus '…' is blocked:` when a run starts. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).

| Message | Fix |
|---|---|
| `Focus '…' names factor '…', which the data file does not have (factors: …) — rename it to '…'?` | The Design sheet's column was renamed. Accept the suggested rename (preflight) or edit the Focus. |
| `Focus '…' names level '…' of <factor>, which the data file does not contain (levels: …) — rename it to '…'?` | As above, for a level. |
| `Focus '…': treatment '…' is in the data file but has no individuals once exclusions are applied — change the Exclusion Group or drop that level from the Focus` | QC removed every chamber of a cell. |
| `Focus '…' selects no individuals — edit the Focus` | The Focus's filters match nobody. |

## When adding data to a Project

Adding a workbook or directory checks the workbook's headers first. These messages mean it is not a usable DLife workbook:

- `<file>: not a file.` / `<file>: not an .xlsx workbook.` / `<file>: cannot be opened as an Excel workbook (…).`
- `<file>: no 'Design' sheet.` / `<file>: no 'RawData' sheet.`
- `<file>: Design sheet has no 'Chamber' column.` (or `'SampleSize'`, `'StartTime'`)
- `<file>: Design sheet has no treatment factor columns after 'StartTime'.`
- `<file>: RawData sheet is missing AgeH, Censored, ….`
- `<dir> has no data/ subdirectory.` / `No .xlsx file in <dir>/data.` (Add directory)

See [Input data formats](help:data-formats) for the sheet layout.

## Pitfalls

- **Valid is not the same as runnable.** Validation does not open the data. A config can pass and still fail to load, for example with a wrong `time_col`.
- **YAML syntax errors.** A file that is not valid YAML at all (a tab used for indentation, an unclosed quote, a missing colon) is reported as `<file>, line N: not valid YAML — <what the reader found>. (<path>)`. The line is where the broken construct starts: the line with the unclosed quote, or the key missing its colon. A tab gets the hint "(YAML indents with spaces, never tabs)".
  - A member's `survival_config.yaml`: the member is still listed, with that message as its problem (and as a `bad config` Blocked Member), and the rest of the Project validates and runs normally. Nothing runs or writes under the broken file until it is fixed, because a write would replace your file with defaults.
  - `project.yaml`: the Project cannot be opened, since its defaults are unknown. Selecting it shows the message, and the folder stays selected, so **Validate YAMLs** reports it too (`<folder>: validation problems:` and the line). Fix the file and select it again. A standalone Experiment Directory whose `survival_config.yaml` does not parse is treated the same way.
- **Divergence is not a problem.** `divergence — …` lines are informational. They also appear in the Project Report's Divergence Note.

## See also

- [survival_config.yaml reference](help:config-experiment)
- [project.yaml and Project Defaults](help:config-project)
- [The Batch preflight](help:preflight)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [Troubleshooting](help:troubleshooting)
