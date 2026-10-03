# The AI narrative

The AI narrative is an optional, AI-written prose summary for the Project Report: one paragraph for each analysed Focus, plus one closing paragraph on where the separate Focuses agree and disagree. It **summarises numbers the app has already computed and saved**; the AI never sees your raw data and never performs an analysis of its own. It is off unless you ask for it, and if the AI service fails you lose the narrative, never the report.

## Setting up a provider

Two providers are supported. The app uses whichever has an API key set:

| Provider | Environment variable | Model used | Python package |
|---|---|---|---|
| Anthropic | `ANTHROPIC_API_KEY` | `claude-opus-5` | `anthropic` |
| OpenAI | `OPENAI_API_KEY` | `gpt-5.2` | `openai` |

Set the key either:

- as an environment variable before starting the app, or
- in a file named `.env` in the folder you start the app from (or any folder above it), containing a line such as `ANTHROPIC_API_KEY=sk-...`.

A variable already set in the environment takes precedence over the `.env` file. The model is fixed per provider; it cannot be chosen in the app. Keep your key out of shared folders and version control.

## In the app

Open the Experiment tile and choose the **AI** sub-tile. The sub-tile reads "no API key — add one to .env" and is dimmed when no provider is configured, and is also dimmed until a Project is loaded — the narrative is written per Project.

The **AI narrative** card shows:

- a status line — "Ready: anthropic, openai" or "No provider configured — set ANTHROPIC_API_KEY or OPENAI_API_KEY in your environment or a .env file.";
- **Provider** — the configured providers to choose from;
- **Write narrative** — generates the narrative with the chosen provider, saves it (see *Where it is saved* below) and prints each paragraph in the log, headed by its section name. It is not added to any report;
- **Project report with narrative** — generates the narrative with the chosen provider, saves it, and builds the [Project Report](help:project-report) with it.

In scripts, use `project_report` with `with_narrative: true` (and an optional `provider`) to build the report with the narrative, or `generate_ai_narrative` (with an optional `provider`), which generates and saves the text and logs how many sections were written. See [Script action reference](help:script-actions).

## What it writes

- **One paragraph per Focus** (at most about 120 words), for every Focus of every member whose saved results are current. Focuses that have not been analysed, or whose results are Out of Date, are not summarised. In the Project Report it appears at the top of that Focus's section.
- **One "Across Focuses" paragraph** (at most about 100 words), written only when two or more Focuses were summarised. It is placed after the Focus Inventory under the heading *Across Focuses* and captioned *"Qualitative summary only — no statistic in this report combines Focuses or members."*

Every build of a report with the narrative asks the provider again, and the text may differ between builds. The experiment (member) reports never include it.

## Where it is saved

Each time a narrative is written it is saved to `<project>_narrative.json` in the Project folder, beside the Project Report, replacing the previous one. The file records when it was written, the provider and model, and each paragraph together with a fingerprint of the Run Summary it summarised.

The narrative is a derivative of the analysis it describes, so **re-running the analysis deletes it**: once a Focus has been re-analysed, its paragraph no longer matches that Focus's Run Summary and is removed from the file the next time the narrative is read, together with the across-Focuses paragraph (which was written from it). When nothing is left, the file is deleted. A paragraph whose Focus has become Out of Date without being re-run stays in the file but is not used, just as the report does not present that Focus's results.

## What is sent to the provider

For each Focus, the app sends a compact text **digest** of that Focus's saved results, with instructions. The digest contains only:

- the member and Focus names, and the Experiment Type;
- the Focus's one-line description and its treatment names;
- the varying factors;
- individuals, deaths, censored (count and %) and number of treatments;
- the name of the Exclusion Group, if one is active;
- each Not Applicable action with its reason, and each analysis or figure Left Out by choice (so the AI does not read a missing test as a null result);
- the median survival table;
- the mean survival (restricted mean) table;
- the omnibus log-rank result (χ², df, p);
- the pairwise log-rank table (first 20 rows);
- for each Factorial Battery model: its formula, Reference Levels, interaction likelihood-ratio test and the first 12 rows of its coefficient table.

For the across-Focuses paragraph it sends the Project's question (from `project.yaml`) and the per-Focus paragraphs the AI has just written — not the numbers again.

**Never sent:** the data file or any individual-level records, census counts, chamber identities, file names or paths, life tables, figures, the hazard-ratio, Gehan-Wilcoxon, parametric or proportional-hazards tables, and any Focus whose results are not current. Your API key goes only to its own provider.

## The instructions the AI is given

Every request carries the same rules: summarise numbers that have already been computed; never compute, infer or estimate anything; never speculate about mechanism; write plain prose without headings or lists; and if a number is absent, say the analysis does not report it rather than guess. The across-Focuses request adds: describe agreement and disagreement qualitatively, and do not combine, average or meta-analyse the numbers or state a combined effect or p-value. The Standard Lifespan type also asks for median and mean lifespan per treatment, which log-rank comparisons were significant, and — when a factorial model is present — each main effect and whether the interaction was significant, relative to the Reference Levels.

## When it fails

Everything soft-fails. With no key configured the log says so and the report is built without a narrative. If the provider errors, declines, or its package is not installed, that Focus's paragraph (or the across paragraph) is skipped with a log line, and the rest continues.

## Reading it responsibly

- Treat the narrative as a draft summary. Check every number in it against the tables in the same section.
- The across-Focuses paragraph is qualitative only. No statistic in the app combines Focuses or members.
- A saved narrative describes the runs it was written from. After a re-run, write it again rather than reusing old text — the app deletes the paragraphs a re-run invalidated.

## See also

- [The Project Report](help:project-report)
- [The Run Summary](help:run-summary)
- [Script action reference](help:script-actions)
- [Analysed, Out of Date, Blocked and Orphaned results](help:focus-status)
