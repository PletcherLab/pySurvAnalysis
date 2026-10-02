# pySurvAnalysis

Survival and demography analysis for lifespan experiments — a headless
pipeline plus a PyQt6 desktop UI, for DLife census workbooks and CSV/TSV
cohorts.

Structurally a sibling of [PyTrackingAnalysis](../PyTrackingAnalysis): the same
Batch → Project → Experiment layout, the same tile-strip Hub, the same
two-level scripting and publication-figure system. One deliberate difference
runs through everything: **a Project here never pools its members.**

## The three levels

```
Batch/                          a folder of Projects (structural; batch.yaml optional)
└── Project/                    project.yaml — defaults, scripts
    ├── plot_specs.yaml         the Project's Plot Specs and Styles
    ├── rep_a/                  a Member Experiment — one data file
    │   ├── survival_config.yaml    input, censoring, exclusions, and its Focuses
    │   ├── data/                   the workbook or CSV
    │   ├── analysis/
    │   │   ├── Crowding20v40/      one directory per Focus, every file named for it
    │   │   └── DilpOnly/           (…/run_summary_DilpOnly.json, plots/kaplan_meier_DilpOnly.png, …)
    │   ├── qc/                     remove_chambers.csv
    │   └── figures/<focus>/        vector Publication Figures
    └── rep_b/
```

Factors are never declared: they are **discovered** from the data file (the
Design sheet's columns after `StartTime`, or a CSV's factor columns), with each
factor's levels in the order they first appear. What a config declares instead
is one or more **Focuses** — named slices of those factors and levels. One data
file often holds several experiments whose lines must be analysed separately;
each is a Focus, analysed on its own, with its own results and its own report
section.

Nothing is pooled — not across Focuses, and not across a Project's members,
which address one question in different ways. The Project Report binds one
section per Focus behind a **Focus Inventory**, plus a divergence note when
members' data-source settings (censoring, exclusion group, time unit) differ.
An Experiment Directory also works perfectly well on its own, with no Project
above it.

See [CONTEXT.md](CONTEXT.md) for the glossary and [docs/adr/](docs/adr/) for the
decisions that shaped this — [ADR-0011](docs/adr/0011-focus-replaces-experiment-type-as-the-design-unit.md)
for Focuses.

## Install

```bash
uv sync
```

## Use

```bash
# The Hub (default)
uv run python main.py [path]

# Analyse one experiment: every Focus of an Experiment Directory (or just the
# ones named), or a bare data file under Unfiltered
uv run python main.py run path/to/rep_a
uv run python main.py run path/to/rep_a --focus Crowding20v40
uv run python main.py run cohort.csv --format long

# Run a Project Script, then the same across a whole Batch
uv run python main.py project path/to/Project --script "Report pipeline"
uv run python main.py batch   path/to/Batch

# Turn a pre-overhaul folder into an Experiment Directory (nothing is deleted)
uv run python main.py upgrade path/to/old_folder --dry-run

# The other two apps
uv run python main.py qc    path/to/rep_a
uv run python main.py plots path/to/rep_a
```

## Focuses

A Focus names, per factor, the levels it keeps, in **display order** (legends,
facets, plot cells), plus an optional **Reference Level** — the Cox baseline,
which defaults to the first level listed and can differ from display order:

```yaml
experiment_type: standard_lifespan
input:
  format: excel
exclusions:
  group: default
focuses:
  Crowding20v40:
    factors:
      Sex:     [Female, Male]
      Density: ["20x", "40x"]
    reference:
      Density: "40x"             # show 20x first, baseline on the 40x control
    display_names: {Female/20x: "F, 20x"}
    colours: {Female/20x: "#b2182b"}
  DilpOnly:
    factors:
      Genotype: [wCS, mDilp235bx]
      Sex:      [Female]         # one level: a filter, not a label
```

A factor named with two or more levels **varies** and labels the treatments; one
named with a single level is a **filter**; a discovered factor the Focus does not
name is **pooled over** — and every report says which. A Focus is the
rectangular product of its levels, so a cell the data never held (an unbalanced
design) is simply absent.

* **No `focuses:` block** means one Focus, `Unfiltered` — every factor at every
  level — written into the file on first use so you can see and rename it.
* **Author them in the Hub**: the Experiment panel's Focus selector picks the
  Active Focus that Analyze, Plots and AI act on, and New…/Edit… open the Focus
  window (live N, treatments and shape; Import from DefinedPlots; Copy Focuses
  from another member). Hand-editing the YAML works too.
* **The Focus decides what is offered.** Each analysis declares what it needs:

  | Needs | Offered when the Focus… | Computed when the data… | Analyses |
  |---|---|---|---|
  | nothing | always | always | KM, Nelson-Aalen, hazard, mortality, distribution, at-risk, parametric fits |
  | a comparison | implies ≥2 treatments | populates ≥2 treatments | log-rank (pairwise, omnibus), Gehan-Wilcoxon, hazard-ratio forest, log-log PH check |
  | a factorial figure | varies ≥2 factors | populates ≥2 treatments | faceted KM (the headline), lifespan interaction plot |
  | a factorial model | varies ≥2 factors | crosses every pair of them fully | Cox and RMST factorial models (main effects + pairwise interactions) |

  Something not offered has no Hub button, no figure and no report section — a
  one-factor Focus is never asked about interactions. Something offered but not
  computable (two varying factors with an empty cell) is greyed in the Hub with
  the reason and recorded as **Not Applicable** in the log, the Run Summary and
  the report — never silently.
* **Results stay honest.** A Focus naming levels the file no longer has, or
  whose cells the Exclusion Group empties, is **Blocked** — named in the Batch
  preflight, skipped, while the member's other Focuses run. Results produced
  under a since-changed Focus definition or Exclusion Group are **Out of Date**
  and are not shown in reports. A Focus renamed in the Focus window takes its
  results with it.

There is one **Experiment Type**, Standard Lifespan, and it describes the data
source (input shape, time unit, censoring default, report sections) — not the
design. Configs written before Focuses keep working: a `factors:` block becomes
a Focus named `Interaction`, verbatim, so every Reference Level survives.

## Scripting

Two levels, one visual editor, separate registries.

* **Experiment Scripts** live in `survival_config.yaml` `scripts:` (or centrally
  in the Project's `experiment_scripts:`). A `run_in_focuses` step repeats the
  rest of the script once per Focus (or just those its `only:` names); without
  one, a script runs under the Hub's Active Focus, or under every Focus when
  run unattended. A step naming an action that does not exist is a hard error
  — the script refuses to start — while a real step the Focus Shape does not
  admit is Not Applicable: recorded, and the run goes on.
* **Project Scripts** live in `project.yaml` `scripts:`. The only bridge
  downward is `run_in_experiments`, which runs a named Experiment Script in
  every member.
* A **Batch Run** executes one designated Project Script in every Project,
  continue-on-error.

## Publication figures

The Plot Editor (`main.py plots <experiment>`) renders survivorship figures
with plotnine from a **Plot Spec** + **Plot Style**, and exports SVG/PDF with
editable text. Specs (axis labels, limits, reference line) and Styles live in
the Project's `plot_specs.yaml`, so every member's figures match. Curve order,
display names and per-curve colours belong to the **Focus**; a Spec may only
narrow a figure to some of its Focus's treatments, never reorder them. The
number-at-risk counts are drawn inside the plot as an **At-Risk Band**, keeping
each figure a single grammar object.

## Reports

One backend-agnostic block model, two renderers: `<name>_report_<focus>.pdf`
via reportlab and `report_<focus>.md` via the markdown backend, so the two can
never disagree. Every report names its Focus and describes the slice. An opt-in
AI narrative adds a paragraph per Focus plus a labelled, explicitly qualitative
across-Focuses paragraph — it summarizes the saved numbers and never computes
its own.

## Tests

```bash
uv run pytest
```

The suite covers the structural layer — discovery, defaults resolution, type
validation, script registries, spec resolution, exclusion stamping, report
block assembly, and UI state. It deliberately does not re-test lifelines' math.
