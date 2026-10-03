# The Hub runs a selection, not actions; the selection is configuration

The Analyze and Plots panels had grown a button per action — log-rank
pairwise, log-rank omnibus, Gehan-Wilcoxon, parametric AFT, the Cox factorial
model, the RMST factorial model, a report button, a button per figure — beside
a **Run analysis** that already ran all of them. A 2×2 Focus showed the Cox and
RMST factorial models as two buttons for what a reader thinks of as one
question (is there an interaction?). Each panel is now **a checkbox per item
its set offers the Active Focus, over one button that runs them**: Analyze
lists the type's **Analysis Set** above Run analysis, and Plots lists the
**Plot Set** above Generate plots. The Factorial Battery is one box,
*Interaction analyses*, shown only to a Focus that varies two or more factors.

The ticks are **configuration, not UI state**: an `omit:` block in
`survival_config.yaml` naming the analysis and plot ids a run leaves out.
Run analysis, an Experiment Script's `run_analysis` step and a Batch Run
therefore produce the same report. The block records what is left *out*, so a
config nobody touched runs everything, and an analysis a later version adds is
included until someone unticks it. A run states each left-out item — in the
log, the Run Summary and the report's Focus section — as a choice, separate
from **Not Applicable**, which is a property of the data. A figure that draws
from an unticked analysis (the forest from the pairwise hazard ratios) is left
out with it, and the earlier run's copy of anything left out is deleted, so the
folder never shows a stale figure as current.

This amends ADR-0002 for the Hub only. Actions are still **core ∪ type** and
still the script vocabulary, and a script naming an unknown action still
refuses to start. What an Experiment Type contributes to the Hub is now its
Analysis Set and Plot Set, not buttons.

## Considered alternatives

- **Checkboxes as Hub-session state, scripts and batches running everything.**
  Rejected: the same experiment would yield a different report depending on
  whether a person or a Batch Run produced it, with nothing on the page saying
  why — the failure ADR-0011 closed for the Focus.
- **Store what is included.** Rejected: every analysis added later would be
  silently missing from every existing experiment's runs.
- **Keep the per-analysis buttons as quick looks beside the saved run.**
  Rejected: two ways to run one analysis, one of which leaves nothing on disk.
  The individual actions remain available as script steps.
