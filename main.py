"""Entry point for the pySurvAnalysis pipeline.

Usage:
    python main.py                         # Launch the interactive UI
    python main.py <file.xlsx>             # Run headless analysis and open UI with results
    python main.py --headless <file.xlsx>  # Run headless analysis only (no UI)
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
        help="Excel file (.xlsx) with RawData and Design sheets",
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
        help="Do not assume unaccounted individuals are right-censored. "
             "Cohort size = sum of deaths + censored per chamber.",
    )
    args = parser.parse_args()

    if args.headless:
        if not args.input_file:
            parser.error("--headless requires an input file")
        from pysurvanalysis.pipeline import run_analysis

        assume_censored = not args.no_assume_censored
        result = run_analysis(args.input_file, args.output_dir, assume_censored=assume_censored)
        print(f"Analysis complete. Results saved to {result.input_file.stem}_results/")
        return

    # Launch UI
    from pysurvanalysis.ui import launch_ui, MainWindow, QApplication

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()

    if args.input_file:
        # Auto-load the file, reading censoring default from PrivateData
        window.show()
        window.load_file(Path(args.input_file))
    else:
        window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
