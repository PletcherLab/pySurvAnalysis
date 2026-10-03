# Project Scripts

A **Project Script** is a saved, re-runnable list of project-level steps, stored in `project.yaml` under `scripts:`. It is how you analyse every member, render figures and rebuild the Project Report in one action. A Batch Run is the same thing done in many Projects at once. The **Scripts** card, the last card in the Project panel, runs and edits them. It is dimmed until a Project is open.

## The Scripts card

- **The script picker** lists the Project's own scripts first (from `project.yaml`), then the built-ins **Standard pipeline** and **Report pipeline**, unless the Project already has scripts with those names.
- **Run script** runs the picked script in the background. Progress streams to the Output tab as `[1/3] Run in experiments`, `[2/3] …`, with each member's lines prefixed `[member]`. A script with a step naming an unknown action refuses to start. With no Project open it warns *No Project selected.*
- **Edit scripts…** opens the [Script Editor](help:script-editor) on the Project's `project.yaml`, at the *Project scripts* level, whether or not an experiment is loaded. Switch the level to *Central experiment scripts* to edit `experiment_scripts:`. When you save, the Hub re-reads the Project, so the picker lists the saved scripts at once.

## The `batch` script

Every new `project.yaml` is created with one Project Script named `batch`. It is the script a Batch Run executes in this Project unless another is designated:

```yaml
scripts:
  - name: batch
    notes: Created with the project, and what a Batch Run runs here …
    steps:
      - action: run_in_experiments
        script: Standard analysis
      - action: render_publication_figures
      - action: project_report
experiment_scripts: []
```

It is an ordinary script: you can edit, rename or replace it. A Project whose `scripts:` list is empty cannot be run by a Batch Run that has no designated script. The run fails that Project, says to author a script, and moves on. A `project.yaml` with no `scripts:` key at all gets the `batch` script added on its next save.

## Project actions

| Action (YAML key) | Parameters | What it does |
|---|---|---|
| **Validate project** (`validate_project`) | none | Checks every member shares the Project's Experiment Type and that each config is valid. Any problem **fails the script**. Divergences are logged without failing. |
| **Run in experiments** (`run_in_experiments`) | `script`: an Experiment Script name; `only`: member names (blank = every member) | Runs the named Experiment Script in each member, continue-on-error: a failing member is logged and the others still run. |
| **Render publication figures** (`render_publication_figures`) | `format`: `svg` (default), `pdf` or `png` | Same as the Actions card button: curated figures for every member and current Focus. |
| **Project report** (`project_report`) | `formats`: default `pdf,md`; `with_narrative`: true/false | Writes the Project Report from saved results. Fails the script if nothing was written. |
| **Generate AI narrative** (`generate_ai_narrative`) | `provider`: blank, `anthropic` or `openai` | Writes the narrative. A provider failure is logged and the script continues. |

## How run_in_experiments finds the Experiment Script

For each member, the named Experiment Script is looked up in this order:

1. the Project's central `experiment_scripts:` in `project.yaml` (one recipe serving every member);
2. the member's own `scripts:` in its `survival_config.yaml`;
3. the built-in of that name. The only built-in is `Standard analysis`: `run_in_focuses`, then `run_analysis`.

Every new `survival_config.yaml` is created with its own `Standard analysis` script (the same two steps), so you can see and edit it per member. Because `run_in_focuses` runs the rest of the script once per Focus, the `batch` script analyses **every Focus of every member**, not just the Active Focus.

A member with no script of that name is logged as skipped and counted as a failure. A member whose script contains a step its Experiment Type does not provide **stops the whole Project's run**: this is a hard error, not a skip. At the end, the log reports `run_in_experiments(<name>): k/n member(s) completed`, and the script reports `Completed with N member failure(s): …` when any member failed.

## The built-in Project Scripts

| Name | Steps |
|---|---|
| **Report pipeline** | run_in_experiments (`Standard analysis`) → render_publication_figures → project_report. When no member has curated figure specs, the render step is dropped up front and the log says so. |
| **Standard pipeline** | validate_project → run_in_experiments (`Standard analysis`) → render_publication_figures → project_report. Validation failures stop it before anything runs, which is why Report pipeline suits unattended runs better. |

The seeded `batch` script has the same steps as Report pipeline, but as a copy in your file it always keeps its render step. With nothing curated, that step just logs *nothing rendered*.

## When a picked name is resolved

**Run script** looks the picked name up in the Project's own `scripts:` first, then among the built-ins. A Project script you name `Report pipeline` therefore overrides the built-in.

## See also

- [Experiment and Project Scripts](help:scripts-overview)
- [The Script Editor](help:script-editor)
- [Script action reference](help:script-actions)
- [Running Experiment Scripts](help:experiment-scripts)
- [Batch runs](help:batch-panel)
- [project.yaml and Project Defaults](help:config-project)
