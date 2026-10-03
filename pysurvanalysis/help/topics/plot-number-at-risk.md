# Number at risk

This figure plots, for each treatment, the **number of individuals at risk** (alive and not yet censored) at each age. It shows how much data supports every part of the survival curves, and it makes heavy or uneven censoring easy to see. It is in the Standard Lifespan Plot Set and offered to every Focus.

## In the app

- **Plots panel:** the **Number at risk** checkbox (plot id `number_at_risk`). Its caption reads "Individuals at risk over time."
- **Plot Editor:** `number_at_risk`, with the y axis labelled "Individuals at risk".

## What is computed

For each treatment, the lifetable column `n_at_risk` at each observed age t:

```
n(t) = (group size) − (deaths and censorings at all earlier observed ages)
```

It counts the individuals present **just before** the events at t. The starting value is the number of individuals in the treatment (after exclusions and the [Censoring policy](help:censoring)).

## What is drawn

- **x axis:** age from 0, labelled with your configured time label (for example "Age (days)").
- **y axis:** "Number at Risk", from 0. This is a count of individuals.
- One step curve per treatment, flat at the starting group size from age 0 to the first observed age. Treatments are in the Focus's order, with its display names and colours (the fixed colour cycle, in Focus order, for any treatment without one).
- Title "Number at Risk", 10 × 6 inches.

## Reading it

- Each downward step is the deaths **plus** the censorings at the previous observed age. A step much larger than the KM drop at the same age means many individuals were censored there (for example, lost or escaped).
- A large drop at the final census usually reflects individuals unaccounted for being treated as censored.
- Curves that start at very different heights mean the treatments had different sample sizes. Their KM curves and tests rest on different amounts of data.
- Where a curve approaches 0, survival estimates for that treatment become unreliable.

## Where it appears

- File: `analysis/<focus>/plots/number_at_risk_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `number_at_risk` is curated in the Plot Editor.

## When it is not drawn

It has no requirement. Every Focus is offered it, and it is missing only when unticked (**Left Out**).

## See also

- [KM curves with at-risk table](help:plot-km-risk-table)
- [Kaplan-Meier curves](help:plot-km-curves)
- [Censoring policy](help:censoring)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
