"""The AI Narrative: per-Focus summaries plus one across-Focuses paragraph.

Two rules hold this together. The AI *summarizes* the pipeline's analysis and
never performs its own — every number it sees is one the pipeline already
computed and saved. And the across-Focuses paragraph is qualitative by
construction: it is written from the per-Focus digests, combines no numbers,
and is captioned as non-statistical wherever it appears. That paragraph is the
only cross-Focus synthesis anywhere in the app (ADR-0001, ADR-0011).

Only Focuses whose saved results are current are summarized: an Out of Date
Focus's numbers describe a slice its config no longer declares.

The narrative is **a derivative of a run**, and is saved as one: every
generation writes ``<project>/<project>_narrative.json``, each paragraph
stamped with the Run Summary it was written from. Re-running a Focus's
analysis rewrites that summary, so the paragraph no longer matches and is
deleted the next time the file is read — and so is the across-Focuses
paragraph, which was written from it. What :func:`load` returns is therefore
never prose about numbers the folder no longer holds.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import ProviderError, load_dotenv_if_present

ACROSS_KEY = "__across__"

SYSTEM = (
    "You are writing the results narrative for a survival-analysis report. "
    "You summarize numbers that have already been computed; you never compute, "
    "infer, or estimate anything yourself, and you never speculate about "
    "mechanism. Write plain scientific prose with no headings, no bullet lists, "
    "and no markdown. If a number you would want is absent, say the analysis "
    "does not report it rather than guessing."
)


def available_providers() -> list:
    from .anthropic_provider import AnthropicProvider
    from .openai_provider import OpenAIProvider

    load_dotenv_if_present()
    return [p for p in (AnthropicProvider(), OpenAIProvider()) if p.available()]


def get_provider(name: str | None = None):
    """The named provider, or the first configured one (``None`` if none are)."""
    from .anthropic_provider import AnthropicProvider
    from .openai_provider import OpenAIProvider

    load_dotenv_if_present()
    if name:
        provider = {"anthropic": AnthropicProvider,
                    "openai": OpenAIProvider}.get(str(name).lower())
        if provider is None:
            raise ProviderError(f"unknown AI provider {name!r}")
        return provider()
    configured = available_providers()
    return configured[0] if configured else None


# ---------------------------------------------------------------------------
# Digests — the only thing a provider ever sees
# ---------------------------------------------------------------------------

def lr_statistic(lr: dict):
    """The likelihood-ratio χ² of a factorial model's interaction test.

    Read ``statistic`` first, then ``lr_stat`` (what Run Summaries written
    before the key was settled carry), then ``chi2`` — one rule, so a saved
    summary of any age gives the narrative its number instead of ``None``.
    """
    for key in ("statistic", "lr_stat", "chi2"):
        value = (lr or {}).get(key)
        if value is not None:
            return value
    return None


def member_digest(saved) -> str:
    """A compact text rendering of one member's saved numbers."""
    lines: list[str] = []
    es = saved.experiment_summary
    rec = saved.focus_record
    lines.append(f"Experiment type: {saved.experiment_type.label}")
    if rec:
        lines.append(f"Focus: {rec.get('name')} — {rec.get('description') or ''}")
        if rec.get("treatments"):
            lines.append(f"Treatments: {', '.join(map(str, rec['treatments']))}")
    lines.append(f"Varying factors: {', '.join(saved.factors) or 'none'}")
    lines.append(
        f"Individuals: {es.get('n_total')}, deaths: {es.get('n_deaths')}, "
        f"censored: {es.get('n_censored')} ({es.get('pct_censored')}%), "
        f"treatments: {es.get('n_treatments')}"
    )
    if saved.exclusion_group:
        lines.append(f"Exclusion group applied: {saved.exclusion_group}")
    for item in saved.not_applicable:
        lines.append(f"Not applicable: {item.get('action')} — {item.get('reason')}")
    ## Said, so the narrative never reads a deliberately absent test as a
    ## null result.
    for item in getattr(saved, "left_out", None) or []:
        lines.append(f"Left out of this run by choice (not computed): {item.get('item')}")

    median = saved.median_surv
    if len(median):
        lines.append("Median survival by treatment:")
        lines.append(median.to_string(index=False))

    ## The type's prompt asks for mean lifespan; without the table the model
    ## could only say the analysis does not report it.
    mean = getattr(saved, "mean_surv", None)
    if mean is not None and len(mean):
        lines.append("Mean survival (restricted mean) by treatment:")
        lines.append(mean.to_string(index=False))

    omnibus = saved.omnibus_lr
    if omnibus:
        lines.append(
            f"Omnibus log-rank: chi2={omnibus.get('chi2')}, "
            f"df={omnibus.get('df')}, p={omnibus.get('p_value')}"
        )

    pairwise = saved.pairwise_lr
    if len(pairwise):
        lines.append("Pairwise log-rank tests:")
        lines.append(pairwise.head(20).to_string(index=False))

    for model in saved.cox_analyses:
        if model.get("error"):
            continue
        ref = model.get("reference") or {}
        ref_text = (" (reference: " + ", ".join(f"{f}={v}" for f, v in ref.items()) + ")"
                    if isinstance(ref, dict) and ref else "")
        lines.append(f"{model.get('title') or model.get('model_type')}: "
                     f"{model.get('formula')}{ref_text}")
        lr = model.get("lr_interaction") or {}
        if lr:
            lines.append(f"  interaction LR test: chi2={lr_statistic(lr)}, "
                         f"df={lr.get('df')}, p={lr.get('p_value')}")
        coefs = model.get("coefficients")
        if coefs is not None and len(coefs):
            lines.append(coefs.head(12).to_string(index=False))
    return "\n".join(lines)


def _member_prompt(name: str, digest: str, prompt_hint: str) -> str:
    return (
        f"{prompt_hint}\n\n"
        f"Write ONE paragraph (at most 120 words) summarizing the analysis "
        f"named {name!r} (a member experiment and the Focus — the slice of its "
        f"data — it was analysed under) from the output below. Do not restate "
        f"every number — pick the ones that carry the result.\n\n"
        f"--- analysis output ---\n{digest}\n--- end ---"
    )


def _across_prompt(question: str, summaries: dict[str, str]) -> str:
    joined = "\n\n".join(f"[{name}] {text}" for name, text in summaries.items())
    return (
        "Below are independent summaries of separate analyses in one project, "
        "each a Focus — a slice of one experiment's data. They were analysed "
        "separately and their numbers were never pooled.\n\n"
        f"The project's question: {question or 'not stated'}\n\n"
        "Write ONE paragraph (at most 100 words) describing where these "
        "independent analyses agree and where they disagree. This is a "
        "qualitative comparison only: do not combine, average, or "
        "meta-analyse their numbers, and do not state a combined effect or a "
        "combined p-value. If they point in different directions, say so "
        "plainly.\n\n"
        f"--- summaries ---\n{joined}\n--- end ---"
    )


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------

def generate(project, provider: Any = None, log=None,
             include_across: bool = True, save: bool = True) -> dict[str, str]:
    """Narrative for a Project: ``{"<member> · <focus>": text, "__across__": text}``.

    *provider* is a provider object, a provider name (``"anthropic"``,
    ``"openai"``), or ``None`` for the first configured one. Whatever was
    written is saved (see :func:`save`) unless *save* is False.

    Soft-fails throughout — a provider outage costs you the narrative, never
    the report.
    """
    from ..project_report import SavedAnalysis, section_key

    emit = log or (lambda _m: None)
    if provider is None or isinstance(provider, str):
        provider = get_provider(provider if isinstance(provider, str) else None)
    if provider is None:
        emit("No AI provider configured (set ANTHROPIC_API_KEY or OPENAI_API_KEY "
             "in your environment or a .env file) — skipping the narrative.")
        return {}

    out: dict[str, str] = {}
    #: key → (member, focus, run stamp): what each paragraph was written from.
    sources: dict[str, tuple[str, str, str | None]] = {}
    for member in project.members():
        statuses = {fs.name: fs for fs in member.status(check_blocked=False).focuses}
        for focus in member.focuses():
            fs = statuses.get(focus.name)
            if fs is None or not fs.analyzed or fs.out_of_date:
                continue
            saved = SavedAnalysis(member, focus)
            if not saved.exists:
                continue
            key = section_key(member.name, focus.name)
            ## Stamped before the provider is asked: the paragraph describes
            ## the run whose numbers went into the digest.
            stamp = run_stamp(member, focus)
            try:
                text = provider.complete(
                    SYSTEM,
                    _member_prompt(key, member_digest(saved),
                                   member.type.ai_summary_prompt()),
                )
            except ProviderError as exc:
                emit(f"  [{key}] narrative skipped: {exc}")
                continue
            out[key] = text
            sources[key] = (member.name, focus.name, stamp)
            emit(f"  [{key}] narrative written ({len(text.split())} words).")

    if include_across and len(out) > 1:
        try:
            out[ACROSS_KEY] = provider.complete(
                SYSTEM, _across_prompt(project.question, out))
            emit("  across-Focuses paragraph written.")
        except ProviderError as exc:
            emit(f"  across-Focuses paragraph skipped: {exc}")
    if save and out:
        path = _save(project, out, sources, provider)
        emit(f"  narrative saved to {path.name}.")
    return out


# ---------------------------------------------------------------------------
# The saved narrative — a derivative of the runs it summarizes
# ---------------------------------------------------------------------------

def narrative_path(project) -> Path:
    """``<project>/<project>_narrative.json``, beside the Project Report it
    is written for and named the same way."""
    directory = Path(project.directory)
    return directory / f"{directory.name}_narrative.json"


def run_stamp(member, focus) -> str | None:
    """What identifies the run a paragraph summarizes: the sha256 of that
    Focus's Run Summary. Every analysis rewrites the summary, so a re-run —
    even one that happens to reproduce the same numbers — breaks the match."""
    path = member.outputs(focus).summary
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _save(project, out: dict[str, str], sources: dict, provider) -> Path:
    payload = {
        "written_at": datetime.now().isoformat(timespec="seconds"),
        "provider": getattr(provider, "name", None),
        "model": getattr(provider, "model", None),
        "sections": {
            key: {"member": sources[key][0], "focus": sources[key][1],
                  "run": sources[key][2], "text": text}
            for key, text in out.items() if key in sources
        },
    }
    if ACROSS_KEY in out:
        ## Written from every paragraph above, so it is only as current as
        ## all of them.
        payload["across"] = {"text": out[ACROSS_KEY],
                             "runs": {k: sources[k][2] for k in sources}}
    path = narrative_path(project)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                    encoding="utf-8")
    return path


def load(project) -> dict[str, str]:
    """The saved narrative, as :func:`generate` returns it — current parts only.

    A paragraph whose Focus has been re-analysed since it was written no
    longer matches its Run Summary and is **deleted** from the file, with the
    across-Focuses paragraph, which was written from it; the file goes when
    nothing is left. A paragraph whose Focus is merely Out of Date is kept on
    disk but not returned — its run is intact, the config just no longer
    describes it, exactly as the report treats the results themselves.
    """
    path = narrative_path(project)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    sections = payload.get("sections") or {}
    members = {m.name: m for m in project.members()}

    kept: dict[str, dict] = {}
    current: dict[str, str] = {}
    for key, entry in sections.items():
        member = members.get(entry.get("member"))
        if member is None:
            continue
        try:
            focus = member.focus(entry.get("focus"))
        except Exception:  # noqa: BLE001 - a Focus renamed or deleted since
            continue
        stamp = entry.get("run")
        if stamp is None or run_stamp(member, focus) != stamp:
            continue                           # re-run since: deleted
        kept[key] = entry
        status = member.focus_status(focus, check_blocked=False)
        if status.analyzed and not status.out_of_date:
            current[key] = str(entry.get("text") or "")

    across = payload.get("across") or None
    if across is not None and any(kept.get(k, {}).get("run") != stamp
                                  for k, stamp in (across.get("runs") or {}).items()):
        across = None
    if across is not None and set(current) >= set(across.get("runs") or {}):
        current[ACROSS_KEY] = str(across.get("text") or "")

    if kept != sections or across != payload.get("across"):
        if kept:
            payload["sections"] = kept
            if across is None:
                payload.pop("across", None)
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False),
                            encoding="utf-8")
        else:
            path.unlink(missing_ok=True)
    return current
