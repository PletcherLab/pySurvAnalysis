# Creating and opening a Project

The **Create/Load** card is the first card in the Project panel (click the **Project** tile). It has one button for each state a folder can be in before it is a Project, an editor for the Project that is open, and a validator. Below the buttons, a summary describes what is loaded.

## The buttons

| Button | Use it when | What it does | Disabled when |
|---|---|---|---|
| **Open project…** | the folder already has a `project.yaml` | Opens a folder picker. The folder you choose becomes the selection: a Project, a Batch, or a standalone Experiment Directory (a Project is never required). Choosing the Project that is already open re-reads it from disk, so changes made outside the Hub show up. | never |
| **Create project…** | the Project does not exist yet | Opens the Project editor (below). The directory you name is created if needed, and `project.yaml` is written into it. | never |
| **Initialize existing directory…** | you have a folder, usually with experiment subfolders in it, but no `project.yaml` | Opens the Project editor in *initialize* mode: the folder keeps its own name, its subfolders become the members, and `project.yaml` is written there. Nothing is moved. | never |
| **Edit config…** | a Project is open | Opens the Project editor on the open Project's `project.yaml`. | no Project is open. It only edits: to give a folder its first `project.yaml`, use *Initialize existing directory…* |
| **Validate YAMLs** | any time | Checks the Project's `project.yaml` and every member's `survival_config.yaml`, then writes the results to the Output log. See below. | never (with no Project and no experiment loaded it warns *No Project selected.*) |

## The Project editor

*Create project…*, *Initialize existing directory…* and *Edit config…* share one dialog.

- **Directory**: the Project folder. Type a path or use **Browse…**. In create mode a path that does not exist yet is created. Choosing a folder that is already a Project loads its values, and saving edits it.
- **Project name**: written as `name:`. It defaults to the folder name. In initialize mode it is read-only and is always the folder's own name. The Project Report's file name always comes from the folder name, not from this field.
- **Question**: the one question the members address. The Project Report's cover and the AI narrative both read it.
- **Project Defaults — seeded into every new member**:
  - **Experiment type**: the one value every member must share. In initialize mode it is preset to the type of the first subfolder that already has a config.
  - **Global**: one field for each of the type's `global:` settings. For Standard Lifespan these are `time_unit` (default `days`), `time_label` (default `Age (days)`), the `assume_censored` checkbox (default on) and `min_n_per_chamber` (default `5`). A text field left empty is not written, so the type's default applies.

There are no factor fields. Factors are discovered from each member's data file, and each member names its own Focuses. Keys the dialog does not show (`scripts:`, `experiment_scripts:`, other `defaults:` entries, anything from a newer version) are carried through a save unchanged.

**Save** writes `project.yaml` and opens the Project. A new `project.yaml` is created with a Project Script named `batch` (what a Batch Run runs here) and an empty `experiment_scripts:` list.

### When Save refuses or asks

- No directory entered: *Choose a directory first.*
- Initialize mode, folder does not exist: use *Create project…* instead.
- Initialize mode, folder is already a Project: open it and use *Edit config…*.
- The folder holds a `survival_config.yaml` (it is an Experiment Directory): the dialog offers to create the Project on its parent folder instead, so this folder becomes a member.

## The summary line

Under the buttons, the card describes the open Project: **name · Experiment Type · N member(s)**, then, when they apply:

- *N directory(ies) with no config: …*: subfolders that are not members yet (see [The Experiments card — members](help:project-members));
- *Question: …*;
- *Divergence: …*: the data-source settings (time unit, censoring, exclusion group) on which members differ;
- *N problem(s) — run Validate YAMLs.*

With nothing open it reads *No Project loaded*.

## Validate YAMLs in detail

With a Project open, the Output log lists:

- *Project validation passed.* or *Project validation problems:* followed by each problem. Problems include a member whose Experiment Type differs from the Project's, each member's own config problems, and a `defaults:` that contains `focuses:` (ignored, because Focuses are never inherited) or a pre-Focus `factors:`;
- each divergence;
- each **blocked** member folder: data but no config, a config but no data, or several candidate data files (ambiguous);
- a final line: `[validate] N file(s) checked, N problem(s), N blocked member(s).`

With no Project open but a standalone experiment loaded, it validates that experiment's config alone. See [Validating configuration](help:validation).

## See also

- [project.yaml and Project Defaults](help:config-project)
- [The Experiments card — members](help:project-members)
- [Validating configuration](help:validation)
- [Batches, Projects, Experiments and Focuses](help:concepts)
- [Experiment Types](help:experiment-types)
