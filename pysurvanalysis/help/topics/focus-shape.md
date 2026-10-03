# Focus Shape — what a Focus is offered

Which analyses and figures you get depends on the **Focus**, not on the experiment. A [Focus](help:focus) that compares three genotypes gets log-rank tests but no interaction model. A Focus crossing genotype with diet also gets the faceted KM, the interaction plot and the Factorial Battery. A single-treatment Focus gets the survivorship battery only. The **Focus Shape** is what decides this: the factors the Focus varies and how many levels each has, which of the implied treatments actually hold individuals, and where the crossing of two varying factors has a hole.

## Reading a shape

A shape is written as the level counts of the varying factors:

| Shape | Meaning |
|---|---|
| `single cell` | nothing varies — one treatment |
| `3` | one varying factor with three levels |
| `2×2` | two varying factors with two levels each, all four cells populated |
| `2×2 (3 of 4 cells)` | the same, but one implied cell holds no individuals |
| `2×3×2` | three varying factors |

## Two questions: relevant, then computable

Each conditional analysis or figure declares a **Requirement**, and each Requirement is checked in two steps:

1. **Relevance** is decided by the Focus's *definition* alone (how many factors it varies and how many treatments its levels imply). An action that is not relevant is **not offered**: no checkbox in the Hub, no figure, no report section, no note in the report. It is not a question this slice asks.
2. **Computability** is decided by the *data*: which treatments hold individuals once the Exclusion Group is applied. A relevant action the data cannot support is **Not Applicable**. It is greyed out in the Hub with the reason, and the run records it in the log, the Run Summary and the report. See [Not Applicable and Left Out](help:not-applicable).

## The three Requirements

| Requirement | Offered (relevant) when | Computable when | Used by |
|---|---|---|---|
| **Comparison** | the levels imply 2 or more treatments | 2 or more treatments hold individuals | log-rank pairwise and omnibus, Gehan-Wilcoxon, pairwise hazard ratios, the hazard-ratio forest, the log-log diagnostic |
| **Factorial plot** | the Focus varies 2 or more factors | 2 or more treatments hold individuals | the faceted Kaplan-Meier and the lifespan interaction plot |
| **Factorial model** | the Focus varies 2 or more factors | as above, **and** every pair of varying factors is fully crossed | the interaction analyses: the Cox factorial model and the RMST factorial model |

Everything else needs nothing and is always offered: life tables, summary statistics, median and mean survival, Kaplan-Meier curves (with and without the at-risk table), Nelson-Aalen, the smoothed hazard, mortality (qx), number at risk, the lifespan distribution and the parametric AFT fits.

The factorial figures need only two populated treatments, because a missing cell is just a missing curve or point. The factorial models need full crossing, because an interaction term cannot be estimated across an empty cell.

## Crossing gaps

For the factorial models, the app checks every **pair** of varying factors. For each pair it looks for any combination of their levels with no individuals. Each such combination is a *crossing gap*, written like `Genotype=mut × Diet=DR`. One gap makes the models Not Applicable, with the gap named in the reason:

```
Focus 'GxD' has no individuals for Genotype=mut × Diet=DR, so the
Factorial Battery's interaction terms cannot be estimated
```

The models fit main effects plus **pairwise** interactions, so with three varying factors a missing three-way cell is not a gap as long as every pair is still covered.

An *absent* cell (one the data never contained) and a cell *emptied by exclusions* both count as unpopulated for computability. They differ in another way: a cell that QC emptied **blocks** the whole Focus. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).

## Where you see the shape

- **Focus window** – the preview line `N = 409 · 4 treatment(s) · shape 2×2`, followed by `This Focus offers a comparison between treatments; a figure crossing factors; the Factorial Battery.` Any offered item the data cannot compute is marked *(not computable: …)*. A single-treatment Focus reads "offers the survivorship battery only — no comparison or factorial analysis applies to a single treatment".
- **Hub, Focus card** – the shape line under the Focus selector: the Focus description, `shape …`, the same "offers …" text, then any Not Applicable items from the last run and any Blocked or Out of Date notice.
- **Analyze and Plots panels** – one checkbox per offered item. A greyed box is relevant but not computable (hover for the reason). An italic line at the bottom names what is *not offered* for this Focus (hover for why).
- **Plots sub-tile** – the shape of the last run (`focus shape: 2×2`).
- **Report** – the Focus section states the shape, the treatments and any absent cells. The Run Summary records the shape.

## Estimated before anything runs

The Hub and the Focus window know the shape before you analyse. The Hub reads the workbook's Design sheet (one row per chamber) and removes the chambers excluded by the active Exclusion Group and the workbook's chamber flags; it does not read the census data. The Focus window computes N and the shape from the loaded data. A run then measures the shape exactly from the data it loaded. For a CSV, which has no chambers, the estimate is simply the cells the file contains.

## The Headline Figure follows the shape

When the Focus can draw the faceted KM (two or more varying factors and two populated treatments), the faceted KM is the [Headline Figure](help:plots-panel) that leads the report. Otherwise the headline is the KM with at-risk table.

## Scripts

A script step can name any action, whatever the Focus. When a step's Requirement is not admitted (not relevant, or not computable) for the Focus it runs under, the step is **Not Applicable**: it is logged and recorded, and the script carries on. Only an action name the app does not know at all is a hard error that stops the script from starting. See [Script action reference](help:script-actions).

## See also

- [What a Focus is](help:focus)
- [Not Applicable and Left Out](help:not-applicable)
- [Interaction analyses (Factorial Battery)](help:analysis-interaction)
- [The Analyze panel and Run analysis](help:analyze-panel)
- [The Plots panel and Generate plots](help:plots-panel)
