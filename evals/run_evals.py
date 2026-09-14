#!/usr/bin/env python3
"""Run deterministic RPI tests and validate the eval catalog."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def validate_catalog() -> None:
    catalog = json.loads((ROOT / "evals" / "cases" / "catalog.json").read_text(encoding="utf-8"))
    ids = set()
    for case in catalog["cases"]:
        required = {"id", "phase", "fixture", "expected"}
        missing = required - case.keys()
        if missing:
            raise SystemExit(f"{case.get('id', '<unknown>')} missing: {sorted(missing)}")
        if case["id"] in ids:
            raise SystemExit(f"duplicate case id: {case['id']}")
        ids.add(case["id"])
        if not case["expected"]:
            raise SystemExit(f"empty expected criteria: {case['id']}")
    print(f"eval catalog: {len(ids)} cases valid")


def main() -> int:
    validate_catalog()
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=False,
    )
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
