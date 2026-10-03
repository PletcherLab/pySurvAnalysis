# Installing and launching

pySurvAnalysis is a Python application with a Qt interface. It runs on Windows, macOS and Linux, needs **Python 3.13 or later**, and is installed into its own environment with [uv](https://github.com/astral-sh/uv). No separate Qt installation is needed: PyQt6 brings its own.

## Installing

1. Install uv once, if you do not have it:

```
# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Get the code and create the environment. From the folder you want it in:

```
git clone https://github.com/PletcherLab/pySurvAnalysis
cd pySurvAnalysis
uv sync
```

`uv sync` creates a `.venv` folder inside the repository and installs everything the app needs: lifelines (Kaplan-Meier, log-rank, Cox models), statsmodels (the RMST regressions), scipy, numpy and pandas, matplotlib and plotnine (figures), openpyxl (DLife workbooks), reportlab (PDF reports), PyQt6 with its theme and icon packages, PyYAML, and the anthropic and openai client libraries used only by the optional [AI narrative](help:ai-narrative).

## Updating

After pulling a newer version (`git pull`), run `uv sync` again so the environment matches. `uv sync --upgrade` moves every package to its newest compatible release.

## Launching

From the repository folder:

| Command | Opens |
|---|---|
| `uv run pysurv` | The Analysis Hub (also `uv run pysurv-hub`) |
| `uv run pysurv-hub path/to/Project` | The Hub with that Project, Batch folder or Experiment Directory already selected |
| `uv run pysurv-qc path/to/experiment` | The Chamber QC viewer on one experiment |
| `uv run pysurv-plots path/to/experiment` | The Plot Editor on one experiment |
| `uv run python main.py` | The Hub (the same program, through the script in the repository) |

The Hub opens with nothing selected unless a path is given: choose **Open project…** on the Project panel, or **Recent** in the top bar. Everything else — analysis, figures, reports, scripts, batches — is done from the Hub. The same work can also be run without the interface; see [Command-line use](help:command-line).

## The manual

This manual is part of the app. Open it with **Help** in the Hub's top bar or with **F1** in any window (it opens at the page for whatever you are looking at), or with any small **?** button beside a control. A copy of the whole manual is kept in the repository as `doc/user_guide.md`.

## See also
- [Your first analysis](help:quickstart)
- [Command-line use](help:command-line)
- [The Analysis Hub](help:hub)
- [Troubleshooting](help:troubleshooting)
