# The Chamber QC viewer

The Chamber QC viewer shows each chamber's survival curve, one tab per treatment, so you can spot chambers that behave unlike their siblings: a vial where everyone died in the first days, one that never lost anyone, a curve that falls off a cliff. You can click curves to mark chambers as excluded, then save the selection as a named **Exclusion Group**.

It works only for DLife workbooks, because individual-level CSV data has no chambers.

## Opening it

On the Hub, load an experiment, open **QC** under the Experiment tile, and click **Chamber QC viewer…**. The viewer opens on that experiment's directory, together with the Hub's Active Focus. It can also be pointed at another directory with **Pick project…** in its side panel. That button takes any Experiment Directory, not a Project.

## The window

**Side panel (left)**

- **Project** — the directory being viewed, and **Pick project…** to choose another.
- **Only Focus** *name* — shown when the viewer was opened from the Hub. When ticked (the default), only individuals in the Active Focus are shown, and the tabs are that Focus's treatments. Untick it to see every chamber in the file, labelled by the full combination of all factors. This only changes what you *see*. Saved groups always apply to the whole directory, every Focus alike.
- **Active exclusion group** — an editable list of the groups in `qc/remove_chambers.csv`, or `default` if there are none yet. The viewer opens on the experiment's **active** group (the one `exclusions: group:` names, which every run applies), listed even if it has no rows yet. Choosing another group from the list loads its chambers as the current selection. If you have clicked chambers since the last save, the viewer first asks whether to **Save** them to the group you are leaving, **Discard** them, or **Cancel** and stay. Typing a new name does not change the selection: it only names the group that **Save Exclusions…** will offer.
- **Excluded chambers** — the current selection, as `Chamber <id>`. Double-click an entry to un-exclude it.
- **Clear all** — empty the selection.
- An amber note lists the chambers with fewer individuals than `global.min_n_per_chamber` (see below).

**Tabs (right)** — one per treatment, in display order: the Focus's level order when **Only Focus** is ticked, otherwise the order the data file lists the levels in (the order every Focus starts from). Never alphabetical. Each tab draws every chamber of that treatment as a Kaplan-Meier step curve over the same axes (survival probability against time):

- An included chamber is a thin, translucent **blue solid** line.
- An excluded chamber is a **red dashed** line.
- A chamber with fewer individuals than `global.min_n_per_chamber` (and not excluded) is an **amber solid** line. It is flagged for your decision, never excluded automatically. The tab's tooltip lists that treatment's small chambers with their N. `0` turns the flag off.
- **Hover** over a curve to see `Chamber <id> — <n> events, last t=<time>`, with `N=<n>, below the minimum of <min> per chamber` added for a small chamber.
- **Click** a curve to toggle that chamber between included and excluded. The change shows in every tab and in the side list.
- The matplotlib toolbar above each plot zooms and pans. This helps when many curves overlap.

**Save Exclusions…** (top bar) asks for a group name, pre-filled with the name in the drop-down. It writes the current selection as that group's complete list in `qc/remove_chambers.csv`, replacing any rows that group already had and leaving other groups untouched. A chamber that stays in the group keeps the `note` it already had in the file. A message confirms how many chambers were saved.

Closing the viewer with unsaved clicks asks the same Save / Discard / Cancel question as switching groups.

## A typical session

1. Open the viewer from the QC panel.
2. Go through the treatment tabs. Hover over outlying curves to identify them, and click each one you judge invalid.
3. Click **Save Exclusions…** and name the group (e.g. `default` or `strict`).
4. Back on the Hub's QC panel, choose that group and click **Set active group**. Saving alone does not make a group active.
5. Run the analysis again. Focuses analysed under the previous group show as Out of Date until you do.

## What the curves are

Each curve is a Kaplan-Meier estimate computed from that chamber's individuals alone, read exactly as an analysis reads them: the experiment's own data file, its `input:` options and its censoring policy (`global.assume_censored`, with the Project's defaults applied for a member). The one difference is that the viewer loads **every** chamber. It never pre-removes the active group's chambers or the workbook's ChamberFlags chambers, so that you can see all of them and decide.

The time axis carries the experiment's time label (`global.time_label`, or `Age (<time_unit>)`).

## Pitfalls

- **Saving is not activating.** Saving a group writes it to the file; only **Set active group** on the QC panel makes runs apply it. The exception is saving under the group that is already active: runs apply the new list from then on, and Focuses analysed with the old list show as Out of Date.
- **Notes are kept, not shown.** The viewer has no notes column. Notes you type into `qc/remove_chambers.csv` survive a save for every chamber that stays in the group; a chamber you un-exclude loses its row, note included.
- **CSV experiments.** The viewer says the data has no chamber-level information and shows nothing.
- **Several data files.** The viewer never guesses. For an experiment with several candidate files and no `data_file:` key it shows the same message as a run ("Name one with `data_file:`…"). For a plain folder with no `survival_config.yaml` it asks which file to show.

## See also

- [Exclusion Groups](help:exclusions)
- [The QC panel](help:qc-panel)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [What a Focus is](help:focus)
- [Censoring policy](help:censoring)
