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
import rpi_jev  # noqa: E402
import typesafe_grader  # noqa: E402
from rpi_core import RPIError, apply_event, compute_delta, harness_content_digest, load_run, start_run  # noqa: E402
from rpi_bootstrap import apply as apply_bootstrap  # noqa: E402
from rpi_log import redact  # noqa: E402
from rpi_jev import review_phase  # noqa: E402
from run_live_ab import summarize_records, summarize_semantic_grades  # noqa: E402
from typesafe_grader import MAX_FIELD_CHARS, collect_eval_state, grade_with_typesafe  # noqa: E402


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

    def test_semantic_summary_is_separate_from_deterministic_pass_rate(self) -> None:
        records = [
            {
                "grade": {"passed": False},
                "semantic_grade": {
                    "status": "success",
                    "answers": {
                        "research_supported": {"noul": 0.8},
                        "diff_alignment": {"choice": "aligned", "confidence": 0.9},
                    },
                },
            },
            {"grade": {"passed": True}, "semantic_grade": {"status": "error"}},
        ]
        summary = summarize_semantic_grades(records)
        self.assertEqual(summary["status_counts"], {"success": 1, "error": 1})
        self.assertEqual(summary["metrics"]["research_supported"]["mean"], 0.8)
        self.assertFalse(records[0]["grade"]["passed"])


class TypeSafeGraderTests(RepoCase):
    class FakeAnswer:
        def __init__(self, **values: object) -> None:
            self.__dict__.update(values)

    class FakeUsage:
        input_tokens = 123
        output_tokens = 0

    class FakeResponse:
        usage = None
        answers = {}

    class FakeClient:
        response = None
        error = None

        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def system_one(self, **kwargs: object) -> object:
            if self.error is not None:
                raise self.error
            return self.response

        def close(self) -> None:
            return None

    class FakeSDK:
        TypeSafeClient = None

        @staticmethod
        def Noul(**kwargs: object) -> dict:
            return {"type": "noul", **kwargs}

        @staticmethod
        def Choice(**kwargs: object) -> dict:
            return {"type": "choice", **kwargs}

    def setUp(self) -> None:
        super().setUp()
        self.run_dir, _ = self.start()
        (self.run_dir / "RESEARCH.md").write_text("evidence\n", encoding="utf-8")
        self.sdk = self.FakeSDK()
        self.client = self.FakeClient
        self.sdk.TypeSafeClient = self.client

    def test_disabled_and_missing_key_do_not_load_or_call_sdk(self) -> None:
        disabled = grade_with_typesafe(self.root, "task", enabled=False, environ={}, sdk=self.sdk)
        missing = grade_with_typesafe(self.root, "task", enabled=True, environ={}, sdk=self.sdk)
        self.assertEqual(disabled["status"], "disabled")
        self.assertEqual(missing["status"], "not_configured")

    def test_missing_sdk_is_reported_without_failing(self) -> None:
        with mock.patch.object(typesafe_grader, "_load_sdk", side_effect=ModuleNotFoundError):
            result = grade_with_typesafe(
                self.root, "task", enabled=True, environ={"TYPESAFE_API_KEY": "secret"}
            )
        self.assertEqual(result["status"], "sdk_unavailable")
        self.assertFalse(result["authoritative"])

    def test_success_serializes_answers_and_usage(self) -> None:
        response = self.FakeResponse()
        response.usage = self.FakeUsage()
        response.answers = {
            "research_supported": self.FakeAnswer(noul=0.91),
            "diff_alignment": self.FakeAnswer(
                choice="aligned", confidence=0.87, probabilities={"aligned": 0.87, "incomplete": 0.13}
            ),
        }
        self.client.response = response
        self.client.error = None
        result = grade_with_typesafe(
            self.root, "task", enabled=True, environ={"TYPESAFE_API_KEY": "secret"}, sdk=self.sdk
        )
        self.assertEqual(result["status"], "success")
        self.assertFalse(result["authoritative"])
        self.assertEqual(result["answers"]["research_supported"]["noul"], 0.91)
        self.assertEqual(result["answers"]["diff_alignment"]["choice"], "aligned")
        self.assertEqual(result["usage"], {"input_tokens": 123, "output_tokens": 0})
        self.assertNotIn("secret", json.dumps(result))

    def test_service_failure_is_contained(self) -> None:
        self.client.response = None
        self.client.error = TimeoutError("secret should not escape")
        result = grade_with_typesafe(
            self.root, "task", enabled=True, environ={"TYPESAFE_API_KEY": "secret"}, sdk=self.sdk
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "TimeoutError")
        self.assertNotIn("secret", json.dumps(result))

    def test_collected_state_bounds_artifacts(self) -> None:
        (self.run_dir / "PLAN.md").write_text("x" * (MAX_FIELD_CHARS + 25), encoding="utf-8")
        state = collect_eval_state(self.root, "task")
        self.assertIn("[truncated 25 characters]", state["artifacts"]["PLAN.md"])

    def test_collected_state_includes_staged_product_changes(self) -> None:
        (self.root / "app.py").write_text("def value():\n    return 'staged'\n", encoding="utf-8")
        command(self.root, "git", "add", "app.py")
        state = collect_eval_state(self.root, "task")
        self.assertIn("return 'staged'", state["product_diff"])


class JevPhaseReviewTests(RepoCase):
    class FakeAnswer:
        def __init__(self, **values: object) -> None:
            self.__dict__.update(values)

    class FakeResponse:
        usage = None
        answers = {}

    class FakeClient:
        response = None
        error = None
        calls = []

        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

        def system_one(self, **kwargs: object) -> object:
            self.calls.append(kwargs)
            if self.error is not None:
                raise self.error
            return self.response

        def close(self) -> None:
            return None

    class FakeSDK:
        TypeSafeClient = None

        @staticmethod
        def Noul(**kwargs: object) -> dict:
            return {"type": "noul", **kwargs}

        @staticmethod
        def Choice(**kwargs: object) -> dict:
            return {"type": "choice", **kwargs}

    def setUp(self) -> None:
        super().setUp()
        self.sdk = self.FakeSDK()
        self.sdk.TypeSafeClient = self.FakeClient
        self.FakeClient.calls = []
        self.FakeClient.error = None

    def test_start_is_opt_in_and_records_configuration(self) -> None:
        _, disabled = self.start()
        self.assertFalse(disabled["jev"]["enabled"])
        _, enabled = start_run(
            self.root,
            "Review with Jev",
            jev_enabled=True,
            jev_model="jev-test",
            jev_timeout=12.0,
        )
        self.assertTrue(enabled["jev"]["enabled"])
        self.assertFalse(enabled["jev"]["authoritative"])
        self.assertEqual(enabled["jev"]["model"], "jev-test")

    def test_disabled_review_does_not_write_artifact(self) -> None:
        run_dir, _ = self.start()
        result = review_phase(run_dir, "research", environ={}, sdk=self.sdk)
        self.assertEqual(result["status"], "disabled")
        self.assertFalse((run_dir / "JEV_RESEARCH_REVIEW.json").exists())
        self.assertEqual(self.FakeClient.calls, [])

    def test_missing_key_is_fail_open_and_recorded(self) -> None:
        run_dir, _ = start_run(self.root, "Review with Jev", jev_enabled=True)
        (run_dir / "RESEARCH.md").write_text("Evidence\n", encoding="utf-8")
        result = review_phase(run_dir, "research", environ={}, sdk=self.sdk)
        self.assertEqual(result["status"], "not_configured")
        artifact = json.loads((run_dir / "JEV_RESEARCH_REVIEW.json").read_text())
        self.assertEqual(artifact["status"], "not_configured")
        _, _, manifest = load_run(run_dir)
        self.assertEqual(manifest["state"], "research_pending")
        self.assertEqual(manifest["jev"]["reviews"]["research"]["status"], "not_configured")

    def test_phase_review_uses_narrow_questions_and_preserves_state(self) -> None:
        response = self.FakeResponse()
        response.answers = {
            "evidence_supported": self.FakeAnswer(noul=0.92),
            "unresolved_material_gap": self.FakeAnswer(noul=0.08),
        }
        self.FakeClient.response = response
        run_dir, _ = start_run(self.root, "Review with Jev", jev_enabled=True)
        (run_dir / "RESEARCH.md").write_text("Claim with source app.py:1\n", encoding="utf-8")
        result = review_phase(
            run_dir,
            "research",
            environ={"TYPESAFE_API_KEY": "secret"},
            sdk=self.sdk,
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["answers"]["evidence_supported"]["noul"], 0.92)
        self.assertNotIn("secret", json.dumps(result))
        self.assertEqual(set(self.FakeClient.calls[0]["questions"]), {
            "evidence_supported", "request_coverage", "unresolved_material_gap",
        })
        _, _, manifest = load_run(run_dir)
        self.assertEqual(manifest["state"], "research_pending")

        review_phase(
            run_dir,
            "research",
            environ={"TYPESAFE_API_KEY": "secret"},
            sdk=self.sdk,
        )
        archived = list((run_dir / "history").glob("*--JEV_RESEARCH_REVIEW.json"))
        self.assertEqual(len(archived), 1)

    def test_external_error_is_contained(self) -> None:
        self.FakeClient.response = None
        self.FakeClient.error = TimeoutError("secret should not escape")
        run_dir, _ = start_run(self.root, "Review with Jev", jev_enabled=True)
        (run_dir / "RESEARCH.md").write_text("Evidence\n", encoding="utf-8")
        result = review_phase(
            run_dir,
            "research",
            environ={"TYPESAFE_API_KEY": "secret"},
            sdk=self.sdk,
        )
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error_type"], "TimeoutError")
        self.assertNotIn("secret", json.dumps(result))

    def test_phase_state_is_enforced(self) -> None:
        run_dir, _ = start_run(self.root, "Review with Jev", jev_enabled=True)
        with self.assertRaisesRegex(RPIError, "cannot run"):
            review_phase(
                run_dir,
                "plan",
                environ={"TYPESAFE_API_KEY": "secret"},
                sdk=self.sdk,
            )


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
