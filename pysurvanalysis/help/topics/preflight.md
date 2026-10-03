# The Batch preflight

The **Batch Run — review** window always opens when you click **Run batch** on the Batch panel, even when nothing is wrong. Because Projects are discovered recursively, the folder you picked does not tell you what will run. This window is the one place that states the target list, and the last point at which you can change it. Nothing in it blocks a run: a Project with blocked members still runs its healthy ones.

## The heading

The heading reads, for example, `D:\Lifespan — 5 project(s) found, 4 checked to run, 2 blocked member(s), 1 blocked focus(es)`. A note below the buttons adds:

- *N directory(ies) skipped — see the Output log after the run.* (unreadable folders, symbolic links, folders marked as Projects with no members);
- *The scan stopped early …* when the folder is too large to walk fully;
- *Nothing to run …* when no Project was found.

## The tree

One top-level row per Project, with child rows for what is wrong inside it.

| Column | Project row | Child row |
|---|---|---|
| **Project** | checkbox and key (path relative to the Batch folder) | a blocked member's folder name, or `member · Focus` for a Blocked Focus |
| **Members** | usable / total member folders | blank |
| **Status** | `ok`, or `N blocked`, `N focus(es) blocked`, or both | the member's status (`no config`, `no data`, `ambiguous`, `unreadable`, `bad config`), or `focus blocked` |

Projects with anything blocked are shown in red and expanded. Hover over a child row for the full reason.

### What the statuses mean

- **no config**: the folder holds a data file but no `survival_config.yaml`. *Fixable here.*
- **ambiguous**: the folder has a config, but there are several candidate data files and no `data_file:` naming one. The loader refuses to guess. *Fixable here, one member at a time.*
- **no data**: a config with no `.xlsx`/`.csv`/`.tsv` in `data/` or the folder root, or a `data_file:` naming a file that does not exist. Supply the data outside the app.
- **unreadable**: the folder cannot be listed (permissions). Fix it outside the app.
- **bad config**: the member's `survival_config.yaml` is not valid YAML; the detail names the file and line (`survival_config.yaml, line N: not valid YAML — …`). Fix the file in an editor; the rest of the Project runs.
- **focus blocked**: a Focus names a factor or level the data file no longer contains (**stale**, for example after a level was renamed in the Design sheet), or a cell it keeps has no individuals left after the active Exclusion Group (**empty**). Finding these means reading each usable member's Design sheet. The member's other Focuses still run.

## Checking and unchecking

A checked Project runs, and an unchecked one is **not touched at all**. A Project nobody has decided about is checked exactly when it has at least one usable member; one with no usable member starts unchecked, because it could only fail. You can still check it.

What you decided is kept, wherever you decided it. On opening, the Batch panel's table is read as your choices: a Project you unchecked there starts unchecked here, and one with nothing usable that you checked there starts checked. Your clicks in this window are remembered too. After a repair or a **Rescan** the tree is rebuilt, and every Project keeps the box you gave it; the ones you never touched follow what they can do *now* — so a Project you have just repaired joins the run, unless you had unchecked it. When you click **Run batch**, your choices here are carried back to the Batch panel's table.

## Buttons

| Button | What it does | Enabled when |
|---|---|---|
| **Fix selected…** | On a **no config** row, writes a minimal config from that Project's Defaults. On an **ambiguous** row, asks which file is the experiment and writes `data_file:`. On a **stale** Blocked Focus row, shows the Focus rewritten with each missing level replaced by its close match in the data file, and asks you to confirm. Its saved results are then Out of Date until re-run. | a row with a one-click fix is selected. For an empty Focus or a stale one with no close match, it stays disabled, and the tooltip suggests editing the Focus or changing the Exclusion Group |
| **Scaffold every missing config** | Writes a minimal config into every **no config** member across the whole Batch. Ambiguous members are left alone, because which file is the experiment is your decision. | always (it says so when there is nothing to scaffold) |
| **Rescan** | Walks the Batch folder again, for changes made outside the app. | always |
| **Run batch** | Closes the window and starts the run on the checked Projects. | at least one Project is checked |
| **Cancel** | Closes the window without running. Repairs you already made stay on disk. | always |

Each repair is logged in the Hub's Output tab with a `[preflight]` prefix. Whether you run or cancel, the Hub rescans the Batch afterwards, so its table reflects your repairs.

## See also

- [Batch runs](help:batch-panel)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [The Experiments card — members](help:project-members)
- [The Focus window](help:focus-window)
- [Exclusion Groups](help:exclusions)
