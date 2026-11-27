# `about:` says what a recording is, and no analysis reads it

Decided with labdata (its decision CB, `docs/LIFESPAN_ABOUT_PLAN.md`, on
2026-11-27), under the shared contract pyflic (its ADR-0024) and
PyTrackingAnalysis (its ADR-0019) already follow. It amends nothing here:
ADR-0011 (the Focus) and ADR-0013 (the Referenced Data File) stand as written.

## Context

The lab's catalogue, labdata, files each lifespan experiment — one DLife
workbook — as a **run**. The workbook states the design: its Design sheet's
columns after `StartTime` are the factors, and their values the levels. It does
not say what the experiment is for, who ran it, which flies, or what `mDilp`
or `20x` stand for. A colleague a year later, an agent reading the folder, or
the catalogue cannot recover any of that from the workbook.

On 2026-11-21 the lab head decided how the analysis packages and labdata meet:

- **Describe, then file.** A person describes a recording in its own folder
  with the package, usually before any Project exists. labdata then files the
  run from that folder, reading the description, and asks for nothing twice.
- **Every field is optional and in the person's own words.** labdata applies
  its own vocabulary when it files the run.
- **After filing, labdata's record is the truth,** and labdata rewrites the
  description to match it: in the run folder's copy and in every copy an
  analysis holds. The section can change on disk while one of this app's
  windows has the file open.
- **A new recording starts from an earlier one.** Recordings of one series
  share most of their description.

On 2026-11-27 he settled where the line falls for lifespans: "the focus sits
at the level of the analysis/project, not the run/rep … Several different
studies and analyses will likely point to the same pysurv run with different
foci." A labdata run folder holds the workbook and a `survival_config.yaml`
whose `about:` describes it. Each analysis is a Project whose Member
Experiment reads that workbook as a Referenced Data File (ADR-0013) and keeps
its own `survival_config.yaml`, with its own Focuses. The run's config is
never analysed.

Before this work a config read by Windows Notepad's "ANSI" save — one accented
name in it — raised a bare `UnicodeDecodeError` naming no file, and blocked
the member or the whole Project. A description in a person's own words makes
that likely, so it is fixed here too.

## Decision

- **One optional top-level section, `about:`,** of a recording's
  `survival_config.yaml`. Every field is optional, and so is the section:
  `title` (one line; 60 characters fit a list), `purpose`, `experimenter`,
  `series`, `organism`, `sex` (a list), `age_at_start`, `protocol` (`name`,
  `version`, `link`), `notes`, and `factors`, which gives each factor of the
  data file a `kind` (genotype, treatment, diet, condition, sex, other) and
  each level a line of meaning — text, or a mapping whose `definition` is that
  text. `run:` and a level mapping's `term`, `label` and `role` are the
  catalogue's: kept, shown, never edited. A key the app does not know is kept.

- **No analysis reads it.** No summary, statistic, Focus, cache, Run Summary,
  Divergence Note or Out of Date verdict depends on it. None of it is put on a
  report, and the AI narrative is built from the saved Run Summaries, so none
  reaches an AI provider. A config without the section loads, validates and
  analyses as before, and every file the app writes for it is byte-identical
  ("no key, no change"), apart from the encoding fix below.

- **It never holds analysis settings, and is never inherited.** Focuses,
  scripts, the Exclusion Group and `omit:` stay in each member's own config,
  where each analysis keeps its own. `about` joins `NEVER_INHERITED`, so
  `merge_defaults` never passes one down and `Project.create` never seeds one;
  a `defaults: about:` written by hand is ignored, with a warning.

- **One module, mirrored.** `pysurvanalysis/about.py` is a verbatim copy of
  pyflic's `pyflic/base/about.py` at `30211ab`, the same copy
  PyTrackingAnalysis keeps. It differs only in its header and in the word
  "pyflic" before pyflic's ADR numbers, and `tests/test_about_mirror.py` pins
  it with the origin's digest, so a change made only here fails. Its
  docstrings speak pyflic's language (`flic_config.yaml`, Members, a design
  declared in the config); the header says how to read them here. Its
  messages are translated where they are shown: "which
  experimental_design_factors does not declare" becomes "which is not a
  factor of the data file", and `meaning_spread`'s closing words about pooled
  results are dropped, because members here are never pooled (ADR-0001).

- **Warnings, never errors.** `config.config_warnings` (the channel
  `data_file:` already used) reports `about.about_problems` through
  `config.check_about`, against the factors and levels of the folder's own
  data file. That file is found and read the way the classifier reads it
  (`layout.folder_design`: `data_location`, then the Design sheet alone),
  never by constructing an Experiment. A config without the key reads nothing.
  When the data file cannot be read, the section is checked on its own, so no
  factor is called undeclared for want of a file. `validate_config` is not
  touched. Validate YAMLs, `pysurvanalysis run` and the editor show the
  warnings.

- **Every writer keeps the About on disk.** `config.save_config` writes the
  `about:` the file holds at save time, read again then, wherever its
  caller's config came from; a file with none gets none, and only a file that
  does not exist yet takes the caller's own. A writer that sets the section
  passes it (`about=`). This covers every writer of the file:
  - `SurvivalExperiment.save_focuses` (and through it `rename_focus`,
    `apply_focus_edits`, `repair_focus`, `delete_focus`), `materialize_focuses`
    and `set_included` already read the file at save time
    (`_config_on_disk`); `save_config` now guarantees it for the section.
  - The Hub's **Set active group** and its, the Experiment configs dialog's
    and the Batch Preflight's **Set data file…** read the file just before
    writing, and go through `save_config`.
  - The Script Editor splices `scripts:` into the file as read at save time,
    through `write_yaml`; `about:` rides along unchanged.
  - `Project.add_member`, `adopt_directory`, `adopt_data_file`,
    `reference_data_file` and `upgrade.apply` write only a config that does
    not exist yet, and none carries an About. **Reference data file…** writes
    none: the recording's description stays in its own folder.
  - The Hub's **Copy config from…** gives the new member the **shared About**
    of the config it copies (`about.shared_about`, limited to the new
    member's factors and levels when its workbook can be read): never the
    title, the purpose, the notes or `run:`. It still copies byte for byte
    when nothing has to stay behind.
  - **Add directory…** copies a whole recording folder in, About included:
    it is that recording, not a new one started from it.

- **`pysurv-config <folder>` edits it.** A new app (`apps/config_editor.py`,
  also `pysurvanalysis config`) that opens a recording folder — a workbook at
  its root or in `data/`, or named by `data_file:`, with or without a config —
  and has two tabs. **About** holds the fields, a 60-character count on the
  title, `run:` read-only, a kind per factor and a meaning per level, the
  factors and levels being the workbook's. **Design** shows the workbook's
  design read-only: factors and levels, chambers with their sample sizes,
  ChamberFlags' exclusions. **Start from another recording…** fills in the
  shared About of a chosen config, limited to this workbook's factors and
  levels. **Save** writes `about:` alone (`config.write_about`): every other
  key is taken from the file as it is then, nothing is seeded, a folder with
  no config gets one holding `about:` alone, and a blank section is not
  written. Only a level's meaning is edited (`about.with_meaning`), so a
  mapping keeps its other keys. A section nobody touched is not rewritten, so
  opening and saving a config does not strip its comments.
  - Three fields are already typed in whenever the file gives none, because
    they are what the lab's lifespans almost always are: Organism
    *Drosophila melanogaster*, Age at start *2-3 days old*, Protocol
    *DLife Lifespan* (Scott, 2026-11-27, departing from P15's "opens with
    blank fields"). They belong to the form as opened, so a folder never
    looks changed for them and nothing is written until something is
    edited; then they are saved like any field, and clearing one leaves it
    out. A value the file gives is never replaced.

- **A change on disk is never overwritten silently.** The editor keeps the
  config's bytes as it last read or wrote them and compares before saving. If
  they differ, it says which sections differ and offers to reload (the edits
  are lost, nothing is written), to overwrite (the About from the window,
  every other section as it is now) or to cancel, the default. Compared by
  content, as ADR-0010 compares runs.

- **Reachable from the Hub.** Right-click a member in the members table, or
  select it in *Experiment configs…*: **Edit About…** opens the same window on
  the member's folder. A member with no About opens blank, apart from
  three of the lab's usual values (below).

- **A Project warns when members describe one level differently**
  (`about.meaning_spread`, as `Project.about_warnings`, which
  `Project.warnings` includes). Their Focus sections sit side by side in the
  Project Report under one level name, so a reader would take them for one
  thing. Never an error, and never on the report.

- **A config is read as UTF-8, with or without a BOM, then as
  Windows-1252,** the rule `exclusions` already applies to its CSV. Bytes
  that are neither raise `ConfigEncodingError`, a `ValueError` naming the
  file, so every caller that lists a bad config lists this one. Every save
  writes UTF-8.

- **The app stays unaware of labdata.** It reads no labdata file and gains no
  dependency. `run:` is the catalogue's id; it has nothing to do with a Batch
  Run.

Also built with this, beside the contract: a DLife workbook whose
`PrivateData.IsCompleted` is 0 draws a warning in the same channel — its
survivors are censored at the last census, so its results are provisional.
**Reference data file…** still names the member after the workbook without
asking: a name prompt there would be a modal step that every existing caller
of the action, the tests among them, would have to answer. The domain method
already takes a name.

Rejected:

- **Putting Focuses, or any analysis setting, into the About.** Several
  analyses of one recording ask different questions of it; a Focus beside the
  workbook would be one analysis's choice imposed on every other.
- **A sidecar file.** The catalogue reads the description where the
  configuration is, and two files per recording drift.
- **Describing the recording in `project.yaml`.** A recording is described
  before a Project exists, and several Projects analyse one recording.
- **Constructing an Experiment to read the design.** Loading one creates
  `analysis/` and `qc/`, and the run folder must gain nothing but its config.
- **Reading a Windows-1252 file as Latin-1 when that fails too,** as the CSV
  reader does. A config that decodes to nonsense would be rewritten as
  nonsense by the next save; an error naming the file is better.
- **A whole-file Config Editor,** as PyTrackingAnalysis has. A member config
  here is a dozen hand-editable lines, and the one section a person cannot be
  expected to type correctly — with a catalogue rewriting it — is the About.

## Consequences

- The mirrored module must be copied again whenever pyflic's changes; until
  then the digest test names the commit this copy is from, and MIRRORED.md
  lists it.
- `save_config` re-reads the file it is about to write. That costs one read
  per save, and makes the About on disk win over any caller's stale copy.
- Every writer that rewrites the file whole goes through PyYAML, so comments
  are still lost on a full rewrite. That is unchanged; the editor alone skips
  a save that would change nothing.
- `Project.warnings` now includes the meaning spread. Nothing puts
  `Project.warnings` on a report today, and nothing may: About text never goes
  on one.
- A config that held `about:` and is copied in by **Add directory…** keeps it
  whole. labdata rewrites the copies analyses hold, so the duplicate is kept
  in step there.
- Untested on Windows: the suite runs on Linux only.
