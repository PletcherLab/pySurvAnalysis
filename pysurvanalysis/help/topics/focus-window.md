# The Focus window

The Focus window is where you create and edit an experiment's [Focuses](help:focus). You tick the factors a Focus names, tick and order each factor's levels, pick each varying factor's [Reference Level](help:reference-level), and name and colour the treatments. A live preview shows N, the treatments, the [Focus Shape](help:focus-shape) and anything that would block the Focus while you edit, so you know before analysing what the Focus will be offered. Nothing you edit is written until you press **Save** (opening the window can write an implicit Focus into the file; see below).

## Opening it

Load an experiment (double-click its row in the Project panel's members table, or select a standalone Experiment Directory). The Experiment panel opens with the **Focus** card at the top:

- **New…** opens the window and immediately adds a new Focus.
- **Edit…** opens the window with the Active Focus selected.

The window title is `Focuses — <experiment name>`. If the data file cannot be read, the window does not open and the Hub says why ("The Focus window could not read this experiment's data").

Opening the window writes any *implicit* Focus into `survival_config.yaml` before you edit anything: Unfiltered, or a migrated Interaction Focus. This makes it a declared Focus you can see and rename, and freezes the data file's level order so a later re-sort of the Design sheet cannot move a Reference Level. It happens even if you then press Cancel: it is part of opening the Focuses for editing, not one of your edits.

## The layout

The intro line at the top names the data file the factors come from. Below it the window is split in two:

- **Left:** the list of this experiment's Focuses, with the buttons that add or remove them.
- **Right:** the editor for the Focus selected in the list (its name, one box per discovered factor plus one per factor the data file lacks, the preview, and the treatment table).

**Save** and **Cancel** are at the bottom.

## The Focus list and its buttons

| Button | What it does |
|---|---|
| **New** | Adds a Focus over every discovered factor at every level, named `New focus` (then `New focus 2`, …). |
| **Duplicate** | Copies the selected Focus, including its Reference Levels, display names and colours, as `<name> copy`. |
| **Delete** | Removes the selected Focus. Its results stay on disk and are listed in the Hub as **Orphaned Results** until you adopt or delete them. An experiment must keep at least one Focus ("An experiment needs at least one Focus."). |
| **Import from DefinedPlots…** | Proposes a Focus for each plot in the workbook's `DefinedPlots` sheet (see below). Enabled only for an `.xlsx` data file. |
| **Copy Focuses from…** | Copies Focuses from another member of the same Project (see below). Enabled only when the experiment is a Member Experiment. |

## Name

The **Name:** field renames the selected Focus. The list updates as you type. If you clear the field, the Focus keeps its previous name. Renaming here is safe. When you save, the Focus's results folder `analysis/<old>/` is moved to `analysis/<new>/` and the name suffix of every file in it is renamed, so nothing becomes orphaned. The save is refused if the new folder already exists (`analysis/<new>/ already exists; delete or adopt it before renaming…`).

## The factor boxes

There is one box per factor discovered in the data file, titled with the factor's name and with a checkbox in its title:

- **Box unticked** – the factor is **pooled over**.
- **Box ticked, one level ticked** – the factor is a **filter**.
- **Box ticked, two or more levels ticked** – the factor **varies** and labels the treatments.

A ticked box with *no* level ticked is neither: the preview shows *Blocked: factor '…' is ticked but none of its levels is — tick the levels to keep, or untick … to pool over it*, and **Save** refuses until you do one or the other.

Inside each box:

- **Level list** – every level the data file holds for this factor, each with a tick box. Tick the levels the Focus keeps. The list shows four rows and scrolls if there are more.
- **Order** – drag a level, or select it and use **▲** / **▼**, to set the display order. The order controls legends, the facet panels of the faceted KM, and the cells of the interaction plot. It is saved as the order of the level list in the YAML.
- **Reference:** – a drop-down of the ticked levels, giving this factor's Cox baseline. It defaults to the first ticked level, and once chosen it stays with its level when you reorder the list. It is enabled only when the box is ticked and at least two levels are ticked. **Save** writes every varying factor's reference under `reference:`, the default included, so reordering the levels later (here or by hand in the YAML) never moves the baseline. Writing the default down changes no number and does not put saved results Out of Date.

If a Focus names something the data file no longer has (a **stale** Focus, which is blocked), the window shows it so you can remove it:

- A stale **level** appears in its factor's list in red, marked "(not in the data file)", ticked. Untick it to drop it from the Focus.
- A stale **factor** gets a box of its own above the discovered ones, titled "*factor* — not in the data file", ticked and listing the levels the Focus names. Untick the box to drop the factor.

## The preview line

Under the factor boxes, a few lines update with every change:

- **`<name>: <description>`** – each varying factor with its levels and reference, any filters (`only Sex = Female`) and the factors pooled over.
- **`N = … · k treatment(s) · shape …`** – the individuals the Focus selects after the active Exclusion Group and the workbook's chamber flags are applied, the number of populated treatments, and the Focus Shape (for example `2×2`, or `2×2 (3 of 4 cells)`).
- **`This Focus offers …`** – which conditional analyses the Focus is offered (a comparison between treatments; a figure crossing factors; the Factorial Battery), with *(not computable: …)* after any that the data cannot support.
- **`Absent cells (never in the data — not an error): …`** – cells the levels imply that the data never held.
- **`Blocked: …`** (in red) – each reason the Focus cannot run as declared: a factor or level the data does not contain, or a cell the exclusions have emptied. A Focus with no factors ticked shows *Blocked: Tick at least one factor.*

If the data could not be loaded for the preview, only the description and the stale-name check are shown.

## The treatment table

The table lists the Focus's treatments: the populated ones if the preview could be computed, otherwise every implied one.

| Column | Meaning |
|---|---|
| **Treatment** | The treatment label (levels of the varying factors joined with `/`). Not editable. |
| **Display name** | What the treatment is called in Publication Figures. Leave it blank, or equal to the label, to use the label. |
| **Colour** | A swatch. Click it to pick the treatment's curve colour (the dialog has an alpha channel; alpha 0 means transparent). A swatch reading *auto* means no colour is set. |

Display names and colours are stored in the Focus (`display_names:` and `colours:`) and used by the Plot Editor and the Publication Figures. Curve colours changed in the Plot Editor are written back into the Focus, so both places agree. Neither changes any number, so editing them never makes results Out of Date.

## Import from DefinedPlots…

This reads the workbook's `DefinedPlots` sheet and lists every plot. A plot can be imported only if its treatments form a **rectangular product** of levels. That means the Focus built from the levels it uses would contain exactly the listed treatments among those the data holds, and no others. Plots that cannot be imported are greyed out, with the reason in the tooltip (for example "its treatments are not a rectangular product of levels (the product would also include …)"). Tick the ones you want and press OK. Each becomes a new Focus named after the plot. Import is offered rather than automatic because a Focus is an independent analysis with its own report section, not just a figure. If the workbook has no DefinedPlots sheet, the window says so. See [Defined Plots](help:defined-plots).

## Copy Focuses from…

Choose another member of the Project. Every one of its Focuses is checked against **this** member's data and exclusions before anything is added. A Focus is not copied if a Focus of the same name already exists here, if it names a factor or level this member's data file does not contain, or if one of its treatments that this member's data holds would have no individuals once this member's active Exclusion Group (and ChamberFlags) are applied. The skipped ones are listed with the reason ("Not copied — they would be blocked here or clash by name"). The copied Focuses appear in the list and are written only when you Save. Focuses are never inherited from `project.yaml`, so this is the way to share a design between members.

## Save and Cancel

**Save** first takes the selected Focus exactly as the window shows it, then checks the whole set. Any problem is shown in a *Cannot save* message and the window stays open. Problems include a Focus with no factors, a factor ticked with no level ticked, a level listed twice, a `reference:` naming a level the factor does not keep, two Focuses with the same name or output folder, and a reserved name (`plots`, `statistics`, `data_output`). If any Focus still names a factor or level the data file does not contain, Save asks *Save blocked Focuses?*, listing them; Cancel keeps the window open so you can drop them. If all is well it:

1. moves the results of every renamed Focus to its new folder,
2. writes the complete `focuses:` block to `survival_config.yaml` (removing an old pre-Focus `factors:` block if there was one), and
3. makes the Focus selected in the list the Active Focus.

The log records `[focus] <experiment>: saved N Focus(es)` and any renames.

**Cancel** discards your edits in the window.

## Pitfalls

- Changing a Focus's levels, level order or Reference Level after analysing it makes its saved results [Out of Date](help:focus-status).
- Deleting a Focus does not delete its results. Clear them from the Focus card in the Hub (**Delete…**).

## See also

- [What a Focus is](help:focus)
- [Reference Levels](help:reference-level)
- [Focus Shape — what a Focus is offered](help:focus-shape)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
- [The Experiment panel](help:experiment-panel)
- [Defined Plots](help:defined-plots)
