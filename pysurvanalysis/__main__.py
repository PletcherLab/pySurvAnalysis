"""Allow ``python -m pysurvanalysis [hub|qc|run] [args]``.

Delegates to :func:`pysurvanalysis.cli.main`, the same entry point the
``pysurvanalysis`` console script uses.
"""

from .cli import main

if __name__ == "__main__":
    main()
