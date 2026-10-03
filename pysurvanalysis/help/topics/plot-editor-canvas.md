# Plot Editor — Canvas & type

The **Canvas & type** card sets a figure's physical size, its overall theme and all of its text. These are **Plot Style** settings. When you click **Save Project default**, they are saved under the figure's own name in the `styles:` section of the container's `plot_specs.yaml`. Use *Copy style from…* on the Figure card to give another figure the same look.

Every change redraws the preview at once.

## Fields

**Size (mm):** width × height of the finished figure in **millimetres** (whole numbers, steps of 5). Width ranges from 40 to 400 and height from 30 to 400. The default is **120 × 90 mm**. This is the size the SVG, PDF or PNG is written at, so set it to the column width your journal asks for: typically about 85–90 mm for one column and 170–180 mm for two. Fonts are in points, so they stay the same physical size when you change the figure size.

**Theme:** the plotnine base theme the rest is laid over:

- `theme_classic` (default): white background with x and y axis lines and no box;
- `theme_bw`: white background with a panel border;
- `theme_minimal`: no axis lines or border;
- `theme_light`: light grey panel border;
- `theme_matplotlib`: matplotlib's look.

The editor switches off the theme's gridlines unless you turn them on under [Panels & legend](help:plot-editor-panels).

**Font:** the font family for all text, chosen from the fonts installed on this computer. The default is DejaVu Sans. If the chosen font is not installed where the figure is rendered, the first available of Helvetica, Arial, Liberation Sans and DejaVu Sans is used, and the exported SVG names the font actually used.

**Base size (pt):** the text size every other text size follows (4 – 32 pt in steps of 0.5; default **9 pt**). Change only this and all text scales together.

**text:** the swatch beside Base size sets **one colour for all text**: title, axis titles, tick labels, legend and facet strips. Default black. Panel borders and boxed facet strips are also outlined in this colour. Axis lines and ticks keep the theme's own colour.

**Per-element sizes.** Each is 0 – 40 pt in steps of 0.5, and shows **auto** at 0 (the default), meaning "follow the base size":

| Field | Applies to | When auto |
|---|---|---|
| Title (pt) | the figure title | base + 2 pt |
| Axis titles (pt) | the x and y axis titles | base |
| Tick labels (pt) | the numbers and level names on the axes | base |
| Legend (pt) | legend entries and the legend title | base |
| Facet strips (pt) | panel titles of a faceted figure | base + 1 pt |

Set one of these only for the element that has to differ, such as a long title or cramped tick labels. Leaving the rest on auto keeps the figure scaling as one thing when you change the base size.

The At-Risk Band's numbers have their own size, set under [Panels & legend](help:plot-editor-panels).

## See also

- [The Plot Editor](help:plot-editor)
- [Plot Editor — Curves & points](help:plot-editor-curves)
- [Plot Editor — Panels & legend](help:plot-editor-panels)
- [Publication Figures, Specs and Styles](help:publication-figures)
