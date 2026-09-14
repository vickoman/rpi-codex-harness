#!/usr/bin/env python3
"""Optionally add .codex/rpi/ to a repository's local Git exclude file."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rpi_core import RPIError, git, resolve_project_root


ENTRY = ".codex/rpi/"


def exclude_path(project: Path) -> Path:
    result = git(project, "rev-parse", "--git-path", "info/exclude")
    value = Path(result.stdout.decode("utf-8", "replace").strip())
    return value.resolve() if value.is_absolute() else (project / value).resolve()


def apply(project: Path) -> tuple[Path, bool]:
    target = exclude_path(project)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding="utf-8") if target.exists() else ""
    lines = {line.strip() for line in existing.splitlines()}
    if ENTRY in lines:
        return target, False
    separator = "" if not existing or existing.endswith("\n") else "\n"
    with target.open("a", encoding="utf-8") as handle:
        handle.write(f"{separator}{ENTRY}\n")
        handle.flush()
    return target, True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--apply", action="store_true", help="Perform the local Git metadata mutation")
    args = parser.parse_args()
    try:
        project = resolve_project_root(args.project_root)
        target = exclude_path(project)
        if not args.apply:
            print(f"dry-run: would ensure {ENTRY} in {target}")
            return 0
        target, changed = apply(project)
        print(f"{'updated' if changed else 'already configured'}: {target}")
        return 0
    except (OSError, RPIError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
