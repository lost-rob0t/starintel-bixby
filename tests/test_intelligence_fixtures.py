import json
import unittest
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "intelligence"


class IntelligenceFixtureTests(unittest.TestCase):
    def load(self, name: str):
        path = FIXTURES / name
        self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")
        return json.loads(path.read_text(encoding="utf-8"))

    def test_person_success_fixture_is_unambiguous_and_normalized(self):
        fixture = self.load("person-resolve-success.json")
        self.assertEqual(200, fixture["status"])
        self.assertEqual("John Smith", fixture["request"]["query"])
        response = fixture["response"]
        self.assertEqual(1, len(response["matches"]))
        self.assertEqual(response["matches"][0]["id"], response["profile"]["id"])
        self.assertEqual(
            {"query", "matches", "profile"},
            set(response),
        )

    def test_person_ambiguity_fixture_never_selects_a_profile(self):
        fixture = self.load("person-resolve-ambiguous.json")
        self.assertEqual(409, fixture["status"])
        self.assertEqual("AMBIGUOUS_PERSON", fixture["response"]["error"]["code"])
        self.assertGreaterEqual(len(fixture["response"]["matches"]), 2)
        self.assertNotIn("profile", fixture["response"])

    def test_person_not_found_fixture_uses_stable_safe_error(self):
        fixture = self.load("person-resolve-not-found.json")
        self.assertEqual(404, fixture["status"])
        self.assertEqual("PERSON_NOT_FOUND", fixture["response"]["error"]["code"])
        self.assertNotIn("stack", json.dumps(fixture).lower())

    def test_document_success_fixture_is_bounded_and_public_link_only(self):
        fixture = self.load("documents-search-success.json")
        self.assertEqual(200, fixture["status"])
        limit = fixture["request"]["limit"]
        documents = fixture["response"]["documents"]
        self.assertLessEqual(len(documents), limit)
        self.assertLessEqual(limit, 10)
        for document in documents:
            self.assertEqual({"id", "title", "summary", "dtype", "url"}, set(document))
            parsed = urlparse(document["url"])
            self.assertEqual("https", parsed.scheme)
            self.assertTrue(parsed.hostname)
            self.assertFalse(parsed.hostname.endswith(".star.intel"))
            self.assertFalse(parsed.path.startswith("/api/"))
            self.assertFalse(parsed.path.startswith("/v1/"))

    def test_document_empty_fixture_uses_stable_not_found_error(self):
        fixture = self.load("documents-search-empty.json")
        self.assertEqual(404, fixture["status"])
        self.assertEqual("DOCUMENTS_NOT_FOUND", fixture["response"]["error"]["code"])


if __name__ == "__main__":
    unittest.main()
