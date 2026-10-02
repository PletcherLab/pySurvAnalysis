# A Focus carries the design; the Experiment Type carries only the data source

Factors and levels are now **discovered from the data file**, never declared,
because no two experiments here share a factor set and the loader already reads
the Design sheet. What config declares instead is one or more named
**Focuses** — a chosen slice of those discovered factors and levels, collapsed
into the `treatment` every analysis groups by. This exists because one workbook
routinely holds several experiments whose lines must be analysed separately,
which the old one-directory-one-design model could not express.

The consequence is that **Interaction Experiment is retired as an Experiment
Type**. A 2×2 was never a property of a directory — it is a property of a
design, and one file can hold both a 2×2 and a three-level comparison. Its
analyses survive unchanged as ordinary actions gated by **Focus Shape**:
offered when the active Focus's two factors of two levels each give four
populated cells, Not Applicable otherwise — cells counted rather than levels,
because unbalanced designs are common and an interaction term with an empty
cell is not estimable. **Standard Lifespan** becomes the general case and the only type,
describing the data source alone — input shape, time unit, censoring default,
quality criteria, report sections.

## Considered alternatives

- **Keep Focus as transient UI state.** Rejected: a focus that filters the raw
  data changes N, every curve and every p-value, so an unstamped focus means
  two reports from one file disagree with nothing on the page saying why. It is
  also invisible to an unattended Batch Run (ADR-0007), which has nobody to
  click a window, and it would overwrite the previous Focus's outputs in the
  single `analysis/` directory.
- **Retire Experiment Type entirely.** Rejected, narrowly: with the design
  concerns gone the type is thin, and with one type left its cross-member
  validation cannot fail. But deleting it leaves a Project enforcing *nothing*
  (ADR-0001 rests on that single check), and "these members read the same kind
  of file and share a time unit" is still the thing that would produce an
  incoherent bound report if violated.
- **Order-as-reference only.** Rejected: it forces a presentation choice to
  rewrite the statistics. A Focus names each factor's Reference Level
  explicitly, defaulting to the first level listed.

## Consequences

- Outputs are per-Focus — `analysis/<focus>/`, with the Focus name carried in
  each filename — and the **Run Summary** is one per Focus. Analysing a second
  Focus no longer overwrites the first.
- The **Project Report** sections per Focus rather than per Member Experiment.
  A declared-but-unrun Focus yields "not analyzed", which is why Focuses are
  declared in config and not merely chosen: an un-run Focus and one nobody ever
  conceived must not look the same.
- **Amends ADR-0002.** The registry becomes *core ∪ type ∪ what the Focus
  Shape admits*, and its hard-error rule is split in two. An action name
  outside *core ∪ type* — a typo, a step from another app — is still a hard
  error that refuses to start the script. But a real action whose Focus Shape
  does not admit it is **Not Applicable**: non-fatal, and recorded in the run
  log, the Focus's Run Summary and its report section. Scripts run once per
  Focus (`run_in_focuses`) and Focus names differ between members, so one
  recipe necessarily meets Focuses of different shapes; a hard error there would
  fail every heterogeneous member. What ADR-0002 actually forbade was the
  *silent* skip — a report that looks complete and is not — and a stated
  non-applicability is the opposite of that.
- The "level present in the data but not declared is a load error" rule dies
  with declaration. Discovery cannot drift from the data it reads.
- **Custom Experiment** is retired; a config with no `experiment_type` key is a
  Standard Lifespan. A config with no `focuses:` block gets one Focus,
  **`Unfiltered`** — every discovered factor at every level — written into the
  file on first save, so every pre-Focus config keeps running unchanged.
- **Migration preserves every Reference Level.** An existing config's declared
  `factors:` block becomes a Focus named `Interaction`, verbatim — same
  factors, same level order — and `experiment_type: interaction` is dropped.
  No `Unfiltered` is added beside it, matching the retired type's behaviour of
  analysing only its declared cells, so a re-run gives identical numbers.
  Discovery orders levels by first appearance in the Design sheet, never
  alphabetically: dropping the block and sorting would have made `mDilp235bx`
  the reference over `wCS`, flipping every coefficient and inverting every
  hazard ratio in a re-run that looked normal.
- **Results from before Focuses are not adopted.** Bare `analysis/` outputs
  carry no Focus stamp and no recorded definition, so they show as "not
  analyzed" rather than being moved into `analysis/Unfiltered/` — adopting them
  would vouch for a definition the old Run Summary never recorded. The cost is
  one re-run per experiment.
