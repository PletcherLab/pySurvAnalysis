"""Script runner: walks a list of steps and dispatches to action callables."""

from __future__ import annotations

from .actions import ACTIONS, RunContext


def run_script(script: dict, ctx: RunContext) -> None:
    """Execute every step in *script* in order, threading *ctx*."""
    steps = script.get("steps") or []
    name = script.get("name", "(unnamed)")
    ctx.log(f"\n=== Script: {name}  ({len(steps)} steps) ===")
    for i, step in enumerate(steps, 1):
        if not isinstance(step, dict):
            ctx.log(f"  [{i}] skipped (malformed step)")
            continue
        action_key = step.get("action")
        action = ACTIONS.get(action_key)
        if action is None:
            ctx.log(f"  [{i}] unknown action: {action_key!r}")
            continue
        params = {k: v for k, v in step.items() if k != "action"}
        ctx.log(f"  [{i}] {action.title}")
        action.execute(params, ctx)
    ctx.log("=== Script complete ===")
