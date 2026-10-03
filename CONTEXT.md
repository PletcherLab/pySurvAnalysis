# pySurvAnalysis

Survival/demography analysis pipeline and desktop UI for lifespan experiments
(DLife Excel workbooks and CSV/TSV cohorts). This glossary fixes the domain
language; it is not a spec.

Structurally modelled on PyTrackingAnalysis (Batch → Project → Experiment,
tile-strip Hub, two-level scripting, Experiment Types, publication figures),
with one deliberate divergence: **Projects here never pool.**

## Language

**Batch**:
A directory with at least one Project anywhere beneath it. Discovery is
**recursive and prunes at each Project** (ADR-0009): the walk descends until
it finds a Project — `project.yaml` plus at least one Member Experiment — and
never looks inside one, because a Project's subdirectories are its members by
definition. Projects therefore need not be immediate children, and grouping
folders (`Sept2026/`, `Archive/2025/`) are transparent. Purely a processing
convenience for running many Projects unattended; it holds no analysis of its
own and never combines results. A Batch may contain Batches — whichever is
selected is the one that runs, and a nested `batch.yaml` is named in the log
and ignored.
_Avoid_: study, collection, batch root

**Batch Project**:
One Project a Batch Run can target, identified by its **key** — its POSIX path
relative to the Batch root (`Sept2026/ProjA`; a top-level Project is just
`ProjA`, so every `batch.yaml` written before discovery went recursive still
resolves). Deliberately *not* called a member: at this level "member" would
collide with **Member Experiment** one level down, and "a member with four
members" is a sentence this codebase must not be able to write. It is the word
the sister app uses for the same thing; the collision is why we diverge.
_Avoid_: member, batch member, replicate

**Blocked Member**:
A Member Experiment a run cannot use as it stands: a directory holding data
with no `survival_config.yaml`, a config with no data file, or an **ambiguous**
one holding several candidate files where the loader refuses to guess. Each
reason names its own fix — scaffold the config, supply the data, or name one
with `data_file:`. Blocked is a property of the Member Experiment, never of
the Project: a Project with four healthy members and one blocked member runs
the four. Blocked members are named before a Batch Run starts and again in its
summary — being reported is the whole point, and a run is never refused
because of one (a stale folder must not stop ten Projects at 2am). There is no
"unfiled" state here: the loader searches `data/` **and** the directory root,
so a file at either is already found (ADR-0009 diverging from the sister app,
whose loader reads `data/` alone and which therefore also *files* recordings).
_Avoid_: invalid member, broken member (nothing is broken — the run just
cannot use it yet), unfiled

**Blocked Focus**:
A **Focus** a run cannot use as declared — the **Blocked Member** rule applied
one level down. Two reasons, each naming its fix: **stale**, where the Focus
names a factor or level the data file no longer contains (a corrected Design
sheet renamed `mDilp` to `mDilp235bx`; the fix offers the close match), and
**empty**, where a cell the data *did* contain has no individuals left once the
active Exclusion Group is applied — QC changed the design out from under the
Focus. A cell the data never had is not empty in this sense; it is absent, and
absence is normal. The matching rule is deliberately asymmetric: data
holding levels a Focus does not name is *normal*, since selecting a subset is
what a Focus is for; a Focus naming levels the data lacks is the failure. A
Blocked Focus never runs silently narrowed — it is named in the Batch
Preflight and the run summary, and its member's other Focuses run.
_Avoid_: stale focus (one of its two reasons, not the state), invalid focus,
empty focus

**Batch Preflight**:
The modal a Batch Run always opens first: the discovered Projects with their
keys, usable-member counts, blocked members and **Blocked Focuses**, each
offering the action that clears it, then Run or Cancel. Finding a Blocked
Focus means reading each Design sheet's factor columns — a deliberate bend of
the preflight's otherwise layout-only, no-data-read rule, accepted because
those sheets hold one row per chamber and a Focus silently narrowed in the
middle of a run is far costlier. Shown even when nothing is
wrong, because with recursive discovery the folder you picked no longer says
what will run, and that target list is the one thing no other surface states.
Unchecking a Project means "do not touch this one"; a Project repaired inside
the preflight joins the run, since the repair is what made it runnable.
_Avoid_: batch dialog, confirmation

**Project**:
A directory with a `project.yaml` at its root whose immediate subdirectories
holding a `survival_config.yaml` are its **Member Experiments** — a set of
independently analyzed experiments addressing one question in slightly
different ways. A Project never pools its members. A Project is never also a
Batch: its subdirectories are its members, so a `project.yaml` nested inside
one does not make a second Project (ADR-0009).
_Avoid_: batch parent, parent directory

**Project Defaults**:
The `defaults:` section of `project.yaml` — a seed and template inherited by
Member Experiments unless a member overrides it: the Experiment Type, the
time unit and censoring policy, input settings, the default Exclusion Group
name, quality criteria. The data-source concerns, in other words — the same
boundary the Experiment Type now draws. It is *not* an authority: the only
value hard-validated across members is the **Experiment Type**. It never
carries design: factors are discovered, and **`focuses:` is the one section a
member never inherits** — members rarely share factors, so an inherited Focus
would be a Blocked Focus in every member it does not fit, and editing one
would silently put every member's results Out of Date at once. Sharing a
design is the explicit *Copy Focuses from…* in the Focus window, validated
against the receiving member's discovered factors before it is written — the
same move ADR-0005 made for Styles.
_Avoid_: design (the PyTrackingAnalysis term, which IS an authority and
implies pooling)

**Member Experiment**:
An Experiment that belongs to a Project — one data file, analysed apart from
its siblings and never pooled with them, related to them by the *question*
they address rather than by an identical design. Within it, each **Focus** is
analysed on its own; a member is the container, the Focus the unit. The Hub's Experiments card offers five ways to get one,
answering two different questions (ADR-0010). **What state is the folder in?**
— it does not exist (**Create experiment…**), its directory is in the Project
but has no config (**Initialize existing directory…**), or it is a member
already (the table, and **Experiment configs…** for the bulk view). **Where
does it come from?** — ADR-0008's two ways in from outside, and the Hub keeps
them strictly outside: an existing directory copied in (**Add directory**
refuses a folder already in the Project, naming Initialize instead), or one
built around a single DLife workbook (moved in if it was already loose in the
Project tree, copied otherwise).
_Avoid_: replicate (implies same-design repeats and pooling — the very thing
this app does not do), arm, variant

**Experiment Directory**:
One data file's directory — `survival_config.yaml` at its root, the input
workbook/CSV at the root or in `data/`, outputs in `analysis/<focus>/` one
subdirectory per **Focus**, QC state in `qc/` — either standalone or as a
Member Experiment inside a Project. The file may hold several experiments; the
directory holds them all and the Focuses tell them apart.
_Avoid_: project directory (the pre-overhaul name), results folder,
`<stem>_results/` (the superseded output convention)

**Experiment Type**:
A named bundle describing the **data source** — the expected input shape, the
time unit and axis label, the censoring policy, the default quality criteria,
and the report sections. It deliberately says nothing about the experimental
*design*: which analyses apply is decided by **Focus Shape**, because one data
file may hold several designs. All Member Experiments of a Project share one.
_Avoid_: assay, protocol, template, design (the Focus carries the design)

**Standard Lifespan**:
The general case, and the only Experiment Type: a DLife census workbook of
chambers/vials scored to death, assumed censoring on. Every analysis the app
can do is reachable from it, gated by Focus Shape rather than by type.

**Focus Shape**:
The signature of a **Focus** — which factors it varies and how many levels
each has, which of the implied cells hold individuals after the Exclusion
Group, and where the crossing of two varying factors has a hole — and what
every **Requirement** is checked against. Its definition half is known from
`survival_config.yaml` without reading any data; its populated half the Hub
estimates from the Design sheet and the active exclusions, so both are on
screen before anything runs.
_Avoid_: design shape, factorial flag

**Requirement**:
What an analysis or figure needs from a Focus, in two halves.
**Relevance** is decided by the Focus's *definition*: an action that is not
relevant is **not offered** — no Hub button, no figure, no report section —
because it is not a question the slice asks; one quiet line in the Hub says
what is not offered and why. **Computability** is decided by the *data*: a
relevant action the populated cells cannot support is **Not Applicable**,
greyed in the Hub with the reason and recorded by the run. There are three:
**comparison** (relevant with two or more implied treatments, computable with
two populated — log-rank, Gehan-Wilcoxon, hazard ratios and their forest, the
log-log PH diagnostic); **factorial plot** (relevant with two or more varying
factors — the faceted KM and the interaction plot, where a missing cell is
only a missing curve); and **factorial model** (relevant on the same
condition, computable only when every pair of varying factors is fully
crossed — the Cox and RMST models, whose interaction terms are not estimable
across an empty cell). Everything else — KM, Nelson-Aalen, hazard, mortality,
distribution, parametric fits — needs nothing.
_Avoid_: precondition, gate, criteria

**Not Applicable**:
What a real action does when it is **relevant** to the Focus but the data
cannot **compute** it — the Factorial Battery for two varying factors whose
crossing has an empty cell, say — or when a script step asks explicitly for
one the Focus is not offered. Recorded in three places, because a warning in a
log nobody reads at 2am is the silent skip ADR-0002 forbade: the run log, the
Focus's **Run Summary** as a machine-readable entry, and one line of prose in
that Focus's report section. An action merely *not offered* — the battery for
a one-factor Focus — is not recorded at all: it was never a question the slice
asked, and a note in every report would teach readers to skip the ones that
matter. Distinct from an
action name outside *core ∪ type*, which is a typo and remains a hard error
that refuses to start the script.
_Avoid_: skipped, warning (a warning is the severity, not the record), n/a

**Factorial Battery**:
The interaction analyses — the Cox main-effects vs pairwise-interaction model
with the LR omnibus and Schoenfeld PH test, plus the RMST pseudo-value
companion — together with the faceted KM and the lifespan interaction plot.
Formerly the whole point of an "Interaction Experiment" type, and limited to a
2×2; now ordinary actions any experiment can reach, offered whenever the Focus
varies **two or more factors**, of any number of levels each. The models are
computed when every pair of those factors is fully crossed, and are Not
Applicable, with the empty cell named, when one is not (ADR-0011).
_Avoid_: interaction experiment (the retired type), factorial design, 2x2
experiment

**Reference Level**:
A factor's Cox dummy-coding baseline and the baseline in the report's prose,
named per factor in a **Focus**'s `reference:` key and defaulting to the first
level listed when that key is absent. The Focus window always writes it down,
so reordering levels there can never silently move the baseline; a hand-written
Focus without the key still means the first level, and the two are the same
analysis — Out of Date compares the level the model uses, not whether the key
was written. Declaring it separately from level order
keeps a presentation choice from silently rewriting the statistics: the order
governs legends, facets and plot cells, while the Reference Level governs the
sign of every coefficient, the interaction term included — so densities may
read `20x, 40x` while the model baselines on the `40x` control.
_Avoid_: control, baseline level, first group, first declared level (the
default, no longer the definition)

**Custom Experiment**:
Retired (ADR-0011). It named the absence of a chosen Experiment Type, in which
"all discovered factors get the full battery" — which is now simply what
**Standard Lifespan** does, with the battery gated by **Focus Shape**. A config
with no `experiment_type` key is a Standard Lifespan.
_Avoid_: generic, freeform, none, untyped

**Focus**:
A **named** selection over the factors and levels *discovered in the data
file* — the slice of the factor space to be analysed — collapsed into the
`treatment` that every downstream analysis, figure and statistic groups by.
It is the **rectangular product** of the levels it names: a cell that product
implies but the data never contained (an unbalanced design that ran `InR`
only at `20x`) is simply absent, not an error, and the Focus Inventory shows
which cells exist. A diagonal — two of four existing cells — is not
expressible, by choice. Each discovered factor plays one of three roles: named
with two or more levels it is **varying** and labels the treatments; named
with one level it is a **filter**; not named at all it is **pooled over**.
Every report and the Hub say which, because pooling changes every number.
Individuals with no recorded level for a factor the Focus names belong to no
treatment; a run counts them and says so rather than dropping them unsaid.
Declared in `survival_config.yaml`'s `focuses:` block — each factor's levels
in display order, an optional `reference:` naming each factor's **Reference
Level**, and the display names and colours of the treatments it produces — and
authored in the Focus window, where the selection is free to change between analyses; it
becomes part of the record the moment an analysis runs under it,
giving its name to every output file and figure that run produces and being
named and described in every report built from them. A data file holding
several experiments is analysed one Focus at a time, and their results coexist
because the name keeps them apart — without it the second analysis would
overwrite the first.

A config that declares no `focuses:` block has one anyway: **`Unfiltered`**,
every discovered factor at every level, materialised into the file the first
time the experiment is analysed or its Focuses are opened for editing, so it
can be seen and renamed. Discovery orders levels by **first
appearance in the Design sheet**, never alphabetically — appearance order is
what the experimenter typed and controls usually come first, whereas
alphabetical order would quietly make `mDilp235bx` the reference over `wCS`.
Materialising freezes that order, so a later re-sort of the sheet cannot move a
Reference Level either. Named for what it is rather than `All`,
which would collide with "run under all Focuses" — two readings with opposite
blast radii. It is what the retired **Custom Experiment** meant, and it makes
every config written before Focuses existed keep running unchanged — outputs
land in `analysis/Unfiltered/`. There is no such thing as
an unfocused analysis: an output with no Focus name is the provenance gap
ADR-0011 exists to close.
_Avoid_: filter (an **Exclusion Group** filters, by chamber), subset, view (a
view leaves no trace; a Focus names what it produced), selection

**Active Focus**:
The Focus the Hub is currently showing and that Analyze, Plots and AI act on —
**UI state, deliberately**, where the active Exclusion Group is configuration.
The asymmetry is the point: a directory has one active Exclusion Group, so
switching it silently changes every result and must be recorded; every Focus's
outputs coexist under their own names, so switching the Active Focus changes
nothing on disk and is navigation, like double-clicking a member.
_Avoid_: current focus, selected focus, default focus (`Unfiltered` is the
default *declared* Focus; which one is active is a separate matter)

**Plot Set**:
The ordered list of figures a run produces — what the report embeds and what
the Plot Editor offers. Standard Lifespan's base set is the general
survivorship battery, less any figure whose **Requirement** is not relevant
to the Focus (a single-treatment Focus gets no forest and no log-log
diagnostic); a Focus varying two or more factors adds the faceted KM (its
**Headline Figure**) and the lifespan interaction plot. The Plot Set is
therefore a property of the run — type plus Focus — not of the directory.
_Avoid_: plot list, figure set

**Analysis Set**:
The optional analyses a run may perform — log-rank pairwise and omnibus,
Gehan-Wilcoxon, pairwise hazard ratios, parametric AFT, and the interaction
analyses (the **Factorial Battery**, one item) — less any whose **Requirement**
is not relevant to the Focus. The survivorship core (lifetables, summaries,
median and mean survival) is not in it: every figure and section stands on
that core, so it always runs. Like the Plot Set, a property of the run.
_Avoid_: analysis list, battery (that is the whole run)

**Left Out**:
An item of the Analysis Set or Plot Set the Focus is offered that the
experiment's `omit:` block excludes from every run — Hub, script or Batch
alike; the boxes unticked on the Hub's Analyze and Plots panels (ADR-0012).
The run records each in the log, the Run Summary and the report's Focus
section, apart from **Not Applicable**: left out is a choice, Not Applicable
is the data. A figure that draws from a left-out analysis (the forest, from
the hazard ratios) is left out with it.
_Avoid_: skipped, disabled

**Headline Figure**:
The one figure of a Plot Set that states a **Focus**'s primary result — the
faceted KM when the Focus crosses factors, the KM with at-risk counts
otherwise.
It leads that Focus's report section and is the default plot the Plot Editor
opens.
_Avoid_: main plot, key figure

**Publication Figure**:
A hand-curated, journal-ready vector figure (SVG with editable text, or PDF)
rendered by plotnine from a Plot Spec + Plot Style — distinct from the
matplotlib figures the Hub previews and the QC Viewer draws. It is **authored
in the Plot Editor and rendered from the Project panel**, and nowhere else:
a Spec belongs to one experiment (ADR-0005), while rendering walks every
member, so the two actions have different subjects and do not share a card.
The Plots tile holds only the Type Actions the loaded Experiment Type
contributes.
_Avoid_: report figure, plot export

**Plot Style**:
One figure's look, **owned by that figure**: saving a figure writes its spec
and its style together, under the figure's own name, so editing the mortality
plot's line width never restyles the KM curves. A shared look is applied
deliberately, with the Figure card's *Copy style from…* (another figure, or
any named style in the file). Edited in the Plot Editor's four style cards: **canvas and type** (size,
theme, font family, base size, a per-element point size for title / axis
titles / ticks / legend / strips, and one text colour for all of them),
**curves and points** (curve width, the separate weight of the axis
furniture, markers on the curve with their shape, size, opacity, fill and
outline, censor ticks, the confidence band), **panels and legend** (panel
fill and border, gridlines, facet-strip style and fill, legend position, the
At-Risk Band's size and times), and **colours** (a per-curve assignment, over
a fallback cycle). Every per-element size defaults to 0 = *follow the base*,
so a style that sets only `base_size` still scales as one thing. Axis
**limits** are Spec fields, not Style: pinning a range is a per-figure
editorial decision, optional per axis behind a checkbox.
_Avoid_: theme (a plotnine theme is one field inside a style), shared default
style (the superseded model — `default_style` survives only as the seed for a
figure's first edit)

**Defined Plot**:
A named treatment grouping an experimenter writes into the DLife workbook's
`DefinedPlots` sheet at design time — one column per plot, the name in row 1,
treatment labels from row 6. It is a **figure**, not an analysis. It is
relevant to a Focus that pools over nothing and holds, within its levels,
every listed treatment the data file has; there it renders as a KM figure
named for the plot and the Focus, or — when a listed treatment is absent,
emptied by exclusion, or a typo the file never had — is **Not Applicable**
with the missing labels named, never drawn with fewer curves than the
experimenter listed. A plot comparing the sexes is not about a females-only
Focus, so it is simply not drawn there. Because experimenters often use it to mark the separate experiments in
one file, the Focus window offers *Import from DefinedPlots*, proposing a
Focus for each plot whose treatments form a rectangular product of levels —
offered rather than automatic, since promotion turns a figure into an
independent analysis with its own report section.
_Avoid_: plot definition, custom plot, defined analysis (it becomes an analysis
only by promotion to a Focus)

**Plot Spec**:
One Publication Figure's content decisions — axis labels, axis limits,
reference line, and optionally a **narrowing** of its Focus's treatments to a
subset — plus the name of the Plot Style it uses. Specs and Styles live
together in **one `plot_specs.yaml` at the container** (the Project, or a
standalone Experiment Directory) — ADR-0005 as amended: the curation is the
project default, and every member renders with it. A Spec never orders or
renames treatments: order and inclusion belong to the **Focus**, which decides
them for every analysis rather than one figure, and display names and colours
belong to it too, because treatment labels are Focus-scoped and a Project-wide
list of them would match almost nothing. Narrowing can make a figure smaller,
never contradict the model printed beside it. The whole Plot Set is curatable, not just the
KM curves; each plot's kind gates which Style features apply to it. Only
figures **saved into** `plot_specs.yaml` are rendered — "Save Project
default" writes one spec (and the Style it names) at a time, so a render
produces the curated figures and nothing else. A curated figure also
**outranks the analysis's own figure in the reports** (as in the sister app):
the member report and the Project Report show a curated plot through its
Spec + Style, at 200 dpi, and fall back to the default matplotlib figure only
for plots nothing was curated for — a curated `km_curves` stands in for both
default KM figures, since the at-risk band is a Style toggle there.
_Avoid_: plot config, settings, per-member spec (the superseded layout),
treatment list (a Spec narrows; the Focus lists)

**At-Risk Band**:
The number-at-risk counts drawn as a `geom_text` layer in a reserved band
below the curves *inside the same ggplot*, rather than as a separate axes.
Keeps a Publication Figure one grammar object, so faceting, theming and
vector export need no figure composition.
_Avoid_: risk table (the matplotlib two-axes construction in `plotting.py`,
which remains what the Hub preview and QC Viewer use)

**Analysis Hub**:
The main app: a two-tier tile strip. The ribbon is exactly **Batch ·
Project · Experiment** (one width, 220% of the old tile size), each showing
only live status, with the status readout filling the rest of the strip and
a full-width output/plots area below. There is no Tools tile: every tool it
held duplicated a control that lives where the work is (Validate YAMLs on
the Project card — which also validates a loaded standalone — Clear output
on the output area, Create/Initialize on the Create/Load card). The **Experiment tile** fronts the five
experiment-level surfaces — **QC · Analyze · Plots · Scripts · AI**, QC first
because you decide what to exclude before you analyse it — as sub-tiles in
its panel: all five wait on the same loaded experiment, and five dimmed
ribbon chips said that five times over. A sub-tile opens the panel it
always had, anchored under the Experiment tile; the Experiment tile itself is
the one tile that refuses to open with nothing loaded — it is dimmed, and a
click says where to load one instead — since its panel holds no fixer
control, only the gates. Above the five
sub-tiles sits the **Active Focus** selector — a scope the sub-tiles act on,
not a sixth destination — with New… and Edit… opening the Focus window and a
shape line (`Genotype: wt, mut (reference wt) × Diet: AL, DR (reference AL) ·
shape 2×2 · offers a comparison between treatments; …; the Factorial
Battery`) showing, before anything runs, which conditional analyses the
Focus is offered and which its data cannot compute. The status readout carries
a Focus row, since "which experiment" without "which Focus" is now half an
answer; its rows run Selection, Project, Experiment, Focus, then the Project's
question, and whatever does not fit goes to its tooltip. All controls live in a tile's anchored panel, one open at a time.
The Analyze and Plots panels are each a checkbox per item of the loaded
**Experiment Type**'s **Analysis Set** or **Plot Set** the Active Focus is
offered, over one button — Run analysis, Generate plots; an unticked box is
**Left Out** of every run (ADR-0012). The selection names the working
container — a Batch, a Project, or a standalone Experiment Directory; a Member
Experiment is loaded by double-clicking its row in the Project panel's members
table, which lands on the Experiment panel so the Focus is chosen before
anything runs. The Project
panel is three cards deep: **Create/Load** (the ways into a Project, plus
Validate YAMLs), **Experiments** (the members table and the ways to make one),
and **Actions** (report, view, plot editor) over the Project **Scripts** card.
_Avoid_: sidebar card column (the pre-overhaul layout), Load tile (absorbed:
input format, time/event columns and censoring policy now live in
`survival_config.yaml`)

**Type Action**:
A script action contributed by an Experiment Type rather than by the core.
Until ADR-0012 each was also a Hub button; the Hub now offers the type's
Analysis Set and Plot Set as checkboxes instead. The action registry at each level is
*core ∪ type ∪ what the active Focus Shape admits* — `cox_interaction` and
`interaction_plot` are always in the registry, so a script naming them is
valid; whether they apply is decided per Focus at run time, and a Focus
they do not suit records them as **Not Applicable** (ADR-0011). A script step naming an action outside that union is a
hard error: the script refuses to start, and in a Batch Run that
Project is logged, counted as a failure, and the Batch continues.
_Avoid_: plugin, extension, custom action

**Experiment Script**:
A saved, re-runnable step list of experiment-level actions. Lives in an
Experiment Directory's `survival_config.yaml` `scripts:` — or, for Member
Experiments, centrally in the Project's `experiment_scripts:` section, where
one recipe serves every member without being copied. The palette resolves
from the Project's Experiment Type, but the **Focus Shape** half of the
registry is per-Focus, so a shared recipe is valid only for the Focuses whose
shape admits its steps.
_Avoid_: recipe, macro, pipeline

**`run_in_focuses`**:
The experiment-level bridge downward, mirroring the Project's
`run_in_experiments` one level lower: it runs the rest of an Experiment Script
once per **Focus**, continue-on-error, with a blank `only:` meaning every
Focus and a named list meaning just those. Steps therefore never name a Focus
themselves — they cannot, since Focus names differ between Member Experiments
— which is what keeps one `Standard analysis` recipe serving every member
uncopied (ADR-0007). A script with no `run_in_focuses` step runs under the
**Active Focus** — or, unattended, where there is none, under every Focus:
an unattended run that analysed one Focus and stayed quiet about the rest
would be the silent gap Focuses exist to close.

**Project Script**:
A saved step list of project-level actions in `project.yaml` `scripts:` —
same shape and visual editor as an Experiment Script, separate registry.
The only bridge down is `run_in_experiments`, which runs a named Experiment
Script in every Member Experiment (or just those named in its `only:` list),
continue-on-error.

**`batch` script**:
The Project Script every `project.yaml` is created with (ADR-0007), named for
what it is: the one a Batch Run executes in this Project unless another is
designated. Written into the file rather than kept in code, so it is visible,
editable and renameable. A Project whose `scripts:` is empty does not run.
_Avoid_: default script (says nothing about when it runs)

**`Standard analysis` script**:
The Experiment Script every `survival_config.yaml` is created with (ADR-0007
amendment) — the one a Project's `batch` script names in
`run_in_experiments`, so a Batch Run works on a fresh Project with nothing
authored. Seeded on the file's first write when it has no `scripts:` key at
all, and left alone once the block exists (an empty list is a deletion).
Resolution by name is the Project's central `experiment_scripts:`, then the
member's own file, then the in-code built-in — the last only so a config
written before the default was seeded still runs.
_Avoid_: default script, built-in (it lives in the file, not in code)

**Batch Run**:
One execution of a designated Project Script in every **checked** Project of a
Batch, continue-on-error with per-Project log prefixes. The checked set is
confirmed in the **Batch Preflight** and nothing outside it is touched.
`batch.yaml` holds the designation and a central `project_scripts:` section.
The Hub's script picker writes the designation (`script:`), and its default
entry — each Project's own — removes it rather than create the file; a
`batch.yaml` that will not parse lists the Batch but refuses to run or be
written. **No designation means each Project runs its own `batch` script** — resolution
for a named one is central `project_scripts:`, then the Project's own
`scripts:`, then the built-ins; a name that resolves nowhere fails that
Project, and the run continues. The summary carries a usable/total member
ratio per Project, so "succeeded" cannot be read as "analysed everything".

**Project Report**:
`<project>/<project>_report.pdf`: a cover carrying the project's question, a
**Focus Inventory**, a **Divergence Note** when members' data-source settings
differ, then one independent section per **Focus** built from that Focus's
*saved* analysis outputs. A declared Focus that has not been analyzed yields a
"not analyzed" section rather than being silently analyzed — which is why
Focuses are declared in the config and not merely chosen: an un-run Focus and
one nobody ever conceived must not look the same.
_Avoid_: combined report, pooled report

**Focus Inventory**:
The Project Report's table of every Focus in every Member Experiment, one row
each: member, Focus name, the slice it takes (factors, ordered levels and
Reference Levels, in one line), N, deaths, % censored, treatments, and state — analysed, not analysed, **Out of Date**,
**Blocked** — plus any **Not Applicable** actions. It replaced the Member
Inventory when the Focus became the unit of analysis, and it absorbed design
divergence from the Divergence Note: with members rarely sharing factors,
listing every design side by side says more than "they differ" ever did.
_Avoid_: member inventory (the superseded per-member table), design table

**Divergence Note**:
The Project Report's prose statement of where Member Experiments differ in
**data-source** settings — censoring policy, active Exclusion Group, time unit
— which the Experiment Type and Project Defaults are meant to keep uniform and
a member may override. Design divergence is not here: factors differ between
members by default, so a note saying so on every Project would teach readers to
skip it, and with it the one line that mattered. Divergence in data-source
settings is legal, which is exactly why it must be declared — assumed
censoring on in one member and off in another changes how every death is
counted, and can flip a comparison's conclusion.
_Avoid_: design divergence (the Focus Inventory shows design)

**AI Narrative**:
An optional, AI-written summary attached to a report: one paragraph per
**Focus** from that Focus's own numbers, plus a closing qualitative
"across Focuses" paragraph on agreement and disagreement, captioned as
non-statistical. The AI *summarizes* the pipeline's analysis; it never performs
its own, and no numbers are ever combined. Saved beside the Project as
`<project>_narrative.json`, each paragraph stamped with the Run Summary it
summarised; a derivative of a run — re-running a Focus's analysis retires that
Focus's paragraph and the across-Focuses one, which are never shown again.
_Avoid_: AI analysis, AI interpretation, meta-analysis

**Exclusion Group**:
A named set of chambers removed from analysis, stored in `qc/remove_chambers.csv`
(a legacy root-level `remove_chambers.csv` is still read, and its groups move
into `qc/` on the first save). A member opts out of a group its Project
Defaults name with an explicit `exclusions: {group: ''}`; a script step that
excludes more on top (`apply_exclusions`) stamps the run with both names
(`base + extra`), so those results read as Out of Date against the config.
The **active** group is configuration (`exclusions: {group: ...}` in
`survival_config.yaml`), not UI state, and its name is stamped on every report
and Run Summary — so the same input and config always give the same result.
The stamp reports what the group *actually removed*: a cohort with no chamber
identities (a CSV) records the group in force and zero removals rather than
claiming exclusions that could not have happened. One active group per
**directory**, shared by every Focus in it: a chamber's validity is a fact
about the chamber, not about which slice is being analysed, and per-Focus
groups would let two sections of one report disagree about whether the same
vial is valid data. The QC viewer *shows* the Active Focus's chambers — that is
navigation — but the groups it saves belong to the directory.
_Avoid_: filter, exclusion set, removed vials, focus exclusions

**Chamber**:
One vial/container of individuals, the unit of the DLife census and the unit
an Exclusion Group removes. Individuals within a chamber share a treatment.
_Avoid_: vial, cage, replicate

**Assumed Censoring**:
The DLife convention that individuals unaccounted for at the end of a census
are treated as right-censored rather than dead. A per-experiment policy, set by
the Experiment Type's default and overridable in `survival_config.yaml`.

**Initialize**:
Give a directory that already exists the marker file that makes it a Project
or a Member Experiment, keeping its own name and contents — `project.yaml` at
the Project level, `survival_config.yaml` one level down. The third of the
three states a folder can be in (ADR-0010): **Open** wants the marker already
there, **Create** makes the directory too, and Initialize is the one for a
directory you already have. Distinct from **Upgrade**, which rewrites an old
*layout* into the current one; initializing writes a marker and moves nothing.
_Avoid_: adopt (reserved for ADR-0008's two ways a member arrives from
outside the Project, which copy or move data), convert, import

**Upgrade**:
The pre-overhaul → current layout rewrite (`domain/upgrade.py`): move a root
`remove_chambers.csv` into `qc/`, sniff a config for an adopted workbook. No
longer a Hub button — the Create/Load card's Initialize covers promoting old
directories, and `sniff_config` keeps serving adoption — so `plan`/`apply`
survive as library code only.
_Avoid_: migration (overloaded), conversion

**Run Summary**:
`analysis/<focus>/run_summary_<focus>.json` — the small record of one analysis
run under one **Focus** (counts, the Focus's **analytic definition** — its
factors, their ordered levels and its Reference Levels — the Exclusion Group
and which chambers it actually removed — the stamp is `base + extra` when a
script excluded more — the data file's content hash, the censoring policy, the
`omit:` selection, the figures
written, any **Not Applicable** actions and why, the omnibus test, and each
factorial model's headline numbers). One per Focus, never one per directory: that is what keeps analysing a second
Focus from overwriting the first. Recording the definition is what lets the Hub
and the report notice when a Focus has changed since it was analysed — see
**Out of Date**. The Hub's members table and the Project Report read it instead of
re-analysing, which is what makes a bound Project Report cheap and what makes
"not analysed" a visible state rather than an inferred one.
_Avoid_: cache, manifest

**Out of Date**:
A Focus whose saved results no longer describe what a run would now produce:
a different analytic definition — factors, levels or the Reference Level the
model uses — a different Exclusion Group or a different set of chambers
removed from the Focus's own cells, a changed data file (compared by content,
not date), a changed censoring policy, or a changed `omit:` selection. Found
by comparing what the Run Summary recorded with the current config and file;
a summary written before a field was recorded is not judged on it. Its report section says the results
predate a change and need a re-run, and presents none of them: the report never
silently analyses on the user's behalf, and by the same rule never silently
presents results for something they no longer describe. Display names and
colours are excluded from the comparison, since they change no number.
_Avoid_: stale (reserved for a **Blocked Focus** naming levels the data lacks),
dirty, invalidated

**Orphaned Results**:
A directory under `analysis/` that no declared Focus names — left by renaming a
Focus by hand in the YAML, or by deleting one. Listed in the Hub with *adopt
as…* or *delete*, and never bound into a report. Renaming through the Focus
window cannot orphan anything: the rename moves the directory and its
name-suffixed files with it.
_Avoid_: stale results, leftovers

**Minimal Member Config**:
What **Create experiment…** writes: the least a Member Experiment must state
itself,
with everything the Project's `defaults:` supplies left out. A member that
restates a default freezes it — later edits to the Project stop reaching that
member — so scaffolds stay minimal on purpose.
_Avoid_: template config, full config

## Relationships

- A **Batch** contains many **Projects**, at any depth; a **Project** contains
  many **Member Experiments**; each Member Experiment is an **Experiment
  Directory**. As a Batch Run target a Project is a **Batch Project**, named by
  its key.
- An Experiment Directory may also stand alone, with no Project above it.
- A **Blocked Member** belongs to the Member Experiment level, so a Project is
  never blocked — it just has fewer members the run can use. A **Blocked
  Focus** belongs to the Focus level by the same rule: a member is never
  blocked by one of its Focuses, it just has fewer Focuses the run can use.
- Every Member Experiment of a Project shares that Project's **Experiment
  Type** — the only value validated across members. With one type in
  existence the check cannot currently fail; it is kept because the thing it
  guards (members whose input shape and time unit differ, bound into one
  report) would still be incoherent.
- An **Experiment Type** owns the data-source concerns — input shape, time
  unit, censoring default, quality criteria, report sections. A **Focus
  Shape** owns which analyses and figures apply, so the **Plot Set** a given
  run produces is the type's base set plus what the Focus admits.
- A **Member Experiment** declares one or more **Focuses**; a Focus names a
  slice of that Experiment Directory's discovered factors and levels. The same
  data file may carry several, analysed independently, and every output a run
  produces carries the Focus's name. The **Focus**, not the directory, is the
  unit of independent analysis — the nesting got one level deeper, and still
  nothing pools (ADR-0001).
- A **Plot Spec** lives with an Experiment Directory and names a **Plot Style**
  that lives with the Project.
- A **Project Report** binds one section per **Focus**, across every Member
  Experiment; it never combines their numbers.

## Example dialogue

> **Dev:** "Two members of this Project have different genotypes in them. Do I
> validate that, or pool them by treatment?"
> **Domain expert:** "Neither — they're **Member Experiments**, not replicates.
> They ask the same question two ways. Analyse each one alone and say in the
> **Divergence Note** that they differ."
> **Dev:** "So what does the Project actually enforce?"
> **Domain expert:** "Just the **Experiment Type** — and these days that's
> only the data source, since there's one type and it's the general case.
> Everything else in `defaults:` is a starting point, not a rule."
> **Dev:** "Then how does the app know to offer me the interaction model?"
> **Domain expert:** "It doesn't ask the experiment, it asks the **Focus**. If
> the Focus I'm analysing names two factors with two levels each, that's a 2×2
> **Focus Shape** and the **Factorial Battery** is on the menu. The workbook
> next door has three genotypes in one Focus — same Experiment Type, no
> interaction model, because there's no interaction to fit."
> **Dev:** "And if one file holds two separate experiments?"
> **Domain expert:** "Two **Focuses**, named, both declared in the config.
> They're analysed independently and their outputs carry their names, so the
> report has a section for each and nothing overwrites anything."
> **Dev:** "One folder in there has the workbook but nobody wrote it a config.
> Does that fail the Project?"
> **Domain expert:** "No — that's a **Blocked Member**. The Project runs the
> members it can and the run tells me which one it skipped, before it starts
> and again at the end. If it refused the whole Project I'd lose a night's
> analysis over one folder somebody forgot."

## Flagged ambiguities

- "replicate" was used for a Project's children while also stating those
  children differ in design and are never pooled — resolved: they are
  **Member Experiments**; "replicate" is reserved for nothing in this repo.
- Output paths were a function of the data filename (`<stem>_results/`) —
  resolved: fixed `analysis/`, so no path helper has to discover the data
  file first and renaming a workbook cannot orphan results.
- A 2×2's reference levels were implicit (alphabetical / `drop_first`) —
  resolved: a **Focus** names each factor's **Reference Level** explicitly,
  defaulting to the first level listed, so display order and statistical
  baseline are separable and every coefficient's sign is stable.
- "Interaction Experiment" was an **Experiment Type**, which made a 2×2 a
  property of the whole directory — untenable once one file could hold both a
  2×2 and a three-level design. Resolved (ADR-0011): the type is retired, the
  analyses survive as actions gated by **Focus Shape**.
- "Load" named both an input-format dialog and the act of making an
  experiment current — resolved: format is configuration
  (`survival_config.yaml`), loading is a selection/double-click.
- "experiment" named both the data file / directory and the thing analysed
  on its own, once one file was allowed to hold several experiments — resolved:
  the directory stays the **Member Experiment**, and each independently
  analysed slice within it is a **Focus**. "Analysed entirely on its own" is now
  a property of the Focus.
- Outputs keyed on a user-editable name were rejected once already
  (`<stem>_results/`, so "renaming a workbook cannot orphan results"), and
  `analysis/<focus>/` reintroduces the pattern deliberately, because the Focus
  name must travel with a figure that leaves the directory. Resolved by
  making the drift visible rather than impossible: renames through the Focus
  window move their results, hand renames leave **Orphaned Results**, and a
  same-name redefinition is **Out of Date**.
- "Not Applicable" was about to be printed for every analysis a Focus is never
  asked — the interaction model in each one-factor Focus's report. Resolved:
  a **Requirement** has two halves; failing *relevance* means not offered and
  not mentioned, failing *computability* means Not Applicable and recorded.
  The same split retired the "exactly 2×2" rule: the Factorial Battery is
  offered for two or more varying factors of any number of levels.
- "declared treatment" was used of a Focus, which declares *levels*, not
  treatments — so an unbalanced design read as a Focus with a missing
  treatment, and would have blocked. Resolved: a Focus's treatments are the
  populated cells of its rectangular product; a never-populated cell is
  absent, and only a cell emptied by exclusion blocks.
- "all" was about to name both the default Focus and a quantifier over every
  Focus — resolved: the default Focus is **`Unfiltered`**, and "every Focus" is
  expressed as a blank `only:` on `run_in_focuses`, following the convention
  `run_in_experiments` already set.
- "Member" was about to name both a Batch's Projects (following the sister
  app) and a Project's experiments — resolved: a Batch's children are **Batch
  Projects**; "member" belongs to the Project→Experiment level alone.
