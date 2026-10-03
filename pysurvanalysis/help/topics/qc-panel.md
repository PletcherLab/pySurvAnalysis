# The QC panel

The QC panel is where you decide which chambers an experiment's analyses leave out. Here you choose the experiment's **active Exclusion Group** (a named list of chambers to remove) and open the **Chamber QC viewer**, where those lists are made. QC comes first among the Experiment sub-tiles because you decide what to exclude before you analyse.

## Opening it

Load an experiment by double-clicking its row in the Project panel's members table, or select a standalone Experiment Directory. Then click **QC** under the Experiment tile. Its tile shows a two-line summary:

- `group: <name>` — the active Exclusion Group, or `none`.
- `N chamber(s) excluded` — how many of this data file's chambers the current configuration removes: the active group plus the workbook's ChamberFlags. It describes what every Focus's next run will leave out, so it changes as soon as you set a group or save one in the viewer. Chambers a group lists that the file does not have are not counted, and a CSV (which has no chambers) shows 0.

## Controls

**Active group** is an editable drop-down listing every group in this experiment's `qc/remove_chambers.csv`, in the order they first appear in the file. The current active group is pre-selected.

- If the file has no groups yet, a note says so. Open the Chamber QC viewer, flag chambers, and use **Save Exclusions…** under a name, and the group will appear here — the list is re-read every time the viewer saves, and again when it closes.
- If the active group's name is not in the file, a warning says it "currently excludes no chambers". A misspelt name is not an error, but it removes nothing.

**Set active group** writes the chosen name into `survival_config.yaml` as:

```yaml
exclusions:
  group: default
```

The log confirms the change. From then on, every run of this experiment (Hub, script or Batch Run) drops that group's chambers and stamps the group's name on its report and Run Summary.

Clearing the box and clicking **Set active group** means *no group*. Normally that removes the `exclusions:` key from the experiment's config. When the Project's `project.yaml` sets a default group (`defaults: exclusions: group:`), removing the key would hand the member straight back to that group, so the panel instead writes an explicit empty group, which overrides the default:

```yaml
exclusions:
  group: ''
```

The log then says it is overriding the Project default.

**Chamber QC viewer…** opens the viewer on this experiment, starting on the Hub's Active Focus. See [The Chamber QC viewer](help:qc-viewer).

## What changes when you set a group

- **Nothing is re-analysed automatically.** Every Focus that was analysed under a different group becomes **Out of Date** ("analysed under exclusion group 'x', config now asks for 'y'"). Its report section stops presenting the old numbers until you run it again.
- **All Focuses share one group.** The group belongs to the experiment directory, not to a Focus: whether a chamber is valid data is a fact about the chamber.
- **A Focus can become Blocked.** If the new group removes every chamber of a treatment the Focus names, that Focus is Blocked (`treatment '…' … has no individuals once exclusions are applied`) until you change the group or drop the level from the Focus.
- **The Focus shape line updates.** The Experiment panel's shape line and the Analyze/Plots boxes are estimated from the Design sheet minus the active group's chambers, so they show the effect before anything runs.

## Pitfalls

- **Editing the YAML by hand.** Deleting a member's `exclusions:` key yourself makes it inherit the Project's default group, if there is one. Use `group: ''` to mean "no group" in a member of such a Project — what clearing the box writes for you.
- **CSV data has no chambers.** For CSV/TSV experiments a group can be set, but it removes nothing. Reports record the group with zero chambers removed.
- **Workbook flags always apply.** Chambers marked `Excluded` = 1 on the workbook's ChamberFlags sheet are removed from every run, on top of the active group.

## See also

- [Exclusion Groups](help:exclusions)
- [The Chamber QC viewer](help:qc-viewer)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [The Experiment panel](help:experiment-panel)
- [The Analysis Hub](help:hub)
