# Nelson-Aalen cumulative hazard

The Nelson-Aalen figure draws the **cumulative hazard** H(t) for each treatment: the total risk of death built up from age 0 to age t. The KM curve shows how many survive. This curve shows how much mortality has accumulated, and because it is cumulative it is often easier to read for differences in the **rate** of dying than a KM curve.

## In the app

- **Plots panel:** the **Nelson-Aalen cumulative hazard** checkbox (plot id `nelson_aalen`).
- **Scripts:** the **Nelson-Aalen** action (optionally for a chosen list of treatments).
- **Plot Editor:** `nelson_aalen`, with the confidence band and point options available.

## What is computed

For each treatment, at every observed age tᵢ (from the Focus's lifetable):

```
H(t)      = Σ over tᵢ ≤ t of dᵢ / nᵢ
Var(H(t)) = Σ over tᵢ ≤ t of dᵢ / nᵢ²
95% CI    = H(t) ± 1.96 · √Var(H(t)), lower bound clipped at 0
```

Here dᵢ is the number of deaths at tᵢ and nᵢ the number at risk just before it. The interval is symmetric on the linear scale. It is computed in the app's own lifetable code (columns `na_H`, `na_se`, `na_ci_lo`, `na_ci_hi` of `lifetables_<focus>.csv`).

## What is drawn

- **x axis:** age from 0, labelled with your configured time label (for example "Age (days)").
- **y axis:** "Cumulative Hazard H(t)", from 0. It has no upper limit and can exceed 1.
- **One step curve per treatment**, starting at H(0) = 0, with a shaded 95% CI band.
- Legend at upper left. Treatments are in the Focus's order, with its display names and colours (the fixed colour cycle, in Focus order, for any treatment without one).
- Title "Nelson–Aalen Cumulative Hazard", 10 × 6 inches.

## Reading it

- The **slope** of a curve is the hazard (the death rate) at that age. A curve that bends upward shows mortality that accelerates with age, which is typical of ageing cohorts.
- A curve that runs **above** another has accumulated more risk. If two curves keep a constant **ratio** (on a log scale, a constant vertical gap), the hazards are proportional.
- H(t) is closely tied to survival: −log Ŝ(t) ≈ H(t). The two figures tell the same story on different scales.
- The band widens at old ages, where few individuals remain.

## Where it appears

- File: `analysis/<focus>/plots/nelson_aalen_<focus>.png` (150 dpi).
- The experiment report's figures section, or the curated version if `nelson_aalen` is curated in the Plot Editor.

## When it is not drawn

It has no requirement. Every Focus is offered it, and it is missing only when unticked (**Left Out**).

## See also

- [Kaplan-Meier curves](help:plot-km-curves)
- [Smoothed hazard](help:plot-smoothed-hazard)
- [Log-log diagnostic](help:plot-log-log)
- [Life tables and the Kaplan-Meier estimator](help:lifetables)
- [The Plots panel and Generate plots](help:plots-panel)
