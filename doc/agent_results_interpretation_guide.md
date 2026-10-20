# Interpreting pySurvAnalysis Results — A Guide for AI Agents

This document is written for an AI agent that is given one or more folders of
results produced by **pySurvAnalysis** and asked to summarize and interpret
them. It is meant to be included in a larger prompt. It tells you how the
results are laid out on disk, how to recognize the treatments and the design
of an experiment you know nothing about in advance, how to judge the quality
of the data and the analysis, how to establish which treatments differ and
how, and how to read every statistic the package produces.

You will not be told in advance what organism was studied, what the factors
mean, or what hypothesis was tested. Everything you need to recover the
design is on disk; where it is not, you must state your assumptions rather
than guess silently.

---

## Contents

1. Ground rules
2. The data model and the folder layout
3. Ingestion procedure — what to read, in what order
4. Recognizing treatments and the experimental design
5. Quality control — what to check and how it changes your conclusions
6. Ascertaining treatment differences
7. Analysis-by-analysis reference
8. Multiple comparisons and inference hygiene
9. Comparing across Focuses and Member Experiments
10. Writing the summary
11. Checklists and common mistakes
- Appendix A — Run Summary schema
- Appendix B — CSV column reference
- Appendix C — Configuration keys
- Appendix D — Glossary
- Appendix E — Worked example

---

## 1. Ground rules

These rules exist because the package was built around them. Results it
writes are reproducible and stamped with their provenance; anything you add
on top must not blur that.

1. **The Focus is the unit of analysis. Never pool.** Each Focus (a named
   slice of one data file) is analysed independently. Member Experiments in a
   Project are never pooled, and Focuses within one experiment are never
   pooled. Do not average, combine, or meta-analyse numbers across Focuses or
   members, and never state a combined effect size or a combined p-value. You
   may compare them *qualitatively* (agree / disagree / point the same way).

2. **Report only numbers you can trace to a file.** Every number you state
   must come from a saved output, or be a clearly labelled simple derivation
   of saved numbers.
   - **Permitted derivations** (label each as "derived"): differences and
     ratios of reported point estimates (e.g. median A − median B, percent
     change against a stated reference); converting a hazard ratio to a
     percent change in hazard; summing model coefficients to get a
     cell-specific effect; inverting a pairwise hazard ratio (1/HR, with the
     confidence limits swapped and inverted); unit conversions you state
     explicitly.
   - **Permitted QC tallies** (label as "agent-derived QC"): counts computed
     from `individual_data_<focus>.csv`, such as chambers per treatment or
     individuals per chamber.
   - **Forbidden**: new hypothesis tests, new p-values, new confidence
     intervals (including for derived combinations of coefficients), refitted
     models, re-running any analysis, imputing missing values, reading
     numbers off a figure when the same number exists in a table.

3. **Interpret only current results.** For every Focus, first establish its
   state: *analysed and current*, *not analysed*, *out of date*, *blocked*,
   or *orphaned / legacy*. Only analysed-and-current results are findings.
   Out-of-date results describe a slice or configuration that no longer
   exists; mention that they exist, but do not present their numbers as
   results.

4. **Absence is information — say which kind.** An analysis or figure can be
   missing because it was *not offered* (the Focus never asks that question),
   *Not Applicable* (relevant, but the data could not support it), *Left Out*
   (deliberately unticked), *failed* (a model error), or simply *missing* (a
   file you expected is not there). These mean different things. A missing
   test is never a null result.

5. **Every claimed difference carries four things:** direction (which
   treatment lived longer), magnitude (in time units and/or as a hazard
   ratio), uncertainty (a confidence interval), and the test (which test,
   adjusted or not), with the comparator or reference level named. Never
   report a p-value alone. Never write "significant" without saying which
   test and whether the p-value was adjusted for multiple comparisons.

6. **Quality control comes before interpretation, and travels with it.**
   Every QC finding that bears on a conclusion must be stated next to that
   conclusion, not in a separate appendix the reader may skip.

7. **Separate observation from interpretation.** State what the numbers show
   first. Mark any biological interpretation as interpretation. Do not state
   mechanisms as findings.

8. **Prefer primary sources.** Precedence, highest first: the CSV files (full
   precision) → the Run Summary JSON → the Markdown report → the PDF report →
   figures. Report prose, figure captions and any saved AI narrative are
   secondary; never cite them as evidence for a number.

9. **State your assumptions.** Which level you take to be the control, what
   the time unit really is, what a factor name means — when these are
   inferred rather than recorded, say so.

10. **Use the package's vocabulary** (Appendix D): Focus, Member Experiment,
    treatment, chamber, Exclusion Group, Reference Level, Not Applicable,
    Left Out, Out of Date, Blocked. Do not call Member Experiments
    "replicates" — they are not.

---

## 2. The data model and the folder layout

### 2.1 The hierarchy

| Level | How to recognize it on disk | What it is | Key fact for interpretation |
|---|---|---|---|
| **Batch** | any folder with a Project somewhere beneath it; optional `batch.yaml` | a processing convenience for running many Projects | holds no results of its own; never combines anything |
| **Project** | folder with `project.yaml` and at least one member subfolder | a set of Member Experiments addressing one question | never pools its members; `project.yaml` holds the `question` |
| **Member Experiment** (Experiment Directory) | immediate subfolder of a Project holding `survival_config.yaml` | one data file, analysed apart from its siblings | related to siblings by the *question*, not by an identical design |
| **Focus** | `analysis/<focus>/` inside an Experiment Directory, declared under `focuses:` in `survival_config.yaml` | a named slice of the factors and levels in that data file | **the unit of independent analysis**; every output carries its name |
| **Treatment** | a value of the `treatment` column | one cell of the Focus: one level of each varying factor, joined by `/` | what every curve, table and test groups by |
| **Chamber** | `chamber` column (DLife workbooks only) | one vial/container of individuals sharing a treatment | the unit that QC excludes; not modelled by any statistic |
| **Individual** | one row of `individual_data_<focus>.csv` | one animal with a `time` and an `event` flag | the unit every test treats as independent |

A standalone Experiment Directory (no Project above it) is also valid and is
laid out the same way.

The only Experiment Type is **Standard Lifespan**: a census-scored lifespan
cohort (DLife workbook of chambers scored to death) or an individual-level
CSV/TSV. The package is built around invertebrate lifespan work (DLife is a
Drosophila lifespan tool), but do not assume the organism; check (Section 4.6).

### 2.2 The annotated folder tree

```
<Batch>/                                  optional; no results here
├── batch.yaml                            optional; which Project Script a batch run executes
└── <Project>/
    ├── project.yaml                      name, question, Project Defaults, scripts
    ├── plot_specs.yaml                   Publication Figure specs/styles (curation, not analysis)
    ├── <Project>_report.md               Project Report (Markdown) — cover, Focus Inventory,
    ├── <Project>_report.pdf                Divergence Note, one section per Focus
    ├── <Project>_report_figures/         images used by the Markdown Project Report
    ├── <Project>_narrative.json          optional saved AI narrative (derived prose; secondary)
    └── <Member>/                         one Member Experiment
        ├── survival_config.yaml          the experiment's configuration (Focuses, exclusions, settings)
        ├── <datafile>.xlsx|.csv|.tsv     the data file — at the root or in data/
        ├── data/
        ├── qc/
        │   └── remove_chambers.csv       Exclusion Groups: group,chamber,note
        ├── figures/<focus>/              rendered Publication Figures (curated; may show a subset)
        └── analysis/
            └── <focus>/                  one folder per Focus
                ├── run_summary_<focus>.json          THE authoritative record of the run
                ├── report_<focus>.md                 the experiment report (Markdown)
                ├── report_<focus>_figures/           images for the Markdown report
                ├── <Member>_report_<focus>.pdf       the same report as PDF
                ├── data_output/
                │   ├── individual_data_<focus>.csv   one row per individual
                │   ├── lifetables_<focus>.csv        KM / life table per treatment
                │   ├── summary_<focus>.csv           N, deaths, censored per treatment
                │   ├── median_survival_<focus>.csv   KM median with 95% CI
                │   └── mean_survival_<focus>.csv     RMST to the common τ
                ├── statistics/
                │   ├── survival_quantiles_<focus>.csv
                │   ├── lifespan_treatment_stats_<focus>.csv
                │   ├── lifespan_factor_stats_<focus>.csv        only if ≥2 varying factors
                │   ├── logrank_pairwise_<focus>.csv             if run
                │   ├── gehan_wilcoxon_pairwise_<focus>.csv      if run
                │   ├── hazard_ratios_<focus>.csv                if run
                │   ├── factorial_01_coefficients_<focus>.csv    Cox factorial model
                │   ├── factorial_01_ph_test_<focus>.csv         Schoenfeld PH check
                │   ├── factorial_02_coefficients_<focus>.csv    RMST factorial model
                │   └── parametric_aic_<focus>.csv               parametric AFT comparison
                └── plots/                                       PNG figures (see Section 7.15)
```

There is **no CSV for the omnibus log-rank test**; it lives in the Run
Summary (`omnibus_lr`) and the report. There are **no log files on disk**;
everything a run noticed is recorded in the Run Summary and the report.

### 2.3 File naming

`<focus>` in every path is the Focus name made file-system safe: every run of
characters other than letters, digits, `.`, `_` and `-` becomes `_`, and
leading/trailing `.`/`_` are stripped. A Focus named `Crowding 20 v 40`
writes to `analysis/Crowding_20_v_40/` with files ending
`_Crowding_20_v_40`. The default Focus is `Unfiltered`. The Run Summary's
`focus.name` holds the name as typed; `focus.slug` holds the path form.

### 2.4 Things that look like results but are not current results

| What you see | What it is | What to do |
|---|---|---|
| `plots/`, `statistics/`, `data_output/`, `run_summary.json`, `report.md`, `*_report.pdf` directly under `analysis/` (no Focus folder) | **Pre-Focus legacy results** from an old version; they record no Focus definition | Never interpret as current. Mention they exist. |
| A folder under `analysis/` whose name matches no declared Focus slug | **Orphaned results** (a Focus renamed by hand or deleted) | Never interpret as current; mention them. |
| `<datafile-stem>_results/<focus>/` next to a data file | outputs of the package's direct-file mode (no config) | Usable, but there is no config to check currency against; say so. |
| A report PDF in a Focus folder whose prefix is not the current experiment folder name (e.g. `Old_report_X.pdf` beside `Current_report_X.pdf`) | a leftover from before the directory was renamed | Ignore; use `report_<focus>.md` and the CSVs. |
| `figures/<focus>/*.svg|pdf|png` | curated Publication Figures; a Spec may **narrow** a figure to a subset of treatments | Not analysis output; never infer from a missing curve that a treatment was absent. |
| `<Project>_narrative.json` | an earlier AI-written summary of saved numbers | Secondary; may be stale; never a source of numbers. |

---

## 3. Ingestion procedure — what to read, in what order

Work through these steps for every Project (or standalone Experiment
Directory) you are given. Keep notes as you go; Section 10 tells you how to
turn them into the summary.

### Step 1 — Discover the structure

- Find every `project.yaml`. Its immediate subfolders containing
  `survival_config.yaml` are its Member Experiments. Do not look for Projects
  inside a Project.
- A `survival_config.yaml` with no `project.yaml` above it is a standalone
  experiment.
- For each experiment, list the folders under `analysis/` and every
  `run_summary_*.json`.

### Step 2 — Read the Project context

From `project.yaml`: `name`, `question` (often empty — then you must infer
the aim, and say that you did), and `defaults:` (Experiment Type, `global`
settings such as `assume_censored` and `time_unit`, a default Exclusion
Group). Members inherit `defaults:` unless they state their own value.

If a Project Report (`<Project>_report.md`) exists, read its cover status
line ("N of M Focus(es) analysed and current"), its **Focus Inventory** (one
row per Focus with its State) and any **Divergence Note** (members processed
under different censoring policies, Exclusion Groups or time units). The
inventory's State column was correct when the report was generated; compare
its "Generated" time with each Run Summary's `analyzed_at` — if a Run
Summary is newer than the report, the report is stale for that Focus.

### Step 3 — Read each experiment's configuration

From `survival_config.yaml` record:

- `focuses:` — every declared Focus: `factors` (each factor's levels in
  display order), `reference` (Reference Levels), `display_names`,
  `colours`. A config with no `focuses:` block has one implicit Focus,
  `Unfiltered`, which is written into the file on first analysis.
- `exclusions: {group: …}` — the active Exclusion Group (blank or absent
  means none, unless Project Defaults name one; `group: ''` explicitly
  overrides a Project default to mean none).
- `global:` — `time_unit`, `time_label`, `assume_censored`,
  `min_n_per_chamber` (falling back to Project Defaults, then the type
  defaults `days`, `Age (days)`, `true`, `5`).
- `omit:` — analyses and plots deliberately left out of every run.
- `data_file:` — which data file, if named explicitly.
- `input:` — for CSV/TSV: time/event column names, factor columns, layout.

Also read `qc/remove_chambers.csv` (columns `group,chamber,note`). The notes
often say *why* a chamber was excluded.

### Step 4 — Determine each Focus's state

| State | How to recognize it |
|---|---|
| **not analysed** | the Focus is declared but has no `run_summary_<slug>.json` |
| **blocked** | the Project Report says so; or the Focus names a factor or level the data file lacks (stale), or the active exclusions empty one of its treatments (empty). A blocked Focus has nothing current to interpret. |
| **out of date** | a Run Summary exists but what it recorded differs from the current config or data (checks below) |
| **analysed and current** | a Run Summary exists and none of the checks below finds a difference |
| **orphaned** | a folder under `analysis/` that no declared Focus names |

Out-of-date checks you can perform yourself (each applies only when the Run
Summary recorded the value; older summaries lack some keys):

1. **Definition.** `focus.definition.factors` (factors and their *ordered*
   levels) must equal the config's `focuses.<name>.factors`. A changed level
   order counts as a change.
2. **Reference Levels.** `focus.definition.reference` must equal the
   config's `reference:` for each varying factor, where a factor with no
   `reference:` entry means its first listed level.
3. **Exclusion Group.** `exclusion_group` must equal the config's active
   group (treat `null` and `''` as "none"). A value of the form
   `base + extra` means a script excluded more on top; that run is out of
   date against the config by design.
4. **Excluded chambers.** `excluded_chambers` should match the chambers the
   active group currently lists in `qc/remove_chambers.csv` (plus any
   workbook ChamberFlags), restricted to chambers in this Focus. A
   difference suggests the group was edited after the run.
5. **Data file.** If you can compute it, the SHA-256 of the current data
   file must equal `data_sha256`.
6. **Censoring policy.** `assume_censored` must equal the resolved
   `global.assume_censored` (workbooks only — the setting has no effect on
   CSV data).
7. **Selection.** `omit` must equal the config's `omit:` block.

Display names and colours are not part of the check; they change no number.

When a check cannot be performed (no hash tool, key not recorded), say the
currency of that Focus is **unverified** rather than asserting it is current.

These changes are *not* detected by the package and leave old results
looking current: edits to `input:` settings, edits to `global:` keys other
than `assume_censored` (e.g. `time_label`), and upgrades of the package
itself. If you see evidence of these (Section 5.2), say so.

### Step 5 — Read each current Focus's outputs

In this order: the Run Summary (identity, counts, flags, QC records, omnibus
test, factorial headlines) → `summary_<focus>.csv` → median, mean and
quantile tables → lifespan statistics → pairwise tables → factorial
coefficient and PH tables → parametric AIC table → `report_<focus>.md` for
anything you missed (Not Applicable and Left Out tables, Data quality
section, warnings tables) → figures, if you can view images, for the shape
of the curves only.

### Step 6 — QC (Section 5), then interpretation (Sections 6–9), then the write-up (Section 10)

---

## 4. Recognizing treatments and the experimental design

### 4.1 Where factors come from

Factors are **discovered from the data file**, never declared:

- **DLife workbook (.xlsx):** every column of the `Design` sheet to the right
  of `StartTime` is a treatment factor (e.g. `Sex`, `Genotype`, `Diet`,
  `Density`). The Design sheet has one row per chamber with its
  `SampleSize`.
- **CSV/TSV long format:** every column other than the time column (default
  `Age`) and event column (default `Event`) is a factor, unless
  `input.factor_cols` lists a subset.
- **CSV/TSV wide format:** exactly two factors named by `input.factor_names`;
  each column holds the ages of one factor-level combination and outcome.

Levels are listed in **order of first appearance** in the Design sheet or
file — never alphabetically. Experimenters usually enter the control first,
which is why the first level is the default Reference Level.

`discovered_factors` in the Run Summary lists every factor the file holds;
`factors` lists the Focus's varying factors.

### 4.2 What the Focus does to the factors

Each discovered factor plays exactly one role in a Focus:

| Role | How it arises | Effect | Where recorded |
|---|---|---|---|
| **varying** | named with ≥2 levels | its levels label the treatments | `focus.definition.factors`; Run Summary `factors` |
| **filter** | named with exactly 1 level | keeps only that level; not in the label | `focus.filters` (factor → level) |
| **pooled over** | not named | individuals at every level are mixed into each treatment | `focus.pooled_over` |

**Pooling changes every number.** A Focus that pools over Sex mixes males
and females into every curve; a Focus that filters to `Sex = F` describes
females only and must not be generalized to males. Always state the role of
every discovered factor in your summary.

### 4.3 Treatment labels and the Focus Shape

- A **treatment label** is the levels of the varying factors joined by `/`,
  in the Focus's factor order: with `Genotype: [wt, mut]` then
  `Diet: [AL, DR]`, the labels are `wt/AL`, `wt/DR`, `mut/AL`, `mut/DR`.
  If nothing varies (a single-cell Focus), the label is built from every
  named factor.
- The Focus is a **rectangular product** of its levels. Cells the product
  implies but the data never held are **absent** (`focus.absent_cells`) —
  normal for an unbalanced design, not an error.
- `focus.treatments` lists the populated treatments in display order.
- `focus.shape` gives the level counts of the varying factors in Focus
  order: `single cell`, `3` (one factor, three levels), `2×2`,
  `2×2 (3 of 4 cells)` (one implied cell empty), `2×3×2`.
- `focus.unassigned` counts individuals with no recorded level for a factor
  the Focus names. They belong to no treatment and are outside the analysis.
- `focus.headline` names the Headline Figure: `km_faceted` when the Focus
  crosses factors, otherwise `km_risk_table`.

The same individuals can carry different labels in different Focuses (a
Focus that filters `Sex = F` labels a treatment `20x`; `Unfiltered` labels
the same animals `F/20x`). Map labels through the factor columns of
`individual_data`, not by string matching alone.

### 4.4 Display names and colours

`display_names:` in the Focus config maps raw labels to the names used in
figures (e.g. `Red/SS002769xWCS: R2R4_Cont_Light`). CSVs and the Run Summary
always use the **raw labels**; figures and publication figures use display
names. Display names often reveal what the experimenter considers the
control and what an abbreviation means ("Cont", "Ctrl", "Veh"). Use them to
interpret, and always give the raw label alongside so a reader can find the
row.

### 4.5 Identifying controls and reference levels

The **Reference Level** of each varying factor is recorded in
`focus.definition.reference` (and in the report's Focus definition table).
It is the baseline of the Cox and RMST models. It is *probably* the control,
but it is a modelling choice, not a declaration. To judge which level is the
experimental control, weigh:

- level names that conventionally denote controls: `wt`, `WT`, `+/+`,
  `w1118`, `CS`, `Canton-S`, `wCS`, `Oregon-R`, background or parental
  lines, `control`, `ctrl`, `cont`, `mock`, `vehicle`, `veh`, `sham`,
  `untreated`, `0`, `0x`, `AL` (ad libitum), `standard`, `std`, `normal`,
  `dark` vs `light` depending on design, crosses to a neutral line
  (`xWCS`, `xw1118`, `>+`, `xattP2`) in GAL4/UAS-style genetics;
- the display names (e.g. "Cont");
- the Reference Level and first-appearance order;
- Defined Plot names and Focus names;
- the Project question.

When the evidence is mixed, say which level you treat as the control and
why. When the design has no natural control (e.g. two sexes), say so and
describe differences symmetrically.

### 4.6 Inferring what factors mean and what organism this is

Common factor types and how to treat them:

| Factor looks like | Usual meaning | Interpretive note |
|---|---|---|
| `Sex` with `F`/`M`, `Female`/`Male` | sex | sexes almost always differ in lifespan; pooling over sex is a major caveat |
| genotype names, crosses (`AxB`, `UAS-…`, `GAL4`, `/+`) | genetic manipulation | genetic background effects are common; note when a control is a different background |
| `Diet`, `AL`/`DR`, `%yeast`, `SY10`, `HS` | nutrition | |
| `Density`, `1x`/`20x`/`40x` | crowding/social | |
| `Dose`, `Drug`, numeric levels, `0`, `10uM` | pharmacology | ordered levels |
| `Temp`, `25C`/`29C` | temperature | |
| `Light`, `Red`/`Dark` | optogenetics or photoperiod | |
| `Mated`/`Virgin` | reproductive status | |
| `Rep`, `Replicate`, `Block`, `Batch`, `Vial`, `Cohort`, `Run`, `Date` | **experimental blocking/replication, not a treatment** | see below |

**All factors are treated as unordered categories.** The package has no
trend or dose-response test. For ordered levels (doses, densities,
temperatures) you may *describe* a monotonic pattern in the medians, but do
not claim a dose-response has been tested.

**Blocking and replicate factors.** A column such as `Replicate`, `Block` or
`Vial` sitting among the factors is discovered as a factor like any other.
If a Focus *varies* it, treatments are split by replicate (each replicate is
a "treatment") — usually a misconfiguration, or a deliberate replicate-
consistency check; say which. If a Focus *pools over* it, replicates are
combined and block effects are ignored; if blocks are unbalanced across
treatments, the comparison can be confounded. In CSV inputs, an ID or vial
column left in the file becomes a factor with very many levels — a strong
sign of misconfiguration.

**Organism and time scale.** Do not assume the organism. Clues: DLife
workbooks and "chambers"/vials point to Drosophila or similar small
invertebrates; level names may contain fly-genetics notation. Use this only
to sanity-check time scales (Section 5.8).

### 4.7 Several Focuses in one data file

One data file often holds several experiments (two genotype panels run in
parallel, say), each declared as its own Focus. Clues that a Focus is a
sub-experiment: its name matches a **Defined Plot** (the workbook's
`DefinedPlots` sheet, where experimenters list intended comparisons), and
its treatments are exactly that plot's treatments. Current versions pass
over a Defined Plot silently in Focuses it is not about; older versions
recorded it there as **Not Applicable** with "not in Focus …", which is
benign.

**`Unfiltered`** is every discovered factor at every level. When named
Focuses exist, `Unfiltered` often mixes separate sub-experiments into one
large design: its omnibus test and its Bonferroni family span comparisons
the experimenter never intended (e.g. a genotype from one panel against a
control from another). Prefer the named Focuses for the scientific
conclusions, and treat `Unfiltered` as context.

**Overlapping Focuses share individuals.** A named Focus and `Unfiltered`
contain the same animals. Agreement between them is not independent
confirmation — it is the same data seen twice. For the same pair of
treatments under the same exclusions, the pairwise log-rank χ², raw p-value
and O/E hazard ratio are computed from those two treatments only, so they
are **identical** across Focuses; only the Bonferroni-adjusted p-value
differs (different family size). Cox and RMST models differ because they are
fitted to different sets of treatments.

### 4.8 Member Experiments

Members have their own data files. They may be independent cohorts (a
repeat of the experiment on another date, the other sex in a separate
workbook) or different designs addressing the same question. They are
**never replicates in the pooling sense**. Agreement across members that
are genuinely separate cohorts is stronger evidence than agreement across
Focuses of one file — but it is still qualitative agreement, never a pooled
estimate. Members' factors and level names often differ; the same label in
two members need not mean the same thing.

### 4.9 Anomalies in level names

Look for data-entry problems in level names, because they silently split
or mislabel groups:

- near-duplicates differing by a character or digit
  (`SS0027609xChr` vs `SS002769xWCS`, where the data file name says
  `SS002769`), case (`wt` vs `WT`), or whitespace;
- the same genotype spelled two ways in two members;
- a level name that contradicts the data file name or the display name.

Report suspected typos as a QC finding; do not silently "correct" them.

### 4.10 What to write down about the design

For every Focus: the varying factors with levels in order and Reference
Levels; filters; pooled-over factors; the treatments with N; absent cells;
unassigned individuals; your judgment of which level is the control and on
what evidence; whether the Focus looks like a sub-experiment, the whole
file, or a replicate split.

---

## 5. Quality control — what to check and how it changes your conclusions

Perform every check below for every current Focus. Record each finding with
a severity (Section 5.12). Several checks use thresholds; these are
heuristics, not rules of the package — say so if you rely on one.

### 5.1 Provenance and currency

- The Focus's state (Section 3, Step 4) and whether currency was verified.
- `analyzed_at`: when the run happened. Results from widely different dates
  within one Project may come from different package versions.
- `input_file` should be the file the config resolves to.
- Stale artefacts: extra PDFs with a different prefix, legacy or orphaned
  folders (Section 2.4).

### 5.2 Version fingerprints of older outputs

The package has changed; older outputs differ in known ways. Signs that a
Focus was run by an older version:

| Sign | Implication |
|---|---|
| Run Summary lacks `data_sha256`, `excluded_chambers`, `omit`, `load_warnings`, `small_chambers`, `left_out`, `parametric_models` | Currency checks for those values are impossible; QC records are incomplete |
| `factorial_models[].lr_interaction` has `lr_stat` but no `statistic` | The report may print "—" for the LR χ²; read `lr_stat` |
| `median_survival` CSV lacks `median_ci_lo`/`median_ci_hi` | No CI for medians |
| lifespan stats CSVs lack a `tau` column, and `mean_rmst` differs from `rmst` in `mean_survival` for the same treatment | Older RMST used trapezoids and per-row restriction times; `mean_rmst` values are not over a common window — use `mean_survival` (`rmst`, `restriction_time`) |
| Pairwise tables and `omnibus_lr.groups` list treatments alphabetically rather than in the Focus's level order | `group1` is the alphabetically first label — read `group1`/`group2` explicitly; never assume the direction |
| `omnibus_lr.groups` is a string like `"['a', 'b']"` | cosmetic |
| Cox coefficient CSV has a `cmp to` column (all zeros) | cosmetic |
| Report rows marked ✅ in pairwise tables where `significant_0.05` is `False` | older reports highlighted raw p < 0.05; newer ones highlight Bonferroni-significant rows. Trust the CSV columns, not the marks |
| Report shows p-values as `0.000` | older formatting; read the CSV |
| Report's parametric table is a block of raw text | older report rendering; read `parametric_aic_<focus>.csv` or the Run Summary instead |

When you detect an older version, say so and recommend a re-run if a
conclusion depends on an affected quantity.

### 5.3 Internal consistency checks

These should all hold for one current Focus. A failure means mixed or stale
files; treat the Focus's results as unreliable until explained.

- In `summary`: `n_deaths + n_censored = n_individuals` for each treatment;
  the sums over treatments equal the Run Summary's `n_total`, `n_deaths`,
  `n_censored`.
- The treatments in `summary` equal `focus.treatments`, and their count
  equals `n_treatments`.
- In `lifetables`, each treatment's first `n_at_risk` equals its
  `n_individuals`.
- The median in `median_survival` equals `S=50%` in `survival_quantiles` and
  `median` in `lifespan_treatment_stats` (up to rounding).
- `restriction_time` is identical in every row of `mean_survival`, and (in
  current versions) equals `tau` in the lifespan stats and the RMST model's
  `tau`.
- In `logrank_pairwise`, `observed_1` equals `n_deaths` of `group1`.
- `omnibus_lr.df` equals the number of treatments minus 1.
- `factorial_models[].n_subjects` equals `n_total`, and `n_events` equals
  `n_deaths`.
- Pairwise tables have k(k−1)/2 rows for k treatments; `p_bonferroni` equals
  `min(1, p_value × rows)`.
- Every figure listed in `figures` exists in `plots/`.

### 5.4 Exclusions

Read `exclusion_group`, `excluded_chambers`, `n_excluded`,
`n_excluded_listed`, `qc/remove_chambers.csv`, and the report's Data quality
section.

- **What was removed.** `n_excluded` chambers were actually removed from this
  data. Exclusions apply to the whole experiment directory: every Focus of a
  member shares them.
- **Workbook flags.** Chambers marked `Excluded = 1` on the workbook's
  `ChamberFlags` sheet are removed from every run, whatever the group. A
  report reading "none declared (N removed by the workbook)" means this.
- **Listed but absent.** `n_excluded_listed > n_excluded` means the group
  lists chambers this file does not have — a typo, the wrong group, or a
  group name inherited from Project Defaults that was written for another
  member. Minor, but say so.
- **A group that removes nothing.** An active group name with no rows in the
  file removes nothing; the report says "nothing listed".
- **Balance across treatments.** Excluded chambers are absent from
  `individual_data`, so to see which treatments lost chambers you need the
  `note` column or the workbook's Design sheet (one row per chamber with
  its factor levels), if you can read it. If exclusions fall
  disproportionately on one treatment — particularly a treatment that
  drives a key result — that is a major caveat: removing whole chambers can
  change a treatment's curve.
- **Reasons.** Notes such as "contamination", "mites", "flooded", "dropped",
  "mis-scored", "low N" are legitimate pre-specified reasons. Notes like
  "outlier" or "short-lived" without a cause suggest exclusions chosen by
  looking at survival, which can bias comparisons; flag that.
- **Alternative groups.** Several groups in `remove_chambers.csv` (e.g.
  `default`, `strict`) mean the experimenter considered alternatives. Only
  the active group's results exist unless other runs were saved; you cannot
  report a sensitivity analysis that was not run, but you can recommend it.
- **CSV data has no chambers.** Exclusion Groups remove nothing from CSV/TSV
  inputs; the group is recorded with zero removals.

### 5.5 Censoring

An individual is right-censored (`event = 0`) when its death was not
observed. Sources:

- **Explicit censoring** (DLife `Censored` column; CSV event 0): escapes,
  accidental losses, sacrifices — at any age.
- **Assumed censoring** (`assume_censored: true`, DLife workbooks only):
  individuals a chamber's `SampleSize` says were set up but that were never
  scored dead or censored are added as censored **at that chamber's last
  census age**. With `assume_censored: false` they do not exist in the
  analysis at all.

Checks:

- **Policy.** Record `assume_censored`. With it on, KM curves typically end
  above zero and survival is higher than with it off. With it off, any
  individuals that really did disappear alive are silently dropped, which
  biases survival downward. If members of a Project differ in policy, the
  Divergence Note says so; comparisons across those members are on
  different footings.
- **Amount.** `pct_censored` overall and per treatment. Low censoring
  (a few percent) is typical of animals scored to death. Heavy censoring
  (heuristically above ~20–30%) means medians may be undefined ("not
  reached") and late-life comparisons are weak.
- **Differential censoring.** Compare `pct_censored` across the treatments
  you are comparing. A treatment with several times the censoring of its
  comparator (e.g. 12% vs 3%) is a major caveat: censoring patterns affect
  every test, and the Gehan-Wilcoxon weights depend on censoring.
- **Timing.** In `lifetables`, look where `n_censored` falls. A block of
  censorings at the last census in one treatment while its curve is still
  high means the experiment ended before that treatment finished dying:
  its median and RMST are underestimated relative to a full follow-up, and
  the common τ truncates everyone's RMST. Censoring concentrated early may
  reflect handling losses.
- **Phantom censoring.** With assumed censoring on, a `SampleSize` typed too
  large creates censored individuals that never existed. A chamber or
  treatment with unexpectedly high censoring at its last census is the
  signature.
- **Informative censoring.** Every method assumes censoring says nothing
  about when an individual would have died. If escapes or removals are
  linked to frailty or treatment, that assumption fails.
- **Top-percentile columns** (`top_10pct_mean`, `top_5pct_mean`) are
  produced only when `assume_censored` is false and the group has more than
  10 deaths, and are computed from deaths only. They are meaningful only
  when censoring is minimal.

### 5.6 Sample size, events and balance

- Individuals and **deaths** per treatment (`summary`). Statistical power
  comes from deaths, not individuals.
- Imbalance between treatments (one cell far smaller than the others).
- For the Cox factorial model, a common rule of thumb is at least ~10
  deaths per model term; fewer makes estimates unstable. Count terms in the
  `formula`.
- A treatment with very few deaths gives wide confidence intervals; a
  non-significant result there means "not determinable", not "no
  difference".
- Parametric fits are skipped for treatments with fewer than 5 individuals
  or fewer than 2 deaths (recorded in the `note` column).

### 5.7 Chambers and clustering (pseudo-replication)

Every test and model in the package treats **individuals as independent** and
pools chambers within a treatment. Individuals in one chamber share an
environment, so when chambers differ, the effective sample size is smaller
than the number of individuals and p-values are too small and intervals too
narrow. No analysis in the package models chamber effects.

Checks (agent-derived QC from `individual_data_<focus>.csv`):

- **Chambers per treatment** (count distinct `chamber` per `treatment`). A
  treatment housed in one or two chambers has its treatment effect
  confounded with chamber effects; flag this as major. Several chambers per
  treatment (e.g. 5–10+) is the usual design.
- **Individuals per chamber** and the Run Summary's `small_chambers`
  (chambers below `min_n_per_chamber`, default 5). Small chambers are
  flagged, never excluded, by the package; they are noisy.
- Optionally, **per-chamber spread**: the median age at death per chamber
  within a treatment (descriptive only). A chamber far from its siblings
  (e.g. an early die-off) is what the QC viewer exists to catch; if such a
  chamber is still included, say so.
- `n_chambers` in the Run Summary is the number of chambers in this Focus
  after exclusions. **For CSV inputs it reads 1** (every row has chamber
  `N/A`) — this does not mean one chamber; clustering is simply unknown.

### 5.8 Time scale and observation window

- **The time unit is only a label.** Survival times are taken exactly as
  recorded (the DLife `AgeH` column, conventionally *hours*; or the CSV time
  column). `global.time_unit` and `time_label` (default `days`, `Age
  (days)`) change no number. Check plausibility: if a fly cohort labelled
  "days" has medians around 1,300, the values are almost certainly hours
  (~55 days). When the label and the magnitude disagree, report the values
  "in the recorded unit (labelled X)", state the likely true unit and your
  reason, and give any converted values as clearly labelled derivations.
  Never convert silently.
- **Time origin.** Ages are not adjusted for the Design sheet's `StartTime`,
  and there is no left-truncation adjustment: every individual is treated as
  at risk from time 0. If chambers started at different ages, ages are not
  directly comparable.
- `time_min`: very early deaths (first census) can reflect handling or
  transfer injury; check `S=90%` and the KM curves for an early drop.
- `t_max` per treatment (lifespan statistics) and the common **τ** (the
  smallest of the treatments' last observed times). One treatment followed
  for less time shortens τ for all, and every RMST then describes only the
  window 0–τ.
- Census granularity: deaths are recorded at census ages, so medians and
  quantiles fall on census ages and many deaths share a time. Differences
  smaller than one census interval are not resolvable.

### 5.9 Loader warnings and unassigned individuals

- `load_warnings` (Run Summary) and the report's Data quality warnings table,
  e.g. "Chamber 12: RawData records 23 deaths and censorings but its
  SampleSize is 20 — N uses the 23 recorded". This is a data-entry error in
  the Design or RawData sheet. One such warning is minor; many, or one in a
  key treatment, is major.
- For CSV inputs, "N row(s) dropped: their time or event is blank or not a
  number" — check how many.
- `focus.unassigned` > 0: individuals with a blank level for a factor the
  Focus names were left out. A handful is minor; a substantial fraction is
  major (what were they?).
- RawData rows whose chamber is not on the Design sheet are skipped by the
  loader without a warning, and a Design chamber with no RawData rows
  contributes no individuals. If the number of chambers is lower than the
  design implies, these are possible causes.

### 5.10 Model diagnostics

- **Proportional hazards.** `factorial_01_ph_test_<focus>.csv` (Schoenfeld
  test per term; p < 0.05 suggests that term's hazard ratio changes with
  age) and the log-log figure (non-parallel or crossing lines). When PH
  fails for a term you rely on, describe that hazard ratio as an average
  over the observed ages and lead with the RMST model and the curve
  descriptives instead. With large samples the test flags trivial
  departures; with many deaths tied at census ages it is coarse.
- **Model warnings and errors.** `factorial_models[].warnings` (convergence
  trouble, near-singular design, a PH test that could not run) and
  `factorial_models[].error` (the model could not be fitted). Numbers from
  a model with a convergence warning need an explicit caveat; a model with
  an error has no numbers.
- **Unstable estimates.** Very large standard errors, hazard-ratio
  intervals spanning orders of magnitude, or coefficients of implausible
  size indicate sparse cells or separation.
- **Fit summaries.** Cox `concordance` (0.5 = chance) and RMST `r_squared`
  are usually modest for lifespan data because individual variation is
  large; a low value does not mean the factors have no effect.
- **Parametric fits.** Rows with `note` starting "not fitted:" say why.

### 5.11 Not Applicable, Left Out, not offered

Read `not_applicable` (list of `{action, reason}`) and `left_out` (list of
`{id, item, reason}`) in the Run Summary and the report's Focus section.

| Entry | Meaning | Consequence |
|---|---|---|
| Not Applicable — "Survival comparisons" | the Focus implies ≥2 treatments but fewer than 2 hold individuals | no tests at all; nothing can be said about differences |
| Not Applicable — "Factorial Battery" | ≥2 varying factors, but some pair of factors has an empty cell (reason names it, e.g. `Genotype=mut × Diet=DR`) | no Cox/RMST models, no formal interaction test; the faceted KM and interaction plot may still exist and can be described |
| Not Applicable — a figure | the data could not draw it | describe what is missing |
| Not Applicable — "Defined Plot 'X'" | a workbook-defined figure about this Focus that cannot be drawn in full: a listed treatment is absent, emptied by exclusion, or a typo; or its labels fit no Focus at all (recorded under every Focus) | informative — an intended comparison could not be drawn; say which treatment is missing. (Older versions also recorded "not in Focus …" for plots about other slices; that form is benign.) |
| Left Out | the experimenter unticked it (`omit:`); "draws from …, which is unticked" for a figure whose analysis was left out | a choice; the question was simply not asked |
| not offered (no entry) | the Focus never asks this (e.g. no factorial section for a one-factor Focus; no comparisons for a single treatment) | nothing to report; do not call it missing |

### 5.12 QC severity and its effect on conclusions

| Severity | Examples | Effect on your write-up |
|---|---|---|
| **Critical** | Focus not analysed, out of date, blocked, or orphaned; Run Summary contradicts the CSVs (Section 5.3); data file hash differs from the one analysed; files from different runs mixed in one Focus folder | Do not present the numbers as findings. Report the state and what would fix it. |
| **Major** | differential censoring between compared treatments; heavy censoring with medians not reached; exclusions concentrated in a key treatment or justified only by survival; one or two chambers per treatment; many loader warnings or warnings in key treatments; substantial unassigned individuals; a pooled-over factor likely to matter (e.g. sex); suspected level-name typo splitting a group; model convergence warnings; PH violation for a key term (when relying on HRs); fewer than ~10 deaths per Cox term; older package version for a quantity you rely on; time unit evidently mislabelled | Report the result with the caveat stated beside it; lower your confidence by one step (Section 6.7); prefer the analyses the issue does not affect. |
| **Minor** | a single small chamber; group lists chambers absent from this file; "not in Focus …" Defined Plot entries in older outputs; modest censoring; cosmetic version differences | Mention briefly in the QC section. |

---

## 6. Ascertaining treatment differences

### 6.1 The evidence ladder

Work up from description to inference, for each Focus:

1. **Descriptives** — N, deaths, % censored; KM median with 95% CI; RMST to
   the common τ; survival quantiles (S = 90%, 75%, 50%, 25%, 10%); `t_max`;
   top-percentile means (when available).
2. **Overall test** — omnibus log-rank: does any treatment differ?
3. **Pairwise tests** — log-rank (Bonferroni-adjusted), Gehan-Wilcoxon
   (Bonferroni-adjusted), O/E hazard ratios with 95% CI.
4. **Factorial models** (Focuses varying ≥2 factors) — Cox hazard ratios
   relative to the Reference Levels with the LR interaction test and PH
   check; RMST differences in time units.
5. **Shape of mortality** — parametric AFT families; hazard, mortality and
   cumulative-hazard figures.

### 6.2 Direction cheat sheet

Directions are easy to get wrong because the statistics use opposite sign
conventions. Hazard-based quantities go *up* when life gets *shorter*;
time-based quantities go *up* when life gets *longer*.

| Quantity | Longer life | Shorter life | No difference |
|---|---|---|---|
| Median, RMST, quantile, `t_max`, AFT median (A − B) | > 0 | < 0 | 0 |
| Log-rank `observed_1` vs `expected_1` | O < E: group1 longer-lived | O > E: group1 shorter-lived | O ≈ E |
| Pairwise `hazard_ratio` (group1 / group2) | < 1: group1 longer-lived | > 1: group1 shorter-lived | 1 |
| Cox `coef` (β) / `HR` for a level vs its Reference Level | β < 0 / HR < 1 | β > 0 / HR > 1 | 0 / 1 |
| Cox interaction `HR` | < 1: the combination does better than the main effects predict | > 1: it does worse | 1 |
| RMST model `coef` | > 0 | < 0 | 0 |
| RMST interaction `coef` | > 0: the combination gains more time than additive | < 0: less | 0 |
| Nelson-Aalen H(t), hazard, qx, log(−log S) curve | lower curve | higher curve | overlapping |
| KM curve, cumulative-deaths curve | higher KM / lower cumulative deaths | lower KM / higher cumulative deaths | overlapping |
| Gehan-Wilcoxon χ² | no direction — use the curves, medians or HRs | | |

So a Cox interaction HR > 1 normally pairs with an RMST interaction
coefficient < 0; both say the combination fares worse than additivity
predicts. If the two models point in opposite *life* directions, discuss why
(PH violation, effects late in life beyond τ, sparse cells).

**Which group is `group1`?** In current outputs, the treatment earlier in the
Focus's display order (its level order). In older outputs it may be the
alphabetically earlier label. It is *not* necessarily the control. Always
read the `group1` and `group2` columns. To express a pair the other way
round: HR' = 1/HR, with limits 1/`hr_ci_hi` and 1/`hr_ci_lo`.

### 6.3 Expressing magnitude

- **Time differences**: report the difference in medians and in RMST in the
  time unit, and optionally as a percent of the reference treatment
  (state the denominator): "median 64 vs 52 days (+12 days, +23% relative
  to wt/AL; derived)".
- **Hazard ratios**: "HR 0.48 (95% CI 0.39–0.59), i.e. a 52% lower hazard of
  death at any age (derived, assuming proportional hazards)". An HR is not
  a ratio of lifespans: HR 0.5 does not mean "lives twice as long".
- Prefer RMST differences for a plain-language "time gained"; prefer HRs for
  "relative risk of death"; always give both when available.
- **Biological importance** depends on the field and organism. Do not label
  an effect "small" or "large" without a stated basis (e.g. a comparison
  with the experiment's own control-vs-control variation, or the Project
  question). Statistical significance is not importance: in large cohorts
  tiny effects reach small p-values.

### 6.4 Where in life does the difference occur?

- **Survival quantiles**: `S=90%` and `S=75%` describe early mortality,
  `S=50%` the median, `S=25%` and `S=10%` late life and the long-lived tail.
  An effect present at S=90% but absent at S=10% is an early-life effect;
  the reverse is a late-life or tail effect.
- **`top_10pct_mean`, `top_5pct_mean`, `t_max`**: proxies for maximum
  lifespan (when available and censoring is low). `t_max` is a single
  individual and is noisy.
- **Log-rank vs Gehan-Wilcoxon**: both significant → the curves differ
  throughout; only Gehan-Wilcoxon → the difference is early, or the curves
  converge or cross later; only log-rank → the difference is mainly late.
- **Figures** (if you can view them): crossing KM curves, a hazard curve
  shifted right (delayed ageing) vs lowered (proportional benefit), early
  steps from a die-off.

### 6.5 When the metrics disagree

| Pattern | Likely explanation | How to report |
|---|---|---|
| Same median, significant log-rank | census granularity (medians snap to census ages) or differences away from the median | lead with RMST, quantiles and HR |
| Different medians, non-significant tests | small N/few deaths, wide CIs | "the medians differ by X but the test does not support a difference" |
| Significant log-rank, HR CI includes 1 | O/E HR is approximate; borderline evidence | report both; call the evidence borderline |
| Cox HR significant, RMST difference not | effect concentrated late (beyond τ) or early with little area; or PH violation | inspect quantiles and PH; describe where the effect lies |
| RMST significant, Cox HR not | non-proportional hazards (crossing curves) | lead with RMST; describe the crossing |
| Omnibus not significant, one pairwise raw p < 0.05 | multiplicity | "nominal; not significant after adjustment, and no overall difference detected" |
| Omnibus significant, no pairwise survives Bonferroni | diffuse differences or conservative adjustment | report the omnibus; describe the largest contrasts as unconfirmed |

### 6.6 Classifying the evidence for a difference

Assign each comparison you report one of these categories, then adjust for
QC (Section 5.12: a Major issue lowers the category by one step).

| Category | Criteria |
|---|---|
| **Strong** | Bonferroni-adjusted log-rank p < 0.05; HR CI excludes 1; median and RMST differences agree in direction; no major QC issue |
| **Supported** | adjusted p < 0.05 but one metric discordant (e.g. equal medians from census ties), or a Gehan-Wilcoxon-only difference with a consistent early-life pattern |
| **Suggestive / nominal** | raw p < 0.05 but adjusted p ≥ 0.05; or HR CI excludes 1 without a significant adjusted test |
| **Not detected** | no test significant; state the CI so the reader sees which effect sizes the data cannot exclude ("HR 0.92, 95% CI 0.71–1.19: neither a 29% reduction nor a 19% increase in hazard is excluded") |
| **Not assessable** | Not Applicable, Left Out, failed, blocked, out of date, or not analysed |

The package has no equivalence test; never conclude "the treatments are the
same". With a narrow CI around 1 you may say the data are compatible only
with small differences, giving the interval.

### 6.7 Confidence in a Focus's conclusions

Rate each Focus's main conclusion **High**, **Moderate** or **Low**:

- **High**: current results, verified currency, no major QC issues, strong
  evidence, metrics concordant, PH acceptable or RMST concordant.
- **Moderate**: one major QC issue, or evidence "supported", or a key
  assumption (control identity, time unit) inferred rather than recorded.
- **Low**: several major issues, evidence "suggestive", unverified
  currency, or results from an older version for the quantity relied on.

---

## 7. Analysis-by-analysis reference

Each subsection gives the files, what is computed, how to read it, and its
pitfalls. All p-values are two-sided; the significance threshold is 0.05.

### 7.1 Life tables and the Kaplan-Meier estimator

**File:** `data_output/lifetables_<focus>.csv` — one row per distinct death
or censoring time per treatment. Built by the package's own code; matches
lifelines.

- `n_at_risk` (alive and uncensored just before the time; individuals
  censored at t are at risk at t), `n_deaths`, `n_censored`.
- `qx` = d/n (interval probability of death), `px` = 1 − qx,
  `lx` = `km_lx` = Kaplan-Meier survival Ŝ(t).
- `se_km`: Greenwood standard error; `km_ci_lo`/`km_ci_hi`: 95% log-log
  ("exponential Greenwood") band, always within [0, 1].
- `hx`: actuarial interval hazard 2q/((1+p)·Δt), Δt = gap to the next time.
- `na_H`, `na_se`, `na_ci_lo`, `na_ci_hi`: Nelson-Aalen cumulative hazard
  with a normal-approximation 95% band (lower bound clipped at 0).

**Pitfalls:** `qx` is per census interval, so if census intervals vary in
length, `qx` is not comparable across ages (use `hx`, which adjusts for
width). The tail is noisy: few individuals remain at risk.

### 7.2 Per-treatment summary

**File:** `data_output/summary_<focus>.csv` — `treatment`,
`n_individuals`, `n_deaths`, `n_censored`, `pct_censored` (one decimal).
Counts after the Focus and the Exclusion Group are applied. The report adds
the observation window (`time_min`–`time_max`) and the number of chambers.

### 7.3 Median survival

**File:** `data_output/median_survival_<focus>.csv` — `median_survival`:
first time Ŝ(t) ≤ 0.5; `median_ci_lo`, `median_ci_hi`: the first times the
lower and upper edges of the log-log band reach 0.5 (the same method as R's
`survfit`). Blank/NaN means **not reached** — say "median not reached
(> last observed time)", not "missing".

**Pitfalls:** medians fall on census ages; two treatments can share a median
yet differ. The upper CI limit is often not reached even when the median is.

### 7.4 Mean survival (RMST)

**File:** `data_output/mean_survival_<focus>.csv` — `rmst`: the exact area
under the KM step function from 0 to `restriction_time` (τ), the same τ for
every treatment: τ = the smallest of the treatments' last observed times.
Read RMST as "average lifespan within the window 0–τ". Always quote τ.

**Pitfalls:** RMST says nothing about survival after τ. A treatment with
short follow-up shortens τ for every treatment. No CI or test accompanies
this table; formal RMST inference exists only in the factorial model.

### 7.5 Survival quantiles

**File:** `statistics/survival_quantiles_<focus>.csv` — columns `S=90%`,
`S=75%`, `S=50%`, `S=25%`, `S=10%`: the first time the KM curve falls to or
below each survival level. `S=90%` is when 10% have died. Blank = never
reached. No CIs.

### 7.6 Lifespan statistics by treatment and by factor level

**Files:** `statistics/lifespan_treatment_stats_<focus>.csv` and, when ≥2
factors vary, `statistics/lifespan_factor_stats_<focus>.csv`.

Columns: `group` (a treatment, or `Factor=level`), `n`, `n_deaths`,
`n_censored`, `mean_rmst` (area to the common τ — in current versions equal
to `rmst` in `mean_survival`), `tau`, `median`, `t_max` (the group's own last
observed time), and, only when `assume_censored` is false and the group has
>10 deaths, `top_10pct_mean`/`top_5pct_mean` (mean age at death of the
longest-lived 10%/5% of individuals that died).

**The factor-level table pools individuals across the other factors**:
`Genotype=wt` combines every wt treatment whatever its diet. These are
*marginal, unadjusted, size-weighted* descriptives. If cells are unbalanced,
a factor-level difference can reflect the composition of the other factor;
and if there is an interaction, a marginal effect averages effects that
differ. Use them as context, never as the factor's "main effect".

### 7.7 Omnibus log-rank

**Where:** Run Summary `omnibus_lr` (`chi2`, `p_value`, `df`, `groups`) and
the report's "Overall comparison"; no CSV. K-sample log-rank on K
treatments, df = K − 1. A single test; no adjustment.

A small p says at least one treatment differs, not which. It ignores
factorial structure (a 2×2 is four unrelated groups) and can miss one
deviant treatment among many. With exactly two treatments it equals the
single pairwise test. The report cover line "treatments differ" /
"no overall difference detected" is this test.

### 7.8 Pairwise log-rank

**File:** `statistics/logrank_pairwise_<focus>.csv` — `group1`, `group2`,
`observed_1`, `expected_1`, `chi2` (1 df), `p_value` (raw), `df`,
`p_bonferroni` = min(1, p × number of pairs), `significant_0.05` (True when
the **adjusted** p < 0.05).

Mantel-Cox test, equal weight to every death time; ties handled with the
hypergeometric variance. Direction from `observed_1` vs `expected_1`
(Section 6.2). Most powerful under proportional hazards; crossing curves can
cancel. Bonferroni with many treatments is conservative (6 treatments → 15
pairs → each raw p × 15). In a factorial Focus, only some pairs are
scientifically meaningful contrasts (simple effects; Section 7.11), but the
correction counts all pairs.

### 7.9 Gehan-Wilcoxon pairwise

**File:** `statistics/gehan_wilcoxon_pairwise_<focus>.csv` — `group1`,
`group2`, `chi2`, `p_value`, `df`, `p_bonferroni`, `significant_0.05`. No
observed/expected columns, so no direction: take direction from the curves,
medians or HRs.

Weighted log-rank with weight = number at risk, so early deaths count most.
Compare with the log-rank results (Section 6.4). The two tables are adjusted
separately; nothing corrects for running both. Very different censoring
patterns between the two groups distort the weights.

### 7.10 Pairwise hazard ratios

**File:** `statistics/hazard_ratios_<focus>.csv` — `group1` (numerator),
`group2` (denominator), `hazard_ratio`, `hr_ci_lo`, `hr_ci_hi`. Drawn as the
hazard-ratio forest.

Estimated by the log-rank observed/expected method:
HR = (O₁/E₁)/(O₂/E₂), SE(log HR) = √(1/E₁ + 1/E₂), 95% CI = exp(log HR ±
1.96·SE). Not a Cox fit; approximate, especially for large effects or
unequal censoring. No p-value and no adjustment: with many pairs some
intervals exclude 1 by chance — pair it with the Bonferroni-adjusted
log-rank row. Missing when an expected count or O₂ is zero. Assumes
proportional hazards; check the log-log figure.

### 7.11 Cox factorial model (Factorial Battery, model 01)

**Offered** when the Focus varies ≥2 factors; **computed** only when every
pair of varying factors is fully crossed in the populated cells; otherwise
"Factorial Battery" is Not Applicable with the empty cell named.

**Files:** `statistics/factorial_01_coefficients_<focus>.csv`,
`statistics/factorial_01_ph_test_<focus>.csv`; Run Summary
`factorial_models[0]`.

**Design.** Each varying factor is dummy-coded against its **Reference
Level** (L levels → L − 1 terms named `Factor_level`); every pair of factors
contributes product terms named `A_a:B_b`. Only pairwise interactions — with
three factors there is no three-way term. Fitted with lifelines
`CoxPHFitter` (Efron ties, no penalty) to individuals. All tabulated
coefficients come from the **interaction model**.

**Columns:** `covariate`, `coef` (β, log HR), `HR` = exp(β), `se`,
`coef_lo`/`coef_hi`, `HR_lo`/`HR_hi` (95% Wald), `z`, `p_value` (Wald,
**unadjusted**), `-log2(p)` (S-value, bits of evidence), `term_type`
(`main_effect` or `interaction`).

**Run Summary headline:** `formula`, `n_subjects`, `n_events`,
`concordance`, `AIC` (partial), `reference`, `warnings`, `error`, and
`lr_interaction`: `statistic` (or `lr_stat` in older files), `df` (number of
interaction terms), `p_value`, `ll_main`, `ll_interaction`,
`concordance_main`, `interaction_cols`.

**How to read it — the essential rule:** with interactions in the model, a
**main-effect coefficient is a simple effect at the Reference Level of every
other factor**, not an average effect. With references wt and AL:

- `Genotype_mut` HR = effect of mut vs wt **on AL only**;
- `Diet_DR` HR = effect of DR vs AL **in wt only**;
- `Genotype_mut:Diet_DR` HR = how many times the DR effect is multiplied in
  mut relative to wt (a ratio of hazard ratios). HR = 1 means no
  interaction.

**Deriving the other simple effects** (point estimates only; label as
derived; no CI is available for these sums):

- DR effect in mut: HR = exp(β_Diet_DR + β_mut:DR) = HR_Diet_DR × HR_int.
- mut effect on DR: HR = HR_Genotype_mut × HR_int.
- mut/DR vs wt/AL: HR_mut × HR_DR × HR_int.

The pairwise tables give a test and a CI for each simple effect directly,
because a simple effect is a comparison of two cells within one level of
the other factor: the DR effect within mut is the pair `mut/AL` vs
`mut/DR` in `logrank_pairwise` and `hazard_ratios`. Its `p_bonferroni` is
adjusted over every pair in the table, including pairs that are not simple
effects, so it is conservative.

**The LR interaction test** (`lr_interaction`) is the one test of "is there
any interaction?" — it compares the interaction model with the main-effects
model, df = number of interaction terms. Prefer it to reading interaction
coefficients one by one, especially with multi-level factors (e.g. 3
genotypes × 2 diets gives 2 interaction terms and an LR test on 2 df).

**Classifying an interaction** (using the derived simple effects and the
faceted KM / interaction plot):

- **quantitative** — the effect has the same direction at every level of the
  other factor but differs in size (e.g. DR extends life in both genotypes,
  less in mut);
- **qualitative / crossover** — the direction reverses;
- **effect confined to one level** — present at one level, absent
  (CI spanning 1) at another.

**When the LR test is not significant**, the main-effect coefficients are
still simple effects at the reference; the main-effects-only model (average
effects) is fitted but not tabulated. Do not reinterpret the tabulated
coefficients as average effects. You may describe the factor-level
lifespan statistics as marginal descriptives, with their caveats
(Section 7.6).

**Changing a Reference Level** changes every coefficient and can flip
interaction signs, but not the fit, the LR test, or any curve. Always state
the Reference Levels when quoting a coefficient.

**Pitfalls:** proportional hazards assumed (check 7.12); individuals treated
as independent, no chamber term; coefficient p-values unadjusted; sparse
cells give unstable estimates.

### 7.12 Proportional-hazards check (Schoenfeld residuals)

**File:** `statistics/factorial_01_ph_test_<focus>.csv` — `covariate`,
`test_statistic` (χ², 1 df), `p_value`. One row per Cox interaction-model
term; no global test; no adjustment. Run with lifelines
`proportional_hazard_test(..., time_transform="rank")`.

p < 0.05 → that term's hazard ratio is not constant with age; the HR is an
average. A PH failure in an interaction row means the *interaction* changes
with age. A large p is no proof of PH. If the test could not run, there is
no CSV and the model's `warnings` say "PH assumption test failed: …".
One-factor Focuses and the pairwise HRs have no formal PH test; use the
log-log figure.

### 7.13 RMST factorial model (Factorial Battery, model 02)

Same offer and computability rules and the same design as the Cox model, on
the restricted-mean scale; **no proportional-hazards assumption**.

**Files:** `statistics/factorial_02_coefficients_<focus>.csv`; Run Summary
`factorial_models[1]` with `tau`, `rmst_overall` (pooled RMST θ),
`r_squared`, `f_statistic`, `f_p_value`, `AIC`, `warnings`.

**Method:** jackknife pseudo-values of the pooled RMST to τ (τ = the common
restriction time, the same as in `mean_survival`), regressed by OLS on the
factorial design with HC1 robust standard errors.

**Columns:** `covariate` (`const`, main effects, interactions), `coef` (in
the data's time unit), `se`, `z`, `p_value` (unadjusted), `coef_lo`,
`coef_hi`, `term_type`; `HR`, `HR_lo`, `HR_hi` are always blank.

**Reading it** (references wt, AL): `const` = mean lifespan to τ in the
reference cell (wt/AL); `Genotype_mut` = time gained by mut on AL;
`Diet_DR` = time gained by DR in wt; `Genotype_mut:Diet_DR` = difference of
differences (how much the DR gain changes in mut). Cell means are sums:
mut/DR = const + mut + DR + interaction (derived). Ignore the test of
`const` (it asks whether the reference cell's mean lifespan is zero).
There is no LR interaction test for this model; judge the interaction terms
by their own p-values (jointly when there are several). The RMST model's
AIC is not comparable with the Cox AIC.

**Pitfalls:** everything is "up to τ"; main effects are simple effects at the
reference; chambers ignored (robust SEs handle unequal variance, not
clustering).

### 7.14 Parametric AFT models

**Files:** `statistics/parametric_aic_<focus>.csv`; Run Summary
`parametric_models` — `treatment`, `model` (`Weibull`, `Log-Normal`,
`Log-Logistic`), `aic`, `delta_aic`, `log_likelihood`, `median_survival`
(model-based), `best`, `note`.

Each treatment is fitted on its own (no covariates), so these compare
*distribution shapes within a treatment*, not treatments. Compare AIC
within a treatment only: ΔAIC < 2, models equivalent; ≥ 10, strong support
for the lower. Weibull = hazard rising (or falling) as a power of age;
log-normal/log-logistic = hazard rising then falling. If one family wins in
every treatment it describes the cohort well. Agreement between the model
median and the KM median indicates a reasonable fit. Not fitted below 5
individuals or 2 deaths, or on failure — stated in `note`. No p-values.

### 7.15 Figures

Figures are 150-dpi PNGs in `analysis/<focus>/plots/`. A figure that is Left
Out, Not Applicable or not offered has no file. Use figures for the shape of
curves; take numbers from the tables.

| File | Shows | Read it for |
|---|---|---|
| `km_with_risk_table_<focus>.png` | KM curves, number at risk at 0/25/50/75/100% of the last age | headline for one-factor Focuses; how many remain at risk late |
| `kaplan_meier_<focus>.png` | KM curves with 95% bands and censor ticks | separation, crossing, early drops |
| `km_faceted_<focus>.png` | one panel per level of the **first** varying factor, curves coloured by the others | headline for factorial Focuses; compare within-panel gaps across panels (interaction) |
| `interaction_lifespan_<focus>.png` | KM median per cell with 95% CI; first varying factor on x, a line per level of the others | parallel lines = no interaction on the median scale; crossing = reversal |
| `cumulative_events_<focus>.png` | 1 − Ŝ(t) with band | same information as KM, inverted |
| `survival_distribution_<focus>.png` | distribution (violin) of ages at death — **deaths only** | clustering, bimodality (early die-off + normal ageing) |
| `mortality_qx_<focus>.png` | interval probability of death | depends on census interval width |
| `hazard_rate_<focus>.png` | raw interval hazard | noisy; late-life swings |
| `smoothed_hazard_<focus>.png` | kernel-smoothed hazard, no CI | lowered curve = proportional benefit; right-shifted = delayed ageing |
| `nelson_aalen_<focus>.png` | cumulative hazard with band | lower = longer-lived |
| `number_at_risk_<focus>.png` | individuals at risk over time | how much data supports the tail |
| `hazard_ratio_forest_<focus>.png` | pairwise O/E HRs with CIs (group1/group2) | which pairs exclude 1 (unadjusted) |
| `log_log_diagnostic_<focus>.png` | log(−log Ŝ) vs log time | parallel = PH plausible; crossing = non-PH; straight = Weibull-like |
| `defined_<name>_<focus>.png` | KM of the treatments listed in a workbook Defined Plot | the experimenter's intended comparison |

---

## 8. Multiple comparisons and inference hygiene

- **Only the two pairwise test tables are adjusted** (Bonferroni, within
  each table). Cox and RMST coefficients, PH checks and pairwise HR
  intervals are unadjusted. The omnibus and LR interaction tests are single
  tests.
- **Nothing corrects across tables, tests or Focuses.** Running log-rank
  and Gehan-Wilcoxon, reading every coefficient, and analysing several
  Focuses all multiply the chances of a false positive. When you report
  unadjusted p-values, say they are unadjusted. Prefer the single combined
  tests (omnibus, LR interaction) for headline questions.
- **Report both raw and adjusted** p for pairwise contrasts; base
  "significant" on the adjusted value.
- **Do not count stars.** The report's `*`/`**`/`***` markers and ✅/⚠️ icons
  are display aids; the CSV values are authoritative.
- **Forking paths.** Focuses defined after looking at the data, Exclusion
  Groups changed after seeing results, and many overlapping Focuses are
  hidden multiple comparisons. If the configuration suggests this (many
  Focuses on one file, exclusions justified by survival), say so.
- **Non-significant ≠ no effect.** Give the confidence interval.
- **Independence.** All p-values assume independent individuals; chamber
  clustering makes them optimistic (Section 5.7).
- **No trend tests.** Ordered levels are tested as unordered groups.

---

## 9. Comparing across Focuses and Member Experiments

- **Never pool.** No combined medians, no averaged HRs, no combined
  p-values, no vote-counting presented as a statistic.
- **Overlapping Focuses** (same file; e.g. `Unfiltered` and a named subset)
  share individuals: agreement is not independent evidence. Identical raw
  pairwise statistics for the same pair across such Focuses are expected
  (Section 4.7); different values for the same pair under the same
  exclusions signal stale or mixed results.
- **Separate Member Experiments** with their own data files may be
  independent cohorts. Describe consistency qualitatively: same direction?
  similar magnitude (compare effect sizes, not p-values)? Is a difference in
  significance explained by sample size?
- **Check the footing before comparing.** Members may differ in censoring
  policy, Exclusion Group, time unit (the Divergence Note lists these), in
  level names, Reference Levels, and which factors are pooled or filtered.
  A comparison across members on different footings must say so.
- **Same label, different meaning.** `wt` in one member may be a different
  background from `wt` in another; check names and display names.
- **When results disagree**, say so plainly and offer the QC- or
  design-based explanations the files support (different sex, censoring,
  exclusions, follow-up length, sample size), without inventing others.

---

## 10. Writing the summary

### 10.1 Structure

Produce, in this order:

1. **Scope** — what was examined: Batch/Project/members/Focuses, with paths.
   The Project question, or "no question recorded; inferred aim: …".
2. **Inventory** — a table of every Focus: member, Focus, slice
   description, state (current/unverified/out of date/not analysed/blocked/
   orphaned/legacy), N, deaths, % censored, treatments, Not Applicable
   items.
3. **One section per current Focus**, using the template below.
4. **Across Focuses and members** — qualitative agreement and disagreement,
   with independence and footing stated (Section 9).
5. **Open issues and recommendations** — re-runs needed, QC decisions to
   revisit, typos to fix, analyses worth adding (e.g. a sensitivity run under
   an alternative Exclusion Group; a Focus separating a pooled factor; a
   chamber-aware model outside this package).

### 10.2 Per-Focus template

```
### <Member> · <Focus>
State: analysed and current (analyzed_at <…>; currency verified / unverified because <…>)
Slice: <varying factors with levels and Reference Levels>; filters: <…>; pooled over: <…>
Treatments: <label (display name)>: N, deaths, % censored — for each
Control / comparator: <level> (recorded Reference Level / inferred because <…>)
Time unit: <recorded label>; <plausibility note if any>; τ = <…>

QC
- [Critical/Major/Minor] <finding> — <effect on interpretation>

Results
- Overall: omnibus log-rank χ²=<…>, df=<…>, p=<…>
- Descriptives: medians (95% CI), RMST to τ, notable quantiles
- Key contrasts: direction, Δmedian, ΔRMST, HR (95% CI), log-rank raw/adjusted p, Gehan-Wilcoxon
- Factorial (if present): Reference Levels; main (simple) effects; interaction LR test;
  derived simple effects at other levels; RMST counterparts; PH check
- Where in life: early vs late (quantiles, GW vs LR)

Interpretation
- <what the results mean for the question, labelled as interpretation>

Evidence and confidence: <category per key contrast>; overall <High/Moderate/Low> because <…>
Not assessed: <Not Applicable / Left Out / failed items and why>
```

### 10.3 Phrasing rules

- Lead with the direction in words, then the numbers: "DR-fed wt females
  lived longer than AL-fed wt females: median 64 (95% CI 62–66) vs 52
  (50–54) days (+12 days, +23%; derived); RMST to τ = 86 days 61.8 vs 51.3
  (+10.5; derived); O/E hazard ratio wt/AL vs wt/DR 2.05 (1.68–2.50), i.e.
  DR/AL = 0.49 (0.40–0.60); log-rank p_bonferroni < 0.0001."
- Always name the comparator and the Reference Level.
- Give units every time.
- Report p-values to two significant figures, or "< 0.0001"; HRs to two
  decimals; times to the precision the census supports.
- Say "no difference was detected (HR …, 95% CI …)", never "there was no
  effect". Never use "trend towards significance".
- Use causal language only for the treatments as assigned in the design
  ("DR extended median lifespan"), qualified by QC caveats (chamber
  confounding, exclusions); never for mechanisms.
- Mark derived numbers "(derived)" and agent-computed QC tallies
  "(agent-derived QC)".
- Do not restate every number; choose the ones that carry the result, but
  never omit a caveat that bears on a stated conclusion.

---

## 11. Checklists and common mistakes

### 11.1 Before interpreting a Focus

- [ ] State established (current / unverified / out of date / not analysed / blocked / orphaned)
- [ ] Varying, filter and pooled-over factors listed
- [ ] Reference Levels and inferred control stated
- [ ] Treatment N, deaths, % censored read
- [ ] Time unit plausibility checked; τ noted
- [ ] Exclusions: group, chambers removed, reasons, balance
- [ ] Censoring: policy, amount, differential, timing
- [ ] Chambers per treatment; small chambers; loader warnings; unassigned
- [ ] Internal consistency checks passed
- [ ] Version fingerprints checked
- [ ] Not Applicable / Left Out read
- [ ] PH check and model warnings read (factorial Focuses)

### 11.2 Common mistakes to avoid

1. Reading a pairwise hazard ratio backwards (group1 is the numerator, and
   group1 is not necessarily the control).
2. Reading a Cox main effect as an average effect when an interaction is in
   the model.
3. Treating Cox and RMST signs as the same convention (they are opposite).
4. Calling a raw p < 0.05 in a pairwise table "significant" when
   `significant_0.05` is False.
5. Trusting report highlight marks over CSV columns.
6. Treating `Unfiltered` and a named Focus that share individuals as
   independent confirmation.
7. Pooling or averaging across Focuses or members.
8. Reporting results of an out-of-date Focus as findings.
9. Taking `time_unit` at face value when the magnitudes say otherwise.
10. Reading a missing analysis as a null result (check Not Applicable / Left
    Out).
11. Describing factor-level pooled statistics as main effects.
12. Equating HR 0.5 with "twice the lifespan".
13. Concluding "no difference" from a non-significant test with a wide CI.
14. Generalizing a filtered Focus (e.g. females only) beyond its filter, or
    ignoring a pooled-over factor.
15. Reading `n_chambers = 1` in a CSV-based Focus as one chamber.
16. Comparing RMSTs from different Focuses or members without noting that τ
    differs.
17. Comparing parametric AICs across treatments.
18. Taking numbers from a saved AI narrative or a figure.

---

## Appendix A — Run Summary schema (`analysis/<focus>/run_summary_<focus>.json`)

| Key | Meaning |
|---|---|
| `analyzed_at` | date and time of the run |
| `input_file` | data file name |
| `data_sha256` | SHA-256 of the data file analysed |
| `experiment_type` | always `standard_lifespan` |
| `focus.name`, `focus.slug` | the Focus name; its file-system form |
| `focus.definition.factors` | factor → ordered list of levels (the analytic definition) |
| `focus.definition.reference` | factor → Reference Level |
| `focus.description` | one-line slice description, e.g. `Light: Red, Dark (reference Red) × Genotype: …` |
| `focus.filters` | factor → the single level kept |
| `focus.pooled_over` | discovered factors the Focus does not name |
| `focus.shape` | e.g. `2×2`, `2×2 (3 of 4 cells)`, `single cell` |
| `focus.treatments` | populated treatment labels, display order |
| `focus.absent_cells` | implied cells the data never held |
| `focus.headline` | Headline Figure id |
| `focus.unassigned` | individuals with no level for a named factor |
| `factors` | varying factors |
| `discovered_factors` | every factor in the file |
| `n_total`, `n_deaths`, `n_censored`, `n_treatments`, `n_chambers` | counts (n_chambers = 1 for CSV inputs) |
| `time_min`, `time_max` | observation window |
| `assume_censored` | censoring policy |
| `exclusion_group` | active group name, `null` if none, `base + extra` if a script added a group |
| `excluded_chambers` | chamber ids actually removed (listed and present) |
| `n_excluded`, `n_excluded_listed` | removed; listed (including absent) |
| `omit` | `{analyses: [...], plots: [...]}` left out by configuration |
| `load_warnings` | loader warnings (e.g. deaths > SampleSize) |
| `min_n_per_chamber`, `small_chambers` | threshold; `[{chamber, treatment, n}]` below it |
| `figures` | plot id → file name |
| `defined_plots` | Defined Plot name → file name |
| `not_applicable` | `[{action, reason}]` |
| `left_out` | `[{id, item, reason}]` |
| `omnibus_lr` | `{chi2, p_value, df, groups}` or `{}` |
| `parametric_models` | `[{treatment, model, aic, delta_aic, log_likelihood, median_survival, best, note}]` |
| `factorial_models` | `[{title, model_type (cox_ph / rmst_pseudo), formula, error, n_subjects, n_events, concordance, AIC, reference, lr_interaction {statistic, lr_stat, df, p_value, ll_main, ll_interaction, concordance_main, interaction_cols}, tau, rmst_overall, r_squared, f_statistic, f_p_value, warnings}]` — index 0 Cox, index 1 RMST |

Older summaries lack some keys; read `lr_stat` when `statistic` is absent.

## Appendix B — CSV column reference

| File | Columns |
|---|---|
| `individual_data` | `time`, `event` (1 death, 0 censored), `chamber` (`N/A` for CSV), `treatment`, one column per factor |
| `lifetables` | `treatment`, `time`, `n_at_risk`, `n_deaths`, `n_censored`, `qx`, `px`, `lx`, `hx`, `km_lx`, `se_km`, `km_ci_lo`, `km_ci_hi`, `na_H`, `na_se`, `na_ci_lo`, `na_ci_hi` |
| `summary` | `treatment`, `n_individuals`, `n_deaths`, `n_censored`, `pct_censored` |
| `median_survival` | `treatment`, `median_survival`, `median_ci_lo`, `median_ci_hi` |
| `mean_survival` | `treatment`, `rmst`, `restriction_time` |
| `survival_quantiles` | `treatment`, `S=90%`, `S=75%`, `S=50%`, `S=25%`, `S=10%` |
| `lifespan_treatment_stats`, `lifespan_factor_stats` | `group`, `n`, `n_deaths`, `n_censored`, `mean_rmst`, `tau`, `median`, `t_max`, [`top_10pct_mean`, `top_5pct_mean`] |
| `logrank_pairwise` | `group1`, `group2`, `observed_1`, `expected_1`, `chi2`, `p_value`, `df`, `p_bonferroni`, `significant_0.05` |
| `gehan_wilcoxon_pairwise` | `group1`, `group2`, `chi2`, `p_value`, `df`, `p_bonferroni`, `significant_0.05` |
| `hazard_ratios` | `group1`, `group2`, `hazard_ratio`, `hr_ci_lo`, `hr_ci_hi` |
| `factorial_01_coefficients` (Cox) | `covariate`, `coef`, `HR`, `se`, `coef_lo`, `coef_hi`, `HR_lo`, `HR_hi`, `z`, `p_value`, `-log2(p)`, `term_type` |
| `factorial_01_ph_test` | `covariate`, `test_statistic`, `p_value` |
| `factorial_02_coefficients` (RMST) | `covariate`, `coef`, `HR` (blank), `se`, `z`, `p_value`, `coef_lo`, `coef_hi`, `HR_lo`, `HR_hi` (blank), `term_type` |
| `parametric_aic` | `treatment`, `model`, `aic`, `delta_aic`, `log_likelihood`, `median_survival`, `best`, `note` |

Column sets in older outputs may differ (Section 5.2).

## Appendix C — Configuration keys

**`project.yaml`:** `name`; `question`; `defaults:` (`experiment_type`,
`global`, `input`, `exclusions`, `omit` — inherited key by key; `focuses` is
never inherited); `scripts`; `experiment_scripts`.

**`survival_config.yaml`:** `experiment_type`; `data_file`; `global:`
(`time_unit`, `time_label`, `assume_censored`, `min_n_per_chamber`);
`input:` (CSV `format`, `time_col`, `event_col`, `factor_cols`,
`factor_names`, `col_mapping`, `factor_levels`); `exclusions: {group}`;
`focuses: {<name>: {factors, reference, display_names, colours}}`;
`omit: {analyses, plots}` (analysis ids: `logrank_pairwise`,
`logrank_omnibus`, `gehan_wilcoxon`, `hazard_ratios`, `parametric_aft`,
`interaction`; plot ids: `km_risk_table`, `km_curves`, `cumulative_events`,
`survival_distribution`, `mortality`, `hazard`, `smoothed_hazard`,
`nelson_aalen`, `number_at_risk`, `hazard_ratio_forest`, `log_log`,
`km_faceted`, `interaction_lifespan`); `scripts`; legacy `factors` (becomes a
Focus named `Interaction`).

**`qc/remove_chambers.csv`:** `group,chamber,note`. Numeric chamber ids match
however written (`12` = `12.0`); text ids match exactly, case included.

**DLife workbook sheets:** `Design` (`Chamber`, `SampleSize`, `StartTime`,
then factor columns), `RawData` (`AgeH`, `Chamber`, `IntDeaths`, `Censored`),
optional `ChamberFlags` (`Chamber`, `Excluded`), `DefinedPlots` (row 1 plot
name, row 6 down full treatment labels), `PrivateData` (`AssumeCensored`,
read only when a config is first written).

## Appendix D — Glossary

- **Absent cell** — a treatment a Focus's levels imply but the data never
  held; normal, not an error.
- **Assumed censoring** — DLife convention: individuals unaccounted for at the
  end are censored at the chamber's last census (`assume_censored: true`).
- **Blocked Focus** — cannot run as declared: it names a factor/level the
  data lacks (stale), or exclusions emptied one of its treatments (empty).
- **Chamber** — one vial/container; the unit of exclusion.
- **Defined Plot** — an experimenter-listed treatment grouping in the
  workbook, drawn as a KM figure; signals intended comparisons.
- **Divergence Note** — Project Report statement that members differ in
  censoring policy, Exclusion Group or time unit.
- **Exclusion Group** — named set of chambers removed from every run; one
  active group per experiment directory.
- **Factorial Battery** — Cox and RMST factorial models plus the faceted KM
  and interaction plot; offered when ≥2 factors vary.
- **Focus** — a named slice of the factors and levels in one data file; the
  unit of analysis.
- **Focus Shape** — level counts of the varying factors and which cells are
  populated.
- **Headline Figure** — faceted KM for factorial Focuses, KM with at-risk
  table otherwise.
- **Left Out** — deliberately excluded by `omit:`.
- **Member Experiment** — one Experiment Directory within a Project; not a
  replicate.
- **Not Applicable** — relevant but not computable from the data; recorded
  with a reason.
- **Not offered** — not relevant to the Focus; not recorded anywhere.
- **Orphaned results** — an `analysis/` folder no declared Focus names.
- **Out of Date** — saved results no longer match the config or data.
- **Reference Level** — a factor's baseline in the Cox/RMST models; defaults
  to the first listed level.
- **RMST** — restricted mean survival time: area under the KM curve to τ.
- **Run Summary** — `run_summary_<focus>.json`, the authoritative record of a
  run.
- **τ (tau)** — the common restriction time: the smallest of the
  treatments' last observed times.
- **Unfiltered** — the default Focus: every factor at every level.

---

## Appendix E — Worked example

*The numbers below are invented to illustrate the reasoning; they do not
come from a real experiment.*

**Files found.** Project `DietGenotype`, question "Does dietary restriction
extend lifespan, and does the extension depend on genotype?". One member,
`Cohort1`, with a DLife workbook whose Design sheet has factors `Sex`,
`Genotype`, `Diet`. Declared Focuses: `Unfiltered` and `GxD_females`.
`GxD_females` has a Run Summary; its definition (Genotype: wt, mut,
reference wt; Diet: AL, DR, reference AL; filter Sex = F) matches the
config; `exclusion_group` = `default` matches the config; the data hash
matches. State: analysed and current (verified).

**Design.** Varying: Genotype (wt, mut; reference wt), Diet (AL, DR;
reference AL). Filter: Sex = F, so conclusions apply to females only.
Nothing pooled. Shape 2×2, treatments `wt/AL`, `wt/DR`, `mut/AL`, `mut/DR`.
Control: wt/AL (recorded references; `wt` and `AL` are conventional control
names). Time label "Age (days)"; medians around 50–65 are plausible for days
in a fly cohort. τ = 86 days.

| treatment | N | deaths | % censored | chambers (agent-derived QC) |
|---|---|---|---|---|
| wt/AL | 198 | 192 | 3.0 | 8 |
| wt/DR | 201 | 194 | 3.5 | 8 |
| mut/AL | 190 | 183 | 3.7 | 8 |
| mut/DR | 164 | 144 | 12.2 | 6 |

**QC.**
- [Major] `mut/DR` has 12.2% censoring against 3.0–3.7% elsewhere, and the
  lifetable shows most of it at the last census: differential censoring in
  the cell that drives the interaction.
- [Major] Both excluded chambers (31, 32; note "mite infestation") belong to
  `mut/DR`, leaving it 6 chambers. The reason is pre-specified and
  legitimate, but the cell is smaller.
- [Major] Schoenfeld test for `Diet_DR` p = 0.012: the DR hazard ratio
  changes with age; lead with RMST for the diet effect.
- No other findings: none of the 30 analysed chambers falls below
  `min_n_per_chamber`; no loader warnings; `unassigned` = 0; internal
  consistency checks pass.

**Results.**
- Omnibus log-rank χ² = 96.4, df = 3, p < 0.0001.
- Medians (95% CI): wt/AL 52 (50–54), wt/DR 64 (62–66), mut/AL 58 (56–60),
  mut/DR 61 (58–64). RMST to τ: 51.3, 61.8, 56.9, 59.4.
- Cox (references wt, AL): `Genotype_mut` HR 0.72 (0.59–0.88), p = 0.0013;
  `Diet_DR` HR 0.48 (0.39–0.59), p < 0.0001; `Genotype_mut:Diet_DR` HR 1.62
  (1.21–2.17), p = 0.0012. LR interaction χ² = 10.4, df = 1, p = 0.0013.
- Derived simple effect of DR in mut: HR 0.48 × 1.62 ≈ 0.78 (no CI
  available for this derivation).
- RMST model: const 51.3; `Genotype_mut` +5.6 (2.1 to 9.1), p = 0.0017;
  `Diet_DR` +10.5 (7.0 to 14.0), p < 0.0001; `Genotype_mut:Diet_DR` −8.0
  (−13.1 to −2.9), p = 0.002. Derived DR gain in mut: 10.5 − 8.0 = +2.5 days.
- Pairwise, DR within mut (`mut/AL` vs `mut/DR`): log-rank raw p = 0.031,
  p_bonferroni = 0.19 (not significant after adjustment); Gehan-Wilcoxon
  p_bonferroni = 0.024 (significant). Pairwise DR within wt: log-rank
  p_bonferroni < 0.0001.

**Reading it.**
- The Cox interaction HR > 1 and the RMST interaction coefficient < 0 agree:
  the combination mut + DR does worse than additivity predicts.
- In wt, DR clearly extends female lifespan: +12 days median (+23% vs
  wt/AL; derived), +10.5 days RMST, HR 0.48 — **strong** evidence, though
  the HR is an age-averaged effect given the PH result.
- In mut, the DR benefit is much smaller: +3 days median, +2.5 days RMST
  (derived), HR ≈ 0.78 (derived). The log-rank test does not support a
  difference after adjustment, while Gehan-Wilcoxon does, which places the
  mut DR effect early in life. Evidence for a DR effect in mut:
  **suggestive**, lowered further by the censoring and exclusion issues in
  `mut/DR`.
- The interaction is **quantitative** (attenuation), not a crossover: DR
  does not shorten life in mut.
- Confidence in "DR extends lifespan in wt females": High. Confidence in
  "the DR benefit is attenuated in mut": Moderate — the interaction is
  significant on both the hazard and the RMST scales, but it rests on the
  cell with the most censoring and the only exclusions.
- Not assessed: males (filtered out of this Focus). The `Unfiltered` Focus
  is current and varies Sex as well (a 2×2×2 design), but it contains every
  female in this Focus, so its female contrasts are the same data, not
  independent support; its Factorial Battery also estimates only pairwise
  interactions, so it cannot test whether the Genotype × Diet interaction
  differs by sex.
- Recommendations: check why `mut/DR` has excess censoring at the last
  census (SampleSize entries for its chambers); consider a Focus for males;
  consider a sensitivity run without the `default` exclusions.
