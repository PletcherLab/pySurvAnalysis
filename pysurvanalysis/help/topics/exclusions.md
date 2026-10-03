# Exclusion Groups

An **Exclusion Group** is a named set of chambers to remove from analysis: vials that were contaminated, mis-scored, dropped, or otherwise not valid data. Groups are stored per experiment in `qc/remove_chambers.csv`. One group at a time is **active**, and the active group is part of the experiment's configuration (`exclusions: {group: …}` in `survival_config.yaml`). Every run removes its chambers and records the group's name. The same data and the same config always give the same result, and every report says what was removed.

## Why named groups

You may want to compare results with and without a questionable set of chambers, or keep a strict and a lenient QC policy side by side. Each is a separate group in the same file. Switching the active group is a deliberate, recorded change of configuration, never a hidden setting. Results produced under a different group are flagged **Out of Date**.

## The file: qc/remove_chambers.csv

A plain CSV with three columns:

```
group,chamber,note
default,3,low N — early deaths only
default,7,
strict,3,
strict,7,
strict,12,suspicious survival
```

| Column | Meaning |
|---|---|
| `group` | The group's name. Rows with a blank group are ignored. |
| `chamber` | A chamber id, as on the workbook's Design sheet. A whole number is read as that number however it is written (`12`, `12.0`, ` 12 `). Anything else is read as text. |
| `note` | Optional free text. The app keeps notes it finds but does not display them. |

A chamber may appear in several groups. The file lives in the experiment's `qc/` folder. An older experiment may still have the file at the directory root. That copy is read while `qc/` has none, but nothing is ever written back to it: the first save copies all its groups into `qc/remove_chambers.csv`, which is used from then on. The old root file is left in place and can be deleted.

You can edit the file by hand, in any editor or spreadsheet (a "CSV UTF-8" save from a spreadsheet is read correctly). The usual way to write it is the Chamber QC viewer's **Save Exclusions…**, which replaces every row of the named group and leaves other groups untouched. Notes already in the file are kept for every chamber that stays in the group. Saving a group with no chambers flagged removes that group's rows. If the file cannot be read at all, the save is refused rather than rewriting the file without its other groups.

## Making a group active

On the Hub's QC panel, pick the group in **Active group** and click **Set active group**. This writes:

```yaml
exclusions:
  group: strict
```

In a Project, `defaults: exclusions: group:` in `project.yaml` gives every member a default active group name. Each member still reads its own `qc/remove_chambers.csv`. A member opts out with `group: ''`, which is what clearing the QC panel's group box writes in such a Project. See [The QC panel](help:qc-panel).

## What a run does

1. It removes every chamber listed under the active group, plus every chamber the workbook's **ChamberFlags** sheet marks `Excluded` = 1.
2. It analyses what remains under the chosen Focus.
3. It records the result:
   - The report's cover line **Exclusion group** reads, for example, `strict — 3 chamber(s) removed`. Other forms are `strict — nothing listed`, `strict — no chambers removed (N listed, none present in this data)`, `none declared (N removed by the workbook)`, or `none`.
   - The report's **Data quality** section lists the excluded chamber ids and the group.
   - The Run Summary (`run_summary_<focus>.json`) stores `exclusion_group`, `excluded_chambers` (the ids removed from this data), `n_excluded` (how many), and `n_excluded_listed` (chambers listed).

The Hub's members table shows each member's active group, and the Project Report's Divergence Note says when members use different groups.

## One group per experiment, shared by every Focus

The active group applies to the whole Experiment Directory. A chamber's validity is a fact about the chamber, not about which slice you are analysing. If groups were set per Focus, two sections of one report could disagree about whether the same vial is valid data. The Chamber QC viewer can *show* only the Active Focus's chambers, but the groups it saves belong to the directory.

## Effects to expect

- **Out of Date.** Changing the active group makes every Focus analysed under the old one Out of Date until it is re-run. So does changing *which chambers* the active group lists, for every Focus whose chambers the change touches.
- **Blocked Focus.** If the group removes every chamber of a treatment a Focus names, that Focus is Blocked. The message names the treatment and suggests changing the group or dropping the level from the Focus. A cell the data never contained is simply absent and does not block.
- **Shape changes.** Removing chambers can empty a cell of a two-factor Focus. The interaction models then become Not Applicable, because the crossing has a hole.

## In scripts

An Experiment Script's `run_analysis` step uses the active group from the config, like the Hub. The separate `apply_exclusions` step (parameter `group`, default `default`) adds a named group's chambers on top for the rest of that script; the runs it changes name both groups (`default + extra`) and show as Out of Date against the config. See [Script action reference](help:script-actions).

## Pitfalls

- **CSV data has no chambers.** Exclusion Groups remove nothing from CSV/TSV experiments. Reports record the group with zero chambers removed rather than claiming exclusions that could not happen.
- **A name with no rows excludes nothing.** The QC panel warns when the active group is not in the file.
- **Text ids must match exactly.** Numeric ids match however they are written (`12.0` is chamber 12), but text ids are compared as written, case included: `A12` and `a12` are different chambers.
- **Saving is not activating.** Saving a group in the viewer does not make it active. Set it on the QC panel.

## See also

- [The QC panel](help:qc-panel)
- [The Chamber QC viewer](help:qc-viewer)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [Input data formats](help:data-formats)
- [The Run Summary](help:run-summary)
