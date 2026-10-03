# The Analysis Hub

The Analysis Hub is pySurvAnalysis's main window. It has a top bar, a strip of three tiles with a status readout, and a full-width output area below. Each tile shows only live status. Its controls live in a panel that drops down under it when you click. Only one panel is open at a time.

You can launch the Hub with a folder already selected by passing its path on the command line (`pysurvanalysis hub <path>`). Otherwise it opens with nothing selected.

## Top bar

- **Recent**: a menu of folders you have opened before. Picking one selects it again.
- **Help**: opens this manual at the page for the panel that is open (or this page when none is). **F1** does the same.
- The **theme** button toggles light and dark.

## The tile strip

| Tile | Opens | Its summary shows |
|---|---|---|
| **Batch** | [Batch runs](help:batch-panel) | the number of Projects found and how many members are blocked, or a hint when the selection is not a Batch |
| **Project** | the Project panel ([Create/Load](help:project-create), [Experiments](help:project-members), [Actions](help:project-actions), [Scripts](help:project-scripts)) | member count, how many of the members' Focuses have current results (for example `3 member(s) · 4/5 Focuses analysed` — Out of Date results are not counted), and which member is loaded |
| **Experiment** | [The Experiment panel](help:experiment-panel) | the loaded experiment and its Active Focus |

The Batch and Project tiles are never dimmed. Their panels hold the pickers that create everything else, so they are always available. The **Experiment** tile is dimmed until an experiment is loaded, and clicking it then does not open a panel. Instead the Output log says *Load an experiment first — double-click a member in the Project panel, or open a standalone Experiment Directory.*

The five experiment-level surfaces (**QC · Analyze · Plots · Scripts · AI**) are sub-tiles inside the Experiment panel, under the Focus selector. Each opens its own panel, anchored under the Experiment tile.

### The status readout

To the right of the tiles, a readout answers "what is open right now" without opening a panel. Its rows are **Selection** (the folder you picked), **Project** (name and Experiment Type), **Experiment** (the loaded member, or *none loaded*), **Focus** (the Active Focus and a one-line description of it, once an experiment is loaded) and **Question** (when the Project has one). At most four rows are shown, so with an experiment loaded the Question moves to the tooltip and the Focus row always stays in view. Hover over the readout to see every row.

## What the selection can be

Whatever you open (with **Open project…**, **Choose batch folder…** or **Recent**) is classified:

- a folder with a `project.yaml` is a **Project**: the members table fills, and you load a member by double-clicking it;
- a folder with a `survival_config.yaml` is a **standalone Experiment Directory** and loads at once. If its parent folder is a Project, that Project is opened alongside it;
- any other folder with Projects somewhere beneath it is a **Batch**;
- anything else is just a directory, and the Project tile then suggests *Create / Initialize*.

The Output log records what the selection was taken to be (`Project: …`, `Batch: …`, and so on).

## Panels

A panel opens under its tile and closes when you click the same tile again, open another tile, press **Esc**, or click anywhere outside the panel in the Hub window. Clicking in another window (a dialog, the QC viewer, the Script Editor) does not close it. Some actions move you to a panel: double-clicking a Batch row opens the Project panel, and double-clicking a member opens the Experiment panel.

Cards whose controls have nothing to act on yet are **dimmed**, but stay usable. In the Project panel, the Experiments, Actions and Scripts cards dim until a Project is open. The QC, Analyze, Plots and Scripts panels dim until an experiment is loaded, and the AI panel dims until a Project is open and an AI provider key is configured.

## The output area

Below the strip is a tabbed dock:

- **Output**, the first tab, which cannot be closed: the log of everything the Hub does. A task starts with a `▶ <name>` line, streams its progress, and ends with `✔` (completed) or `✘` (failed, with the error above it). Lines beginning `!` are warnings, and most are also shown in a message box.
- **Figure tabs**: each figure a task produces opens as its own tab (a zoomable image). Figure tabs can be closed individually and dragged to reorder.
- At the top right, **Clear plot tabs** closes every figure tab and returns to Output, and **Clear output** erases the log.

The Hub runs **one task at a time**. Starting a second while one is running gives *A task is already running.* When a task finishes, every table and panel refreshes from disk.

If something goes wrong that no action anticipated, the Hub does not close: the Output log shows *✘ Unexpected error — the action was abandoned, the Hub carries on:* with the error's details (also printed to the console), and you can keep working. A configuration file that is not valid YAML is reported the same way — in a message naming the file and line — wherever the Hub reads it.

During a Batch Run the **Suppress plot tabs during batch runs** box on the Batch panel (on by default) stops figure tabs from opening. Figures are still written to disk. It never suppresses figures you ask for on one experiment.

## See also

- [Your first analysis](help:quickstart)
- [Batches, Projects, Experiments and Focuses](help:concepts)
- [The Experiment panel](help:experiment-panel)
- [Creating and opening a Project](help:project-create)
- [Batch runs](help:batch-panel)
