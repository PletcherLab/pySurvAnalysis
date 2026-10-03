# Publication Figures, Specs and Styles

A **Publication Figure** is a hand-curated, journal-ready version of a figure from the Plot Set. It is drawn with **plotnine** (a ggplot-style library) and written as SVG or PDF with editable text, or as PNG. It is separate from the matplotlib PNGs that **Run analysis** and **Generate plots** produce. You **author** Publication Figures in the [Plot Editor](help:plot-editor) and **render** them from the Project panel.

Each Publication Figure is defined by two things:

- a **Plot Spec**: its content decisions. These are the title, axis labels, legend title, facet factor, axis limits, reference line, and optionally a narrowing to some of the Focus's treatments;
- a **Plot Style**: its look. This covers size in mm, theme, fonts and text sizes, curve and axis weights, markers, censor ticks, confidence band, panels, gridlines, legend, the At-Risk Band and the colour cycle.

## Who decides what

| Decision | Lives in | Set in |
|---|---|---|
| Which treatments exist, their order | the Focus | the Focus window |
| Display names and per-curve colours | the Focus (`display_names:`, `colours:` in `survival_config.yaml`) | the Focus window, or the Plot Editor's Colours card |
| Labels, limits, reference line, facet factor, narrowing | the Spec | the Plot Editor's Figure card |
| Everything about the look | the Style | the Plot Editor's style cards |

A Spec can **narrow** a figure to a subset of the Focus's treatments, but never reorder or rename them. Curves always follow the Focus's order, so a legend never disagrees with the model printed beside it.

## plot_specs.yaml

All Specs and Styles live in **one file at the container**: `plot_specs.yaml` in the Project directory, or in the experiment's own directory for a standalone experiment. Every member of a Project renders with the same curation. A shared Spec still works for a member whose treatments differ: names it does not have are ignored, and its curves follow its own Focus.

The file has three keys:

```yaml
default_style: default        # the Style a figure's first edit is seeded from
styles:
  default: {}                 # built-in values unless overridden
  km_curves:                  # each saved figure owns a Style of its own name
    width_mm: 85.0
    height_mm: 65.0
    theme: theme_classic
    font_family: Arial
    base_size: 8.0
    line_width: 0.9
    censor_ticks: true
    ci_band: false
    risk_table: true
    risk_table_times: [0, 20, 40, 60]
    palette_cycle: ['#4C72B0', '#DD8452', '#55A868', '#C44E52']
    # ...every other Style field
plots:
  km_curves:
    style: km_curves
    title: ''
    x_label: Age (days)
    y_label: Survival probability
    series_label: Treatment
    treatments: []            # empty = every treatment of the Focus
    facet_by: ''
    facet_order: []
    x_limits: []              # [low, high] pins the axis
    y_limits: []
    reference_line: 0.5       # null = no line
```

- **Save Project default** in the Plot Editor writes **one figure at a time**: its Spec under `plots:` and its Style under `styles:`, both under the figure's plot id. Figures you never saved are not in the file.
- Unknown top-level keys are kept when the editor saves, so the file can be edited by hand.
- Valid plot ids under `plots:` are `km_curves`, `km_faceted`, `nelson_aalen`, `number_at_risk`, `cumulative_events`, `mortality`, `hazard`, `smoothed_hazard`, `log_log`, `survival_distribution`, `hazard_ratio_forest` and `interaction_lifespan`. Other ids are ignored. A Spec saved under the retired id `km_risk_table` is read as `km_curves`, because the at-risk counts are a Style option (`risk_table`) there.
- **Legacy member files.** Earlier versions saved Specs in each member's own `plot_specs.yaml`. Those are still read, but only for plot ids the container has no Spec for.

## Rendering

**Project panel → Render publication figures**, with the format chosen beside it (`svg`, `pdf` or `png`):

- walks **every member** of the Project. A member is skipped ("nothing curated — skipped") when the file has no saved Specs, and nothing at all is rendered if nothing is curated;
- for each member, renders under **each of its Focuses** whose results are analysed and current. A Focus that is not analysed, or whose results are **Out of Date**, is named in the log and skipped. Run it first;
- renders **only the figures saved in `plots:`**, never defaults for the rest of the Plot Set;
- under each Focus, renders only the saved figures that **Focus is offered**. A saved `km_faceted` or `interaction_lifespan` is skipped under a Focus varying fewer than two factors, and a saved forest or log-log diagnostic under a single-treatment Focus, each with a log line giving the reason (`km_faceted: not offered — Focus 'Females' varies only Diet; a figure crossing factors needs 2 or more varying factors — skipped.`);
- writes each to `<member>/figures/<focus>/<plot id>_<focus>.<format>`, overwriting the previous render;
- names and skips a figure that has no data under a Focus (for example a forest with no saved hazard ratios, or an interaction plot none of whose cells reaches a median), and carries on with the others.

The same rendering is available as the **Render publication figures** script action, at Project level or for one experiment. In an Experiment Script it renders the script's Focus, or every Focus if none is set.

**Export SVG** in the Plot Editor writes just the current figure to the container's `figures/` folder (`<plot id>_<focus>.svg`, numbered rather than overwritten).

**Formats.** SVG keeps text as editable text (`svg.fonttype: none`). PDF embeds TrueType fonts (`pdf.fonttype: 42`), so labels can still be retyped in an illustration program. PNG is rasterised at 300 dpi. All are written at the Style's size in millimetres.

Figures are drawn from the Focus's **saved** results in `analysis/<focus>/`: lifetables, individual data, and the hazard-ratio table. A Publication Figure never computes a statistic of its own.

## In the reports

A curated figure **replaces** the analysis figure in the experiment report and the Project Report. It is drawn through its Spec and Style at 200 dpi and titled `<figure> — curated figure`. Figures with no saved Spec fall back to the default matplotlib PNG. A curated `km_curves` stands in for **both** default KM figures. If a curated figure fails to render, the report shows the default instead.

## How these differ from the analysis figures

- Both use the Focus's order, display names and per-curve colours. Where the Focus sets no colour, a Publication Figure takes its Style's cycle and an analysis PNG a fixed cycle, each in the Focus's order.
- The At-Risk Band is text inside the same plot, not a separate table axis. This is a deliberate design choice (ADR-0004): one plot object facets, themes and exports as vectors without stitching two figures together.
- The numbers are the same; some figures are drawn differently. The distribution is a density curve rather than a violin (both over recorded deaths only). The forest uses a log ratio axis. The interaction plot shows the same Kaplan-Meier medians and intervals, the same way round. Cumulative deaths are 1 − S(t) in both. See each figure's page.

## See also

- [The Plot Editor](help:plot-editor)
- [Plot Editor — Figure](help:plot-editor-figure)
- [Plot Editor — Colours](help:plot-editor-colours)
- [Project actions — reports, figures, Plot Editor](help:project-actions)
- [The Focus window](help:focus-window)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
