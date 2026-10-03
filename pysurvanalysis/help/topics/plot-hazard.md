# Hazard rate

The hazard-rate figure plots the raw, unsmoothed **interval hazard** hx for each treatment: the estimated instantaneous rate of death at each observed age. It is in the Standard Lifespan Plot Set and offered to every Focus. The raw rate is noisy, so the Plot Set also has the [Smoothed hazard](help:plot-smoothed-hazard); this figure shows what the smoothing starts from.

## In the app

- **Plots panel:** the **Hazard rate** checkbox (plot id `hazard`). Its caption reads "Raw interval hazard rate, unsmoothed."
- **Scripts:** the **Hazard rate** action (key `hazard_plot`). Left as is, it draws this raw figure. With **Smoothed** ticked it draws the smoothed hazard instead, using its own **Smoothing σ** parameter (range 0.1–20). The figure opens in a tab titled "Hazard rate".
- **Plot Editor:** `hazard`, drawn with straight lines between values by default.

## What is computed

The lifetable has one row per distinct observed age (a death or a censoring) for each treatment. At row i:

```
qᵢ  = dᵢ / nᵢ                      (probability of dying at this age)
pᵢ  = 1 − qᵢ
Δtᵢ = t₍ᵢ₊₁₎ − tᵢ                   (gap to the next observed age;
                                    for the last row, the gap to the previous one;
                                    1 if there is only one row)
hxᵢ = 2·qᵢ / ((1 + pᵢ) · Δtᵢ)
```

This is the actuarial approximation to the hazard over the interval. It is a rate **per unit of your time axis** (per day for a day-scaled census). The "intervals" are the gaps between successive observed ages. In a census design these are usually the census intervals, not fixed bins chosen by the app. The value is the lifetable column `hx` in `lifetables_<focus>.csv`.

## What is drawn

- **x axis:** age from 0, labelled with your configured time label (for example "Age (days)").
- **y axis:** "Hazard Rate", from 0.
- One line with small dot markers per treatment, joining the per-row hx values. Treatments are in the Focus's order, with its display names and colours (the fixed colour cycle, in Focus order, for any treatment without one).
- Title "Hazard Rate Over Time", 10 × 6 inches.

## Reading it

- The hazard is the force of mortality. For ageing cohorts it typically rises with age, often roughly exponentially (Gompertz-like).
- Single-row spikes are common. One death among few survivors, or an unusually short gap between censuses, gives a large hx. Look at the trend, or use the smoothed figure.
- Late values rest on very few individuals and are unreliable.
- A constant **ratio** between two treatments' hazards is what the proportional-hazards assumption says.

## Where it appears

- File: `analysis/<focus>/plots/hazard_rate_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `hazard` is curated in the Plot Editor.

## When it is not drawn

It has no requirement. Every Focus is offered it, and it is missing only when unticked (**Left Out**).

## See also

- [Smoothed hazard](help:plot-smoothed-hazard)
- [Mortality (qx)](help:plot-mortality)
- [Nelson-Aalen cumulative hazard](help:plot-nelson-aalen)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [Script action reference](help:script-actions)
