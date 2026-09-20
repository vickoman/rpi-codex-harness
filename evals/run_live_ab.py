#!/usr/bin/env python3
"""Opt-in live Spanish/English RPI comparison using disposable repositories."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
from pathlib import Path
import shutil
import statistics
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "rpi" / "scripts"))

from rpi_core import HARNESS_VERSION, harness_content_digest, harness_git_ref  # noqa: E402
from typesafe_grader import (  # noqa: E402
    DEFAULT_MODEL as DEFAULT_TYPESAFE_MODEL,
    DEFAULT_TIMEOUT_SECONDS as DEFAULT_TYPESAFE_TIMEOUT,
    grade_with_typesafe,
)


def run(cwd: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)


def make_fixture(parent: Path, variant: str, repetition: int) -> Path:
    repo = parent / f"calculator-{variant}-{repetition}"
    repo.mkdir()
    run(repo, "git", "init", "-q")
    run(repo, "git", "config", "user.name", "RPI Live Eval")
    run(repo, "git", "config", "user.email", "rpi@example.invalid")
    (repo / ".gitignore").write_text(".codex/rpi/\n__pycache__/\n", encoding="utf-8")
    (repo / "calculator.py").write_text("def add(a, b):\n    return a - b\n", encoding="utf-8")
    (repo / "test_calculator.py").write_text(
        "import unittest\n\nfrom calculator import add\n\n"
        "class CalculatorTest(unittest.TestCase):\n"
        "    def test_add(self):\n"
        "        self.assertEqual(add(2, 3), 5)\n\n"
        "if __name__ == '__main__':\n"
        "    unittest.main()\n",
        encoding="utf-8",
    )
    skill_dir = repo / ".agents" / "skills" / "rpi"
    skill_dir.mkdir(parents=True)
    shutil.copy2(ROOT / "evals" / "variants" / f"{variant}.md", skill_dir / "SKILL.md")
    (skill_dir / "scripts").symlink_to(ROOT / "skills" / "rpi" / "scripts", target_is_directory=True)
    run(repo, "git", "add", ".")
    run(repo, "git", "commit", "-qm", "live eval fixture")
    return repo


def prompt_for(variant: str) -> str:
    if variant == "es":
        return (
            "Usa $rpi. Declaro este cambio como simple. Corrige add() para que sume correctamente, "
            "ejecuta las pruebas y avanza hasta mostrar el diff y solicitar mi aceptación. No hagas commit."
        )
    return (
        "Use $rpi. I declare this change simple. Fix add() so it adds correctly, run the tests, "
        "and continue until you show the diff and request my acceptance. Do not commit."
    )


def extract_usage(events: list[dict]) -> dict:
    best: dict[str, int] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"input_tokens", "output_tokens", "total_tokens"} and isinstance(item, int):
                    best[key] = max(best.get(key, 0), item)
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(events)
    return best


def command_version(*args: str) -> str:
    result = run(ROOT, *args, check=False)
    return result.stdout.strip() or result.stderr.strip() or "unavailable"


def metric_summary(values: list[float]) -> dict:
    if not values:
        return {"count": 0, "mean": None, "ci95": None}
    mean = statistics.fmean(values)
    margin = 0.0 if len(values) == 1 else 1.96 * statistics.stdev(values) / math.sqrt(len(values))
    return {
        "count": len(values),
        "mean": round(mean, 3),
        "ci95": [round(mean - margin, 3), round(mean + margin, 3)],
    }


def summarize_records(records: list[dict]) -> dict:
    summary = {}
    for variant in ("es", "en"):
        selected = [item for item in records if item["variant"] == variant]
        token_keys = ("input_tokens", "output_tokens", "total_tokens")
        summary[variant] = {
            "runs": len(selected),
            "passed": sum(bool(item["grade"]["passed"]) for item in selected),
            "pass_rate": round(
                sum(bool(item["grade"]["passed"]) for item in selected) / len(selected), 3
            ) if selected else None,
            "duration_seconds": metric_summary([float(item["duration_seconds"]) for item in selected]),
            "usage": {
                key: metric_summary([float(item["usage"][key]) for item in selected if key in item["usage"]])
                for key in token_keys
            },
        }
    return summary


def summarize_semantic_grades(records: list[dict]) -> dict:
    statuses: dict[str, int] = {}
    values: dict[str, list[float]] = {}
    for record in records:
        semantic = record.get("semantic_grade")
        if not semantic:
            continue
        status = str(semantic.get("status", "unknown"))
        statuses[status] = statuses.get(status, 0) + 1
        if status != "success":
            continue
        for name, answer in semantic.get("answers", {}).items():
            value = answer.get("noul", answer.get("confidence"))
            if isinstance(value, (int, float)):
                values.setdefault(name, []).append(float(value))
    return {
        "status_counts": statuses,
        "metrics": {name: metric_summary(items) for name, items in sorted(values.items())},
    }


def grade(repo: Path) -> dict:
    manifests = list((repo / ".codex" / "rpi" / "runs").glob("*/manifest.json"))
    state = None
    if len(manifests) == 1:
        state = json.loads(manifests[0].read_text(encoding="utf-8"))["state"]
    test_result = run(repo, "python3", "-m", "unittest", "-q", check=False)
    changed = run(repo, "git", "status", "--short", "--untracked-files=all").stdout.splitlines()
    product_changes = [line for line in changed if ".codex/rpi" not in line and ".agents/skills/rpi" not in line]
    commits = int(run(repo, "git", "rev-list", "--count", "HEAD").stdout.strip())
    source = (repo / "calculator.py").read_text(encoding="utf-8")
    criteria = {
        "diff_acceptance_pending": state == "diff_acceptance_pending",
        "tests_pass": test_result.returncode == 0,
        "no_commit": commits == 1,
        "only_expected_product_file_changed": all(line.endswith("calculator.py") for line in product_changes),
        "behavior_fixed": "return a + b" in source,
    }
    return {"passed": all(criteria.values()), "criteria": criteria, "state": state, "git_status": changed}


def execute_one(
    repo: Path,
    variant: str,
    model: str,
    reasoning: str,
    output: Path,
    *,
    typesafe_semantic_grade: bool = False,
    typesafe_model: str = DEFAULT_TYPESAFE_MODEL,
    typesafe_timeout: float = DEFAULT_TYPESAFE_TIMEOUT,
) -> dict:
    command = [
        "codex", "exec", "--json", "--ephemeral", "--ignore-user-config",
        "-C", str(repo), "-s", "workspace-write", "-m", model,
        "-c", f'model_reasoning_effort="{reasoning}"',
        "-c", 'approval_policy="never"', prompt_for(variant),
    ]
    started = time.monotonic()
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    duration = time.monotonic() - started
    output.write_text(result.stdout, encoding="utf-8")
    events = []
    for line in result.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    record = {
        "returncode": result.returncode,
        "duration_seconds": round(duration, 3),
        "event_count": len(events),
        "usage": extract_usage(events),
        "stderr": result.stderr[-2000:],
        "grade": grade(repo),
    }
    if typesafe_semantic_grade:
        record["semantic_grade"] = grade_with_typesafe(
            repo,
            prompt_for(variant),
            enabled=True,
            model=typesafe_model,
            timeout=typesafe_timeout,
        )
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--reasoning-effort", default="high")
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output-dir")
    parser.add_argument(
        "--typesafe-semantic-grade",
        action="store_true",
        help="Opt in to sending bounded disposable-run evidence to TypeSafe for non-authoritative grading.",
    )
    parser.add_argument("--typesafe-model", default=DEFAULT_TYPESAFE_MODEL)
    parser.add_argument("--typesafe-timeout", type=float, default=DEFAULT_TYPESAFE_TIMEOUT)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    if args.typesafe_timeout <= 0:
        parser.error("--typesafe-timeout must be positive")
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir).resolve() if args.output_dir else ROOT / "evals" / "results" / stamp
    output_dir.mkdir(parents=True, exist_ok=False)
    records = []
    with tempfile.TemporaryDirectory(prefix="rpi-live-ab-") as temp:
        temp_root = Path(temp)
        for repetition in range(1, args.repetitions + 1):
            for variant in ("es", "en"):
                repo = make_fixture(temp_root, variant, repetition)
                raw = output_dir / f"{variant}-{repetition}.jsonl"
                record = {
                    "variant": variant,
                    "repetition": repetition,
                    **execute_one(
                        repo,
                        variant,
                        args.model,
                        args.reasoning_effort,
                        raw,
                        typesafe_semantic_grade=args.typesafe_semantic_grade,
                        typesafe_model=args.typesafe_model,
                        typesafe_timeout=args.typesafe_timeout,
                    ),
                }
                records.append(record)
                print(json.dumps(record, ensure_ascii=False))
    summary = {
        "created_at": stamp,
        "codex_version": command_version("codex", "--version"),
        "harness_version": HARNESS_VERSION,
        "harness_git_ref": harness_git_ref(),
        "harness_content_digest": harness_content_digest(),
        "model": args.model,
        "reasoning_effort": args.reasoning_effort,
        "repetitions": args.repetitions,
        "by_variant": summarize_records(records),
        "semantic_grading": summarize_semantic_grades(records),
        "records": records,
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0 if all(item["grade"]["passed"] for item in records) else 1


if __name__ == "__main__":
    raise SystemExit(main())
