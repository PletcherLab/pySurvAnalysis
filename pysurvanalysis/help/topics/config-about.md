# The about: section and pysurv-config

A lifespan recording's folder can say what the recording is, in your own words: why it was run, who ran it, the flies, the protocol, and what each level of each factor means (`mDilp` is which cross, `20x` is which density). That description goes in an optional `about:` section of the folder's `survival_config.yaml`.

**No analysis reads it.** No number, figure, Focus, Run Summary or "re-run needed" verdict depends on the section. It is never printed on a report and never sent to an AI provider. A config without it behaves exactly as before. Every field is optional, and so is the section.

The design itself is not described here: the factors and levels are the workbook's, read from its Design sheet (see [Input data formats](help:data-formats)). The About only says what they mean.

## The section

```yaml
about:
  run: R-20261127-scott-01        # written by a catalogue; shown, never typed
  title: Lifespan on two diets, replicate 1
  purpose: Whether InR knockdown changes the response to dietary restriction.
  experimenter: scott
  series: diet-inr-2026
  organism: Drosophila melanogaster
  sex: [female]
  age_at_start: 2-3 days
  protocol: {name: DLife lifespan, version: "4", link: https://example.org/dlife}
  notes: Incubator 3; food changed every 2-3 days.
  factors:
    Genotype:
      kind: genotype               # genotype | treatment | diet | condition | sex | other
      levels:
        wCS: w1118 (Canton-S background)
        mDilp: Dilp2-3-5 deletion
    Diet:
      kind: diet
      levels:
        AL: 15% SY
        DR: 5% SY
```

| Field | What it holds |
|---|---|
| `title` | One line. Up to 60 characters fit on one line in a list of recordings; a longer title is still saved, with a warning. |
| `purpose`, `notes` | Free text. |
| `experimenter`, `series`, `organism`, `age_at_start` | A word or a short phrase. A series names recordings that belong together. |
| `sex` | A list such as `[female]` or `[female, male]`. One word reads as a list of one. |
| `protocol` | `name`, `version` and `link`. Plain text reads as the name. |
| `factors` | For each factor of the workbook: its `kind`, and a few words for each level. A level's entry may also be a mapping whose `definition:` is that text. |
| `run` | The recording's id in the catalogue that filed it. Written by the catalogue only. |

A catalogue that files the recording, such as the lab's labdata, may rewrite the section afterwards to match its own record. It adds `run:` and, inside a level's mapping, keys such as `term:`, `label:` and `role:`. pySurvAnalysis keeps every key it does not edit, and every writer in the app writes back the section the file holds at that moment, never an older copy it read earlier.

## pysurv-config: the About Editor

Open a recording folder with:

```
uv run pysurv-config path/to/recording
```

The folder holds a DLife workbook at its root or in `data/`, or names one with `data_file:`. It does not need a `survival_config.yaml` yet. You can also pass the workbook itself, or start with no path and use **Open folder…**. The recording folder is the one whose root holds the config: given the workbook in `data/`, or the `data/` folder itself, the editor opens the folder above it, because a config inside `data/` is never read. If it finds one there, left by an earlier save, it says so; when the root has no config yet, it shows that copy's About so that **Save** writes it to the root. The copy in `data/` is left for you to delete.

The window has two tabs.

- **About** holds the fields above. Three are already typed in when the file gives none, because they are what the lab's lifespans almost always are: **Organism** *Drosophila melanogaster*, **Age at start** *2-3 days old* and **Protocol** *DLife Lifespan*. Change or clear them as needed. They are saved only with the rest of the About, once you have edited something; a folder you open and close untouched gains nothing. The title shows its length against 60. `run:` is shown when present and cannot be typed. Under *Factors and levels* there is one row per factor of the workbook for its kind, and one row per level for what it means. A factor or level the file describes that the workbook lacks has no row; it is kept as it is and listed under *Checks*.
- **Design** shows what the workbook says, read-only: the data file, its factors and their levels in the order the Design sheet first lists them, each chamber with its sample size and levels, and the chambers its ChamberFlags sheet excludes. A workbook whose PrivateData sheet says the lifespan is not finished (`IsCompleted` is 0) is flagged here.

**Start from another recording…** fills in what recordings of one series share, from another recording's `survival_config.yaml`: the experimenter, the series, the organism, the sex, the age at start, the protocol, and each factor's kind and each level's whole entry, for the factors and levels this workbook has. The title, the purpose and the notes stay this recording's own, and `run:` is never taken. Nothing is written until you save.

**Save** writes the `about:` section and nothing else. Every other key of the file (`focuses:`, `scripts:`, `exclusions:`, `omit:`, `global:` and any other) is taken as it is on disk at that moment and kept. A folder with no config gets a `survival_config.yaml` holding `about:` alone. A field left blank is not written, and if every field is blank there is no `about:` at all. Saving with nothing changed writes nothing.

If the file changed on disk since the window read it (a catalogue rewrote the description, or the Hub saved a Focus), **Save** says so, names the sections that differ, and offers **Reload from disk** (your edits in the window are lost and nothing is written), **Overwrite** (the About from the window, every other section as it is now) or **Cancel**, the default.

The editor never loads the folder as an experiment, so it never creates `analysis/`, `qc/` or any other file. It edits only the config: the workbook is never written.

## From the Hub

- Right-click a member in the Project panel's members table and choose **Edit About…**, or select it in *Experiment configs…* and press **Edit About…**. Either opens pysurv-config on that member's folder. A member with no About opens with blank fields, apart from the three defaults below.
- **Copy config from…**, offered after **Create experiment…**, copies another member's config into the new one. Of its `about:` only the shared part comes along: never the title, the purpose, the notes or `run:`. Its factors and levels are limited to the new member's workbook when that can be read.
- **Reference data file…** writes no About into the member. A recording described in its own folder keeps that description there; each analysis that reads it holds its own config, with its own Focuses.

An About belongs to one recording. A Project's `defaults:` never carries one (an `about:` written there is ignored, with a warning), and no member inherits it.

## Warnings, never errors

Nothing in `about:` stops a load, a save or a run. What is odd about it is a warning, listed by **Validate YAMLs**, the command line's `run`, and the editor's *Checks*:

| Warning | Meaning |
|---|---|
| `about.title is 72 characters; keep it to 60 …` | The title will not fit on one line of a list. |
| `about.<field> should be text` | A list or a mapping where a line of text belongs. |
| `about.factors.<factor>.kind is 'strain'; expected one of …` | Use one of the six kinds. |
| `about.factors names '<factor>', which is not a factor of the data file` | The workbook has no such factor. Check the spelling against the Design sheet. |
| `about.factors.<factor> describes level '<level>', which is not a level of <factor> in the data file` | The workbook has no such level. |
| `about: members describe <factor> '<level>' differently (…)` | Two members of a Project say different things about the same level. Their Focus sections sit side by side in the Project Report under the same name, so a reader would take them for one. |

When the workbook cannot be read, the section is still checked, but no factor or level is called undeclared.

## Text encoding

A `survival_config.yaml` is read as UTF-8, with or without a Byte Order Mark. A file saved by Windows Notepad in its older "ANSI" encoding (Windows-1252), say with an accented name in `purpose:`, is read too. Every save writes UTF-8. A file that is neither stops with an error naming the file.

See also: [survival_config.yaml reference](help:config-experiment), [The Experiments card](help:project-members), [Validating configuration](help:validation).
