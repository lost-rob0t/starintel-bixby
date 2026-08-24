import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTELLIGENCE = ROOT / "capsules" / "intelligence"
OPERATIONS = ROOT / "capsules" / "operations"


def read(path):
    return path.read_text()


def all_bxb(root):
    return "\n".join(path.read_text() for path in sorted(root.rglob("*.bxb")))


class CapsuleStructureTests(unittest.TestCase):
    def test_both_capsules_target_mobile_and_watch_on_runtime_9(self):
        for root in (INTELLIGENCE, OPERATIONS):
            capsule = read(root / "capsule.bxb")
            self.assertIn("format (3)", capsule)
            self.assertIn("target (bixby-mobile-en-US)", capsule)
            self.assertIn("target (bixby-watch-en-US)", capsule)
            self.assertIn("runtime-version (9)", capsule)
            self.assertIn("js-runtime-version (2)", capsule)

    def test_intelligence_oauth_is_read_only(self):
        auth = read(INTELLIGENCE / "authorization.bxb")
        self.assertIn("starintel.read starintel.search", auth)
        self.assertNotIn("targets.write", auth)
        self.assertNotIn("autodig.control", auth)
        self.assertNotIn("autodig.read", auth)

    def test_operations_oauth_is_separate_and_scoped(self):
        auth = read(OPERATIONS / "authorization.bxb")
        for scope in (
            "starintel.read",
            "starintel.targets.write",
            "starintel.autodig.read",
            "starintel.autodig.control",
        ):
            self.assertIn(scope, auth)
        self.assertNotIn("starintel.search", auth)

    def test_remote_endpoints_use_public_gateway_only(self):
        for root in (INTELLIGENCE, OPERATIONS):
            endpoints = read(root / "resources" / "base" / "all.endpoints.bxb")
            self.assertNotIn("http://", endpoints)
            self.assertNotIn(".star.intel", endpoints)
            self.assertNotIn("rabbit", endpoints.lower())
            self.assertNotIn("couch", endpoints.lower())
            self.assertNotIn("valkey", endpoints.lower())
            self.assertNotIn("10.", endpoints)
            self.assertNotIn("192.168", endpoints)
            self.assertIn("{gateway.url}/v1/bixby/", endpoints)

    def test_intelligence_actions_are_search_only(self):
        actions = all_bxb(INTELLIGENCE / "models" / "actions")
        self.assertIn("action (ResolvePerson)", actions)
        self.assertIn("action (SearchDocuments)", actions)
        self.assertNotIn("type (Commit)", actions)
        self.assertNotIn("BeginTransaction", actions)
        self.assertNotIn("confirm {", actions)

    def test_target_is_begin_then_confirmed_commit(self):
        prepare = read(OPERATIONS / "models" / "actions" / "PrepareTarget.model.bxb")
        commit = read(OPERATIONS / "models" / "actions" / "CommitTarget.model.bxb")
        draft = read(OPERATIONS / "models" / "concepts" / "TargetDraft.model.bxb")
        endpoints = read(OPERATIONS / "resources" / "base" / "all.endpoints.bxb")
        self.assertIn("type (BeginTransaction)", prepare)
        self.assertIn("output (TargetDraft)", prepare)
        self.assertIn("features { transaction }", draft)
        self.assertIn("type (Commit)", commit)
        self.assertIn("type (TargetDraft)", commit)
        self.assertIn("by (OperationConfirmation)", commit)
        self.assertIn("action-endpoint (CommitTarget)", endpoints)
        self.assertIn("accepted-inputs (draft)", endpoints)

    def test_autodig_start_is_begin_then_confirmed_commit(self):
        prepare = read(OPERATIONS / "models" / "actions" / "PrepareAutoDigStart.model.bxb")
        commit = read(OPERATIONS / "models" / "actions" / "CommitAutoDigStart.model.bxb")
        draft = read(OPERATIONS / "models" / "concepts" / "AutoDigStartDraft.model.bxb")
        self.assertIn("type (BeginTransaction)", prepare)
        self.assertIn("output (AutoDigStartDraft)", prepare)
        self.assertIn("features { transaction }", draft)
        self.assertIn("type (Commit)", commit)
        self.assertIn("type (AutoDigStartDraft)", commit)
        self.assertIn("by (OperationConfirmation)", commit)
        self.assertIn("output (AutoDigRunReceipt)", commit)

    def test_every_control_mutation_has_confirmation(self):
        for action in ("PauseAutoDigRun", "ResumeAutoDigRun", "StopAutoDigRun"):
            model = read(OPERATIONS / "models" / "actions" / f"{action}.model.bxb")
            self.assertIn("by (OperationConfirmation)", model, action)
            view = read(OPERATIONS / "resources" / "en-US" / "views" / f"{action}.confirmation.view.bxb")
            self.assertIn(f"{action} (action)", view)

    def test_transaction_support_exists_for_both_drafts(self):
        target = read(OPERATIONS / "resources" / "en-US" / "transactions" / "TargetDraft.transaction.bxb")
        autodig = read(OPERATIONS / "resources" / "en-US" / "transactions" / "AutoDigStartDraft.transaction.bxb")
        self.assertIn("TargetDraft (this)", target)
        self.assertIn("CommitTarget", target)
        self.assertIn("AutoDigStartDraft (this)", autodig)
        self.assertIn("CommitAutoDigStart", autodig)

    def test_no_topology_or_secret_literals_in_capsule_source(self):
        payload = (all_bxb(INTELLIGENCE) + all_bxb(OPERATIONS)).lower()
        for forbidden in (
            ".star.intel",
            "rabbitmq",
            "amqp://",
            "couchdb",
            "valkey",
            "routing_key",
            "routing-key",
            "shell_command",
            "backend_url",
            "password=",
            "api_key=",
        ):
            self.assertNotIn(forbidden, payload)


if __name__ == "__main__":
    unittest.main()
