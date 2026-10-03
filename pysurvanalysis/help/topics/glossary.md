# Glossary

The words pySurvAnalysis uses, in plain language, in alphabetical order. Each entry links to the page that explains it in full.

## A

**Active Focus** – The Focus the Hub is currently showing. QC, Analyze, Plots and AI act on it. You choose it in the Focus card of the Experiment panel. Switching it changes nothing on disk, because every Focus's results are kept under their own name. → [What a Focus is](help:focus)

**AI Narrative** – An optional AI-written summary attached to the Project Report: one paragraph per Focus from that Focus's own numbers, plus a qualitative "across Focuses" paragraph. It only summarises the pipeline's results, never performs its own analysis, and is deleted when the analysis is re-run. → [The AI narrative](help:ai-narrative)

**Analysis Hub** – The main window. A ribbon of three tiles (Batch · Project · Experiment) with a status readout, panels that open under the tiles, and an output area below. The Experiment tile holds the Focus selector and five sub-tiles: QC, Analyze, Plots, Scripts and AI. → [The Analysis Hub](help:hub)

**Analysis Set** – The optional analyses a run can perform: log-rank pairwise, log-rank omnibus, Gehan-Wilcoxon pairwise, pairwise hazard ratios, parametric AFT models, and the interaction analyses. It excludes any that the Focus is not offered. The survivorship core (life tables, summaries, median and mean survival) is not part of it and always runs. → [The Analyze panel and Run analysis](help:analyze-panel)

**Assumed Censoring** – The DLife convention that individuals still unaccounted for at the end of the census are treated as right-censored (alive when last seen) rather than dead. On by default; can be switched off per experiment. → [Censoring policy](help:censoring)

**At-Risk Band** – In a Publication Figure, the row of number-at-risk counts drawn beneath the curves inside the same plot. Its size and times are set in the Plot Editor. → [Plot Editor — Panels & legend](help:plot-editor-panels)

## B

**Batch** – A folder containing one or more Projects at any depth, used to run many Projects unattended. It holds no analysis of its own and never combines results. → [Batch runs](help:batch-panel)

**Batch Preflight** – The window every Batch Run opens first. It lists the Projects that will run, their usable and blocked members, and every Blocked Focus, each with the action that fixes it, and then offers Run or Cancel. → [The Batch preflight](help:preflight)

**Batch Project** – One Project a Batch Run can target, identified by its path relative to the Batch folder (for example `Sept2026/ProjA`). → [Batch runs](help:batch-panel)

**Batch Run** – One execution of a Project Script in every checked Project of a Batch. Each Project's failures are logged and the run continues with the next Project. → [Batch runs](help:batch-panel)

**`batch` script** – The Project Script every new `project.yaml` is given. A Batch Run executes it in each Project unless another script is chosen. → [Batch runs](help:batch-panel)

**Blocked Focus** – A Focus that cannot run as declared. Either it is *stale* (it names a factor or level the data file does not contain) or it is *empty* (a treatment the data holds has no individuals left after exclusions). The member's other Focuses still run. → [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)

**Blocked Member** – A Member Experiment a run cannot use yet: data with no `survival_config.yaml`, a config with no data file, or several candidate data files with none named. The Project still runs its other members. → [The Batch preflight](help:preflight)

## C

**Chamber** – One vial or container of individuals: the unit of the DLife census and the unit an Exclusion Group removes. All individuals in a chamber share a treatment. → [The Chamber QC viewer](help:qc-viewer)

**Custom Experiment** – Retired. It used to mean "no Experiment Type chosen". A config with no `experiment_type` is now simply a Standard Lifespan. → [Experiment Types](help:experiment-types)

## D

**Defined Plot** – A named group of treatments written into the workbook's `DefinedPlots` sheet. It is drawn as a KM figure for every Focus it fits, or recorded as Not Applicable with the missing treatments named. The Focus window can turn one into a Focus. → [Defined Plots](help:defined-plots)

**Divergence Note** – The Project Report's statement of where members differ in data-source settings (censoring policy, Exclusion Group, time unit). → [The Project Report](help:project-report)

## E

**Exclusion Group** – A named set of chambers removed from analysis, stored in `qc/remove_chambers.csv`. One group is active per experiment directory and is shared by every Focus. Its name is stamped on every report and Run Summary. → [Exclusion Groups](help:exclusions)

**Experiment Directory** – One data file's folder: `survival_config.yaml`, the data file (at the root or in `data/`), results in `analysis/<focus>/`, QC state in `qc/`, and publication figures in `figures/`. → [Where results are written](help:outputs-layout)

**Experiment Script** – A saved, re-runnable list of experiment-level steps, stored in `survival_config.yaml` or centrally in the Project's `experiment_scripts:`. → [Running Experiment Scripts](help:experiment-scripts)

**Experiment Type** – A description of the data source: input shape, time unit, censoring default, quality criteria and report sections. It says nothing about the design. All members of a Project share one. → [Experiment Types](help:experiment-types)

## F

**Factorial Battery** – The interaction analyses (the Cox factorial model with its likelihood-ratio and proportional-hazards tests, and the RMST factorial model) together with the faceted KM and the lifespan interaction plot. Offered when a Focus varies two or more factors. The models need every pair of factors fully crossed. → [Interaction analyses (Factorial Battery)](help:analysis-interaction)

**Filter (factor role)** – A factor a Focus names with exactly one level. Only individuals at that level are kept, and the factor does not appear in treatment labels. → [What a Focus is](help:focus)

**Focus** – A named slice of the factors and levels found in the data file. It is the unit of analysis: every output carries its name and every report describes it. Declared in the `focuses:` block of `survival_config.yaml`. → [What a Focus is](help:focus)

**Focus Inventory** – The Project Report's table of every Focus in every member, with its slice, N, deaths, censoring, treatments, state and Not Applicable items. → [The Project Report](help:project-report)

**Focus Shape** – Which factors a Focus varies and how many levels each has (for example `2×2`), which treatments hold individuals, and where a crossing has a hole. It decides which analyses and figures the Focus is offered. → [Focus Shape — what a Focus is offered](help:focus-shape)

**Focus window** – The dialog where Focuses are created, edited, renamed, imported and copied. → [The Focus window](help:focus-window)

## H

**Headline Figure** – The figure that states a Focus's main result and leads its report section: the faceted KM when the Focus crosses factors, otherwise the KM with at-risk table. → [The Plots panel and Generate plots](help:plots-panel)

## I

**Initialize** – Give a folder that already exists the file that makes it a Project (`project.yaml`) or a Member Experiment (`survival_config.yaml`), without moving anything. → [The Experiments card — members](help:project-members)

## L

**Left Out** – An offered analysis or figure you have unticked on the Analyze or Plots panel. It is stored in the config's `omit:` block, left out of every run (Hub, script and Batch alike), and recorded as a choice in the log, the Run Summary and the report. → [Not Applicable and Left Out](help:not-applicable)

## M

**Member Experiment** – An experiment folder inside a Project: one data file, analysed on its own and never pooled with its sibling members. → [The Experiments card — members](help:project-members)

**Minimal Member Config** – What *Create experiment…* writes: only what the member must state itself, leaving everything the Project Defaults supply out, so later edits to the Project still reach it. → [The Experiments card — members](help:project-members)

## N

**Not Applicable** – A relevant analysis or figure that the data cannot compute, for example the interaction model when one combination of levels has no individuals. Greyed in the Hub with the reason, and recorded in the log, the Run Summary and the report. → [Not Applicable and Left Out](help:not-applicable)

**Not offered** – An analysis or figure that is not relevant to a Focus's definition, for example the interaction model for a one-factor Focus. It has no checkbox and is not mentioned in the report. → [Focus Shape — what a Focus is offered](help:focus-shape)

## O

**Orphaned Results** – A folder under `analysis/` that no declared Focus names, left behind when a Focus is deleted or renamed by hand in the YAML. Listed in the Focus card with *Adopt…* and *Delete…*, and never included in a report. → [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)

**Out of Date** – A Focus whose saved results were produced from something that has since changed: its definition (factors, levels, level order, Reference Levels), the Exclusion Group or the chambers it removes, the data file's contents, the censoring policy, or what the run left out. The report shows none of those results until the Focus is re-run. → [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)

## P

**Plot Set** – The ordered list of figures a run produces for a Focus: the general survivorship figures, minus any the Focus is not offered, plus the faceted KM and interaction plot when the Focus varies two or more factors. → [The Plots panel and Generate plots](help:plots-panel)

**Plot Spec** – One Publication Figure's content: axis labels and limits, reference line, an optional narrowing to a subset of the Focus's treatments, and the name of its Plot Style. Stored in `plot_specs.yaml`. → [Publication Figures, Specs and Styles](help:publication-figures)

**Plot Style** – One Publication Figure's look (size, fonts, line widths, markers, panels, legend, colours), owned by that figure. Edited in the Plot Editor. → [The Plot Editor](help:plot-editor)

**Pooled over (factor role)** – A discovered factor a Focus does not name. Individuals at all its levels are combined. → [What a Focus is](help:focus)

**Project** – A folder with a `project.yaml` whose subfolders holding a `survival_config.yaml` are its members. Members address one question in different ways and are never pooled. → [Creating and opening a Project](help:project-create)

**Project Defaults** – The `defaults:` section of `project.yaml`: settings members inherit unless they override them (Experiment Type, time unit, censoring, input settings, Exclusion Group name, quality criteria). Focuses are never inherited. → [project.yaml and Project Defaults](help:config-project)

**Project Report** – `<project>/<project>_report.pdf`: a cover with the question, the Focus Inventory, any Divergence Note, then one independent section per Focus built from its saved results. → [The Project Report](help:project-report)

**Project Script** – A saved list of project-level steps in `project.yaml`. Its `run_in_experiments` step runs an Experiment Script in every member. → [Project Scripts](help:project-scripts)

**Publication Figure** – A journal-ready vector figure (SVG or PDF) authored in the Plot Editor and rendered from the Project panel. → [Publication Figures, Specs and Styles](help:publication-figures)

## R

**Reference Level** – The level a varying factor's model coefficients are measured against (the Cox and RMST baseline). It defaults to the first level listed and can be set separately from display order. → [Reference Levels](help:reference-level)

**Requirement** – What an analysis or figure needs from a Focus: *comparison*, *factorial plot* or *factorial model*. It has two halves, relevance (decided by the definition) and computability (decided by the data). → [Focus Shape — what a Focus is offered](help:focus-shape)

**`run_in_focuses`** – A script step that runs the rest of an Experiment Script once per Focus (every Focus, or just those listed in `only:`). → [Script action reference](help:script-actions)

**Run Summary** – `analysis/<focus>/run_summary_<focus>.json`: the small record of one run under one Focus (counts, the Focus definition, the Exclusion Group, figures written, Not Applicable and Left Out items, key test results). The Hub and the Project Report read it instead of re-analysing. → [The Run Summary](help:run-summary)

## S

**`Standard analysis` script** – The Experiment Script every new `survival_config.yaml` is given. The Project's `batch` script runs it in each member. → [Running Experiment Scripts](help:experiment-scripts)

**Standard Lifespan** – The one Experiment Type: a DLife census workbook of chambers scored to death, with assumed censoring on. Every analysis is reachable from it, gated by Focus Shape. → [Experiment Types](help:experiment-types)

## T

**Treatment** – One cell of a Focus: a combination of levels of its varying factors, written as a label such as `Female/20x`. Every analysis and figure groups by it. → [What a Focus is](help:focus)

**Type Action** – A script action an Experiment Type adds beyond the core actions. Script steps may use any core or type action; one the Focus does not admit is Not Applicable rather than an error. → [Script action reference](help:script-actions)

## U

**Unfiltered** – The Focus every experiment has when its config declares none: every discovered factor at every level. It is written into the config the first time the experiment is analysed or its Focuses are opened in the Focus window. → [What a Focus is](help:focus)

**Upgrade** – Rewriting a pre-overhaul folder layout into the current one. No longer a Hub button; use *Initialize existing directory…* to bring an old folder into a Project. → [The Experiments card — members](help:project-members)

## V

**Varying (factor role)** – A factor a Focus names with two or more levels. Its levels make up the treatment labels. → [What a Focus is](help:focus)

## See also

- [Batches, Projects, Experiments and Focuses](help:concepts)
- [What a Focus is](help:focus)
- [Troubleshooting](help:troubleshooting)
- [What pySurvAnalysis does](help:overview)
