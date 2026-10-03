# Troubleshooting

This page collects the messages pySurvAnalysis shows, grouped by where you meet them, each with its cause and fix. In the Hub, a warning appears in a message box and is copied to the output log with a leading `!`. A task that fails in the background (Run analysis, a script, a Batch Run) is logged with a leading `✘`. Text in angle brackets, like `<name>`, stands for your own folder, file, Focus or factor names.

## Finding the data file

**`<name>: no .xlsx/.csv/.tsv found in <folder> or its data/ subdirectory.`**
The experiment folder has no data file. Put the workbook or CSV in the folder's `data/` subfolder or at its root. (Excel lock files starting `~$` and `remove_chambers.csv` are ignored.)

**`<name>: 2 data files in data (a.xlsx, b.xlsx). Name one with` `data_file:` `in survival_config.yaml.`**
More than one candidate file was found, and the app never guesses. Add `data_file: data/a.xlsx` to the config, or move the extra file out. `data/` is searched before the folder root. The Batch preflight shows the same problem as "N data files in data/ (…) — which is the experiment?".

**`` `data_file: <path>` does not exist (looked at <full path>). ``**
The file named in `data_file:` is missing. Correct the path (relative paths are relative to the experiment folder).

**`No input data file found in <name> (looked in data/ and the directory root).`**
Shown by *Validate YAMLs* and in the Project Report when a member has a config but no data. Add the data file.

**Members-table row reading `missing` in the Config column**
That folder holds no `survival_config.yaml`, so it is not a member yet. Double-click it, or use *Initialize existing directory…*, to scaffold one from the Project Defaults. See [The Experiments card — members](help:project-members).

## Reading the data

**`No treatment factor columns found after StartTime in Design sheet`**
The DLife workbook's Design sheet has no factor columns to the right of `StartTime`. Factors are discovered from those columns, so add them.

**`RawData sheet missing columns: [...]`**, or when adding a workbook: **`<file>: RawData sheet is missing AgeH, ...`**, **`<file>: no 'Design' sheet.`**, **`<file>: Design sheet has no 'Chamber' column.`**
The workbook is not in DLife layout. The Design sheet needs `Chamber`, `SampleSize`, `StartTime` and factor columns after `StartTime`. RawData needs `AgeH`, `Chamber`, `IntDeaths` and `Censored`. See [Input data formats](help:data-formats).

**`Long-format CSV missing columns: [...]`**
The time or event column named in `input:` (default `Age` and `Event`) is not in the CSV. Rename the columns or set `time_col` / `event_col` in [the input: section](help:config-input).

**`Event column must contain only 0 and 1 values.`**
Use 1 for a death and 0 for a censored individual.

**`No factor columns found in CSV. Specify factor_cols explicitly.`** / **`Factor columns not found in CSV: [...]`**
The CSV has no columns besides time and event, or `factor_cols` names columns the file does not have.

**`Wide format requires exactly 2 factor names.`** / **`A wide-format CSV needs input.col_mapping, or input.factor_levels …`** / **`Could not infer complete wide mapping from column names. ... Provide explicit col_mapping.`**
A wide-format CSV needs `factor_names` (two of them) and either `factor_levels` with column names the app can parse, or an explicit `col_mapping`. See [the input: section](help:config-input).

**`Chamber <id>: RawData records <n> deaths and censorings but its SampleSize is <s> …`** (log, report's Data quality section)
More individuals were scored in that chamber than the Design sheet says were set up. The run uses the recorded count. Correct `SampleSize` or the RawData rows.

**`N row(s) dropped: their time or event is blank or not a number.`** (log, report's Data quality section)
Some CSV rows could not be read as an individual. Fix or delete them.

**`Unsupported file type: '.xls'. Expected .xlsx, .csv, or .tsv.`**
Save the file in one of the supported formats.

## Configuration (Validate YAMLs)

**`<file>, line N: not valid YAML — <problem>. (<path>)`**
The file is not YAML at all: often a tab used for indentation ("YAML indents with spaces, never tabs"), an unclosed quote or bracket, or a key missing its colon. Fix that line. A member with a broken `survival_config.yaml` is listed with this problem (and as a `bad config` Blocked Member) while the rest of the Project carries on; nothing runs or saves for that member until it is fixed. A broken `project.yaml` stops the Project opening at all: the Hub shows this message when you select it and keeps the folder selected, so **Validate YAMLs** still reports the line to fix. See [Validating configuration](help:validation).

**`` `input.format` must be auto, excel, long or wide (got '…'). ``** Fix the value in `input:`.

**`` `exclusions:` must be a mapping, e.g. `{group: default}`. ``** Write `exclusions: {group: <name>}`.

**`Unknown experiment_type '…'. Known types: standard_lifespan, or omit the key.`** Remove the key or correct it. A config with no `experiment_type` is a Standard Lifespan. See [Experiment Types](help:experiment-types).

**`` `global.assume_censored` must be true or false. ``** / **`` `global.min_n_per_chamber` must be a non-negative integer (0 turns the check off). ``** Fix the value in [the global: section](help:config-global).

**`` `omit.analyses` names '…', which no run produces. Known: … ``**
A misspelt id in `omit:` would leave nothing out without telling you. Use one of the listed ids, or tick and untick the box in the Hub, which writes the id for you. See [The omit: section](help:config-omit).

**`Focus '<F>' names no factors — give` `factors:` `at least one factor with its levels.`**
**`Focus '<F>': factor '<x>' lists no levels.`** / **`… lists a level twice.`**
Each Focus needs at least one factor, and each factor a non-empty list of distinct levels.

**`Focus '<F>': reference level '<lv>' is not one of <x>'s levels (…).`** / **`Focus '<F>': reference names factor '<x>', which the Focus does not name.`**
The `reference:` must name a level the Focus keeps, for a factor it names. See [Reference Levels](help:reference-level).

**`Focus '<F>' would write to analysis/plots/, which is reserved for pre-Focus results; rename it.`**
A Focus cannot be named `plots`, `statistics` or `data_output`.

**`Focus '<A>' and Focus '<B>' would write to the same output directory (<slug>); rename one.`**
Two names that differ only in spaces or punctuation produce the same folder name. Rename one.

**`project.yaml:` `defaults: focuses:` `is ignored — a member never inherits Focuses.`**
Focuses belong to each member. Remove the block and use *Copy Focuses from…* in the [Focus window](help:focus-window).

**`project.yaml:` `defaults: factors:` `predates Focuses. …`**
An old shared `factors:` block. Members that inherit it become an `Interaction` Focus on their next analysis. Remove it once each member has been analysed.

**`<member> is a … but the Project's type is …`**
Every member must share the Project's Experiment Type.

## Focuses

**`Focus '<F>' is blocked:` followed by reasons**
The Focus cannot run as declared, and nothing was written. The reasons say which of these applies:

- *names factor/level '…', which the data file does not contain … — rename it to '…'?* The Focus is **stale**: the Design sheet changed. Use *Fix selected…* in the Batch preflight, or edit the Focus.
- *treatment '…' is in the data file but has no individuals once exclusions are applied.* The active Exclusion Group (or the workbook's chamber flags) removed every chamber of that cell. Change the Exclusion Group or drop that level from the Focus.
- *Focus '…' selects no individuals.* Edit the Focus.

See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).

**`<experiment>: no Focus could be resolved — is the data file readable?`**
The config declares no Focus, and the data file could not be read to build Unfiltered. Fix the data file first.

**`<experiment> has no Focus named '<F>'. Focuses: …`**
A script, a `run_in_focuses` list or a command named a Focus this member does not declare. In `run_in_focuses`, an unknown name is logged as `Focus '<F>': not declared here — skipped.`

**`The Focus window could not read this experiment's data:` …**
The Focus window needs the data file to discover factors. Fix the error shown, usually one from *Finding the data file* or *Reading the data* above.

**`Cannot save` (Focus window)**
The set of Focuses fails validation (see *Configuration* above), or **`Two Focuses share a name.`**, or **`Focus '<F>': factor '<x>' is ticked but none of its levels is …`** (tick a level, or untick the factor to pool over it). Correct it. The window stays open.

**`Save blocked Focuses?`** (Focus window)
A Focus still names a factor or level the data file lacks (shown in red in the window). Cancel and untick it, or Save to keep it as written; it stays Blocked until the names match the data.

**`analysis/<new>/ already exists; delete or adopt it before renaming '<old>' to '<new>'.`**
A results folder of the new name is already on disk (often an orphan). Delete or adopt it from the Focus card, then rename again.

**`An experiment needs at least one Focus.`** You tried to delete the last Focus.

**`This workbook has no DefinedPlots sheet.`** *Import from DefinedPlots…* has nothing to import. See [Defined Plots](help:defined-plots).

**`This Project has no other member.`** *Copy Focuses from…* needs a second member.

**`Not copied — they would be blocked here or clash by name:` …**
Each listed Focus either names a factor or level this member's data file lacks, has a treatment this member's active exclusions would empty, or has a name a Focus here already uses. Copy the others, then create the rest by hand.

**`There are no orphaned results to adopt — pre-Focus results record no Focus, so they are never adopted.`**
Only folders left by a deleted or hand-renamed Focus can be adopted. Old pre-Focus results can only be deleted.

**`Every Focus already has results — create or rename one first.`** / **`Focus '<F>' already has results.`**
Orphaned results can only be adopted by a Focus with no results folder of its own.

**`N individual(s) have no recorded level of <factors> and belong to no treatment — outside this Focus.`** (log)
Some individuals have a blank level for a factor the Focus names. They are not analysed. Fill in the Design sheet or CSV if they should be.

## "Why is this missing?"

**The *Interaction analyses* box is not on the Analyze panel.** The Active Focus varies fewer than two factors, so the interaction analyses are not offered. Vary a second factor, or make a Focus that does. See [Focus Shape](help:focus-shape).

**A box is greyed out.** Hover over it. *Not applicable to Focus …* means the data cannot compute it (for example a crossing gap, or only one populated treatment). *Draws from Pairwise hazard ratios* means the forest needs that analysis ticked.

**`Not applicable — <item>: <reason>`** in the log, or a *Not applicable to this Focus* table in the report: the item was relevant but the data could not support it. See [Not Applicable and Left Out](help:not-applicable).

**`Left out — <item>: unticked in the Hub (…)`**, or a *Left out of this run* table: the box is unticked, so it is in `omit:`. Tick it and re-run. An earlier copy of a left-out figure or table is deleted on purpose.

**A Defined Plot is never drawn.** It is drawn only for a Focus that pools over nothing and contains every listed treatment the data has. For other Focuses it is silently not relevant. If it is relevant but a treatment is missing, the run records it as Not Applicable with the missing labels. A plot whose labels are not full treatments of the file (the wrong number of `/` parts), or name nothing the file contains, is recorded as Not Applicable under every Focus. See [Defined Plots](help:defined-plots).

**A Focus's section in the Project Report shows no results.** The Focus is not analysed, Out of Date or blocked, and the section says which. Re-run the Focus (or fix it) and rebuild the report.

**A treatment reads `not fitted: …` in the parametric AFT table.** It has fewer than 5 individuals or fewer than 2 deaths (`only N individual(s)`, `only N death(s)`), or that model family failed to converge (`fit failed: …`). The other treatments and families are unaffected. See [Parametric AFT models](help:analysis-parametric-aft).

**Data quality says "This run recorded only the count" of excluded chambers.** The Focus was analysed by an earlier version, whose Run Summary saved how many chambers were excluded but not which. Re-run the Focus to have them listed by id.

**A median's upper confidence limit (`median_ci_hi`) is blank.** The upper edge of the KM confidence band never fell to 50%, so the limit is "not reached". The median itself can still exist. See [Summary statistics](help:survival-summary).

**A Focus reads `out of date` and I changed nothing in its definition.** Out of Date also notices an edited data file, a change to the chambers the active group lists (within that Focus), a change of `assume_censored`, and boxes ticked or unticked on the Analyze or Plots panels. The reason is in the tooltip. Re-run the Focus. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).

**`Pre-Focus results in analysis/ — never adopted and never replaced by a re-run; Delete… removes them.`** Results from before Focuses existed are still in bare `analysis/`. A re-run writes new results under `analysis/<focus>/` and leaves the old ones in place. Delete them with **Delete…** → *pre-Focus results* on the Focus card.

## Scripts and Batch Runs

**`Step N uses action '<x>', which a Standard Lifespan does not provide. Available: …`**
A typo or unknown action. This is a hard error: the script refuses to start, and in a Batch Run that Project is counted as failed while the Batch continues. A real action that merely does not fit the Focus is *Not Applicable* instead. See [Script action reference](help:script-actions).

**`Step N has no action.`** Give the step an action, or delete it.

**`run_in_focuses appears more than once; …`** Keep only one `run_in_focuses` step.

**`run_in_focuses can only run inside an Experiment Script — …`** The step was used where it cannot split the script (for example as a one-off action).

**`<member>: script '<name>' cannot run as a Standard Lifespan:` …** The Experiment Script that `run_in_experiments` named has invalid steps, so the Project's run stops there.

**`batch.yaml, line N: not valid YAML — … The batch is listed but cannot run until batch.yaml is fixed.`** The Batch folder's `batch.yaml` does not parse. Its Projects are still found and listed, but **Run batch** refuses, and choosing a script in the picker is not saved, until the file is fixed: its designated script and central `project_scripts:` are unknown, and writing to it would replace your file. Fix the line, then click **Rescan**, which re-reads `batch.yaml`.

**`Not saved — <file> could not be read, so it was not overwritten`** (Script Editor). The `survival_config.yaml` or `project.yaml` you are editing no longer parses — perhaps it was edited by hand while the editor was open. Fix the file; the editor never writes over one it cannot read.

**`[<member>] no Experiment Script named '<name>' — skipped.`** / **`<member>: not a member of this Project — skipped.`** The script name or an `only:` entry in `run_in_experiments` does not resolve. That member is counted as failed.

**`No Experiment Script named '<name>'.`** / **`No Project Script named '<name>'.`** The chosen script no longer exists in the config.

**`Project validation failed:` …** The `validate_project` step found problems. They are the same ones *Validate YAMLs* shows.

**`<action>: no data loaded — add a 'Load data' step first.`** Add a *Load data* step before steps that need data.

**`Select a directory that holds Projects first.`** / **`No Projects checked — check at least one row.`** A Batch Run needs a folder containing Projects and at least one checked Project in the preflight. See [Batch runs](help:batch-panel).

## Projects and members

**`<folder> is not a Project — no project.yaml. Create one with the Hub's Create/Load card.`** Open a folder that has a `project.yaml`, or initialize one.

**`'<name>' already exists. Use 'Initialize existing directory…' …`** *Create experiment…* makes new folders only. Use Initialize for a folder you already have.

**`'<name>' is already in this Project. Use 'Initialize existing directory…' …`** *Add directory…* copies folders in from **outside** the Project.

**`Every directory in '<project>' already has a survival_config.yaml. …`** Nothing to initialize. Use *Create experiment…* for a new member.

**`<folder> has no data/ subdirectory.`** / **`No .xlsx file in <folder>/data.`** *Add directory…* expects an experiment folder with a workbook in `data/`.

**`Create or select a Project first — a member's defaults are inherited from its project.yaml.`** Member actions need a Project selected.

**`No reports yet — run Project report first.`** Build the Project Report before viewing it.

**`A task is already running.`** Wait for the current task to finish (watch the log).

**`Load an experiment first.`** Double-click a member in the Project panel's members table, or select a standalone experiment folder.

## See also

- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [Not Applicable and Left Out](help:not-applicable)
- [Validating configuration](help:validation)
- [Input data formats](help:data-formats)
- [The Batch preflight](help:preflight)
- [Glossary](help:glossary)
