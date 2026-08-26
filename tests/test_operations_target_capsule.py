import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPSULE = ROOT / "capsules" / "starintel-operations"


class OperationsTargetCapsuleTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        path = CAPSULE / relative
        self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")
        return path.read_text(encoding="utf-8")

    def test_operations_is_a_separate_format_three_capsule(self):
        text = self.read("capsule.bxb")
        self.assertIn("capsule {", text)
        self.assertIn("id (playground.starIntelOperations)", text)
        self.assertIn("format (3)", text)
        self.assertIn("runtime-version (9)", text)
        self.assertIn("js-runtime-version (2)", text)
        intelligence = (ROOT / "capsules" / "starintel-intelligence" / "capsule.bxb").read_text(encoding="utf-8")
        self.assertNotEqual(text, intelligence)

    def test_target_models_are_presentation_contracts_only(self):
        required = {
            "models/primitives/TargetSubject.model.bxb": "name (TargetSubject)",
            "models/primitives/TargetType.model.bxb": "text (TargetType)",
            "models/primitives/TargetActor.model.bxb": "name (TargetActor)",
            "models/structures/TargetDraft.model.bxb": "structure (TargetDraft)",
            "models/structures/TargetReceipt.model.bxb": "structure (TargetReceipt)",
        }
        for path, declaration in required.items():
            with self.subTest(path=path):
                self.assertIn(declaration, self.read(path))

        combined = "\n".join(self.read(path) for path in required)
        for forbidden in ("routing-key", "exchange", "queue", "rmq", "rabbitmq", "shell", "backend-url"):
            self.assertNotIn(forbidden, combined.lower())

    def test_prepare_and_commit_are_distinct_actions(self):
        prepare = self.read("models/action/PrepareTarget.model.bxb")
        commit = self.read("models/action/CommitTarget.model.bxb")

        self.assertIn("action (PrepareTarget)", prepare)
        self.assertIn("input (subject)", prepare)
        self.assertIn("input (targetType)", prepare)
        self.assertIn("input (actor)", prepare)
        self.assertIn("output (TargetDraft)", prepare)
        self.assertNotIn("type (Commit)", prepare)

        self.assertIn("action (CommitTarget)", commit)
        self.assertIn("type (Commit)", commit)
        self.assertIn("input (draft)", commit)
        self.assertIn("output (TargetReceipt)", commit)
        self.assertIn("confirm {", commit)
        self.assertIn("by (TargetConfirmation)", commit)

    def test_commit_has_explicit_confirmation_model_and_view(self):
        confirmation = self.read("models/primitives/TargetConfirmation.model.bxb")
        view = self.read("resources/en/views/CommitTarget.confirmation.bxb")
        self.assertIn("boolean (TargetConfirmation)", confirmation)
        self.assertIn("confirmation-view", view)
        self.assertIn("TargetConfirmation", view)
        self.assertIn("CommitTarget (action)", view)
        self.assertIn("action.draft", view)
        self.assertIn("modal-prompt (true)", view)

    def test_endpoints_are_local_adapters_and_do_not_expose_internal_topology(self):
        endpoints = self.read("resources/base/endpoints.bxb")
        self.assertIn("action-endpoint (PrepareTarget)", endpoints)
        self.assertIn("local-endpoint (PrepareTarget.js)", endpoints)
        self.assertIn("action-endpoint (CommitTarget)", endpoints)
        self.assertIn("local-endpoint (CommitTarget.js)", endpoints)
        self.assertNotIn("remote-endpoint", endpoints)

        prepare = self.read("code/PrepareTarget.js")
        commit = self.read("code/CommitTarget.js")
        for source in (prepare, commit):
            self.assertIn("import http from 'http'", source)
            self.assertIn("import config from 'config'", source)
            self.assertIn("config.get('starintel.gateway.origin')", source)
            self.assertNotIn(".star.intel", source)
            for forbidden in ("rabbitmq", "routing_key", "routing-key", "exchange", "queue", "child_process"):
                self.assertNotIn(forbidden, source.lower())

        self.assertIn("/v1/bixby/targets/prepare", prepare)
        self.assertIn("/v1/bixby/targets/commit", commit)

    def test_operations_authority_is_user_delegated_and_scope_separated(self):
        requirements = json.loads(self.read("auth.requirements.json"))
        self.assertEqual("oauth2-authorization-code", requirements["authorizationType"])
        self.assertEqual("user", requirements["principalMode"])
        self.assertEqual(
            [
                "targets:dispatch",
                "starintel.autodig.read",
                "starintel.autodig.control",
            ],
            requirements["requiredScopes"],
        )
        self.assertFalse(requirements["forwardVivContext"])
        serialized = json.dumps(requirements).lower()
        for forbidden in ("client_secret", "client-secret-value", "admin", "rabbitmq"):
            self.assertNotIn(forbidden, serialized)

    def test_training_covers_generic_and_actor_qualified_target_requests(self):
        training = self.read("training/operations-targets.aligned.txt")
        for phrase in (
            "Create a target for (John Smith)[v:TargetSubject]",
            "Create a (person)[v:TargetType] target for (John Smith)[v:TargetSubject]",
            "Have (BBPD)[v:TargetActor] target (John Smith)[v:TargetSubject]",
        ):
            self.assertIn(phrase, training)

    def test_autodig_capsule_contract_never_becomes_runtime_authority(self):
        paths = [p for p in CAPSULE.glob("**/*") if p.is_file()]
        serialized = "\n".join(p.read_text(encoding="utf-8", errors="ignore") for p in paths).lower()
        for action in ("startautodig", "pauseautodig", "resumeautodig", "stopautodig"):
            self.assertIn(action, serialized)
        self.assertIn("autodig_capability_unavailable", serialized)
        for forbidden in (
            "quasar.control.v1",
            "workerid",
            "leaseid",
            "routing_key",
            "routing-key",
            "rabbitmq",
            "couchdb",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()