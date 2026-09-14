#!/usr/bin/env python3
"""Persist a redacted command log inside an RPI run."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from rpi_core import RPIError, TERMINAL_STATES, atomic_write, load_run, manifest_lock, utc_now


PATTERNS = [
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+"), r"\1 [REDACTED]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"), "[REDACTED_OPENAI_KEY]"),
    (
        re.compile(r"(?i)\b(api[_-]?key|access[_-]?token|token|secret|password|cookie|authorization)\b(\s*[:=]\s*)([^\s,;]+)"),
        r"\1\2[REDACTED]",
    ),
]


def redact(value: str) -> str:
    for pattern, replacement in PATTERNS:
        value = pattern.sub(replacement, value)
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--input")
    args = parser.parse_args()
    try:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.name) or args.name.startswith("."):
            raise RPIError("invalid log name")
        source = Path(args.input).read_text(encoding="utf-8", errors="replace") if args.input else sys.stdin.read()
        with manifest_lock(Path(args.run_dir).expanduser().resolve()):
            run_dir, _, manifest = load_run(args.run_dir)
            if manifest.get("legacy"):
                raise RPIError("v0.1 runs are read-only")
            if manifest["state"] in TERMINAL_STATES:
                raise RPIError("closed runs are read-only")
            header = f"captured_at: {utc_now()}\nrun_id: {manifest['run_id']}\n\n"
            target = run_dir / "logs" / args.name
            atomic_write(target, (header + redact(source)).encode("utf-8"))
        print(target)
        return 0
    except (OSError, RPIError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
