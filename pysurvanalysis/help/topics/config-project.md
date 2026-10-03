# project.yaml and Project Defaults

A **Project** is a directory with a `project.yaml` at its root. Each immediate subdirectory that holds a `survival_config.yaml` is one of its **Member Experiments**. `project.yaml` names the Project, states the question its members address, holds the **Project Defaults** every member inherits, and stores the Project's scripts. A Project never pools its members: each is analysed on its own, and the Project Report binds their results side by side.

## In the app

- **Create project…** and **Initialize existing directory…** (Project panel, Create/Load card) write a new `project.yaml`.
- **Edit config…** opens the same editor on the open Project. It has fields for the name, the question, the Experiment Type and the `global:` defaults. Everything else in the file (scripts, other default sections, keys from a newer version) is carried through unchanged when you save.
- **Validate YAMLs** checks `project.yaml` and every member's config.

## A complete example

```yaml
name: Crowding study
question: Does larval density change adult lifespan, and does it depend on sex?
defaults:
  experiment_type: standard_lifespan
  global:
    time_unit: days
    time_label: Age (days)
    assume_censored: true
    min_n_per_chamber: 5
  input:
    format: excel
  exclusions:
    group: default
  omit:
    analyses: [parametric_aft]
scripts:
- name: batch
  notes: What a Batch Run runs here unless another script is designated.
  steps:
  - action: run_in_experiments
    script: Standard analysis
  - action: render_publication_figures
  - action: project_report
experiment_scripts: []
```

## Top-level keys

| Key | Type | Default | Effect |
|---|---|---|---|
| `name` | string | the directory name | The Project's display name. |
| `question` | string | empty | The one-line question the members address. It is shown on the Project Report cover and read by the AI narrative. |
| `defaults` | mapping | type defaults | **Project Defaults**: settings every member inherits unless it states its own. |
| `scripts` | list | the `batch` script | Project Scripts. A Batch Run executes `batch` unless another is designated. If the key is missing entirely, `batch` is added on the next save. An empty list is left alone, and such a Project fails a Batch Run that designates no script (the Project card still offers the built-ins). See [Project Scripts](help:project-scripts). |
| `experiment_scripts` | list | `[]` | Central Experiment Scripts. A script here serves every member and takes precedence over a member's own script of the same name — in a Batch Run, in `run_in_experiments` and on the Hub's Experiment scripts card alike. |

The Project Report is written to `<project>/<directory name>_report.pdf` (and `.md`). Publication Figure specs and styles live in `<project>/plot_specs.yaml`.

## Keys inside defaults:

| Key | Type | Default | Effect on members |
|---|---|---|---|
| `experiment_type` | string | `standard_lifespan` | The Project's [Experiment Type](help:experiment-types). This is the one value checked across members: every member must resolve to the same type. |
| `global` | mapping | the type's defaults | Merged key by key. See [The global: section](help:config-global). |
| `input` | mapping | none | Merged key by key. See [The input: section](help:config-input). |
| `exclusions` | mapping | none | Merged key by key. `group:` sets the default active Exclusion Group name. Each member has its own `qc/remove_chambers.csv`, so the name only removes chambers in members that define that group. |
| `omit` | mapping | none | Merged per list (`analyses`, `plots`). See [The omit: section](help:config-omit). |
| any other key | any | none | Inherited as a whole value when the member does not state the key. (Experiment Scripts are the exception: share them through `experiment_scripts:` above, not `defaults:`.) |
| `focuses` | — | — | **Never inherited.** Validation warns and the key is ignored. |
| `factors` | — | — | **Legacy.** Validation warns. Members that inherit it become an `Interaction` Focus. |

## How inheritance works

When a member is loaded, its `survival_config.yaml` is merged over `defaults:`:

1. Start from every `defaults:` key except `focuses`.
2. For each key the member states:
   - `global`, `input`, `exclusions` and `omit` (when both sides are mappings) are merged key by key. The member's value wins for each key it states.
   - Any other key replaces the default wholesale.

Defaults are a *seed and template*, not an authority. A member that states a value keeps it. A member that says nothing follows the next edit to `project.yaml`. That is why members created by the app are deliberately minimal: restating a default in a member freezes today's value there. When you copy a config in from another member, the log names any sections that are now stated in the member and so no longer follow the Project.

### Why Focuses are never inherited

Members of one Project rarely share factors. An inherited Focus would be a Blocked Focus in every member it does not fit, and editing it would put every member's results Out of Date at once. To share a design, use **Copy Focuses from…** in the Focus window, which checks each Focus against the receiving member's data before writing it.

## What is enforced, and what is only declared

- **Enforced:** every member's Experiment Type must match the Project's. A mismatch is a validation problem, and a config of the wrong type is refused when copied into a member. There is only one type today, so this check cannot currently fail.
- **Declared, not enforced:** differences in `time_unit`, `assume_censored` and the active Exclusion Group are legal. The Project Report lists them in its **Divergence Note**, and **Validate YAMLs** prints each as `divergence — …`. Differences in factors and Focuses are expected and appear in the Focus Inventory.

## Validation messages from project.yaml

| Message | Fix |
|---|---|
| `` project.yaml: `defaults: focuses:` is ignored — a member never inherits Focuses. Copy them into the members that share the design (the Focus window's Copy Focuses from…). `` | Remove `focuses:` from `defaults:` and copy Focuses into the members that need them. |
| `` project.yaml: `defaults: factors:` predates Focuses. Members that inherit it become an `Interaction` Focus on their next analysis; remove it once each has been analysed. `` | Analyse each member once (so the Focus is written into its config), then delete `factors:` from `defaults:`. |
| `project.yaml: Unknown experiment_type '…'. Known types: standard_lifespan, or omit the key.` | Fix or remove `defaults: experiment_type`. |
| `<member> is a <type> but the Project's type is <type>. Every Member Experiment must share the Project's Experiment Type …` | Make the member's `experiment_type` match, or remove it so it inherits. |

## See also

- [survival_config.yaml reference](help:config-experiment)
- [Creating and opening a Project](help:project-create)
- [The Experiments card — members](help:project-members)
- [Experiment Types](help:experiment-types)
- [Validating configuration](help:validation)
- [Project Scripts](help:project-scripts)
