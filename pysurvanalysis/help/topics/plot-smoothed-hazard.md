# Smoothed hazard

The smoothed-hazard figure shows how the **death rate** changes with age in each treatment. It takes the raw interval hazard from the lifetable and smooths it with a Gaussian kernel, so the age trend is visible through the row-to-row noise. It is in the Standard Lifespan Plot Set and is offered to every Focus.

## In the app

- **Plots panel:** the **Smoothed hazard** checkbox (plot id `smoothed_hazard`). Its caption reads "Kernel-smoothed hazard rate."
- **Scripts:** the **Hazard rate** action with **Smoothed** ticked draws the same figure, with an adjustable **Smoothing σ**.
- **Plot Editor:** `smoothed_hazard`. It uses the same kernel and bandwidth (σ = 3), so the curated figure shows the same estimate.

## What is computed

1. Start from the raw hazard hx at each observed age, the quantity the [Hazard rate](help:plot-hazard) figure draws unsmoothed (see [Hazard rate](help:plot-hazard) for the formula: hx = 2q / ((1 + p)·Δt), using the gap Δt to the next observed age).
2. Smooth the sequence of hx values, in age order, with `scipy.ndimage.gaussian_filter1d` at **σ = 3**.

**σ is measured in lifetable rows, not in time units.** σ = 3 means the kernel's standard deviation spans about three successive observed ages. With a daily census that is about three days. With a census every other day, about six. The filter treats the rows as evenly spaced even if they are not, and handles the ends of the series by reflecting it.

A treatment with **fewer than 5 rows** in its lifetable is not drawn in the analysis figure. The Publication Figure draws such a treatment unsmoothed.

The Plot Set figure and the Publication Figure always use σ = 3, one shared setting in the code (`plotting.SMOOTHED_HAZARD_SIGMA`). Only the script action lets you change σ.

## What is drawn

- **x axis:** age from 0, labelled with your configured time label (for example "Age (days)").
- **y axis:** "Smoothed Hazard Rate", from 0. The units are deaths per individual per unit of your time axis.
- One smooth line per treatment, with a faint fill to 0 beneath it. Treatments are in the Focus's order, with its display names and colours (the fixed colour cycle, in Focus order, for any treatment without one). Legend at upper right.
- Title "Smoothed Hazard Rate", 10 × 6 inches.

## Reading it

- A rising curve means mortality accelerates with age. In many lifespan cohorts the rise is roughly exponential.
- A treatment that **lowers** the curve at all ages has a proportional benefit. One that **delays** the rise shifts the curve to the right.
- Smoothing blurs sharp features: a brief die-off is spread over neighbouring ages, and the curve near the first and last ages is less reliable.
- At the oldest ages few individuals remain, so the curve can swing widely. Read it together with the [Number at risk](help:plot-number-at-risk).
- The figure shows no confidence band. Formal comparisons belong to the log-rank tests and hazard ratios.

## Where it appears

- File: `analysis/<focus>/plots/smoothed_hazard_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `smoothed_hazard` is curated in the Plot Editor.

## When it is not drawn

It has no requirement. Every Focus is offered it, and it is missing only when unticked (**Left Out**).

## See also

- [Hazard rate](help:plot-hazard)
- [Mortality (qx)](help:plot-mortality)
- [Nelson-Aalen cumulative hazard](help:plot-nelson-aalen)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [The Plots panel and Generate plots](help:plots-panel)
