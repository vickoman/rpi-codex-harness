from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "rpi" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "evals"))

import rpi_core  # noqa: E402
from rpi_core import RPIError, apply_event, compute_delta, harness_content_digest, load_run, start_run  # noqa: E402
from rpi_bootstrap import apply as apply_bootstrap  # noqa: E402
from rpi_log import redact  # noqa: E402
from run_live_ab import summarize_records  # noqa: E402


def command(root: Path, *args: str) -> None:
    subprocess.run(args, cwd=root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class RepoCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        command(self.root, "git", "init", "-q")
        command(self.root, "git", "config", "user.name", "RPI Tests")
        command(self.root, "git", "config", "user.email", "rpi@example.invalid")
        (self.root / ".gitignore").write_text(".codex/rpi/\n", encoding="utf-8")
        (self.root / "app.py").write_text("def value():\n    return 'base'\n", encoding="utf-8")
        command(self.root, "git", "add", ".")
        command(self.root, "git", "commit", "-qm", "fixture")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def start(self, risk: str = "standard") -> tuple[Path, dict]:
        return start_run(self.root, "Fix the value behavior", risk_mode=risk)

    def advance_to_preflight(self, run_dir: Path) -> None:
        apply_event(run_dir, "research-complete")
        apply_event(run_dir, "plan-ready")
        apply_event(run_dir, "plan-approved")


class StateMachineTests(RepoCase):
    def test_happy_path_requires_both_human_gates(self) -> None:
        run_dir, manifest = self.start()
        self.assertEqual(manifest["state"], "research_pending")
        self.assertEqual(len(manifest["runtime"]["harness_content_digest"]), 64)
        self.assertEqual(manifest["runtime"]["harness_content_digest"], harness_content_digest())
        self.advance_to_preflight(run_dir)
        manifest = apply_event(run_dir, "preflight-complete", scope=["app.py"])
        self.assertEqual(manifest["state"], "implementation_approval_pending")
        with self.assertRaisesRegex(RPIError, "actor=user"):
            apply_event(run_dir, "implementation-approved", scope=["app.py"])
        manifest = apply_event(run_dir, "implementation-approved", actor="user", scope=["app.py"])
        self.assertEqual(manifest["state"], "implementing")
        (self.root / "app.py").write_text("def value():\n    return 'fixed'\n", encoding="utf-8")
        apply_event(run_dir, "validation-passed")
        apply_event(run_dir, "diff-approved")
        with self.assertRaisesRegex(RPIError, "actor=user"):
            apply_event(run_dir, "diff-accepted")
        manifest = apply_event(run_dir, "diff-accepted", actor="user")
        self.assertEqual(manifest["state"], "ready_to_close")
        with self.assertRaisesRegex(RPIError, "actor=user"):
            apply_event(run_dir, "close-uncommitted")
        manifest = apply_event(run_dir, "close-uncommitted", actor="user")
        self.assertEqual(manifest["state"], "closed_uncommitted")
        self.assertIsNotNone(manifest["closed_at"])

    def test_gap_answer_returns_to_originating_state(self) -> None:
        run_dir, _ = self.start()
        apply_event(run_dir, "research-complete")
        manifest = apply_event(run_dir, "gap-opened")
        self.assertEqual(manifest["resume_state"], "plan_pending")
        with self.assertRaisesRegex(RPIError, "actor=user"):
            apply_event(run_dir, "gap-answered")
        manifest = apply_event(run_dir, "gap-answered", actor="user")
        self.assertEqual(manifest["state"], "plan_pending")
        self.assertIsNone(manifest["resume_state"])

    def test_plan_revision_limit_is_enforced(self) -> None:
        run_dir, _ = self.start()
        apply_event(run_dir, "research-complete")
        for _ in range(2):
            apply_event(run_dir, "plan-ready")
            apply_event(run_dir, "plan-rejected")
        apply_event(run_dir, "plan-ready")
        with self.assertRaisesRegex(RPIError, "maximum"):
            apply_event(run_dir, "plan-rejected")

    def test_simple_mode_skips_implementation_gate_only(self) -> None:
        run_dir, _ = self.start("simple")
        self.advance_to_preflight(run_dir)
        manifest = apply_event(run_dir, "preflight-complete", scope=["app.py"])
        self.assertEqual(manifest["state"], "implementing")

    def test_rejected_diff_requires_human_rework_direction(self) -> None:
        run_dir, _ = self.start("simple")
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        apply_event(run_dir, "validation-passed")
        apply_event(run_dir, "diff-rejected")
        with self.assertRaisesRegex(RPIError, "actor=user"):
            apply_event(run_dir, "rework-approved")
        manifest = apply_event(run_dir, "rework-approved", actor="user")
        self.assertEqual(manifest["state"], "implementing")

    def test_high_risk_requires_positive_security_gate(self) -> None:
        run_dir, _ = self.start("high-risk")
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        apply_event(run_dir, "implementation-approved", actor="user", scope=["app.py"])
        (self.root / "app.py").write_text("secured\n", encoding="utf-8")
        manifest = apply_event(run_dir, "validation-passed")
        self.assertEqual(manifest["state"], "security_review_pending")
        with self.assertRaises(RPIError):
            apply_event(run_dir, "diff-approved")
        manifest = apply_event(run_dir, "security-passed")
        self.assertEqual(manifest["state"], "diff_review_pending")

    def test_failure_and_stop_states_resume_only_with_user_direction(self) -> None:
        run_dir, _ = self.start("simple")
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        manifest = apply_event(run_dir, "validation-failed")
        self.assertEqual(manifest["state"], "validation_failed")
        with self.assertRaisesRegex(RPIError, "actor=user"):
            apply_event(run_dir, "resume")
        manifest = apply_event(run_dir, "resume", actor="user")
        self.assertEqual(manifest["state"], "implementing")
        manifest = apply_event(run_dir, "stop")
        self.assertEqual(manifest["state"], "stopped")
        with self.assertRaisesRegex(RPIError, "invalid"):
            apply_event(run_dir, "stop")
        manifest = apply_event(run_dir, "resume", actor="user")
        self.assertEqual(manifest["state"], "implementing")

    def test_security_failure_resumes_at_implementation(self) -> None:
        run_dir, _ = self.start("high-risk")
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        apply_event(run_dir, "implementation-approved", actor="user", scope=["app.py"])
        (self.root / "app.py").write_text("security candidate\n", encoding="utf-8")
        apply_event(run_dir, "validation-passed")
        manifest = apply_event(run_dir, "security-failed")
        self.assertEqual(manifest["state"], "security_gate_failed")
        manifest = apply_event(run_dir, "resume", actor="user")
        self.assertEqual(manifest["state"], "implementing")

    def test_invalid_transition_does_not_change_manifest(self) -> None:
        run_dir, _ = self.start()
        before = (run_dir / "manifest.json").read_bytes()
        with self.assertRaises(RPIError):
            apply_event(run_dir, "validation-passed")
        self.assertEqual(before, (run_dir / "manifest.json").read_bytes())

    def test_concurrent_gap_events_leave_valid_manifest(self) -> None:
        run_dir, _ = self.start()
        errors = []

        def worker() -> None:
            try:
                apply_event(run_dir, "gap-opened")
            except Exception as exc:  # pragma: no cover - diagnostic collection
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        _, _, manifest = load_run(run_dir)
        self.assertEqual(manifest["material_gaps_open"], 2)
        json.loads((run_dir / "manifest.json").read_text())

    def test_concurrent_starts_leave_complete_runs_and_atomic_latest(self) -> None:
        run_dirs = []
        errors = []

        def worker() -> None:
            try:
                run_dirs.append(self.start()[0])
            except Exception as exc:  # pragma: no cover - diagnostic collection
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len(run_dirs), 2)
        latest = (self.root / ".codex" / "rpi" / "LATEST").read_text(encoding="utf-8").strip()
        self.assertIn(latest, {run_dir.name for run_dir in run_dirs})
        for run_dir in run_dirs:
            json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    def test_failed_baseline_cleans_staging_directory(self) -> None:
        with mock.patch.object(rpi_core, "capture_baseline", side_effect=RPIError("snapshot failed")):
            with self.assertRaisesRegex(RPIError, "snapshot failed"):
                self.start()
        runs = self.root / ".codex" / "rpi" / "runs"
        self.assertEqual(list(runs.glob(".*.staging-*")), [])


class BaselineTests(RepoCase):
    def test_dirty_worktree_delta_starts_after_user_change(self) -> None:
        (self.root / "app.py").write_text("def value():\n    return 'user-change'\n", encoding="utf-8")
        (self.root / "notes.txt").write_text("preexisting\n", encoding="utf-8")
        run_dir, manifest = self.start()
        self.assertEqual(set(manifest["baseline"]["preexisting_paths"]), {"app.py", "notes.txt"})
        (self.root / "app.py").write_text("def value():\n    return 'rpi-change'\n", encoding="utf-8")
        (self.root / "new.py").write_text("created_by_rpi = True\n", encoding="utf-8")
        delta = compute_delta(run_dir)
        self.assertEqual({item["path"] for item in delta["files"]}, {"app.py", "new.py"})
        app_patch = next(item["patch"] for item in delta["files"] if item["path"] == "app.py")
        self.assertIn("-    return 'user-change'", app_patch)
        self.assertNotIn("-    return 'base'", app_patch)

    def test_artifacts_never_appear_in_delta(self) -> None:
        run_dir, _ = self.start()
        (run_dir / "RESEARCH.md").write_text("artifact\n", encoding="utf-8")
        self.assertEqual(compute_delta(run_dir)["files"], [])

    def test_workspace_drift_prevents_approval(self) -> None:
        run_dir, _ = self.start()
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        (self.root / "app.py").write_text("drift\n", encoding="utf-8")
        with self.assertRaisesRegex(RPIError, "drifted"):
            apply_event(run_dir, "implementation-approved", actor="user", scope=["app.py"])

    def test_validation_rejects_file_outside_preflight_scope(self) -> None:
        run_dir, _ = self.start("simple")
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        (self.root / "app.py").write_text("authorized\n", encoding="utf-8")
        (self.root / "debug.py").write_text("unexpected = True\n", encoding="utf-8")
        delta = compute_delta(run_dir)
        self.assertEqual(delta["outside_scope"], ["debug.py"])
        with self.assertRaisesRegex(RPIError, "outside authorized scope"):
            apply_event(run_dir, "validation-passed")

    def test_scope_traversal_is_rejected(self) -> None:
        run_dir, _ = self.start()
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        with self.assertRaisesRegex(RPIError, "invalid scope"):
            apply_event(run_dir, "implementation-approved", actor="user", scope=["../outside"])

    def test_diff_change_after_acceptance_prevents_close(self) -> None:
        run_dir, _ = self.start("simple")
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        (self.root / "app.py").write_text("first\n", encoding="utf-8")
        apply_event(run_dir, "validation-passed")
        apply_event(run_dir, "diff-approved")
        apply_event(run_dir, "diff-accepted", actor="user")
        (self.root / "app.py").write_text("changed-after-acceptance\n", encoding="utf-8")
        with self.assertRaisesRegex(RPIError, "changed"):
            apply_event(run_dir, "close-uncommitted", actor="user")

    def test_diff_change_after_technical_review_prevents_acceptance(self) -> None:
        run_dir, _ = self.start("simple")
        self.advance_to_preflight(run_dir)
        apply_event(run_dir, "preflight-complete", scope=["app.py"])
        (self.root / "app.py").write_text("first\n", encoding="utf-8")
        apply_event(run_dir, "validation-passed")
        apply_event(run_dir, "diff-approved")
        (self.root / "app.py").write_text("changed-after-review\n", encoding="utf-8")
        with self.assertRaisesRegex(RPIError, "changed after technical review"):
            apply_event(run_dir, "diff-accepted", actor="user")

    def test_invalid_ticket_cannot_escape_runs_directory(self) -> None:
        with self.assertRaisesRegex(RPIError, "ticket"):
            start_run(self.root, "unsafe", ticket="../../outside")


class RedactionTests(unittest.TestCase):
    def test_common_secrets_are_redacted(self) -> None:
        value = "Authorization: Bearer abc.def\napi_key=secret-value\nsk-abcdefghijklmnopqrstuvwxyz"
        redacted = redact(value)
        self.assertNotIn("abc.def", redacted)
        self.assertNotIn("secret-value", redacted)
        self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz", redacted)


class LiveEvalSummaryTests(unittest.TestCase):
    def test_variant_summary_reports_success_and_intervals(self) -> None:
        records = [
            {
                "variant": "es", "duration_seconds": 10.0,
                "usage": {"total_tokens": 100}, "grade": {"passed": True},
            },
            {
                "variant": "es", "duration_seconds": 14.0,
                "usage": {"total_tokens": 120}, "grade": {"passed": False},
            },
            {
                "variant": "en", "duration_seconds": 8.0,
                "usage": {"total_tokens": 90}, "grade": {"passed": True},
            },
        ]
        summary = summarize_records(records)
        self.assertEqual(summary["es"]["pass_rate"], 0.5)
        self.assertEqual(summary["es"]["duration_seconds"]["mean"], 12.0)
        self.assertEqual(summary["en"]["usage"]["total_tokens"]["ci95"], [90.0, 90.0])


class BootstrapTests(RepoCase):
    def test_local_git_exclude_is_idempotent(self) -> None:
        target, changed = apply_bootstrap(self.root)
        self.assertTrue(changed)
        self.assertIn(".codex/rpi/", target.read_text(encoding="utf-8"))
        _, changed_again = apply_bootstrap(self.root)
        self.assertFalse(changed_again)


class ArtifactTests(RepoCase):
    def test_artifact_allowlist_tracks_state(self) -> None:
        run_dir, _ = self.start()
        plan = subprocess.run(
            [sys.executable, str(SCRIPTS / "rpi_artifact.py"), "--run-dir", str(run_dir), "--name", "PLAN.md"],
            input="not allowed yet\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(plan.returncode, 2)
        research = subprocess.run(
            [sys.executable, str(SCRIPTS / "rpi_artifact.py"), "--run-dir", str(run_dir), "--name", "RESEARCH.md"],
            input="evidence\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(research.returncode, 0, research.stderr)
        self.assertEqual((run_dir / "RESEARCH.md").read_text(encoding="utf-8"), "evidence\n")

        gap_before_event = subprocess.run(
            [sys.executable, str(SCRIPTS / "rpi_artifact.py"), "--run-dir", str(run_dir), "--name", "GAPS.md"],
            input="question\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(gap_before_event.returncode, 2)
        apply_event(run_dir, "gap-opened")
        gap = subprocess.run(
            [sys.executable, str(SCRIPTS / "rpi_artifact.py"), "--run-dir", str(run_dir), "--name", "GAPS.md"],
            input="question\n",
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(gap.returncode, 0, gap.stderr)

    def test_v01_manifest_is_read_only_but_inspectable(self) -> None:
        legacy = self.root / ".codex" / "rpi" / "runs" / "legacy"
        legacy.mkdir(parents=True)
        (legacy / "manifest.yaml").write_text(
            f"rpi_version: 0.1\nrun_id: legacy\nproject_root: {self.root}\nstatus: VALIDATED\n",
            encoding="utf-8",
        )
        _, _, manifest = load_run(legacy)
        self.assertTrue(manifest["legacy"])
        with self.assertRaisesRegex(RPIError, "read-only"):
            apply_event(legacy, "resume", actor="user")


if __name__ == "__main__":
    unittest.main()
