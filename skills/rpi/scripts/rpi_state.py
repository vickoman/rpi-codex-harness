#!/usr/bin/env python3
"""Create, inspect, validate, and transition RPI runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from rpi_core import RPIError, apply_event, load_run, start_run, status_payload, validate_manifest


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="command", required=True)
    start = commands.add_parser("start")
    start.add_argument("--project-root", required=True)
    start.add_argument("--task", required=True)
    start.add_argument("--ticket")
    start.add_argument("--risk-mode", choices=("simple", "standard", "high-risk"), default="standard")
    start.add_argument("--model", default="unknown")
    start.add_argument("--reasoning-effort", default="unknown")
    for name in ("status", "validate"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", required=True)
    event = commands.add_parser("event")
    event.add_argument("--run-dir", required=True)
    event.add_argument("--event", required=True)
    event.add_argument("--actor", choices=("agent", "user"), default="agent")
    event.add_argument("--scope", nargs="*", default=[])
    return root


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "start":
            run_dir, manifest = start_run(
                args.project_root, args.task, args.ticket, args.risk_mode, args.model, args.reasoning_effort
            )
            payload = {"run_dir": str(run_dir), **status_payload(manifest)}
        else:
            run_dir, _, manifest = load_run(Path(args.run_dir))
            if args.command == "status":
                payload = {"run_dir": str(run_dir), **status_payload(manifest)}
            elif args.command == "validate":
                if manifest.get("legacy"):
                    payload = {"valid": True, **status_payload(manifest)}
                else:
                    validate_manifest(manifest)
                    payload = {"valid": True, **status_payload(manifest)}
            else:
                manifest = apply_event(run_dir, args.event, args.actor, args.scope)
                payload = {"run_dir": str(run_dir), **status_payload(manifest)}
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
        return 0
    except RPIError as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
