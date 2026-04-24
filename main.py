"""Entry point for the pySurvAnalysis pipeline.

Usage:
    python main.py                              # Launch the interactive UI
    python main.py <project_dir>                # Load project directory in UI
                                                # (auto-discovers the .xlsx file)
    python main.py <file.xlsx>                  # Load Excel file in UI
    python main.py <file.csv>                   # Load CSV file in UI (column dialog shown)
    python main.py --headless <project_dir>     # Headless project directory analysis
    python main.py --headless <file.xlsx>       # Headless Excel analysis
    python main.py --headless <file.csv>        # Headless CSV analysis
    python main.py --headless <file.csv> \\
        --time-col Age --event-col Event \\
        --factor-cols IRS1 Foxo               # Headless CSV with explicit columns

Project directory mode
----------------------
When a directory is passed, pySurvAnalysis will:
  1. Locate the single .xlsx file inside the directory.
  2. Write all outputs into organised subdirectories:
       <project_dir>/plots/           — all plot images
       <project_dir>/statistics/      — CSV statistics tables
       <project_dir>/data_output/     — individual & lifetable CSVs
       <project_dir>/report.md        — full Markdown report
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description="pySurvAnalysis — Survival Analysis Pipeline",
    )
    parser.add_argument(
        "input_path",
        nargs="?",
        metavar="INPUT",
        help=(
            "Project directory (containing one .xlsx file), "
            "or a direct file path (.xlsx / .csv / .tsv)"
        ),
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run analysis without launching the UI",
    )
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=None,
        help=(
            "Output directory for results. "
            "Defaults to the project directory (for directory input) "
            "or <input_stem>_results/ (for file input)."
        ),
    )
    parser.add_argument(
        "--no-assume-censored",
        action="store_true",
        help="Excel only: do not assume unaccounted individuals are right-censored.",
    )
    # CSV-specific arguments
    parser.add_argument(
        "--time-col",
        type=str,
        default="Age",
        help="CSV only: column name for survival time (default: Age)",
    )
    parser.add_argument(
        "--event-col",
        type=str,
        default="Event",
        help="CSV only: column name for event indicator 0/1 (default: Event)",
    )
    parser.add_argument(
        "--factor-cols",
        nargs="+",
        default=None,
        metavar="COL",
        help=(
            "CSV long format: factor column names. "
            "If omitted, all columns other than --time-col and --event-col are used."
        ),
    )
    parser.add_argument(
        "--format",
        dest="csv_format",
        choices=["auto", "long", "wide"],
        default="auto",
        help="CSV format hint: auto (default), long, or wide.",
    )
    parser.add_argument(
        "--col-mapping",
        type=str,
        default=None,
        metavar="YAML_FILE",
        help=(
            "CSV wide format: path to a YAML file specifying the column-to-group mapping. "
            "Each entry should have keys: column, factor1_level, factor2_level, event (0 or 1)."
        ),
    )
    parser.add_argument(
        "--factor-names",
        nargs=2,
        default=None,
        metavar=("FACTOR1", "FACTOR2"),
        help="CSV wide format: the two factor names (required for wide format).",
    )
    args = parser.parse_args()

    if args.headless:
        if not args.input_path:
            parser.error("--headless requires an input path (file or project directory)")

        from pysurvanalysis.pipeline import run_analysis

        assume_censored = not args.no_assume_censored

        col_mapping = None
        if args.col_mapping:
            import yaml
            with open(args.col_mapping, "r", encoding="utf-8") as fh:
                col_mapping = yaml.safe_load(fh)

        result = run_analysis(
            args.input_path,
            args.output_dir,
            assume_censored=assume_censored,
            time_col=args.time_col,
            event_col=args.event_col,
            factor_cols=args.factor_cols,
            csv_format=args.csv_format,
            col_mapping=col_mapping,
            factor_names=args.factor_names,
        )

        p = Path(args.input_path)
        if p.is_dir():
            output_str = str(p)
        else:
            output_str = args.output_dir or f"{p.stem}_results"
        print(f"Analysis complete. Results saved to {output_str}/")

        # Print experiment summary
        es = result.experiment_summary
        if es:
            print(f"\nExperiment summary:")
            print(f"  Treatments:  {es.get('n_treatments', '?')}")
            print(f"  Chambers:    {es.get('n_chambers', 'N/A')}")
            print(f"  Total N:     {es.get('n_total', '?')}")
            print(f"  Deaths:      {es.get('n_deaths', '?')}")
            print(f"  Censored:    {es.get('n_censored', '?')} ({es.get('pct_censored', '?')}%)")
            print(f"  Time range:  {es.get('time_min', '?')} – {es.get('time_max', '?')} hours")
        return

    # ── Launch UI ──────────────────────────────────────────────────────────
    from pysurvanalysis.ui import MainWindow, QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()

    if args.input_path:
        window.show()
        window.load_file(Path(args.input_path))
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
