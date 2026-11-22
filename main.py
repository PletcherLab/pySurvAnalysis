"""Run pySurvAnalysis from a checkout: ``uv run python main.py [subcommand] …``.

The command line itself is :mod:`pysurvanalysis.cli`, inside the package, so
that the installed ``pysurvanalysis`` command (the wheel ships the package
alone) and ``python -m pysurvanalysis`` find the same code.
"""

from pysurvanalysis.cli import main

if __name__ == "__main__":
    main()
