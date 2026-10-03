# Analysed, Out of Date, Blocked and Orphaned results

Every [Focus](help:focus) has a state that the app reads from disk, from the Focus's saved Run Summary, without re-analysing anything. The state tells you whether the results you are looking at describe the Focus as it is now declared. There are four states for a Focus, plus two kinds of leftover result folder.

| State | Meaning | What to do |
|---|---|---|
| **analysed** | Saved results exist and match what a run would use now: the Focus's definition, the exclusions, the data file and the settings below. | Nothing. |
| **not analysed** | No Run Summary for this Focus yet. | Run analysis. |
| **out of date** | Saved results exist but were produced from something that has since changed (see below). | Re-run the Focus. |
| **blocked** | The Focus cannot run as declared. | Fix the Focus or the exclusions (below). |

If a Focus is both blocked and analysed, it is shown as **blocked**.

## Where the state is shown

- **Focus card** (Experiment panel) – each entry in the Focus selector reads `<name> — <state>`. The shape line under it appends `BLOCKED — <reasons>` or `out of date — <reasons>` for the Active Focus.
- **Analyze sub-tile** – the Active Focus's state, with N once it has been analysed.
- **Project panel, members table** – the *Analysed* column counts Focuses that are analysed and current (`2/3`), or shows the date of the latest run when all are. It reads `re-run needed` when any Focus is out of date, and `1/3 · 1 blocked` when any is blocked. Rows with a blocked or out-of-date Focus are coloured, and the tooltip lists each one with its reasons.
- **Project Report** – the Focus Inventory's *State* column, and each Focus's section (see below).
- **Batch Preflight** – lists every Blocked Focus before a Batch Run. See [The Batch preflight](help:preflight).

## Out of Date

When a run finishes it writes into the Run Summary what it was run from: the Focus's **analytic definition** (factors, ordered levels and Reference Levels), the Exclusion Group's name and the chambers actually removed, a fingerprint (sha256) of the data file, the censoring policy, and what the run left out. Afterwards the app compares that record with what a run would use now. A difference gives one of these reasons:

- "the Focus's factors or levels changed" – a level added or removed, a factor added or removed, or the **level order** changed
- "a Reference Level changed" – compared as the baseline the model actually uses, so writing down the default reference (as the Focus window does on Save) is not a change
- "analysed under exclusion group 'A', config now asks for 'B'"
- "the excluded chambers changed — now also excludes chamber(s) …; no longer excludes …" – the active group's rows were edited (or the workbook's ChamberFlags changed). Only chambers inside this Focus count: excluding a chamber of another slice changes none of this Focus's numbers.
- "the data file's contents changed since the analysis" – the workbook or CSV was edited or replaced
- "analysed with assumed censoring on, config now has it off" (or the reverse) – workbooks only, since the policy changes nothing for CSV data
- "the analyses selection changed — now leaves out …" / "the plots selection changed — now includes …" – boxes ticked or unticked on the Analyze or Plots panels (the `omit:` block)
- "the saved results predate Focuses and record no definition"

Each of the newer checks applies only when the Run Summary recorded the value. Results from an older version of the app are not marked Out of Date merely for lacking it.

Display names and colours are **not** compared. They change no number.

An Out of Date Focus's section in the Project Report says its results "are out of date — they predate a change and are not shown" with the reasons, and presents **none** of the old numbers. The report never analyses on your behalf, and it never presents results that no longer describe the Focus. Re-run the Focus (Run analysis with it active, or a script or Batch Run) and rebuild the report.

### What Out of Date does not detect

These changes do **not** mark results Out of Date, so re-run yourself after any of them:

- changing `input:` settings (time or event column, layout) or `global:` settings other than `assume_censored`, such as `time_label` or `min_n_per_chamber`
- changing a Project Default that reaches the member only through settings in the previous point
- an upgrade of the app that changes how something is computed

## Blocked

A **Blocked Focus** cannot run as declared. Its member is not blocked: the member's other Focuses still run, and a Batch Run continues. Run analysis on a blocked Focus stops before writing anything, with a message like:

```
Focus 'Crowding' is blocked:
  - Focus 'Crowding' names level 'mDilp' of Genotype, which the data file does not contain (levels: wCS, mDilp235bx) — rename it to 'mDilp235bx'?
```

There are two reasons a Focus can be blocked:

**Stale** – the Focus names a factor or level the data file no longer contains, typically because the Design sheet was corrected after the Focus was written. The message suggests the closest name in the data if there is one ("rename it to '…'?"), otherwise "edit the Focus". To fix it:

- In the **Batch preflight**, select the Blocked Focus row and press **Fix selected…** (enabled only when every stale name has a close match). It rewrites every stale name to its close match after asking you to confirm ("Rewrite Focus … as: … Its saved results will then be out of date until it is re-run").
- In the [Focus window](help:focus-window), drop or replace the stale names. A stale *level* is listed in red, marked "(not in the data file)", so untick it and tick the right one. A stale *factor* gets a box of its own above the others, titled "*factor* — not in the data file", so untick the box to drop it. Saving with stale names still in place asks you to confirm first.

Data holding levels the Focus does not name is normal, since selecting a subset is what a Focus is for. Only the reverse blocks.

**Empty** – a treatment the data file *does* contain has no individuals once the active Exclusion Group and the workbook's chamber flags are applied ("treatment 'Male/40x' is in the data file but has no individuals once exclusions are applied — change the Exclusion Group or drop that level from the Focus"). QC has removed a whole cell from under the Focus. Either change the Exclusion Group or untick that level. A cell the data *never* had is merely absent, and absence does not block. A Focus that selects no individuals at all is blocked with "Focus '…' selects no individuals".

The Hub and the preflight estimate blocking from the Design sheet and the excluded chambers. A run confirms it from the loaded data.

A blocked Focus's section in the Project Report says it "is blocked — it cannot run as declared, so nothing was analysed for it", lists the reasons, and notes that the member's other Focuses are unaffected.

## Orphaned Results

An **orphaned result** is a folder under `analysis/` that no declared Focus names. It appears when a Focus was deleted, or renamed by hand in the YAML. (Renaming in the Focus window moves the results along with the name, so it cannot orphan anything.) Orphaned results are never bound into a report.

When an experiment has orphans, the Focus card shows `Orphaned results (no Focus names them): <folders>` with two buttons:

- **Adopt…** – pick an orphaned folder, then a declared Focus that has no results of its own. The folder is moved to that Focus's place, the name suffix of every file in it is renamed, and the Run Summary is updated to the new name. The adopted results are then judged like any others, so they show as **out of date** if their recorded definition differs from the Focus that adopted them. If every Focus already has results, the Hub asks you to create or rename one first.
- **Delete…** – pick a folder and confirm ("Delete … from analysis/? This cannot be undone.").

## Pre-Focus results

Results written before Focuses existed sit directly in `analysis/` (`run_summary.json`, `plots/`, `statistics/`, `data_output/`, `report.md`, `*_report.pdf`). They record no Focus and no definition, so they are **never adopted**. Adopting them would vouch for a slice nobody can check. The Focus card notes "Pre-Focus results in analysis/ — never adopted and never replaced by a re-run; Delete… removes them." A re-run writes new results under `analysis/<focus>/` and does not touch the old files. Remove them with **Delete…** → *pre-Focus results*.

## See also

- [What a Focus is](help:focus)
- [The Focus window](help:focus-window)
- [The Batch preflight](help:preflight)
- [The Run Summary](help:run-summary)
- [The Project Report](help:project-report)
- [Exclusion Groups](help:exclusions)
