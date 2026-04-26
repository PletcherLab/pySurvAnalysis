"""Allow ``python -m pysurvanalysis [hub|qc|run] [args]``.

Delegates to :func:`main.main`, the same entry point the ``pysurvanalysis``
console script uses.
"""

from main import main

if __name__ == "__main__":
    main()
