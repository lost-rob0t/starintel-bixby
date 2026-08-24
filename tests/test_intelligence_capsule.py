import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPSULE = ROOT / "capsules" / "starintel-intelligence"


class IntelligenceCapsuleStructureTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        path = CAPSULE / relative
        self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")
        return path.read_text(encoding="utf-8")

    def test_capsule_metadata_is_real_bixby_format_three(self):
        text = self.read("capsule.bxb")
        self.assertIn("capsule {", text)
        self.assertIn("id (playground.starIntelIntelligence)", text)
        self.assertIn("format (3)", text)
        self.assertIn("target (bixby-mobile-en-US)", text)

    def test_person_contract_models_exist(self):
        required = {
            "models/primitives/PersonQuery.model.bxb": "text (PersonQuery)",
            "models/primitives/PersonId.model.bxb": "text (PersonId)",
            "models/primitives/PersonName.model.bxb": "text (PersonName)",
            "models/structures/PersonMatch.model.bxb": "structure (PersonMatch)",
            "models/structures/PersonProfile.model.bxb": "structure (PersonProfile)",
            "models/structures/PersonSearchResult.model.bxb": "structure (PersonSearchResult)",
        }
        for path, declaration in required.items():
            with self.subTest(path=path):
                self.assertIn(declaration, self.read(path))

    def test_document_contract_models_exist(self):
        required = {
            "models/primitives/DocumentId.model.bxb": "text (DocumentId)",
            "models/primitives/DocumentTitle.model.bxb": "text (DocumentTitle)",
            "models/primitives/DocumentSummary.model.bxb": "text (DocumentSummary)",
            "models/primitives/DocumentType.model.bxb": "text (DocumentType)",
            "models/primitives/DocumentUrl.model.bxb": "text (DocumentUrl)",
            "models/structures/DocumentHit.model.bxb": "structure (DocumentHit)",
            "models/structures/DocumentSearchResult.model.bxb": "structure (DocumentSearchResult)",
        }
        for path, declaration in required.items():
            with self.subTest(path=path):
                self.assertIn(declaration, self.read(path))

    def test_actions_are_read_only_person_and_document_actions(self):
        resolve = self.read("models/action/ResolvePerson.model.bxb")
        search = self.read("models/action/SearchDocuments.model.bxb")
        self.assertIn("action (ResolvePerson)", resolve)
        self.assertIn("type (Search)", resolve)
        self.assertIn("input (query)", resolve)
        self.assertIn("output (PersonSearchResult)", resolve)
        self.assertIn("action (SearchDocuments)", search)
        self.assertIn("type (Search)", search)
        self.assertIn("input (query)", search)
        self.assertIn("input (personId)", search)
        self.assertIn("input (limit)", search)
        self.assertIn("output (DocumentSearchResult)", search)
        combined = (resolve + search).lower()
        for forbidden in ("target", "autodig", "pause", "resume", "stop"):
            self.assertNotIn(forbidden, combined)

    def test_endpoints_use_local_public_gateway_adapters(self):
        endpoints = self.read("resources/base/endpoints.bxb")
        self.assertIn("action-endpoint (ResolvePerson)", endpoints)
        self.assertIn("local-endpoint (ResolvePerson.js)", endpoints)
        self.assertIn("action-endpoint (SearchDocuments)", endpoints)
        self.assertIn("local-endpoint (SearchDocuments.js)", endpoints)
        self.assertNotIn("remote-endpoint", endpoints)

    def test_training_seed_covers_lookup_and_contextual_followups(self):
        training = self.read("training/intelligence.aligned.txt")
        for phrase in (
            "Who is John Smith",
            "Who is this person",
            "Tell me more about this person",
            "Show me documents about this person",
            "Find documents about John Smith",
        ):
            self.assertIn(phrase, training)
        self.assertIn(":continue", training)

    def test_does_not_fabricate_studio_generated_training_plans(self):
        generated = list((CAPSULE / "resources").glob("**/*.training.bxb")) if (CAPSULE / "resources").exists() else []
        self.assertEqual([], generated, "compiled Bixby training must come from Developer Studio")

    def test_document_view_uses_attribution_link_not_app_launch(self):
        view = self.read("resources/en/views/DocumentSearchResult.view.bxb")
        self.assertIn("result-view", view)
        self.assertIn("attribution-link", view)
        self.assertIn("document.url", view)
        self.assertNotIn("app-launch", view)

    def test_person_view_exposes_multiple_matches_for_disambiguation(self):
        view = self.read("resources/en/views/PersonSearchResult.view.bxb")
        self.assertIn("result-view", view)
        self.assertIn("personResult.matches", view)
        self.assertIn("list-of", view)


if __name__ == "__main__":
    unittest.main()
