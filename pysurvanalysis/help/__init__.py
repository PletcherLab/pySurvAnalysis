"""In-app help: an indexed manual and the ``?`` buttons that open it.

* :mod:`.manifest` — the table of contents (chapters → topic ids);
* :mod:`.pages`    — reading and searching ``topics/<topic-id>.md``;
* :mod:`.window`   — the manual window, :class:`HelpButton`, :func:`with_help`.

The Qt parts are imported on use, so the manifest and pages can be read
without a display.
"""

from .manifest import CHAPTERS, HOME, TITLES, analysis_topic, plot_topic

__all__ = ["CHAPTERS", "HOME", "TITLES", "analysis_topic", "plot_topic"]
