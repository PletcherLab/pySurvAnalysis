"""Entry point for the pySurvAnalysis pipeline.

Usage:
    python main.py                              # Launch the interactive UI
    python main.py <file.xlsx>                  # Load Excel file in UI
    python main.py <file.csv>                   # Load CSV file in UI (column dialog shown)
    python main.py --headless <file.xlsx>       # Headless Excel analysis
    python main.py --headless <file.csv>        # Headless CSV analysis (auto-detect columns)
    python main.py --headless <file.csv> \\
        --time-col Age --event-col Event \\
        --factor-cols IRS1 Foxo               # Headless CSV with explicit column names
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
        "input_file",
        nargs="?",
        help="Input file: Excel (.xlsx) with RawData/Design sheets, or CSV/TSV (.csv/.tsv)",
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
        help="Output directory for results (default: <input_stem>_results/)",
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
        help="CSV long format: factor column names. If omitted, all columns other than "
             "--time-col and --event-col are used as factors.",
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
        help="CSV wide format: path to a YAML file specifying the column-to-group mapping. "
             "Each entry should have keys: column, factor1_level, factor2_level, event (0 or 1).",
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
        if not args.input_file:
            parser.error("--headless requires an input file")

        from pysurvanalysis.pipeline import run_analysis

        assume_censored = not args.no_assume_censored

        # Load optional YAML column mapping for wide CSV
        col_mapping = None
        if args.col_mapping:
            import yaml
            with open(args.col_mapping, "r", encoding="utf-8") as fh:
                col_mapping = yaml.safe_load(fh)

        result = run_analysis(
            args.input_file,
            args.output_dir,
            assume_censored=assume_censored,
            time_col=args.time_col,
            event_col=args.event_col,
            factor_cols=args.factor_cols,
            csv_format=args.csv_format,
            col_mapping=col_mapping,
            factor_names=args.factor_names,
        )
        output_dir = args.output_dir or f"{Path(args.input_file).stem}_results"
        print(f"Analysis complete. Results saved to {output_dir}/")
        return

    # Launch UI
    from pysurvanalysis.ui import MainWindow, QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()

    if args.input_file:
        window.show()
        window.load_file(Path(args.input_file))
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
