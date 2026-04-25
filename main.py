"""Entry point for pySurvAnalysis.

Subcommands::

    pysurvanalysis hub [project_dir]      # launch the Analysis Hub
    pysurvanalysis config [project_dir]   # launch the Config Editor
    pysurvanalysis qc [project_dir]       # launch the QC Viewer
    pysurvanalysis run <input> [opts]     # run the headless pipeline (writes report.md)

Without a subcommand, falls back to launching the Hub.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _add_run_args(p: argparse.ArgumentParser) -> None:
    p.add_argument(
        "input_path",
        metavar="INPUT",
        help="Project directory (one .xlsx) or a file path (.xlsx / .csv / .tsv).",
    )
    p.add_argument("--output-dir", "-o", default=None,
                   help="Output dir (defaults to project dir or <stem>_results/).")
    p.add_argument("--no-assume-censored", action="store_true",
                   help="Excel: don't assume unaccounted individuals are censored.")
    p.add_argument("--time-col", default="Age", help="CSV time column (default: Age).")
    p.add_argument("--event-col", default="Event", help="CSV event column (default: Event).")
    p.add_argument("--factor-cols", nargs="+", default=None, metavar="COL",
                   help="CSV long: factor column names.")
    p.add_argument("--format", dest="csv_format", choices=["auto", "long", "wide"], default="auto",
                   help="CSV format hint.")
    p.add_argument("--col-mapping", default=None, metavar="YAML",
                   help="CSV wide: YAML file with column-to-group mapping.")
    p.add_argument("--factor-names", nargs=2, default=None, metavar=("F1", "F2"),
                   help="CSV wide: two factor names.")
    p.add_argument("--exclusion-group", default=None,
                   help="Apply this exclusion group from remove_chambers.csv.")


def _cmd_hub(args: argparse.Namespace) -> int:
    from pysurvanalysis.apps.hub import main as hub_main

    sys.argv = [sys.argv[0]] + ([str(args.path)] if args.path else [])
    hub_main()
    return 0


def _cmd_config(args: argparse.Namespace) -> int:
    from pysurvanalysis.apps.config_editor import main as cfg_main

    sys.argv = [sys.argv[0]] + ([str(args.path)] if args.path else [])
    cfg_main()
    return 0


def _cmd_qc(args: argparse.Namespace) -> int:
    from pysurvanalysis.apps.qc_viewer import main as qc_main

    sys.argv = [sys.argv[0]] + ([str(args.path)] if args.path else [])
    qc_main()
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    from pysurvanalysis.pipeline import run_analysis

    col_mapping = None
    if args.col_mapping:
        import yaml
        with open(args.col_mapping, "r", encoding="utf-8") as fh:
            col_mapping = yaml.safe_load(fh)

    extra_excluded: set = set()
    if args.exclusion_group:
        from pysurvanalysis import exclusions

        ipath = Path(args.input_path)
        pdir = ipath if ipath.is_dir() else ipath.parent
        extra_excluded = exclusions.chambers_for_group(pdir, args.exclusion_group)
        if extra_excluded:
            print(f"Excluding {len(extra_excluded)} chamber(s) from group "
                  f"'{args.exclusion_group}'.")

    result = run_analysis(
        args.input_path,
        args.output_dir,
        assume_censored=not args.no_assume_censored,
        time_col=args.time_col,
        event_col=args.event_col,
        factor_cols=args.factor_cols,
        csv_format=args.csv_format,
        col_mapping=col_mapping,
        factor_names=args.factor_names,
        extra_excluded_chambers=extra_excluded,
    )

    p = Path(args.input_path)
    output_str = str(p) if p.is_dir() else (args.output_dir or f"{p.stem}_results")
    print(f"Analysis complete. Results saved to {output_str}/")

    es = result.experiment_summary or {}
    if es:
        print("\nExperiment summary:")
        print(f"  Treatments:  {es.get('n_treatments', '?')}")
        print(f"  Chambers:    {es.get('n_chambers', 'N/A')}")
        print(f"  Total N:     {es.get('n_total', '?')}")
        print(f"  Deaths:      {es.get('n_deaths', '?')}")
        print(f"  Censored:    {es.get('n_censored', '?')} ({es.get('pct_censored', '?')}%)")
        print(f"  Time range:  {es.get('time_min', '?')} – {es.get('time_max', '?')} hours")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="pysurvanalysis",
        description="pySurvAnalysis — survival analysis pipeline + apps",
    )
    sub = parser.add_subparsers(dest="cmd")

    for name, summary in (
        ("hub", "Launch the Analysis Hub (default)."),
        ("config", "Launch the Config Editor."),
        ("qc", "Launch the QC Viewer."),
    ):
        sp = sub.add_parser(name, help=summary)
        sp.add_argument("path", nargs="?", help="Optional project directory.")

    sp_run = sub.add_parser("run", help="Run the headless pipeline.")
    _add_run_args(sp_run)

    args = parser.parse_args()
    if args.cmd == "config":
        sys.exit(_cmd_config(args))
    if args.cmd == "qc":
        sys.exit(_cmd_qc(args))
    if args.cmd == "run":
        sys.exit(_cmd_run(args))
    # Default: hub
    if args.cmd is None:
        # Synthesise an argparse Namespace with .path = None
        args = argparse.Namespace(path=None)
    sys.exit(_cmd_hub(args))


if __name__ == "__main__":
    main()
