#!/usr/bin/env python3
"""Deterministic state, baseline, and diff primitives for RPI v0.2."""

from __future__ import annotations

import contextlib
import datetime as dt
import difflib
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
from typing import Any, Iterator


SCHEMA_VERSION = "2.0"
HARNESS_VERSION = "0.3.0"
ARTIFACT_REL = Path(".codex/rpi")
MAX_SNAPSHOT_BYTES = 25 * 1024 * 1024
TERMINAL_STATES = {"closed_uncommitted"}
PAUSED_STATES = {
    "blocked",
    "stopped",
    "validation_failed",
    "security_gate_failed",
}
GAP_CAPABLE_STATES = {
    "research_pending",
    "plan_pending",
    "plan_revision_pending",
    "plan_review_pending",
    "implementation_preflight",
    "implementation_approval_pending",
    "implementing",
    "security_review_pending",
    "diff_review_pending",
    "diff_acceptance_pending",
}

DIRECT_TRANSITIONS = {
    ("research_pending", "research-complete"): "plan_pending",
    ("plan_pending", "plan-ready"): "plan_review_pending",
    ("plan_revision_pending", "plan-ready"): "plan_review_pending",
    ("plan_review_pending", "plan-approved"): "implementation_preflight",
    ("implementation_approval_pending", "implementation-approved"): "implementing",
    ("implementing", "validation-failed"): "validation_failed",
    ("diff_review_pending", "diff-rejected"): "diff_rejected",
    ("diff_acceptance_pending", "diff-accepted"): "ready_to_close",
    ("ready_to_close", "close-uncommitted"): "closed_uncommitted",
}

PHASE_BY_STATE = {
    "research_pending": "research",
    "plan_pending": "plan",
    "plan_revision_pending": "plan",
    "plan_review_pending": "review_plan",
    "implementation_preflight": "implement",
    "implementation_approval_pending": "implement",
    "implementing": "implement",
    "validation_failed": "implement",
    "security_gate_failed": "implement",
    "security_review_pending": "implement",
    "diff_review_pending": "review_diff",
    "diff_acceptance_pending": "review_diff",
    "diff_rejected": "review_diff",
    "ready_to_close": "close",
    "waiting_for_gap": "gap",
    "blocked": "blocked",
    "stopped": "stopped",
    "closed_uncommitted": "closed",
}


class RPIError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def digest_json(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)


@contextlib.contextmanager
def manifest_lock(run_dir: Path) -> Iterator[None]:
    lock_path = run_dir / ".manifest.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except ImportError:  # pragma: no cover - Windows fallback
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def git(project: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(project), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        raise RPIError(f"git {' '.join(args)} failed: {detail}")
    return result


def resolve_project_root(value: str | Path) -> Path:
    candidate = Path(value).expanduser().resolve()
    result = git(candidate, "rev-parse", "--show-toplevel", check=False)
    if result.returncode != 0:
        raise RPIError(f"not a Git repository: {candidate}")
    root = Path(os.fsdecode(result.stdout).strip()).resolve()
    if root != candidate:
        candidate = root
    return candidate


def head_sha(project: Path) -> str:
    result = git(project, "rev-parse", "HEAD", check=False)
    return os.fsdecode(result.stdout).strip() if result.returncode == 0 else "unavailable"


def harness_git_ref() -> str:
    root = Path(__file__).resolve().parents[3]
    result = git(root, "rev-parse", "HEAD", check=False)
    if result.returncode != 0:
        return "unavailable"
    value = os.fsdecode(result.stdout).strip()
    dirty = git(root, "status", "--porcelain", "--untracked-files=all", check=False)
    return f"{value}-dirty" if dirty.stdout else value


def harness_content_digest() -> str:
    root = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
            continue
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def codex_version() -> str:
    result = subprocess.run(["codex", "--version"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    return os.fsdecode(result.stdout).strip() or "unavailable"


def _z_paths(data: bytes) -> set[str]:
    return {os.fsdecode(item) for item in data.split(b"\0") if item}


def is_artifact_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lstrip("./")
    return normalized == ".codex/rpi" or normalized.startswith(".codex/rpi/")


def changed_paths(project: Path) -> list[str]:
    commands = [
        ("diff", "--name-only", "-z", "--"),
        ("diff", "--cached", "--name-only", "-z", "--"),
        ("ls-files", "--others", "--exclude-standard", "-z", "--"),
    ]
    paths: set[str] = set()
    for command in commands:
        paths.update(_z_paths(git(project, *command).stdout))
    return sorted(path for path in paths if not is_artifact_path(path))


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_file_state(project: Path, relative: str, include_content: bool = True) -> dict[str, Any]:
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise RPIError(f"path escapes project: {relative}")
    path = project / relative_path
    if not path.exists() and not path.is_symlink():
        return {"kind": "missing", "mode": None, "size": 0, "sha256": None, "content": None}
    info = path.lstat()
    mode = stat.S_IMODE(info.st_mode)
    if path.is_symlink():
        data = os.readlink(path).encode("utf-8", "surrogateescape")
        kind = "symlink"
    elif path.is_file():
        data = path.read_bytes()
        kind = "file"
    else:
        return {"kind": "other", "mode": mode, "size": info.st_size, "sha256": None, "content": None}
    return {
        "kind": kind,
        "mode": mode,
        "size": len(data),
        "sha256": _hash_bytes(data),
        "content": data if include_content else None,
    }


def workspace_fingerprint(project: Path) -> str:
    entries = []
    for relative in changed_paths(project):
        state = read_file_state(project, relative, include_content=False)
        entries.append({"path": relative, **{k: state[k] for k in ("kind", "mode", "size", "sha256")}})
    return digest_json({"head_sha": head_sha(project), "entries": entries})


def capture_baseline(project: Path, run_dir: Path, initial_paths: list[str]) -> dict[str, Any]:
    snapshots = run_dir / "baseline" / "snapshots"
    snapshots.mkdir(parents=True, exist_ok=True)
    entries = []
    complete = True
    for relative in initial_paths:
        state = read_file_state(project, relative)
        snapshot_name = None
        content = state.pop("content")
        if content is not None:
            if len(content) > MAX_SNAPSHOT_BYTES:
                complete = False
            else:
                snapshot_name = f"{hashlib.sha256(relative.encode('utf-8', 'surrogateescape')).hexdigest()}.bin"
                atomic_write(snapshots / snapshot_name, content)
        entries.append({"path": relative, "snapshot": snapshot_name, **state})
    baseline = {
        "captured_at": utc_now(),
        "head_sha": head_sha(project),
        "workspace_fingerprint": workspace_fingerprint(project),
        "complete": complete,
        "entries": entries,
    }
    atomic_write(run_dir / "baseline.json", json_bytes(baseline))
    return baseline


def _slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return (normalized[:48].rstrip("-") or "change")


def _ticket(value: str | None) -> str | None:
    if value is None:
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", value):
        raise RPIError("ticket must contain only letters, digits, dots, underscores, or hyphens")
    return value


def artifacts_ignored(project: Path) -> bool:
    result = git(project, "check-ignore", "-q", ".codex/rpi/.probe", check=False)
    return result.returncode == 0


def graphify_metadata(project: Path) -> dict[str, Any]:
    graph = project / "graphify-out" / "graph.json"
    if not graph.is_file():
        return {"present": False}
    try:
        payload = json.loads(graph.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"present": True, "valid_json": False, "error": type(exc).__name__}
    keys = ("source_ref", "generated_at", "workspace_root", "files_indexed", "schema_version", "version")
    return {"present": True, "valid_json": True, **{key: payload.get(key) for key in keys if key in payload}}


def start_run(
    project_root: str | Path,
    task: str,
    ticket: str | None = None,
    risk_mode: str = "standard",
    model: str = "unknown",
    reasoning_effort: str = "unknown",
    jev_enabled: bool = False,
    jev_model: str = "jev-latest",
    jev_timeout: float = 30.0,
) -> tuple[Path, dict[str, Any]]:
    if risk_mode not in {"simple", "standard", "high-risk"}:
        raise RPIError(f"invalid risk mode: {risk_mode}")
    if jev_timeout <= 0:
        raise RPIError("Jev timeout must be positive")
    ticket = _ticket(ticket)
    project = resolve_project_root(project_root)
    initial_paths = changed_paths(project)
    now = utc_now()
    compact_time = now.replace("-", "").replace(":", "")
    prefix = ticket if ticket else "NO-TICKET"
    run_id = f"{prefix}--{compact_time}--{_slug(task)}--{secrets.token_hex(2)}"
    runs_dir = project / ARTIFACT_REL / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_dir = runs_dir / run_id
    staging = runs_dir / f".{run_id}.staging-{secrets.token_hex(4)}"
    staging.mkdir()
    try:
        for name in ("history", "logs"):
            (staging / name).mkdir()
        baseline = capture_baseline(project, staging, initial_paths)
        state = "research_pending" if baseline["complete"] else "blocked"
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "harness_version": HARNESS_VERSION,
            "run_id": run_id,
            "project_root": str(project),
            "task": task,
            "ticket": ticket,
            "risk_mode": risk_mode,
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
            "state": state,
            "resume_state": "research_pending" if state == "blocked" else None,
            "material_gaps_open": 0,
            "review_revision_count": 0,
            "baseline": {
                "head_sha": baseline["head_sha"],
                "workspace_fingerprint": baseline["workspace_fingerprint"],
                "complete": baseline["complete"],
                "preexisting_paths": initial_paths,
            },
            "authorized_scope": [],
            "authorized_scope_digest": None,
            "approvals": {
                "implementation": {"granted": False},
                "diff": {"granted": False},
            },
            "technical_diff_review": {"completed": False},
            "jev": {
                "enabled": jev_enabled,
                "authoritative": False,
                "model": jev_model,
                "timeout_seconds": jev_timeout,
                "reviews": {},
            },
            "runtime": {
                "codex_version": codex_version(),
                "model": model,
                "reasoning_effort": reasoning_effort,
                "harness_git_ref": harness_git_ref(),
                "harness_content_digest": harness_content_digest(),
                "graphify": graphify_metadata(project),
            },
            "warnings": [] if artifacts_ignored(project) else [".codex/rpi is not ignored by Git"],
            "events": [{"event": "start", "at": now, "actor": "user", "to": state}],
        }
        atomic_write(staging / "manifest.json", json_bytes(manifest))
        os.replace(staging, run_dir)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    atomic_write(project / ARTIFACT_REL / "LATEST", f"{run_id}\n".encode())
    return run_dir, manifest


def _legacy_status(run_dir: Path) -> dict[str, Any]:
    content = (run_dir / "manifest.yaml").read_text(encoding="utf-8")
    values: dict[str, str] = {}
    for key in ("rpi_version", "run_id", "project_root", "status", "current_phase", "next_action"):
        match = re.search(rf"(?m)^{re.escape(key)}:\s*([^#\n]+)", content)
        if match:
            values[key] = match.group(1).strip().strip("'\"")
    return {"legacy": True, "read_only": True, **values}


def validate_manifest(manifest: dict[str, Any]) -> None:
    required = {
        "schema_version", "harness_version", "run_id", "project_root", "state",
        "risk_mode", "baseline", "approvals", "events",
    }
    missing = sorted(required - manifest.keys())
    if missing:
        raise RPIError(f"manifest missing fields: {', '.join(missing)}")
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise RPIError(f"unsupported schema version: {manifest['schema_version']}")
    if manifest["state"] not in PHASE_BY_STATE:
        raise RPIError(f"unknown state: {manifest['state']}")


def load_run(run_dir_value: str | Path) -> tuple[Path, Path, dict[str, Any]]:
    run_dir = Path(run_dir_value).expanduser().resolve()
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.exists():
        if (run_dir / "manifest.yaml").exists():
            legacy = _legacy_status(run_dir)
            project = Path(legacy.get("project_root", run_dir)).expanduser().resolve()
            return run_dir, project, legacy
        raise RPIError(f"manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RPIError(f"invalid manifest: {exc}") from exc
    validate_manifest(manifest)
    project = resolve_project_root(manifest["project_root"])
    expected = (project / ARTIFACT_REL / "runs" / manifest["run_id"]).resolve()
    if run_dir != expected:
        raise RPIError(f"run path mismatch: expected {expected}")
    return run_dir, project, manifest


def save_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    validate_manifest(manifest)
    manifest["updated_at"] = utc_now()
    atomic_write(run_dir / "manifest.json", json_bytes(manifest))


def _baseline_entry(run_dir: Path, baseline: dict[str, Any], relative: str, project: Path) -> dict[str, Any]:
    entry = next((item for item in baseline["entries"] if item["path"] == relative), None)
    if entry is not None:
        content = None
        if entry["snapshot"]:
            content = (run_dir / "baseline" / "snapshots" / entry["snapshot"]).read_bytes()
        return {**entry, "content": content}
    head = baseline["head_sha"]
    result = git(project, "show", f"{head}:{relative}", check=False) if head != "unavailable" else None
    if result is None or result.returncode != 0:
        return {"kind": "missing", "mode": None, "size": 0, "sha256": None, "content": None}
    mode_result = git(project, "ls-tree", head, "--", relative, check=False)
    mode = None
    if mode_result.returncode == 0 and mode_result.stdout:
        try:
            mode = int(os.fsdecode(mode_result.stdout).split()[0], 8) & 0o777
        except (ValueError, IndexError):
            pass
    return {"kind": "file", "mode": mode, "size": len(result.stdout), "sha256": _hash_bytes(result.stdout), "content": result.stdout}


def compute_delta(run_dir_value: str | Path) -> dict[str, Any]:
    run_dir, project, manifest = load_run(run_dir_value)
    if manifest.get("legacy"):
        raise RPIError("v0.1 runs are read-only and do not support v0.2 diff")
    baseline = json.loads((run_dir / "baseline.json").read_text(encoding="utf-8"))
    if not baseline.get("complete"):
        raise RPIError("baseline snapshot is incomplete")
    paths = set(changed_paths(project)) | {item["path"] for item in baseline["entries"]}
    files = []
    for relative in sorted(paths):
        before = _baseline_entry(run_dir, baseline, relative, project)
        after = read_file_state(project, relative)
        before_key = (before["kind"], before["mode"], before["sha256"])
        after_key = (after["kind"], after["mode"], after["sha256"])
        if before_key == after_key:
            continue
        if before["kind"] == "missing":
            change = "added"
        elif after["kind"] == "missing":
            change = "deleted"
        else:
            change = "modified"
        patch = _unified_diff(relative, before.get("content"), after.get("content"))
        files.append({
            "path": relative,
            "change": change,
            "before": {k: before[k] for k in ("kind", "mode", "size", "sha256")},
            "after": {k: after[k] for k in ("kind", "mode", "size", "sha256")},
            "patch": patch,
        })
    scope = set(manifest.get("authorized_scope", []))
    outside_scope = sorted(item["path"] for item in files if scope and item["path"] not in scope)
    summary = [{"path": f["path"], "change": f["change"], "before": f["before"], "after": f["after"]} for f in files]
    return {
        "run_id": manifest["run_id"],
        "head_sha": baseline["head_sha"],
        "files": files,
        "delta_digest": digest_json(summary),
        "authorized_scope": sorted(scope),
        "outside_scope": outside_scope,
    }


def _unified_diff(relative: str, before: bytes | None, after: bytes | None) -> str:
    before = before or b""
    after = after or b""
    if b"\0" in before or b"\0" in after:
        return "Binary files differ\n"
    try:
        before_lines = before.decode("utf-8").splitlines(keepends=True)
        after_lines = after.decode("utf-8").splitlines(keepends=True)
    except UnicodeDecodeError:
        return "Binary files differ\n"
    return "".join(difflib.unified_diff(before_lines, after_lines, f"a/{relative}", f"b/{relative}"))


def _validate_scope(project: Path, values: list[str]) -> list[str]:
    if not values:
        raise RPIError("preflight requires at least one scope path")
    result = []
    for value in values:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or is_artifact_path(value):
            raise RPIError(f"invalid scope path: {value}")
        resolved = (project / path).resolve(strict=False)
        try:
            resolved.relative_to(project)
        except ValueError as exc:
            raise RPIError(f"scope path escapes project: {value}") from exc
        result.append(path.as_posix())
    return sorted(set(result))


def apply_event(run_dir_value: str | Path, event: str, actor: str = "agent", scope: list[str] | None = None) -> dict[str, Any]:
    run_dir = Path(run_dir_value).expanduser().resolve()
    with manifest_lock(run_dir):
        run_dir, project, manifest = load_run(run_dir)
        if manifest.get("legacy"):
            raise RPIError("v0.1 runs are read-only")
        current = manifest["state"]
        if current in TERMINAL_STATES:
            raise RPIError(f"terminal state does not accept events: {current}")
        target: str
        event_record: dict[str, Any] = {"event": event, "at": utc_now(), "actor": actor, "from": current}

        if event == "gap-opened":
            if current != "waiting_for_gap" and current not in GAP_CAPABLE_STATES:
                raise RPIError(f"gap-opened is invalid from {current}")
            if current != "waiting_for_gap":
                manifest["resume_state"] = current
            manifest["material_gaps_open"] += 1
            target = "waiting_for_gap"
        elif event == "gap-answered":
            if current != "waiting_for_gap" or manifest["material_gaps_open"] < 1:
                raise RPIError("no open material gap to answer")
            if actor != "user":
                raise RPIError("gap answers require actor=user")
            manifest["material_gaps_open"] -= 1
            target = "waiting_for_gap" if manifest["material_gaps_open"] else manifest.get("resume_state")
            if not target:
                raise RPIError("missing resume_state for gap")
            if target != "waiting_for_gap":
                manifest["resume_state"] = None
        elif event == "plan-rejected":
            if current != "plan_review_pending":
                raise RPIError(f"plan-rejected is invalid from {current}")
            if manifest["review_revision_count"] >= 2:
                raise RPIError("maximum plan revision count reached")
            manifest["review_revision_count"] += 1
            target = "plan_revision_pending"
        elif event == "preflight-complete":
            if current != "implementation_preflight":
                raise RPIError(f"preflight-complete is invalid from {current}")
            authorized_scope = _validate_scope(project, scope or [])
            if workspace_fingerprint(project) != manifest["baseline"]["workspace_fingerprint"]:
                raise RPIError("workspace drifted since baseline; preflight not completed")
            manifest["authorized_scope"] = authorized_scope
            manifest["authorized_scope_digest"] = digest_json(authorized_scope)
            event_record["scope_digest"] = manifest["authorized_scope_digest"]
            target = "implementing" if manifest["risk_mode"] == "simple" else "implementation_approval_pending"
        elif event == "implementation-approved":
            if current != "implementation_approval_pending":
                raise RPIError(f"implementation-approved is invalid from {current}")
            if actor != "user":
                raise RPIError("implementation approval requires actor=user")
            approved_scope = _validate_scope(project, scope or [])
            if approved_scope != manifest.get("authorized_scope"):
                raise RPIError("approval scope does not match preflight scope")
            current_fingerprint = workspace_fingerprint(project)
            if current_fingerprint != manifest["baseline"]["workspace_fingerprint"]:
                raise RPIError("workspace drifted since baseline; approval not recorded")
            manifest["approvals"]["implementation"] = {
                "granted": True,
                "actor": actor,
                "at": utc_now(),
                "head_sha": head_sha(project),
                "workspace_fingerprint": current_fingerprint,
                "scope": approved_scope,
                "scope_digest": digest_json(approved_scope),
            }
            event_record["scope_digest"] = manifest["approvals"]["implementation"]["scope_digest"]
            target = "implementing"
        elif event == "validation-passed":
            if current != "implementing":
                raise RPIError(f"validation-passed is invalid from {current}")
            delta = compute_delta(run_dir)
            if delta["outside_scope"]:
                raise RPIError(f"delta contains files outside authorized scope: {', '.join(delta['outside_scope'])}")
            manifest["technical_diff_review"] = {"completed": False}
            manifest["approvals"]["diff"] = {"granted": False}
            target = "security_review_pending" if manifest["risk_mode"] == "high-risk" else "diff_review_pending"
            event_record["delta_digest"] = delta["delta_digest"]
        elif event == "security-passed":
            if current != "security_review_pending" or manifest["risk_mode"] != "high-risk":
                raise RPIError(f"security-passed is invalid from {current}")
            target = "diff_review_pending"
        elif event == "security-failed":
            if current != "security_review_pending" or manifest["risk_mode"] != "high-risk":
                raise RPIError(f"security-failed is invalid from {current}")
            manifest["resume_state"] = "implementing"
            target = "security_gate_failed"
        elif event == "diff-approved":
            if current != "diff_review_pending":
                raise RPIError(f"diff-approved is invalid from {current}")
            delta = compute_delta(run_dir)
            if delta["outside_scope"]:
                raise RPIError(f"delta contains files outside authorized scope: {', '.join(delta['outside_scope'])}")
            manifest["technical_diff_review"] = {
                "completed": True,
                "at": utc_now(),
                "delta_digest": delta["delta_digest"],
            }
            event_record["delta_digest"] = delta["delta_digest"]
            target = "diff_acceptance_pending"
        elif event == "diff-accepted":
            if current != "diff_acceptance_pending":
                raise RPIError(f"diff-accepted is invalid from {current}")
            if actor != "user":
                raise RPIError("diff acceptance requires actor=user")
            delta = compute_delta(run_dir)
            technical_review = manifest.get("technical_diff_review", {})
            if not technical_review.get("completed") or delta["delta_digest"] != technical_review.get("delta_digest"):
                raise RPIError("diff changed after technical review; review it again before acceptance")
            manifest["approvals"]["diff"] = {
                "granted": True,
                "actor": actor,
                "at": utc_now(),
                "head_sha": head_sha(project),
                "delta_digest": delta["delta_digest"],
            }
            event_record["delta_digest"] = delta["delta_digest"]
            target = "ready_to_close"
        elif event == "close-uncommitted":
            if current != "ready_to_close":
                raise RPIError(f"close-uncommitted is invalid from {current}")
            if actor != "user":
                raise RPIError("closing a run requires actor=user")
            approval = manifest["approvals"]["diff"]
            if not approval.get("granted"):
                raise RPIError("human diff acceptance is required")
            delta = compute_delta(run_dir)
            if delta["delta_digest"] != approval["delta_digest"]:
                raise RPIError("diff changed after human acceptance")
            target = "closed_uncommitted"
            manifest["closed_at"] = utc_now()
        elif event in {"block", "stop"}:
            if current in PAUSED_STATES or current in {"waiting_for_gap", "diff_rejected"}:
                raise RPIError(f"{event} is invalid from {current}")
            manifest["resume_state"] = current
            target = "blocked" if event == "block" else "stopped"
        elif event == "rework-approved":
            if current != "diff_rejected" or actor != "user":
                raise RPIError("rework-approved requires diff_rejected and actor=user")
            target = "implementing"
            manifest["resume_state"] = None
            manifest["technical_diff_review"] = {"completed": False}
            manifest["approvals"]["diff"] = {"granted": False}
        elif event == "resume":
            if current not in PAUSED_STATES or actor != "user":
                raise RPIError("resume requires a paused state and actor=user")
            target = manifest.get("resume_state")
            if not target:
                raise RPIError("missing resume_state")
            manifest["resume_state"] = None
        else:
            target = DIRECT_TRANSITIONS.get((current, event), "")
            if not target:
                raise RPIError(f"event {event} is invalid from {current}")
            if event in {"validation-failed", "diff-rejected"}:
                manifest["resume_state"] = current

        manifest["state"] = target
        event_record["to"] = target
        manifest["events"].append(event_record)
        save_manifest(run_dir, manifest)
        return manifest


def status_payload(manifest: dict[str, Any]) -> dict[str, Any]:
    if manifest.get("legacy"):
        return manifest
    return {
        "run_id": manifest["run_id"],
        "state": manifest["state"],
        "phase": PHASE_BY_STATE[manifest["state"]],
        "risk_mode": manifest["risk_mode"],
        "head_sha": manifest["baseline"]["head_sha"],
        "material_gaps_open": manifest["material_gaps_open"],
        "review_revision_count": manifest["review_revision_count"],
        "jev": manifest.get("jev", {"enabled": False, "authoritative": False, "reviews": {}}),
        "warnings": manifest["warnings"],
    }
