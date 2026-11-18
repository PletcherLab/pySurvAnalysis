# A member may read its data file where it lies; the Project owns everything else

Amends [ADR-0008](0008-three-ways-a-member-arrives.md) ("copy in, never
reference") and extends ADR-0009's "one recording, one member" rule from
member folders to data files. The rule is ported from PyTrackingAnalysis's
ADR-0018 (`referenced-data`, `@e91adf5`); this app keeps its existing
`data_file:` key instead of adding that app's `data_folder:`.

## Context

A lab may keep every data collection in a permanent folder of its own, locked
after registration: nothing under it may change, appear or disappear. A
study's analysis lives somewhere else, and several studies analyse the same
recording with different settings. Here a Project is that analysis, and its
members could not do this. ADR-0008 made every way in copy the workbook into
the Project, and a lab that forbids raw-data copies cannot use that.

ADR-0008 rejected referencing because "a member analysed in place from
outside the Project would write `analysis/`, `qc/` and `figures/` outside the
Project". That concern is about where the **member folder** is, not where the
**data** is. `data_file:` already resolved relative to the member folder, and
every output already went to that folder. When `data_file:` names a workbook
elsewhere, the member folder and everything written for it stay inside the
Project. Only the workbook is outside, and it is only read.

## Decision

- **A member may reference its data file.** The Project owns the member
  folder and everything written to it. The referenced file is only ever read.
  A `data_file:` that resolves outside the member folder is a **Referenced
  Data File**. The key is the existing one, and its meaning is unchanged.

- **Inside the member folder, `data_file:` keeps its old job.** It names one of
  several files in the member's own folder, which is what **Set data file…**
  writes. That behaviour stays exactly as it was, including other data files
  beside the named one. "Inside" means inside by name (`data/x.xlsx`, even when
  `data/` is a symlink) or by real path.

- **Relative to the member folder, with forward slashes.** An example is
  `../../../../../runs/lifespan/2026/R-20261020-asmith-01/data/R-20261020-asmith-01.xlsx`.
  The path is resolved by the operating system: `realpath` of the joined path,
  so `..` is taken after any symlink, as `open()` takes it. Windows also
  accepts backslashes. An absolute value works, but **Validate YAMLs** and
  `pysurvanalysis run` warn that it will not travel, and they warn about a
  backslash for the same reason. A warning is a separate channel
  (`config.config_warnings`). It never blocks a run, because a config
  problem is fatal and an absolute path is fragile, not wrong.

- **Never inherited.** `data_file` joins `focuses` in `NEVER_INHERITED`,
  because it names one member's file. The loader used to honour a
  `defaults: data_file:` while the classifier ignored it, so the two could
  disagree. Now neither honours it, and `Project.validate` says that it is
  ignored.

- **No key, no change.** Other labs use this app. A config whose text never
  mentions `data_file` is not even parsed by the resolver. For it, every code
  path, output and message is what it was. The run summary, the reports and
  the load message gain their data-location lines only for a Referenced Data
  File.

- **One resolver: `layout.data_location`.** It answers "which file does this
  member read?" from the member folder and its own config. Without a key it
  returns the loader's search of `data/` and then the root. With a key it
  returns the named file, plus any problem the loader would refuse it for.
  Every place that finds a member's data calls it:
  - the loader (`SurvivalExperiment.data_file`);
  - `layout.classify` and `layout.members_in`, and through them Batch
    discovery, the preflight, Validate YAMLs and the Experiment configs dialog;
  - `Project.member_dirs`;
  - `upgrade`;
  - the QC viewer's bare-folder load.

  So the classifier and the loader cannot disagree.

- **Nothing is written at a data location.** Every output goes to the member
  folder (`analysis/<focus>/`, `qc/`, `figures/<focus>/`) or to the Project
  folder, exactly where it went before. The run refuses a broken reference
  before it creates `analysis/` or `qc/`. Direct mode
  (`pysurvanalysis run <file>`) still writes `<stem>_results/` beside its input
  file, and no member's run can reach it: every Experiment Script and Hub
  action runs with the experiment in hand. `upgrade` is a no-op for any folder
  that has a config.

- **Conflicts are errors, not guesses.** A member whose `data_file:` resolves
  outside its folder is blocked, and the loader raises `DataLocationError`
  naming the key, the value as written and the resolved path, in three cases:
  - **conflict:** the member folder also holds a data file of its own. That is
    a file `data_candidates` would offer, in `data/` or at the root, never a
    hidden file, a `~$` lock file or `remove_chambers.csv`. The question is
    which file is the experiment. An empty `data/` holds nothing, so it is not
    a conflict.
  - **no data:** the named file does not exist.
  - **no data:** the named file is a folder.

  `conflict` is a new status, not `ambiguous`. That status's one-click fix
  names one of the *local* files, which would settle the question by guessing
  against the reference. A conflict has no button, and the fix is a decision
  made by hand.

- **One data file, one member.** ADR-0009 drops a symlinked copy of a member
  by real path. Two members whose data files resolve to one file
  (`normcase(realpath(...))`, for the case-insensitive share) are now one as
  well. The first in sorted order is kept, and the other is reported by name:
  - in `members_in`, as a blocked member with the new status **duplicate**
    and no fix button, so the preflight, Validate YAMLs and the Batch Run
    summary list it;
  - in the Hub, as a red row in the members table;
  - in `Project.duplicates()` and `Project.duplicate_notes()`;
  - on the Project Report's cover.

  `Project.member_dirs` and `members_in` share the rule (`layout.DataLocations`),
  so they cannot disagree about which member is the duplicate. The rule applies
  only when at least one of the two uses `data_file:`. Two plain members whose
  `data/` folders are one folder by symlink are both still analysed, because
  "no key, no change" outranks the tidier rule. Projects never pool
  (ADR-0001), so a duplicate here means the same recording bound into one
  Project Report twice, not double-counted statistics. Nothing is compared
  across Projects: two Projects reading one recording with different settings
  is the point of the feature.

- **Say where the data came from.** For a Referenced Data File only:
  - `run_summary_<focus>.json` gains `data_location: {written, resolved}`;
  - the Focus report's cover gains a *Data location* line;
  - the Project Report gains a *Data files read from outside the Project*
    table;
  - the pipeline's load message and the Hub's "Loaded …" line give both
    forms.

- **A way in through the Hub.** `Project.reference_data_file(source,
  name=None)` sits beside `adopt_directory` and `adopt_data_file`:
  - It validates the workbook as **Add experiment** does.
  - It creates the member folder, named after the file unless a name is given.
  - It writes a minimal config with a relative `data_file:`.
  - It never copies or moves the file.

  It refuses, writing nothing:
  - a file inside the Project tree, which is **Add experiment**'s job;
  - a file with no relative path from the Project (another drive on Windows,
    where `os.path.relpath` raises);
  - a destination that already exists;
  - a file a member already reads.

  The Hub's **Reference data file…** button sits under the divider with the
  other two ways in from outside (ADR-0010), and only calls the method.
  **Add directory** refuses a folder whose config references a file outside
  it, because copying the folder would change what a relative path points to.

### Rejected

- **A second key, as upstream's `data_folder:`.** `data_file:` already names
  a file and already resolves against the member folder. A second key would
  be two ways to say one thing, and would raise the question of which one wins.
- **A Project-level data root, or a registry of members' files.** It would
  split one member's definition across two files, and the Project Defaults
  would carry per-member facts.
- **Symlinking `data/`.** Symlinks on a Windows SMB share need privileges most
  users lack. A symlinked `data/` also looks exactly like a local one, so
  nothing could tell that the data is locked.
- **The strict duplicate rule** (two members reading one file are duplicates
  even without the key). It would change what an existing Project analyses,
  and it would be a one-line change in `DataLocations.claim`.

## Consequences

- **A Project no longer always holds its data.** Identity still lives in the
  Project folder: members are still the subdirectories with a config. But a
  copy of the analysis folder without the recordings finds its referencing
  members blocked, each naming the path it resolved. Moving the whole tree
  keeps every relative reference working.
- **Classification parses YAML a little more often.** `layout.members_in` and
  `Project.member_dirs` now read each member config's text, and parse it only
  when it mentions `data_file`.
- **An inherited `data_file:` is now ignored.** A Project that set one in
  `defaults:` finds each member searching its own folder, and
  `Project.validate` names the key.
- **Windows path prefixes.** Paths are displayed and recorded exactly as
  `realpath` returns them. On Windows that may begin with `\\?\` (paths over
  260 characters) or come back in `\\server\share` form for a mapped drive. It
  still reads correctly. This is untested, because the suite runs on Linux.
- **No alternate config here.** Upstream's loader can read a config other than
  the standard one, so its key and its classifier could read different
  files. This app's loader and classifier both read `survival_config.yaml`.
- **A plain member can be the duplicate.** If a member sorted earlier
  references a file inside a plain member's folder, the plain member is the
  one reported.
- **Two new blocked statuses, `duplicate` and `conflict`, with no fix
  button.** The fix for each is deciding which member, or which file, is the
  experiment.
