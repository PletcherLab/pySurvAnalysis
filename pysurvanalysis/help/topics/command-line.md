# Command-line use

Everything the Hub runs can also be run from a terminal, which is useful on a server, in a scheduled job, or to re-run a whole Batch overnight. The command is `pysurvanalysis` (run it as `uv run pysurvanalysis …` from the repository folder, or `uv run python main.py …`). With no subcommand it opens the Hub.

The command-line runs read the same configuration files as the Hub — `survival_config.yaml`, `project.yaml`, `batch.yaml` — so a run from the terminal produces exactly what the Hub would: the same Focuses, the same active [Exclusion Group](help:exclusions), the same analyses and figures left out by the [omit: section](help:config-omit), written to the same places.

## Subcommands

| Subcommand | What it does |
|---|---|
| `hub [path]` | Open the Analysis Hub, optionally with a Project, Batch folder or Experiment Directory selected. |
| `qc [path]` | Open the Chamber QC viewer. |
| `plots path` | Open the Plot Editor on an Experiment Directory. |
| `run INPUT [options]` | Analyse one experiment (see below). |
| `project path [--script NAME]` | Run a Project Script in a Project. Default script: `Report pipeline`. |
| `batch path [--script NAME]` | Run a Project Script in every Project found under a Batch folder, continue-on-error. Without `--script`, the Batch's designation in `batch.yaml` is used; with none, each Project runs its own `batch` script. Exit code 1 if any Project failed. |
| `upgrade path [--type KEY] [--dry-run]` | Upgrade a directory made by a pre-Project version of the app. `--dry-run` lists what would change and writes nothing; it never deletes or moves files. |

## run

`run` takes either an **Experiment Directory** (a folder with a `survival_config.yaml`) or a **bare data file** (`.xlsx`, `.csv`, `.tsv`, or a folder holding one `.xlsx`).

**Experiment Directory.** Every declared Focus is analysed, each into `analysis/<focus>/` with its report and Run Summary — exactly Run analysis in the Hub, once per Focus. The config is validated first; any problem stops the run with exit code 2 and the list of problems. A [Blocked Focus](help:focus-status) is reported and skipped; the others still run.

**Bare data file.** The file is analysed under the **Unfiltered** Focus (every factor varying) into `<stem>_results/Unfiltered/` next to it, or into `--output-dir`. There is no config, so the CSV options below describe the file.

| Option | Applies to | Meaning |
|---|---|---|
| `--focus NAME` | Experiment Directory | Analyse only this Focus. Repeat to name several. Naming a Focus that is not declared is an error (exit 1). |
| `--exclusion-group NAME` | both | Also exclude this group's chambers, in addition to the config's active group. |
| `--figures` | Experiment Directory | Also render the Publication Figures (see [Publication Figures, Specs and Styles](help:publication-figures)). |
| `--output-dir DIR`, `-o DIR` | bare file | Where to write the results. |
| `--no-assume-censored` | bare `.xlsx` | Do not treat individuals unaccounted for at the last census as censored (see [Censoring policy](help:censoring)). For an Experiment Directory the config's `global: assume_censored` decides. |
| `--format auto/long/wide` | bare CSV | The CSV layout (see [Input data formats](help:data-formats)). |
| `--time-col COL`, `--event-col COL` | bare CSV | Column names for age and the 0/1 death indicator. Defaults: `Age`, `Event`. |
| `--factor-cols COL …` | bare long CSV | The factor columns. |
| `--factor-names F1 F2` | bare wide CSV | The two factor names. |
| `--col-mapping FILE.yaml` | bare wide CSV | The column-to-group mapping. |

When it finishes, `run` prints where each Focus's results are, a short summary (treatments, chambers, N, deaths, censored, time range) and every Not Applicable item.

## Examples

```
# Analyse every Focus of one experiment
uv run pysurvanalysis run Projects/Diet2026/rep_a

# Only the "Diet x Genotype" Focus, and render its publication figures
uv run pysurvanalysis run Projects/Diet2026/rep_a --focus "Diet x Genotype" --figures

# A loose workbook, outside any Project
uv run pysurvanalysis run census.xlsx -o census_results

# Re-run every Project in a folder with each Project's own batch script
uv run pysurvanalysis batch Projects/
```

## Exit codes

`0` success; `1` a Focus or Project failed, or a named Focus does not exist; `2` the configuration has problems, or a bare file was given `--focus`, or the Project Script named does not exist.

## See also
- [Installing and launching](help:installation)
- [Experiment and Project Scripts](help:scripts-overview)
- [Batch runs](help:batch-panel)
- [Where results are written](help:outputs-layout)
- [survival_config.yaml reference](help:config-experiment)
