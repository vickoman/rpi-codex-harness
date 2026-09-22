#!/usr/bin/env python3
"""Run an optional, non-authoritative TypeSafe Jev review for one RPI phase."""

from __future__ import annotations

import argparse
from collections.abc import Mapping
import importlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from rpi_core import (
    RPIError,
    atomic_write,
    compute_delta,
    json_bytes,
    load_run,
    manifest_lock,
    save_manifest,
    utc_now,
)


RUBRIC_VERSION = "rpi-jev-phase-v1"
MAX_FIELD_CHARS = 12_000
PHASE_CONFIG = {
    "research": {
        "artifact": "JEV_RESEARCH_REVIEW.json",
        "states": {"research_pending"},
        "source_artifacts": ("RESEARCH.md", "GAPS.md"),
    },
    "plan": {
        "artifact": "JEV_PLAN_REVIEW.json",
        "states": {"plan_pending", "plan_revision_pending", "plan_review_pending"},
        "source_artifacts": ("RESEARCH.md", "PLAN.md", "GAPS.md"),
    },
    "implement": {
        "artifact": "JEV_IMPLEMENT_REVIEW.json",
        "states": {"diff_review_pending"},
        "source_artifacts": ("RESEARCH.md", "PLAN.md", "PLAN_REVIEW.md", "IMPLEMENTATION.md", "DIFF_REVIEW.md"),
    },
}


def _bounded(value: str, limit: int = MAX_FIELD_CHARS) -> str:
    if len(value) <= limit:
        return value
    return f"{value[:limit]}\n\n[truncated {len(value) - limit} characters]"


def _read_artifacts(run_dir: Path, names: tuple[str, ...]) -> dict[str, str]:
    artifacts = {}
    for name in names:
        path = run_dir / name
        if not path.is_file():
            continue
        try:
            artifacts[name] = _bounded(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            continue
    return artifacts


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
    return {
        field: value
        for field in ("input_tokens", "output_tokens", "total_tokens")
        if isinstance((value := getattr(usage, field, None)), int)
    }


def _questions(sdk: Any, phase: str) -> dict[str, Any]:
    if phase == "research":
        return {
            "evidence_supported": sdk.Noul(
                instructions="Are all material claims in `artifacts.RESEARCH.md` supported by specific repository or authoritative documentation evidence recorded there?"
            ),
            "request_coverage": sdk.Noul(
                instructions="Does `artifacts.RESEARCH.md` investigate every material part of `request` needed before planning?"
            ),
            "unresolved_material_gap": sdk.Noul(
                instructions="Is there a material unresolved decision or missing fact that should prevent planning, considering `artifacts.RESEARCH.md` and `artifacts.GAPS.md`?"
            ),
        }
    if phase == "plan":
        return {
            "request_coverage": sdk.Noul(
                instructions="Does `artifacts.PLAN.md` cover every material requirement in `request`?"
            ),
            "research_traceability": sdk.Noul(
                instructions="Are the approach and decisions in `artifacts.PLAN.md` traceable to evidence in `artifacts.RESEARCH.md`?"
            ),
            "validation_is_observable": sdk.Noul(
                instructions="Does `artifacts.PLAN.md` specify validation that observes the requested behavior, including relevant failure behavior, rather than only command exit codes?"
            ),
            "scope_quality": sdk.Choice(
                instructions="How well bounded is `artifacts.PLAN.md` relative to `request` and the research evidence?",
                criteria={
                    "aligned": "The plan is complete and limited to the requested outcome.",
                    "incomplete": "The plan omits a material requirement or validation.",
                    "scope_creep": "The plan includes material work not required by the request or evidence.",
                    "blocked": "A material unresolved decision or missing fact prevents a reliable plan.",
                },
            ),
        }
    return {
        "requirements_complete": sdk.Noul(
            instructions="Does `product_diff` implement every material requirement in `request` and `artifacts.PLAN.md`?"
        ),
        "validation_is_meaningful": sdk.Noul(
            instructions="Do `artifacts.IMPLEMENTATION.md` and `artifacts.DIFF_REVIEW.md` provide evidence that validation exercised the requested behavior rather than only reporting successful exit codes?"
        ),
        "diff_alignment": sdk.Choice(
            instructions="How does `product_diff` relate to `request` and `artifacts.PLAN.md`?",
            criteria={
                "aligned": "The diff implements the plan without material unrelated changes.",
                "incomplete": "The diff omits material planned or requested behavior.",
                "scope_creep": "The diff adds material changes outside the approved plan.",
                "unrelated": "The diff does not implement the requested outcome.",
            },
        ),
    }


def review_phase(
    run_dir_value: str | Path,
    phase: str,
    *,
    environ: Mapping[str, str] | None = None,
    sdk: Any | None = None,
) -> dict[str, Any]:
    run_dir, _, manifest = load_run(run_dir_value)
    config = PHASE_CONFIG[phase]
    jev = manifest.get("jev", {"enabled": False})
    base = {
        "status": "disabled",
        "phase": phase,
        "authoritative": False,
        "rubric_version": RUBRIC_VERSION,
        "reviewed_at": utc_now(),
    }
    if not jev.get("enabled"):
        return base
    if manifest["state"] not in config["states"]:
        raise RPIError(f"Jev {phase} review cannot run in state {manifest['state']}")

    environment = os.environ if environ is None else environ
    api_key = environment.get("TYPESAFE_API_KEY")
    if not api_key:
        result = {**base, "status": "not_configured"}
    else:
        if sdk is None:
            try:
                sdk = importlib.import_module("typesafe_sdk")
            except (ImportError, ModuleNotFoundError):
                sdk = None
        if sdk is None:
            result = {**base, "status": "sdk_unavailable"}
        else:
            artifacts = _read_artifacts(run_dir, config["source_artifacts"])
            state: dict[str, Any] = {"request": _bounded(manifest["task"]), "artifacts": artifacts}
            if phase == "implement":
                delta = compute_delta(run_dir)
                state["product_diff"] = _bounded("\n".join(item["patch"] for item in delta["files"]))
            client = None
            try:
                model = jev.get("model", "jev-latest")
                client = sdk.TypeSafeClient(
                    api_key=api_key,
                    model=model,
                    timeout=float(jev.get("timeout_seconds", 30.0)),
                )
                response = client.system_one(state=state, questions=_questions(sdk, phase))
                result = {
                    **base,
                    "status": "success",
                    "model": model,
                    "answers": {
                        name: _answer_payload(answer)
                        for name, answer in getattr(response, "answers", {}).items()
                    },
                    "usage": _usage_payload(response),
                }
            except Exception as exc:  # External advice must never control RPI state.
                result = {
                    **base,
                    "status": "error",
                    "model": jev.get("model", "jev-latest"),
                    "error_type": type(exc).__name__,
                }
            finally:
                close = getattr(client, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:
                        pass

    with manifest_lock(run_dir):
        run_dir, _, latest = load_run(run_dir)
        if latest["state"] not in config["states"]:
            raise RPIError(f"RPI state changed before Jev {phase} review was recorded")
        target = run_dir / config["artifact"]
        if target.exists():
            stamp = utc_now().replace(":", "").replace("-", "")
            archived_count = len(list((run_dir / "history").glob(f"*--{config['artifact']}")))
            archived = run_dir / "history" / f"{stamp}--{archived_count:04d}--{config['artifact']}"
            atomic_write(archived, target.read_bytes())
        atomic_write(target, json_bytes(result))
        latest.setdefault("jev", {}).setdefault("reviews", {})[phase] = {
            "status": result["status"],
            "artifact": config["artifact"],
            "reviewed_at": result["reviewed_at"],
        }
        save_manifest(run_dir, latest)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--phase", choices=sorted(PHASE_CONFIG), required=True)
    args = parser.parse_args()
    try:
        result = review_phase(args.run_dir, args.phase)
        print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, RPIError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
