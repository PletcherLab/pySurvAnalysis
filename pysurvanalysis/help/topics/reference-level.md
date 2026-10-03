# Reference Levels

Each varying factor of a [Focus](help:focus) has a **Reference Level**: the level the factorial models compare the other levels against. It sets the sign of every coefficient, including the interaction terms, in the [Cox factorial model](help:cox-factorial) and the [RMST factorial model](help:rmst-factorial). The report's text uses it as the baseline too. It is stored separately from the level *order*, so you can list densities as `20x, 40x` in every legend and still make `40x` the control the model compares against.

## Why it is separate from level order

Level order is presentation: it controls legend order, the panels of the faceted KM and the cells of the interaction plot. The Reference Level is statistics. If the first level listed were always the baseline, re-ordering a legend would silently flip every hazard ratio in the model. Keeping the two separate means a presentation choice never changes a result.

## Setting it

**In the Focus window:** each factor box has a **Reference:** drop-down listing the ticked levels. It defaults to the first ticked level and is enabled once the factor varies (two or more levels ticked). Saving writes every varying factor's reference explicitly, the default included. See [The Focus window](help:focus-window).

**In survival_config.yaml:** add a `reference:` mapping to the Focus, naming a level for each factor you want to set:

```yaml
focuses:
  Crowding20v40:
    factors:
      Genotype: [wCS, mDilp235bx]
      Density: ["20x", "40x"]
    reference:
      Density: "40x"          # Genotype not named -> wCS (first listed)
```

The rules:

- With no `reference:` entry, a factor's Reference Level is the **first level listed** in `factors:`.
- The reference must be one of the levels the Focus keeps for that factor, and the factor must be named in the Focus. Otherwise validation reports it ("reference level '…' is not one of …'s levels", "reference names factor '…', which the Focus does not name") and the Focus window refuses to save.
- The Focus window writes `reference:` for **every** varying factor when it saves, even when the reference is the first level. A reference left out of a hand-written file means "the first level listed", and so moves if the levels are reordered; a written one does not.

## What it affects

| Output | Effect |
|---|---|
| Cox factorial model | Each factor is dummy-coded with the Reference Level as the dropped baseline. Every main-effect hazard ratio is "this level vs the reference", and each interaction term is relative to the reference cell. |
| RMST factorial model | The same coding: differences in restricted mean survival time relative to the Reference Levels. |
| Report | The "Focus definition" table has a *Reference level* column. The coefficient tables are captioned "Relative to the Reference Levels: Density = 40x, …". |
| Hub and Focus window | The Focus description reads `Density: 20x, 40x (reference 40x)`. |
| Run Summary | The Reference Levels are recorded as part of the Focus's analytic definition. |

The Reference Level does **not** change Kaplan-Meier curves, life tables, the log-rank and Gehan-Wilcoxon tests, the pairwise hazard ratios, the parametric AFT fits or any figure. Those depend on the treatments and the display order only.

## Discovered order protects the default

Levels are discovered in **first-appearance order in the Design sheet**, never alphabetically. You usually enter the control first, so the default reference is usually the control. Alphabetical order would, for example, make `mDilp235bx` the reference over `wCS`. When the Unfiltered Focus (or a migrated Interaction Focus) is first written into the config, that order is frozen, so re-sorting the Design sheet later cannot move a Reference Level.

## Changing it after analysing

The Reference Level is part of the Focus's analytic definition. Changing it makes the Focus's saved results **Out of Date** ("a Reference Level changed"). The comparison is of the baseline the model actually uses, so writing down a reference that was already the default (as the Focus window's Save does) is not a change. The Hub and the Project Report then stop presenting those results until the Focus is re-run. See [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status).

## Pitfalls

- In a hand-written Focus with no `reference:` for a factor, the reference **follows the order**: moving another level to the top of the YAML list makes that level the reference. Write `reference:` (or save the Focus once in the Focus window, which writes it for you) to pin the baseline whatever the order.
- A one-level factor (a filter) and a pooled factor have no Reference Level. Only varying factors do.
- When reading a coefficient table, check its caption for the baseline before interpreting the sign of a hazard ratio.

## See also

- [What a Focus is](help:focus)
- [The Focus window](help:focus-window)
- [The Cox factorial model](help:cox-factorial)
- [The RMST factorial model](help:rmst-factorial)
- [Interaction analyses (Factorial Battery)](help:analysis-interaction)
