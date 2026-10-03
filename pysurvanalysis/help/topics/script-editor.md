# The Script Editor

The Script Editor builds and edits saved scripts without typing YAML. You choose actions from a list, arrange them as steps, fill in each step's parameters in a form, and save. The editor writes the scripts into the right section of the right file and leaves the rest of that file alone.

## Opening it

Click **Edit scripts…** on either:

- the **Experiment scripts** card (Experiment tile → Scripts), or
- the Project panel's **Scripts** card.

From the Experiment scripts card the editor opens on the loaded experiment (or, with none loaded, on the selected folder). From the Project panel's Scripts card it always opens on the Project's `project.yaml`, at the *Project scripts* level.

## The three levels

The **Level** drop-down at the top chooses which set of scripts you are editing:

| Level | File and section | Actions offered | Available when |
|---|---|---|---|
| Experiment scripts | `survival_config.yaml` → `scripts:` | experiment actions for the experiment's type | an experiment is open |
| Project scripts | `project.yaml` → `scripts:` | project actions | the directory is, or sits inside, a Project |
| Central experiment scripts | `project.yaml` → `experiment_scripts:` | experiment actions for the Project's type | the directory is, or sits inside, a Project |

Central experiment scripts are one recipe that serves every member without being copied into each `survival_config.yaml`. The label at the right of the control row shows the target file and the action set, for example `survival_config.yaml · core ∪ Standard Lifespan`.

Switching level re-reads that level's scripts from disk. If you have unsaved edits, the editor asks before discarding them.

## The window

- **Top bar** — **+ New script** (asks for a name), **− Delete script** (asks for confirmation) and **Save**.
- **Active script** — the drop-down of scripts at this level, with **Rename…** and **Validate** beside it.
- **Actions** (left) — every action this level offers, grouped under headers (LOAD, ANALYZE, PLOTS, QC, SCRIPTS, AI, TOOLS) and sorted by title. Hover for a description. **Double-click** an action to append it to the end of the active script as a new step, pre-filled with its default parameter values. You need an active script first.
- **Steps** (centre) — one card per step: its number, icon, action title (as this level names it, in its category's colour) and a short summary of its parameters. A step naming an action this level does not provide shows its raw key in grey, with a tooltip saying the script will refuse to start. Each card has **up**, **down** and **delete** buttons. Click a card to select it.
- **Parameters** (right) — the form for the selected step: the action's title and description, then one field per parameter. Changes apply as you type. A field that depends on another is greyed out until it applies (for example *Smoothing σ* on a Hazard rate step is enabled only when *Smoothed* is ticked).
- **Live YAML preview** (bottom) — the current level's scripts exactly as they will be written. It is read-only.

### Parameter fields

| Field | Used for | How to fill it |
|---|---|---|
| Tick box | on/off options | tick or untick |
| Number box | numbers (σ, τ) | type or use the arrows; the allowed range is enforced |
| Drop-down | fixed choices (format, metric, provider) | pick one |
| Factor drop-down | a single factor (Filter rows) | lists the factors found in the experiment's data file |
| Text | names, values | type |
| Comma list | several names (treatments, Focuses, members, factors) | separate with commas; blank means "all" |
| Path | a folder | type it or click **…** to browse |

Empty fields are not written to the YAML, so the action's default applies.

## Validate and Save

**Validate** checks that every step names an action this level provides (and, for experiment levels, that `run_in_focuses` appears at most once). It does not check parameter values or whether a step suits a particular Focus — that is decided per Focus at run time, as **Not Applicable**. A script that fails validation would refuse to start.

**Save** writes every script at the current level into its section of the file — `scripts:` or `experiment_scripts:` — and leaves every other key in that file untouched. A message confirms how many scripts were written and where. When the editor was opened from the Hub, the Hub then re-reads the Project and the loaded experiment, so its **Run script** drop-downs list the saved scripts and the next run uses them.

Closing the window with unsaved edits asks whether to **Save**, **Discard** them, or **Cancel** and keep editing.

## Pitfalls

- Saving replaces the whole section with what the editor shows, including scripts you deleted.
- A script edited here is run from the Hub's **Run script** buttons, from `run_in_experiments`, or from a Batch Run — the editor itself does not run scripts.
- An editor opened from the Hub tells only that Hub about its saves. If you edit a config by hand, re-open the Project (picking it again re-reads it from disk).

## See also

- [Experiment and Project Scripts](help:scripts-overview)
- [Script action reference](help:script-actions)
- [Running Experiment Scripts](help:experiment-scripts)
- [Project Scripts](help:project-scripts)
