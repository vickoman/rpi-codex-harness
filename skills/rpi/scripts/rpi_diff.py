#!/usr/bin/env python3
"""Show only the project delta attributable to an RPI run."""

from __future__ import annotations

import argparse
import json
import sys

from rpi_core import RPIError, compute_delta


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--format", choices=("patch", "json"), default="patch")
    args = parser.parse_args()
    try:
        delta = compute_delta(args.run_dir)
        if args.format == "json":
            print(json.dumps(delta, indent=2, ensure_ascii=False, sort_keys=True))
        else:
            print(f"run_id: {delta['run_id']}")
            print(f"delta_digest: {delta['delta_digest']}")
            print(f"authorized_scope: {', '.join(delta['authorized_scope']) or '<not set>'}")
            print(f"outside_scope: {', '.join(delta['outside_scope']) or '<none>'}")
            if not delta["files"]:
                print("No project changes attributable to this run.")
            for item in delta["files"]:
                print(f"\n# {item['change']}: {item['path']}")
                print(item["patch"], end="" if item["patch"].endswith("\n") else "\n")
        return 0
    except RPIError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
