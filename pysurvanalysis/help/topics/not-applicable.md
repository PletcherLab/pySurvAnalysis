# Not Applicable and Left Out

An analysis or figure can be missing from a run for three different reasons. The app keeps them apart, because a missing table means something different in each case:

| Word | Why it is missing | Recorded? |
|---|---|---|
| **Not offered** | The Focus never asks this question (an interaction model for a one-factor Focus). | No. It is simply not part of this Focus's run. |
| **Not Applicable** | The question is relevant, but the *data* cannot answer it (a crossing with an empty cell). | Yes: log, Run Summary, report. |
| **Left Out** | You chose to leave it out (its box is unticked on the Analyze or Plots panel). | Yes: log, Run Summary, report. |

The rule behind this: a report must never look complete when it is not. A real gap is always stated with its reason. A question the slice never asked is not mentioned, because a "not run" note in every one-factor report would teach readers to skip the note that matters.

## Not offered

Whether an item is offered depends only on the Focus's definition (see [Focus Shape](help:focus-shape)). Items that are not offered have no checkbox. Instead, one italic line at the bottom of the Analyze or Plots panel names them, for example *Not offered for Focus Females: Interaction analyses.* Hover over it for the reason (for example "Focus 'Females' varies only Genotype; the Factorial Battery needs 2 or more varying factors"). Nothing about them appears in the run log or the report.

## Not Applicable

An offered item is Not Applicable when the populated treatments cannot support it. Common causes:

- **Comparisons with one populated treatment** – "only 1 treatment(s) of Focus 'X' hold individuals; a comparison between treatments needs 2 or more". The four comparison analyses are recorded together as *Survival comparisons*.
- **Factorial models with a crossing gap** – "Focus 'X' has no individuals for Genotype=mut × Diet=DR, so the Factorial Battery's interaction terms cannot be estimated". This is recorded as *Factorial Battery*.
- **A figure the data cannot draw** – recorded under the figure's name with "could not be drawn (…)" or "the data cannot support it".
- **A Defined Plot that cannot be drawn in full** – for example "not in Focus 'X': Male/40x", or "Focus 'X' pools over Sex". A Defined Plot is drawn with all the curves its author listed or not at all. See [Defined Plots](help:defined-plots).
- **A script step the Focus does not admit** – for example a `cox_interaction` step run under a one-factor Focus.

### In the Hub, before running

The Hub estimates the shape from the Design sheet and the active exclusions. An offered item that is estimated not to be computable has its checkbox **greyed out**, and its tooltip ends with `Not applicable to Focus X: <reason>.` The Focus card's shape line marks the same items *(not computable: …)*.

### Where a run records it

- **Run log** – `  Not applicable — Factorial Battery: <reason>`
- **Run Summary** – an entry `{"action": …, "reason": …}` in the `not_applicable` list of `analysis/<focus>/run_summary_<focus>.json`. See [The Run Summary](help:run-summary).
- **Experiment report** – a status line on the cover ("N action(s) not applicable to this Focus — listed in the Focus section"), a *Not applicable to this Focus* table (Not applicable / Why) in the Focus section, and, for the battery, "**Factorial Battery: not run** — *reason*" in the Factorial analysis section.
- **Hub** – the Focus card's shape line adds "not applicable last run: …".
- **Project Report** – the Focus Inventory's *Not applicable* column.

Not Applicable is never an error. The rest of the run carries on, and in a script the next step runs.

## Left Out

Each Analyze and Plots checkbox is saved to the experiment's configuration, not kept as Hub state. Unticking a box adds its id to the `omit:` block of `survival_config.yaml`:

```yaml
omit:
  analyses: [parametric_aft]
  plots: [mortality, smoothed_hazard]
```

The same items are then left out of **every** run of this experiment: **Run analysis** in the Hub, a `run_analysis` step in an Experiment Script, and a Batch Run. Each produces the same report. Re-ticking the box removes the id again. The block lists what is left *out*, so an untouched config runs everything, and an analysis added in a later version is included until someone unticks it. See [The omit: section](help:config-omit).

Rules:

- Only items the Focus is **offered** can be left out of its run. An unticked *Interaction analyses* box means nothing to a one-factor Focus and is not recorded there.
- A figure that draws from a left-out analysis is left out with it. The **hazard-ratio forest** draws from the **pairwise hazard ratios**: while that analysis is unticked, the forest's box is greyed out ("Draws from Pairwise hazard ratios — tick it on the Analyze panel to draw this figure"), and the run records the forest as left out because it "draws from Pairwise hazard ratios, which is unticked".
- Files an earlier run wrote for an item that is now left out (its figure, its statistics table) are **deleted** by the next run, so the folder never shows an old result as current.

### Where a run records it

- **Run log** – a line such as *Left out — Mortality (qx): unticked in the Hub (omit: in survival_config.yaml)*
- **Run Summary** – an entry `{"id": …, "item": …, "reason": …}` in the `left_out` list.
- **Experiment report** – a cover status line ("N analysis or figure(s) left out of this run by choice"), a *Left out of this run* table in the Focus section, and, for the interaction analyses, "**Interaction analyses: left out of this run**" in the Factorial analysis section.

**Generate plots** on the Plots panel writes its Not Applicable and Left Out lines to the log only. The Run Summary and the report keep what the last **Run analysis** recorded.

## Left Out vs Not Applicable

Left Out is a choice, and you can reverse it by ticking the box and re-running. Not Applicable is a property of the data, and only different data, a different Exclusion Group or a different Focus changes it. That is why the report lists them in separate tables.

## See also

- [Focus Shape — what a Focus is offered](help:focus-shape)
- [The omit: section — leaving analyses and figures out](help:config-omit)
- [The Analyze panel and Run analysis](help:analyze-panel)
- [The Plots panel and Generate plots](help:plots-panel)
- [The Run Summary](help:run-summary)
- [The experiment report](help:experiment-report)
