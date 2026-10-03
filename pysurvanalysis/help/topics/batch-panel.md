# Batch runs

A **Batch Run** executes one Project Script in every checked Project inside a folder, unattended and continue-on-error. Use it to re-analyse and re-report many Projects overnight. A Batch has no analysis of its own and never combines results across Projects. Open the **Batch** tile to use it.

## Choosing a Batch

**Choose batch folder…** picks the folder that holds your Projects. Discovery is **recursive**: the app walks down through any grouping folders (`Sept2026/`, `Archive/2025/`) until it finds a Project (a folder with `project.yaml` and at least one member), then stops there and never looks inside it. Projects can therefore sit at any depth, and a Project's own subfolders are never mistaken for Projects. The walk skips hidden (dot) folders, does not follow symbolic links, and logs any folder it could not read.

The walk is done once when you choose the folder. **Rescan** walks it again, after you add or repair Projects outside the app, re-reads `batch.yaml`, and logs `[batch] rescanned …: N project(s), N blocked member(s)`.

If the folder is itself a Project, it is opened as a Project rather than a Batch, and the Batch tile says *selection is a project — open its parent to batch*. A very large folder (tens of thousands of subfolders) stops the scan early. The log then says so and suggests choosing a folder closer to the Projects.

Until a Batch is selected, the table, the script picker, **Run batch** and **Rescan** are disabled. **Choose batch folder…** and the suppress-tabs box are always available.

## The Projects table

One row per Project found, in key order.

| Column | Shows |
|---|---|
| **Project** | a checkbox, and the Project's **key**: its path relative to the Batch folder (`Sept2026/ProjA`, or just `ProjA` at the top level). Hover to see the full path |
| **Type** | the Project's Experiment Type, or `error: …` if its `project.yaml` cannot be read |
| **Members** | usable members / all member folders, for example `4/5`. A folder that holds data but no config counts in the total |
| **Report** | `yes` if the Project Report PDF exists, `no` if not (`—` on error) |
| **Status** | `ok`, or `N blocked` when some member folders cannot be used |

A row with blocked members is shown in red. Hover over it for each blocked member and the reason. The checkbox decides whether the Project joins the next run. A row you have not touched is checked exactly when the Project has a usable member, so a Project that cannot run starts unchecked and becomes checked once it is repaired. Your own checks and unchecks are kept whenever the table refreshes, including after a rescan or a repair, and after opening a Project from the table and coming back. Choices you make in the preflight are carried back to this table when you confirm the run.

- **Double-click** a row to open that Project in the Project panel (the selection moves to the Project, and you reach the Batch again by choosing its folder).
- **Right-click** a row for **Fix blocked members in `<key>`…**, which is enabled only when the Project has blocked members and opens the preflight with that Project selected, and **Open `<key>`**.

## The script picker

**Script** chooses what runs in each Project:

- **Each project's own 'batch' script (default)**: every Project runs its own script named `batch`, or its first script if none has that name. A Project with no scripts fails, and the run continues.
- A named script: the Batch folder's central `project_scripts:` from `batch.yaml` (when there is one), then the built-ins **Standard pipeline** and **Report pipeline**. A named script is looked up in each Project in this order: `batch.yaml`'s `project_scripts:`, then the Project's own `scripts:`, then the built-ins. A name found nowhere fails that Project only.

If `batch.yaml` designates a script (`script:`), the picker starts on it, even when it names a script only some Projects carry. Choosing in the picker **saves** the choice as `batch.yaml`'s designation (creating the file if needed, and keeping its `project_scripts:`), so a command-line `batch` run and the next session use the same script. Choosing **Each project's own 'batch' script (default)** removes the designation; it never creates a `batch.yaml` that does not exist. A `batch.yaml` in a nested folder is ignored, and the run log names it.

## Run batch

**Run batch** always opens the [Batch preflight](help:preflight) first. It lists exactly which Projects will run, with their blocked members and Blocked Focuses, and lets you repair them, uncheck Projects, or cancel. Nothing runs until you confirm there. Projects you leave unchecked are not touched at all.

During the run, every log line is prefixed with the Project's key (`[Sept2026/ProjA] …`). Before each Project's script starts, its blocked members and Blocked Focuses are named (*will not be analysed*). A failing Project is logged (`FAILED: …`) and the Batch moves on to the next.

The run ends with one summary line, for example:

```
Batch run: 3 Project(s) completed; incomplete: ProjB (3/4 members, 1 Focus(es) blocked).
Batch run: 2/3 Projects completed; failed: ProjC.
```

*Incomplete* lists Projects that succeeded while leaving members or Focuses out, so "completed" is never read as "analysed everything".

## Suppress plot tabs during batch runs

On by default. A Batch Run would otherwise open a figure tab for every figure of every member. With the box ticked, figures are still written to disk, but no tabs open, and the log notes each figure that was not shown. It affects Batch Runs only. Figures you generate on a single experiment always open.

## See also

- [The Batch preflight](help:preflight)
- [Project Scripts](help:project-scripts)
- [Batches, Projects, Experiments and Focuses](help:concepts)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [The Analysis Hub](help:hub)
