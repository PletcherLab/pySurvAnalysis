# The experiment report

Every analysis run writes a report for the Focus it analysed: a PDF to read and print, and a Markdown copy of the same content. The report is about exactly one Focus and says so on its cover, so two reports from one data file can never be mistaken for each other. Anything that did not run — because the data could not support it, or because you left it out — is stated in the report rather than silently missing.

## In the app

The report is written automatically by:

- **Run analysis** on the Analyze panel (under the Active Focus);
- an Experiment Script's `run_analysis` or `report` step;
- a Project Script or Batch Run that runs those steps in each member.

To open reports, use **View reports** on the Project panel's Actions card, which opens the Project Report and every member report, or open the files directly.

## Where it is written

For a Focus named, say, `diet` in the experiment `Exp12`:

| File | Content |
|---|---|
| `Exp12/analysis/diet/Exp12_report_diet.pdf` | the PDF report |
| `Exp12/analysis/diet/report_diet.md` | the same report as Markdown |

The PDF and Markdown are built from the same content, so they always agree. If the PDF cannot be produced, the Markdown is still written. Re-running the analysis overwrites both.

## The cover

The title is `<experiment> · <focus> — Survival Analysis`, with a short description of the experiment type beneath it. The cover then lists:

| Item | Meaning |
|---|---|
| Focus | the Focus name |
| Slice | one line describing it: varying factors with levels and reference, any filters (`only sex = F`), any factors pooled over |
| Experiment type | e.g. Standard Lifespan |
| Data file | the input file name |
| Generated | date and time the report was built |
| Varying factors | the factors that define the treatments |
| Treatments, Individuals, Deaths | counts in this Focus |
| Censored | number and percentage censored |
| Exclusion group | the active Exclusion Group and how many chambers it actually removed — or "no chambers removed (… listed, none present in this data)", "nothing listed", "none" |
| Censoring policy | "unaccounted individuals censored" or "unaccounted individuals ignored" |

### Cover status lines

Up to three short coloured lines summarise the run:

- **Omnibus log-rank** — "treatments differ (p = …)" when p < 0.05, otherwise "no overall difference detected (p = …)". Shown only when the omnibus test ran.
- **Not applicable** — "N action(s) not applicable to this Focus — listed in the Focus section" (a warning).
- **Left out** — "N analysis or figure(s) left out of this run by choice — listed in the Focus section".

## The sections

For the Standard Lifespan type the sections appear in this order. A section with nothing to show is left out entirely.

**Focus.** A sentence naming the Focus and the slice, then a *Focus definition* table (Factor, Levels in display order, Role — varying, filter or pooled over — and Reference level). A line gives the Focus Shape (e.g. `2×2`, or `2×2 (3 of 4 cells)`), the treatments, and any cells the levels imply but the data never held. If some individuals have no recorded level for a factor the Focus names, it says how many were outside the analysis. Then two tables when they apply:

- **Not applicable to this Focus** — each real action the slice could not support, with the reason.
- **Left out of this run** — each analysis or figure you unticked (the config's `omit:`), with the reason. A choice, not a property of the data.

**Experiment summary.** The per-treatment summary table (individuals, deaths, censored, % censored and related columns) and the observation window and number of chambers. See [Summary statistics](help:survival-summary).

**Survivorship figures.** Every figure of the Plot Set that was drawn, the **Headline Figure** first (labelled "— headline figure"). Where a figure has been curated in the Plot Editor, the curated version replaces the default one (labelled "— curated figure"); a curated KM figure stands in for both default KM figures. Any Defined Plots follow. See [Defined Plots](help:defined-plots).

**Factorial analysis.** Only for a Focus that varies two or more factors. For each model of the Factorial Battery (Cox factorial, then RMST factorial): the model formula, n, events, concordance (Cox), τ, R² and the robust F test (RMST) and AIC where available, a sentence giving the RMST model's τ, the interaction likelihood-ratio test against the main-effects model, the coefficient table (relative to the stated Reference Levels), for Cox the Schoenfeld proportional-hazards check, and a highlighted table of any warnings raised while fitting the model. A model that could not be fitted says why. If the battery did not run, a single line says either "Factorial Battery: not run — reason" or "Interaction analyses: left out of this run". See [Interaction analyses](help:analysis-interaction).

**Lifespan statistics.** Median survival (with its 95% confidence interval) and mean survival (restricted to the common τ, stated in the caption) tables, lifespan statistics by treatment and (when two or more factors vary) by factor level, and survival quantiles. See [Summary statistics](help:survival-summary) and [Life tables](help:lifetables).

**Survival comparisons.** The omnibus log-rank test (χ², df, p and stars), then the pairwise log-rank, pairwise Gehan-Wilcoxon and pairwise hazard-ratio tables, pairs in the Focus's treatment order. Pairwise test rows are highlighted when they are significant after the Bonferroni adjustment (`p_bonferroni` < 0.05, the same rows as `significant_0.05`). The hazard-ratio caption says which way each ratio points: group1 / group2, group1 being the treatment earlier in the Focus's order.

**Data quality.** Which chambers were excluded, by id (and via which group), or "No chambers were excluded from this analysis" (saying so when the group lists chambers this data file does not have). Then, when they apply: a highlighted table of warnings the loader reported about the data file; a highlighted table of chambers with fewer individuals than `global.min_n_per_chamber` (flagged for review, not excluded); and the **Parametric model fits (AFT)** table — per treatment and model, AIC, ΔAIC, the model's median and a note, the best model highlighted and any treatment or model not fitted listed with the reason. See [Parametric AFT models](help:analysis-parametric-aft).

## Reading the numbers

- p-values are shown to four decimals, or `<0.0001`, in every table. Stars: `***` p < 0.001, `**` p < 0.01, `*` p < 0.05, `ns` otherwise. Pairwise p-values are as the tests report them, beside their Bonferroni-adjusted values; see [Reading p-values](help:p-values) for multiple comparisons.
- `—` means a value is missing or could not be computed.
- Long tables show their first 200 rows, with a note saying so.

## Pitfalls

- The report describes the run that wrote it. If you change the Focus or Exclusion Group afterwards, the Hub marks the results **Out of Date**; re-run to refresh the report.
- The experiment report does not include the AI narrative; that appears only in the [Project Report](help:project-report).

## See also

- [The Run Summary](help:run-summary)
- [The Project Report](help:project-report)
- [Not Applicable and Left Out](help:not-applicable)
- [Where results are written](help:outputs-layout)
- [The Analyze panel and Run analysis](help:analyze-panel)
