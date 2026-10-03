# survival_config.yaml reference

Every Experiment Directory has a `survival_config.yaml` at its root. The file is what makes a folder an experiment. It also holds every setting that decides a result: how to read the data file, the censoring policy, the active Exclusion Group, the declared Focuses, and which analyses and figures a run leaves out. The same file and the same data always give the same result, whether the run comes from the Hub, a script, or a Batch Run.

Factors are **never declared** here. They are discovered from the data file (see [Input data formats](help:data-formats)).

## In the app

The Hub writes most of this file for you:

- **Create experiment…**, **Initialize existing directory…** and the *Experiment configs…* dialog scaffold it.
- The QC panel's **Set active group** writes `exclusions:`.
- The Focus window writes `focuses:`.
- The Analyze and Plots checkboxes write `omit:`.
- The Script Editor writes `scripts:`.

To edit the file by hand, use **Edit config…** in the Project panel's *Experiment configs…* dialog. It opens the file in your desktop's YAML editor. Keys the app does not recognise are kept untouched when the app rewrites the file.

## A complete example

```yaml
experiment_type: standard_lifespan
data_file: data/cohort_2026.xlsx       # only needed when data/ holds several files
global:
  time_unit: days
  time_label: Age (days)
  assume_censored: true
  min_n_per_chamber: 5
input:
  format: auto                         # auto | excel | long | wide
  time_col: Age
  event_col: Event
  factor_cols: null
  factor_names: null
  col_mapping: null
exclusions:
  group: default
focuses:
  Crowding20v40:
    factors:
      Sex: [Female, Male]
      Density: ["20x", "40x"]
    reference:
      Density: "40x"
    display_names:
      Female/20x: "F, 20x"
    colours:
      Female/20x: "#b2182b"
omit:
  analyses: [parametric_aft]
  plots: [number_at_risk]
scripts:
- name: Standard analysis
  notes: Runs the standard analysis battery once per Focus.
  steps:
  - action: run_in_focuses
  - action: run_analysis
```

## Top-level keys

| Key | Type | Default | Effect |
|---|---|---|---|
| `experiment_type` | string | `standard_lifespan` | The [Experiment Type](help:experiment-types). Omitted, empty, or a retired key (`interaction`, `custom`) all mean Standard Lifespan. Any other unknown value is an error. |
| `data_file` | path | none | Names the data file, relative to the experiment directory or absolute. Overrides the search of `data/` and the root. Required when that search finds several files. |
| `global` | mapping | type defaults | Time unit, axis label, censoring policy, quality threshold. See [The global: section](help:config-global). |
| `input` | mapping | see below | How to read a CSV/TSV. See [The input: section](help:config-input). |
| `exclusions` | mapping | none | `group: <name>` names the active [Exclusion Group](help:exclusions). Blank (`group: ''`) means no group; absent means no group unless the Project Defaults name one, which a member then inherits. |
| `focuses` | mapping | `Unfiltered` | Named Focuses (below). |
| `omit` | mapping | nothing left out | Analyses and figures every run leaves out. See [The omit: section](help:config-omit). |
| `scripts` | list | `Standard analysis` | Saved Experiment Scripts. See [Experiment and Project Scripts](help:scripts-overview). |
| `factors` | mapping | none | **Legacy.** A pre-Focus factor block. If there is no `focuses:` block, it becomes one Focus called `Interaction`, and it is removed the next time Focuses are saved. |

### exclusions

```yaml
exclusions:
  group: default     # a group name from qc/remove_chambers.csv
```

| Key | Type | Default | Effect |
|---|---|---|---|
| `group` | string | none | Chambers listed under this group in `qc/remove_chambers.csv` are removed from every run. The name is stamped on every report and Run Summary. A name with no rows in the file removes nothing. |

### focuses

Each entry under `focuses:` is one Focus, keyed by its name. The name is used, made filesystem-safe, as the output directory `analysis/<name>/` and as the `_<name>` suffix on every output file.

| Key | Type | Default | Effect |
|---|---|---|---|
| `factors` | mapping factor → list of levels | required | Which factors and levels the Focus selects, in display order. A factor with two or more levels **varies** (it labels treatments). A factor with one level is a **filter**. A discovered factor not named is **pooled over**. |
| `reference` | mapping factor → level | first level listed | The [Reference Level](help:reference-level) for Cox and RMST coding. |
| `display_names` | mapping treatment → text | none | Display names for treatments (labels such as `Female/20x`). |
| `colours` | mapping treatment → colour | none | Curve colours per treatment. |

If the file has no `focuses:` block, the experiment still has one Focus, `Unfiltered`: every discovered factor at every level. It is written into the file the first time the experiment is analysed or its Focuses are edited. See [What a Focus is](help:focus).

Display names and colours don't change any number, so editing them never makes results [Out of Date](help:focus-status). Changing `factors` or `reference`, or the Exclusion Group, does.

### scripts

A list of saved step lists, each with `name`, optional `notes` and `steps` (each step has `action:` plus that action's parameters). If a file has **no `scripts:` key at all**, the default `Standard analysis` script is added the next time the app writes the file. An empty list (`scripts: []`) counts as a deliberate deletion and is left alone. For a Member Experiment, a script of the same name in the Project's `experiment_scripts:` takes precedence. See [Running Experiment Scripts](help:experiment-scripts).

## Members and Project Defaults

For a Member Experiment, this file is merged with the Project's `defaults:` before use. Anything the member states wins. `global`, `input`, `exclusions` and `omit` merge key by key, so a member can override one setting without restating the whole section. `focuses` is never inherited. A member scaffolded by the app is deliberately minimal (often just `experiment_type` and `scripts`), so later edits to the Project Defaults keep reaching it. See [project.yaml and Project Defaults](help:config-project).

## Checking the file

**Validate YAMLs** on the Project panel checks this file, and every member's in an open Project, and lists any problems in the output log. Every message and its fix is listed in [Validating configuration](help:validation).

## See also

- [The input: section](help:config-input)
- [The global: section](help:config-global)
- [The omit: section — leaving analyses and figures out](help:config-omit)
- [project.yaml and Project Defaults](help:config-project)
- [What a Focus is](help:focus)
- [Validating configuration](help:validation)
