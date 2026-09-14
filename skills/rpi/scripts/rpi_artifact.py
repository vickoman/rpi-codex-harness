#!/usr/bin/env python3
"""Archive and atomically write an allowed RPI artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys

from rpi_core import RPIError, atomic_write, load_run, manifest_lock, utc_now


ALLOWED = {"RESEARCH.md", "PLAN.md", "PLAN_REVIEW.md", "IMPLEMENTATION.md", "DIFF_REVIEW.md", "GAPS.md"}
STATE_ALLOWLIST = {
    "RESEARCH.md": {"research_pending"},
    "PLAN.md": {"plan_pending", "plan_revision_pending"},
    "PLAN_REVIEW.md": {"plan_review_pending"},
    "IMPLEMENTATION.md": {
        "implementation_preflight", "implementation_approval_pending", "implementing",
        "validation_failed", "security_review_pending", "security_gate_failed",
    },
    "DIFF_REVIEW.md": {"diff_review_pending", "diff_acceptance_pending", "diff_rejected", "ready_to_close"},
    "GAPS.md": {"waiting_for_gap"},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--name", choices=sorted(ALLOWED), required=True)
    parser.add_argument("--input", help="Read content from this file; stdin when omitted")
    args = parser.parse_args()
    try:
        content = Path(args.input).read_bytes() if args.input else sys.stdin.buffer.read()
        with manifest_lock(Path(args.run_dir).expanduser().resolve()):
            run_dir, _, manifest = load_run(args.run_dir)
            if manifest.get("legacy"):
                raise RPIError("v0.1 runs are read-only")
            if manifest["state"] not in STATE_ALLOWLIST[args.name]:
                raise RPIError(f"{args.name} cannot be written in state {manifest['state']}")
            target = run_dir / args.name
            if target.exists():
                stamp = utc_now().replace(":", "").replace("-", "")
                archived = run_dir / "history" / f"{stamp}--{len(manifest['events']):04d}--{args.name}"
                atomic_write(archived, target.read_bytes())
            atomic_write(target, content)
        print(target)
        return 0
    except (OSError, RPIError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
