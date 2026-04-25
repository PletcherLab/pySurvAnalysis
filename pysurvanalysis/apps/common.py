"""Shared app utilities: background worker, log capture, figure capture.

Vendored from PyTrackingAnalysis with no functional changes.
"""

from __future__ import annotations

import io
import traceback
from contextlib import contextmanager, redirect_stderr, redirect_stdout
from typing import Any, Callable, Iterable

from PyQt6.QtCore import QThread, pyqtSignal


class _SignalIO(io.TextIOBase):
    """Writable text stream that fires a Qt signal on every ``write()``.

    When used with :func:`contextlib.redirect_stdout` / ``redirect_stderr``
    inside a ``QThread``, Qt auto-queues the signal across the thread
    boundary, so the connected slot runs safely on the GUI thread.
    """

    def __init__(self, signal: pyqtSignal) -> None:
        super().__init__()
        self._signal = signal

    def write(self, text: str) -> int:  # noqa: D401 — io API
        if text:
            self._signal.emit(text)
        return len(text)

    def flush(self) -> None:  # noqa: D401
        pass


class TaskWorker(QThread):
    """Runs *fn* on a background thread with stdout/stderr captured.

    *fn* should return a string (shown in the success message), a list of
    ``(title, figure)`` tuples (each becomes a PlotDock tab), or ``None``.
    Exceptions are logged and surface as ``failed`` with a short message.
    """

    finished_ok = pyqtSignal(str)
    failed = pyqtSignal(str)
    log_text = pyqtSignal(str)
    figure_ready = pyqtSignal(str, object)

    def __init__(self, task_name: str, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.task_name = task_name
        self._fn = fn

    def run(self) -> None:  # noqa: D401 — QThread API
        sio = _SignalIO(self.log_text)
        try:
            with redirect_stdout(sio), redirect_stderr(sio):
                result = self._fn()
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, tuple) and len(item) == 2:
                        self.figure_ready.emit(str(item[0]), item[1])
                self.finished_ok.emit(f"{self.task_name} complete.")
            elif isinstance(result, tuple) and len(result) == 2:
                self.figure_ready.emit(str(result[0]), result[1])
                self.finished_ok.emit(f"{self.task_name} complete.")
            else:
                msg = str(result) if result is not None else f"{self.task_name} complete."
                self.finished_ok.emit(msg)
        except Exception:  # noqa: BLE001
            self.log_text.emit(traceback.format_exc())
            self.failed.emit(f"{self.task_name} failed — see log above for details.")


@contextmanager
def capture_figures() -> Iterable[list]:
    """Collect every ``Figure`` passed through ``plt.show()`` while active."""
    import matplotlib.pyplot as plt

    figures: list = []
    original_show = plt.show

    def _capture(*_args, **_kwargs) -> None:  # noqa: ANN002, ANN003
        figures.append(plt.gcf())

    plt.show = _capture  # type: ignore[assignment]
    try:
        yield figures
    finally:
        plt.show = original_show  # type: ignore[assignment]
