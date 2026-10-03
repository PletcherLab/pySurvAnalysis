# Experiment and Project Scripts

A script is a saved, named list of steps that the app can re-run at any time. Scripts are how an analysis becomes repeatable: the same steps, in the same order, give the same outputs whether you run them from the Hub, from a Project, or in an overnight Batch Run. There are two levels of script, and they never mix.

| Level | Acts on | Saved in | Bridge to the level below |
|---|---|---|---|
| **Experiment Script** | one Experiment Directory, one Focus at a time | `survival_config.yaml` → `scripts:` (or centrally in `project.yaml` → `experiment_scripts:`) | `run_in_focuses` repeats the rest of the script once per Focus |
| **Project Script** | a Project and its Member Experiments | `project.yaml` → `scripts:` | `run_in_experiments` runs a named Experiment Script in every member |

Each level has its own list of actions (see [Script action reference](help:script-actions)). An Experiment Script cannot call a project action, and a Project Script cannot call an experiment action directly — it goes through `run_in_experiments`.

## What a script looks like

Every script is a `name`, an optional `notes` line, and a list of `steps`. Each step names an `action` plus any parameters that action takes. You normally build scripts in the [Script Editor](help:script-editor), but the YAML is plain text and can be read or edited by hand.

An Experiment Script in `survival_config.yaml`:

```yaml
scripts:
  - name: Standard analysis
    notes: Runs the standard analysis battery once per Focus.
    steps:
      - action: run_in_focuses
      - action: run_analysis
```

A Project Script in `project.yaml`, plus one central Experiment Script that every member can use:

```yaml
scripts:
  - name: batch
    steps:
      - action: run_in_experiments
        script: Standard analysis
      - action: render_publication_figures
      - action: project_report
experiment_scripts:
  - name: Quick look
    steps:
      - action: load_data
      - action: run_in_focuses
      - action: km_curves
        show_ci: true
```

## The scripts every file starts with

- Every `survival_config.yaml` is given an Experiment Script called **Standard analysis** (`run_in_focuses`, then `run_analysis`) the first time the file is written without a `scripts:` key.
- Every `project.yaml` is given a Project Script called **batch**: `run_in_experiments` (script *Standard analysis*), `render_publication_figures`, `project_report`. A Batch Run executes this script in each Project unless another one is designated.

Both are written into the file, not hidden in code, so you can see and edit them. Once a `scripts:` block exists it is never re-seeded — an empty list is treated as a deliberate deletion. A Project whose `scripts:` list is empty does not run in a Batch Run.

The app also has a few **built-in** scripts that are available by name even when no file defines them:

| Built-in | Level | Steps |
|---|---|---|
| Standard analysis | Experiment | `run_in_focuses`, `run_analysis` |
| Standard pipeline | Project | `validate_project`, `run_in_experiments` (Standard analysis), `render_publication_figures`, `project_report` |
| Report pipeline | Project | `run_in_experiments` (Standard analysis), `render_publication_figures`, `project_report` |

When **Report pipeline** is run by name and no member has curated figure specs, its figure step is dropped before the run starts and the log says so.

## How a script name is found

An Experiment Script name — named by a `run_in_experiments` step, or picked on the Hub's **Experiment scripts** card — is looked up in this order:

1. the Project's central `experiment_scripts:`;
2. the member's own `scripts:` in its `survival_config.yaml`;
3. the built-in Experiment Scripts.

The Hub card lists them in the same order: central scripts first, then the experiment's own scripts whose names no central script uses, then the built-ins. So when a member and the Project both define a script of the same name, the **central** copy runs everywhere.

A named Project Script is looked up in the Batch's central `project_scripts:` (Batch Runs only), then the Project's own `scripts:`, then the built-ins.

## Three kinds of problem, three behaviours

- **Unknown action — the script refuses to start.** A step naming an action that does not exist at that level (a typo, or a project action in an Experiment Script) is a hard error before the first step runs. A silently skipped step would produce a report that looks complete and is not. In a Batch Run the Project is logged as failed and the Batch continues.
- **Not Applicable — recorded, the run goes on.** A real action that the current Focus's shape does not admit (a log-rank test on a single-treatment Focus, the Cox factorial model on a Focus with an empty cell) is logged as *Not applicable — reason*, written into that Focus's Run Summary when the script analysed that Focus, and the next step runs. See [Not Applicable and Left Out](help:not-applicable).
- **Failure — that Focus or member stops, the others continue.** Any other error stops the current Focus only; the remaining Focuses still run, and the error is raised at the end so the member counts as failed. One level up, `run_in_experiments` carries on with the next member.

A **Blocked** Focus is reported and skipped; the member's other Focuses run normally.

## Scripts and the Hub's tick boxes

The `run_analysis` step runs exactly what the Hub's **Run analysis** button runs: the Analysis Set and Plot Set, less anything the config's `omit:` block leaves out (the boxes you unticked on the Analyze and Plots panels). So a script, a Batch Run and the Hub button produce the same report. See [The omit: section](help:config-omit).

## See also

- [Running Experiment Scripts](help:experiment-scripts)
- [Project Scripts](help:project-scripts)
- [The Script Editor](help:script-editor)
- [Script action reference](help:script-actions)
- [Batch runs](help:batch-panel)
