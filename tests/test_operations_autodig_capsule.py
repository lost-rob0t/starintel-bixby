from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAPSULE = ROOT / "capsules" / "starintel-operations"


def read(path: str) -> str:
    return (CAPSULE / path).read_text()


class OperationsAutoDigCapsuleTests(unittest.TestCase):
    def test_operations_auth_requests_only_needed_autodig_scopes(self):
        auth = json.loads(read("auth.requirements.json"))
        self.assertEqual(
            auth["requiredScopes"],
            [
                "targets:dispatch",
                "starintel.autodig.read",
                "starintel.autodig.control",
            ],
        )
        self.assertEqual(auth["principalMode"], "user")
        self.assertIs(auth["forwardVivContext"], False)

    def test_autodig_actions_exist_and_use_bounded_public_contract(self):
        expected = {
            "GetAutoDigStatus": "/v1/bixby/autodig/status",
            "GetAutoDigRun": "/v1/bixby/autodig/run",
            "ListAutoDigRuns": "/v1/bixby/autodig/runs",
            "StartAutoDig": "/v1/bixby/autodig/start",
            "PauseAutoDig": "/v1/bixby/autodig/pause",
            "ResumeAutoDig": "/v1/bixby/autodig/resume",
            "StopAutoDig": "/v1/bixby/autodig/stop",
        }
        endpoints = read("resources/base/endpoints.bxb")
        for action, route in expected.items():
            with self.subTest(action=action):
                self.assertTrue((CAPSULE / f"models/action/{action}.model.bxb").exists())
                self.assertTrue((CAPSULE / f"code/{action}.js").exists())
                self.assertIn(f"action-endpoint ({action})", endpoints)
                self.assertIn(route, read(f"code/{action}.js"))

    def test_autodig_runtime_availability_is_explicit_and_fail_closed(self):
        manifest = json.loads(read("autodig.capabilities.json"))
        self.assertEqual(manifest["source"], "backend-capability-discovery")
        self.assertIs(manifest["defaultAvailable"], False)
        self.assertEqual(
            manifest["operations"],
            {
                "status": False,
                "getRun": False,
                "listRuns": False,
                "start": False,
                "pause": False,
                "resume": False,
                "stop": False,
            },
        )
        self.assertEqual(manifest["unavailableError"], "AUTODIG_CAPABILITY_UNAVAILABLE")

    def test_mutating_autodig_actions_are_commit_and_confirmation_gated(self):
        for action in ("StartAutoDig", "PauseAutoDig", "ResumeAutoDig", "StopAutoDig"):
            with self.subTest(action=action):
                model = read(f"models/action/{action}.model.bxb")
                self.assertIn("type (Commit)", model)
                self.assertIn("confirm", model)
                self.assertTrue((CAPSULE / f"resources/en/views/{action}.confirmation.bxb").exists())

    def test_read_actions_are_not_commit_actions(self):
        for action in ("GetAutoDigStatus", "GetAutoDigRun", "ListAutoDigRuns"):
            with self.subTest(action=action):
                self.assertNotIn("type (Commit)", read(f"models/action/{action}.model.bxb"))

    def test_autodig_run_models_preserve_public_identity_only(self):
        run_model = read("models/structures/AutoDigRun.model.bxb")
        for field in ("runId", "requestId", "status", "target"):
            self.assertIn(field, run_model)
        for field in ("workerId", "leaseId", "routingKey", "queue", "exchange", "workspaceId"):
            self.assertNotIn(field, run_model)

    def test_selected_run_followups_are_real_bixby_continuations(self):
        training = read("training/operations-autodig.aligned.txt")
        self.assertIn("(run-42)[v:AutoDigRunId]", training)
        self.assertIn("What's it doing?", training)

    def test_training_covers_status_start_pause_resume_stop_and_contextual_run(self):
        training = read("training/operations-autodig.aligned.txt")
        for phrase in (
            "Start Auto Dig on (John Smith)[v:AutoDigTarget]",
            "Pause Auto Dig run (run-42)[v:AutoDigRunId]",
            "Resume Auto Dig run (run-42)[v:AutoDigRunId]",
            "Stop Auto Dig run (run-42)[v:AutoDigRunId]",
        ):
            self.assertIn(phrase, training)

    def test_capsule_never_exposes_internal_quasar_protocol_or_private_topology(self):
        serialized = "\n".join(
            p.read_text(encoding="utf-8", errors="ignore")
            for p in CAPSULE.glob("**/*")
            if p.is_file()
        ).lower()
        for forbidden in (
            "quasar.control.v1",
            "rabbitmq",
            "routing_key",
            "routing-key",
            "exchange",
            "queue",
            ".star.intel",
        ):
            self.assertNotIn(forbidden, serialized)
