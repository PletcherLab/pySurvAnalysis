# Running Experiment Scripts

An Experiment Script runs a list of steps against one Experiment Directory. Every step runs under a **Focus**, so a script can analyse one slice of the data file or repeat itself for every Focus the config declares.

## In the app

1. Load an experiment (double-click it in the Project panel's members table, or open an Experiment Directory).
2. Open the Experiment tile and choose the **Scripts** sub-tile. The **Experiment scripts** card appears.
3. Pick a script in the drop-down. The list holds the Project's central `experiment_scripts:`, then the experiment's own scripts (those whose names no central script already uses), then the built-in **Standard analysis**. A name both define runs the **central** script — the same rule `run_in_experiments` and a Batch Run use.
4. Click **Run script**.

The run happens in the background and its progress is written to the log, one line per step (`[2/3] Run analysis`). Only one task runs at a time; if another is still going, the Hub says so. **Edit scripts…** opens the [Script Editor](help:script-editor) on the loaded experiment. When you save there, the Hub re-reads the experiment's config, so the drop-down — and the next run — use the scripts as saved.

Experiment Scripts also run without the Hub: a Project Script's `run_in_experiments` step runs a named Experiment Script in every member, and a Batch Run does the same across Projects. See [Project Scripts](help:project-scripts).

## Which Focus the steps run under

What happens depends on whether the script contains a `run_in_focuses` step.

**Without `run_in_focuses`**

- From the Hub, every step runs once, under the **Active Focus** chosen in the Experiment panel.
- Unattended (from a Project Script or a Batch Run), there is no Active Focus, so the whole script runs once **per declared Focus**. An unattended run that analysed one Focus and said nothing about the others would be a silent gap.

**With `run_in_focuses`**

The script is split at that step:

- Steps **before** it run once. From the Hub they run under the Active Focus; unattended they run with no Focus (a `run_analysis` placed here analyses every Focus).
- Steps **after** it run once for each Focus — every declared Focus when its `only` parameter is blank, or just the Focuses it names. A name in `only` that the experiment does not declare is logged and skipped.

When there is more than one Focus, the log marks each with a line such as `── Focus 'diet' ──`. A script may contain at most one `run_in_focuses` step.

## What happens per Focus

For each Focus the runner cuts that Focus's slice from the loaded data, then:

- **Blocked Focus** — if the Focus cannot run as declared (for example it names a level the data does not contain), it is logged as `BLOCKED` with the reasons and skipped. The other Focuses still run.
- **Not Applicable step** — a step whose requirement the Focus Shape does not meet is logged as `Not applicable — <action>: <reason>` and the next step runs. If this run analysed the Focus (a `run_analysis` or `report` step produced a result), the entry is also added to that Focus's Run Summary under `not_applicable`.
- **Failing step** — any other error stops this Focus (`FAILED: …`) and the runner moves to the next Focus. When all Focuses have had their turn, the script reports the failures together, so a Project counts the member as failed.

## What a script writes

Only some steps write files:

- `run_analysis` (and `report`, when nothing has been analysed yet) runs the full battery and writes `analysis/<focus>/`: the tables, the figures, the report (`<experiment>_report_<focus>.pdf` and `report_<focus>.md`) and `run_summary_<focus>.json`.
- `render_publication_figures` writes curated figures to `figures/<focus>/`.

The individual analysis and plot steps (`log_rank_pairwise`, `cox_ph`, `km_curves`, `hazard_plot` and so on) are quick looks: tests print their tables to the log and plots open as tabs in the Hub's plot area. **They save nothing to disk and do not appear in the report**, and they do not consult the `omit:` block. Use `run_analysis` for results you want to keep.

## Pitfalls

- **Load before you look.** The individual analysis and plot steps need data in memory. Put a `load_data` step before them (before or after `run_in_focuses` both work). `run_analysis` loads the data itself and needs no `load_data` step.
- **`filter` does not reach `run_analysis`.** A `filter` step narrows the in-memory data for the quick-look steps that follow; `run_analysis` reloads from the data file under the Focus. To analyse a subset properly, declare a Focus for it.
- **Exclusions from a script add to the config's.** `apply_exclusions` removes a group's chambers on top of the config's active Exclusion Group, and the run's report and Run Summary name both groups (`base + extra`). Because the config alone no longer describes that run, the Hub then shows its results as Out of Date.
- **Scripts with the same name.** When the Project's central `experiment_scripts:` and a member both define a script of the same name, the central one runs — from the Hub, from `run_in_experiments` and in a Batch Run alike. Rename the member's copy to keep both.

## See also

- [Experiment and Project Scripts](help:scripts-overview)
- [Script action reference](help:script-actions)
- [The Script Editor](help:script-editor)
- [What a Focus is](help:focus)
- [Not Applicable and Left Out](help:not-applicable)
- [The Run Summary](help:run-summary)
