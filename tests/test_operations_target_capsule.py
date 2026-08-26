from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAPSULE = ROOT / "capsules" / "starintel-operations"


class OperationsTargetCapsuleTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        return (CAPSULE / relative).read_text()

    def test_operations_is_a_separate_format_three_capsule(self):
        capsule = self.read("capsule.bxb")
        self.assertIn("format (3)", capsule)
        self.assertIn("id (playground.starIntelOperations)", capsule)
        self.assertNotIn("starIntelIntelligence", capsule)

    def test_target_models_are_presentation_contracts_only(self):
        expected_models = (
            "models/primitive/TargetSubject.model.bxb",
            "models/primitive/TargetType.model.bxb",
            "models/primitive/TargetActor.model.bxb",
            "models/structures/TargetDraft.model.bxb",
            "models/structures/TargetReceipt.model.bxb",
        )
        for relative in expected_models:
            with self.subTest(relative=relative):
                self.assertTrue((CAPSULE / relative).exists())

        draft = self.read("models/structures/TargetDraft.model.bxb").lower()
        receipt = self.read("models/structures/TargetReceipt.model.bxb").lower()
        for forbidden in (
            "routingkey",
            "routing_key",
            "exchange",
            "queue",
            "rabbitmq",
            "backendurl",
            "canonicalactorid",
        ):
            self.assertNotIn(forbidden, draft)
            self.assertNotIn(forbidden, receipt)

    def test_prepare_and_commit_are_distinct_actions(self):
        prepare = self.read("models/action/PrepareTarget.model.bxb")
        commit = self.read("models/action/CommitTarget.model.bxb")
        self.assertIn("action (PrepareTarget)", prepare)
        self.assertNotIn("type (Commit)", prepare)
        self.assertIn("output (TargetDraft)", prepare)
        self.assertIn("action (CommitTarget)", commit)
        self.assertIn("type (Commit)", commit)
        self.assertIn("output (TargetReceipt)", commit)

    def test_commit_has_explicit_confirmation_model_and_view(self):
        commit = self.read("models/action/CommitTarget.model.bxb")
        self.assertIn("confirm", commit)
        self.assertIn("by (Confirmation)", commit)
        confirmation = self.read("resources/en/views/CommitTarget.confirmation.bxb")
        self.assertIn("confirmation-view", confirmation)
        self.assertIn("match", confirmation)
        self.assertIn("CommitTarget", confirmation)
        self.assertIn("TargetDraft", confirmation)

    def test_endpoints_are_local_adapters_and_do_not_expose_internal_topology(self):
        endpoints = self.read("resources/base/endpoints.bxb")
        self.assertIn("action-endpoint (PrepareTarget)", endpoints)
        self.assertIn("action-endpoint (CommitTarget)", endpoints)
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
            "workspaceid",
            "routingkey",
            "rabbitmq://",
            "couchdb://",
        ):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()