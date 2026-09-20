"""Optional TypeSafe semantic grading for disposable RPI live evaluations."""

from __future__ import annotations

from collections.abc import Mapping
import importlib
import os
from pathlib import Path
import subprocess
from typing import Any


RUBRIC_VERSION = "rpi-semantic-v1"
DEFAULT_MODEL = "jev-latest"
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_FIELD_CHARS = 12_000
ARTIFACT_NAMES = (
    "RESEARCH.md",
    "PLAN.md",
    "PLAN_REVIEW.md",
    "IMPLEMENTATION.md",
    "DIFF_REVIEW.md",
    "GAPS.md",
)


def _bounded(value: str, limit: int = MAX_FIELD_CHARS) -> str:
    if len(value) <= limit:
        return value
    omitted = len(value) - limit
    return f"{value[:limit]}\n\n[truncated {omitted} characters]"


def _read_text(path: Path) -> str | None:
    try:
        return _bounded(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError):
        return None


def _product_diff(repo: Path) -> str:
    result = subprocess.run(
        ["git", "diff", "--no-ext-diff", "HEAD", "--", ".", ":(exclude).codex/rpi"],
        cwd=repo,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return _bounded(result.stdout) if result.returncode == 0 else ""


def collect_eval_state(repo: Path, request: str) -> dict[str, Any]:
    """Collect bounded evidence from one disposable RPI evaluation repository."""
    runs = sorted((repo / ".codex" / "rpi" / "runs").glob("*/manifest.json"))
    run_dir = runs[0].parent if len(runs) == 1 else None
    artifacts: dict[str, str] = {}
    if run_dir is not None:
        for name in ARTIFACT_NAMES:
            content = _read_text(run_dir / name)
            if content is not None:
                artifacts[name] = content

    return {
        "request": _bounded(request),
        "artifacts": artifacts,
        "product_diff": _product_diff(repo),
    }


def _load_sdk() -> Any:
    return importlib.import_module("typesafe_sdk")


def _answer_payload(answer: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for field in ("noul", "choice", "score", "confidence", "probabilities"):
        value = getattr(answer, field, None)
        if value is not None:
            payload[field] = dict(value) if isinstance(value, Mapping) else value
    return payload


def _usage_payload(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    if usage is None:
        return {}
    payload = {}
    for field in ("input_tokens", "output_tokens", "total_tokens"):
        value = getattr(usage, field, None)
        if isinstance(value, int):
            payload[field] = value
    return payload


def grade_with_typesafe(
    repo: Path,
    request: str,
    *,
    enabled: bool,
    model: str = DEFAULT_MODEL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    environ: Mapping[str, str] | None = None,
    sdk: Any | None = None,
) -> dict[str, Any]:
    """Return non-authoritative semantic telemetry without raising SDK failures."""
    if not enabled:
        return {"status": "disabled", "authoritative": False}

    environment = os.environ if environ is None else environ
    api_key = environment.get("TYPESAFE_API_KEY")
    if not api_key:
        return {"status": "not_configured", "authoritative": False}

    if sdk is None:
        try:
            sdk = _load_sdk()
        except (ImportError, ModuleNotFoundError):
            return {"status": "sdk_unavailable", "authoritative": False}

    state = collect_eval_state(repo, request)
    questions = {
        "research_supported": sdk.Noul(
            instructions=(
                "Are the material claims in `artifacts.RESEARCH.md` supported by "
                "specific evidence recorded in that artifact?"
            ),
        ),
        "plan_covers_request": sdk.Noul(
            instructions=(
                "Does `artifacts.PLAN.md` cover the complete `request` with an "
                "executable, bounded approach and observable validation?"
            ),
        ),
        "validation_is_meaningful": sdk.Noul(
            instructions=(
                "Do the implementation and review artifacts show validation of the "
                "requested behavior rather than only successful command exit codes?"
            ),
        ),
        "diff_alignment": sdk.Choice(
            instructions=(
                "How does `product_diff` relate to the approved plan and original request?"
            ),
            criteria={
                "aligned": "The diff implements the approved plan and nothing material beyond it.",
                "incomplete": "The diff omits behavior required by the approved plan.",
                "scope_creep": "The diff adds material changes not authorized by the approved plan.",
                "unrelated": "The diff does not implement the original request.",
            },
        ),
    }

    client = None
    try:
        client = sdk.TypeSafeClient(api_key=api_key, model=model, timeout=timeout)
        response = client.system_one(state=state, questions=questions)
        answers = getattr(response, "answers", {})
        return {
            "status": "success",
            "authoritative": False,
            "rubric_version": RUBRIC_VERSION,
            "model": model,
            "answers": {name: _answer_payload(answer) for name, answer in answers.items()},
            "usage": _usage_payload(response),
        }
    except Exception as exc:  # External evaluation must not change deterministic results.
        return {
            "status": "error",
            "authoritative": False,
            "rubric_version": RUBRIC_VERSION,
            "model": model,
            "error_type": type(exc).__name__,
        }
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass
