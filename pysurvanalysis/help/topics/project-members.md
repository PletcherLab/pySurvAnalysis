# The Experiments card — members

The **Experiments** card is the second card in the Project panel. It lists the open Project's Member Experiments, along with any subfolders that are not members yet, and holds the five ways to make a new member. Double-click a member to load it. The card is dimmed, and all five buttons are disabled, until a Project is open.

## The members table

There is one row per member (a subfolder with a `survival_config.yaml`), in name order, followed by one row per subfolder that has no config yet. Every value is read from the config and the saved Run Summaries. Nothing is re-analysed to fill the table, and it re-reads from disk after every task and every change made in the Hub.

| Column | Shows | Possible values |
|---|---|---|
| **Member** | the folder name | the member's directory name |
| **Config** | whether the folder has a `survival_config.yaml` | `yes`, or `missing` (in red) for a folder that is not a member yet |
| **Focuses** | how many Focuses the member has, and the first three names | `2: Unfiltered, FemalesOnly`, `5: A, B, C …` when there are more than three; `—` when none can be resolved (no declared Focus and the data file cannot be read, for example a member with no data yet) |
| **N** | individuals in one analysed slice | for the loaded member, the Active Focus's total when it has current results; otherwise the largest Focus with current results. Hover over the cell to see which Focus it is. `—` when no Focus has current results (an Out of Date result is not counted). It is never a sum over Focuses, which overlap |
| **Analysed** | how far the member's Focuses are analysed (see below) | `no`, `1/3`, a timestamp, `yes`, `re-run needed`, `1/3 · 1 blocked`, `blocked: no data`, `blocked: ambiguous` |
| **Exclusions** | the active Exclusion Group in the member's config | the group name, or `none` |

### The Analysed column

Hover over the **N** and **Analysed** column headers for a reminder of what they count. The first rule that applies wins:

- `blocked: no data` / `blocked: ambiguous`: the member itself cannot run — its config names no data file the loader can find, or the folder holds several candidate data files and no `data_file:` says which is the experiment (see *Red rows* below).
- `k/n · b blocked`: at least one Focus is **Blocked** (it names a level the data lacks, or the active Exclusion Group empties one of its cells). Here *k* is the number of Focuses with current results, *n* the number of Focuses, and *b* the number blocked.
- `re-run needed`: at least one analysed Focus is **Out of Date**. Its saved results were produced under a different Focus definition (factors, levels, Reference Levels) or a different Exclusion Group from the one the config now declares.
- `k/n`: some Focuses have no current results yet.
- the date and time of the most recent run (for example `2026-10-02T14:03:11`): every Focus is analysed and current. It shows `yes` if no run recorded a time.
- `no`: the member has no Focuses that can be resolved.

### Red rows

A member row turns red when the member is blocked, or any Focus is blocked or analysed but out of date. Hover over the row for the reasons: for a blocked member, what is wrong and how to fix it (for example *Blocked — 2 data files in data/ (a.xlsx, b.xlsx) — which is the experiment? Name the experiment's file with Experiment configs… → Set data file….*, or for no data file, *Put its .xlsx/.csv/.tsv in data/ (or the directory root), or point `data_file:` at it.*), then one line per affected Focus, such as *FemalesOnly: blocked — …* or *Unfiltered: out of date — …*. A `missing` row is red too, and its tooltip says why (for example *holds cohort_c.xlsx but no survival_config.yaml*).

### Double-click

- On a member row: loads that member and opens the [Experiment panel](help:experiment-panel), where you choose the Active Focus.
- On a `missing` row: asks *Scaffold one from the Project Defaults and make it a member?* **Yes** writes a minimal config (as *Initialize existing directory…* does) and the row becomes a member.

Selecting a row (single click) also tells **Plot editor…** on the Actions card which member to open.

## Making a member

The first three buttons cover folders inside the Project.

| Button | When | What it does |
|---|---|---|
| **Create experiment…** | the member folder does not exist yet | Asks for a folder name, creates it with an empty `data/`, and writes a minimal `survival_config.yaml` that inherits everything from the Project Defaults. It then offers **Add data file…** (copies a `.xlsx`, `.csv` or `.tsv` into `data/`), **Copy config from…** (replaces the scaffold with another member's config, refused if its Experiment Type differs), or **Later**. It refuses a name that is not a single folder name, and a folder that already exists (use *Initialize* for that). |
| **Initialize existing directory…** | the folder is in the Project but has no config | Lists the Project's subfolders that have no config, each with its state (for example `empty`, `no config`), and scaffolds a minimal config in the one you pick. Nothing is moved, because the loader already finds a data file at the folder root or in `data/`. If the folder holds several candidate data files, it then asks which one is the experiment and writes `data_file:` into the config. When every folder already has a config it says so and points you to *Create experiment…*. A folder that cannot be listed (`unreadable`) is refused, and has to be fixed outside the app. |
| **Experiment configs…** | to see or fix many at once | Opens the bulk view (below). |

The two buttons under **Bring one in from outside** reach outside the Project.

| Button | What it needs | What it does |
|---|---|---|
| **Add directory…** | a folder **outside** the Project with a `data/` subfolder holding a `.xlsx` that validates as a DLife workbook | **Copies** the whole folder into the Project. If it has no `survival_config.yaml`, a minimal one is written (with `data_file:` when `data/` holds more than one data file). A folder that is already a direct child of the Project is refused with a pointer to *Initialize existing directory…*. A destination that already exists is refused rather than merged. |
| **Add experiment…** | one DLife workbook (`.xlsx`) | Creates a member named after the file (`cohort_a.xlsx` becomes `cohort_a/`), puts the workbook in its `data/` (**moved** if it was already inside the Project tree, **copied** otherwise), and writes a minimal config. |

A workbook validates as DLife when it has Design and RawData sheets with the columns each needs and at least one factor column after `StartTime`.

A config written by any of these routes is **minimal**: it states the Experiment Type, plus, for an adopted workbook, the `input:` format and `assume_censored` if the workbook's PrivateData sheet disagrees with the Project's default. Everything else is inherited, so later edits to the Project Defaults keep reaching the member. A config copied in with *Copy config from…* restates whatever it contains. The log then names the keys that will no longer follow the Project.

## The Experiment configs dialog

This dialog lists every subfolder of the Project that is a member or could become one.

| Column | Values |
|---|---|
| **Directory** | folder name |
| **Config** | `yes` or `missing` |
| **Data files** | the candidate data files found (in `data/`, else the folder root), or `none` |
| **Status** | `ok`, `no config`, `no data`, `ambiguous` (several files and no `data_file:`), `unreadable`, or `empty` |

Hover over a row to see the detail behind its status.

| Button | Does | Enabled when |
|---|---|---|
| **Create config** | scaffolds the selected folder's config from the Project Defaults | the selected row has no config |
| **Create all missing** | scaffolds every missing config, after confirming the list | any row has no config |
| **Set data file…** | asks which candidate file is the experiment and writes `data_file:` | the selected row is `ambiguous` |
| **Edit config…** | opens the member's `survival_config.yaml` in your system's YAML editor (there is no built-in config editor) | the selected row has a config |

Double-clicking a row edits it if it has a config, or creates one if it does not.

## See also

- [Creating and opening a Project](help:project-create)
- [The Experiment panel](help:experiment-panel)
- [survival_config.yaml reference](help:config-experiment)
- [project.yaml and Project Defaults](help:config-project)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [Input data formats](help:data-formats)
