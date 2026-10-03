"""Action/parameter primitives shared by the script registries and the
Experiment Types that contribute actions to them.

This module deliberately imports nothing heavy (no pandas, no matplotlib, no
pipeline) so an Experiment Type can declare its **Type Actions** — the Hub
buttons and the script steps mirroring them (ADR-0002) — without dragging the
analysis stack into config validation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from ..ui import Category


@dataclass(frozen=True)
class ParamSpec:
    """Describes one parameter of an action.

    ``kind`` picks the inspector widget:

    * ``"string"`` → QLineEdit
    * ``"int"``    → QSpinBox
    * ``"float"``  → QDoubleSpinBox
    * ``"bool"``   → QCheckBox
    * ``"choice"`` → QComboBox (requires ``choices``)
    * ``"path"``   → QLineEdit + browse button
    * ``"list"``   → QLineEdit (comma-separated)
    * ``"factor"`` → QComboBox of factor names (resolved at runtime)
    * ``"factors"``→ QListWidget multi-select of factor names
    """

    name: str
    kind: str
    label: str
    default: Any = None
    help: str = ""
    choices: tuple[str, ...] | None = None
    min: float | None = None
    max: float | None = None
    enabled_when: str | None = None


@dataclass
class RunContext:
    """State threaded through an *experiment-level* script run.

    The input format and censoring policy are read from the experiment's
    ``survival_config.yaml``; factors are discovered from its data file. Every
    experiment-level step runs under one **Focus**: ``data`` is the slice that
    Focus selects, with ``treatment`` relabelled by it, while ``raw_data``
    keeps the whole (post-exclusion) frame so a later Focus can be cut from
    the same load.
    """

    project_dir: Any = None          # the Experiment Directory
    experiment: Any = None           # SurvivalExperiment, when one is loaded
    data: Any = None                 # individual-level DataFrame, Focus applied
    factors: list[str] | None = None
    focus: Any = None                # the Focus this step runs under
    raw_data: Any = None             # the whole frame, before the Focus
    #: Not Applicable results under the current Focus, as ``(action,
    #: reason)`` pairs, for the Run Summary and the report.
    not_applicable: list = field(default_factory=list)
    #: Per-Focus outcome of the run: ``{focus: {"not_applicable": [...],
    #: "blocked": [...], "failed": message | None}}``.
    focus_log: dict = field(default_factory=dict)
    lifetables: Any = None
    result: Any = None               # AnalysisResult from run_analysis
    log: Callable[[str], None] = lambda _msg: None
    figure: Callable[[str, Any], None] = lambda _title, _fig: None
    excluded_chambers: set | None = None
    #: The Exclusion Group(s) this run applies, as its outputs name them —
    #: the config's active group plus :attr:`script_groups`.
    exclusion_group: str | None = None
    #: Groups ``apply_exclusions`` steps added on top of the config's, in the
    #: order applied.
    script_groups: list = field(default_factory=list)
    assume_censored: bool = True
    input_format: str = "excel"      # excel | csv | csv_long | csv_wide
    wide_factor_names: list[str] | None = None


@dataclass
class ProjectRunContext:
    """State threaded through a *project-level* script run.

    Holds the loaded Project, never an experiment — the two registries cannot
    mix by construction (ADR-0006 in the sister app; same rule here).
    """

    project: Any = None
    log: Callable[[str], None] = lambda _msg: None
    figure: Callable[[str, Any], None] = lambda _title, _fig: None
    failures: list[str] = field(default_factory=list)


@dataclass
class Action:
    key: str
    title: str
    description: str
    category: Category
    icon_name: str
    params: tuple[ParamSpec, ...] = ()
    execute_fn: Callable[[dict, Any], None] | None = None
    applicable_formats: tuple[str, ...] | None = None
    ## No "from_type" flag: it was meant to label Type Actions in the palette
    ## ("·type"), but nothing ever set it — the Factorial Battery belongs to
    ## every experiment (ADR-0011), and with one Experiment Type the label
    ## would mark most of the list. The palette groups by category instead.
    #: The key of the Requirement the action needs from its Focus
    #: (``"comparison"``, ``"factorial_plot"``, ``"factorial_model"`` — see
    #: :mod:`pysurvanalysis.domain.focus`). The Hub shows the button only when
    #: the Active Focus makes the action *relevant*, and greys it when the data
    #: cannot support it. A script step that reaches one anyway is **Not
    #: Applicable** — the action exists, it just does not apply to this slice
    #: — which is different from a name outside the registry, a hard error
    #: that refuses to start the script.
    requires: str | None = None

    def execute(self, params: dict, ctx: Any) -> None:
        if self.execute_fn is None:
            raise NotImplementedError(f"Action {self.key!r} has no execute function")
        merged: dict[str, Any] = {}
        for spec in self.params:
            if spec.name in params:
                merged[spec.name] = params[spec.name]
            elif spec.default is not None:
                merged[spec.name] = spec.default
        if self.requires:
            self.check_shape(ctx)
        self.execute_fn(merged, ctx)

    def check_shape(self, ctx: Any) -> None:
        """Raise :class:`~pysurvanalysis.domain.focus.NotApplicable` when the
        context's Focus does not meet :attr:`requires` — not relevant to its
        definition, or not computable from its populated cells.

        Checked against the data actually loaded, after exclusions, because
        computability counts *populated* cells.
        """
        focus = getattr(ctx, "focus", None)
        data = getattr(ctx, "data", None)
        if not self.requires or focus is None or data is None:
            return
        from ..domain.focus import NotApplicable, focus_shape

        ok, reason = focus_shape(focus, data).admits(self.requires)
        if not ok:
            raise NotApplicable(reason, self.key)
