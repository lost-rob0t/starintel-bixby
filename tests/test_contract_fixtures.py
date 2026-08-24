import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "contracts" / "v1" / "person-resolve.schema.json"
FIXTURE_PATHS = (
    ROOT / "fixtures" / "v1" / "person-resolve-success.json",
    ROOT / "fixtures" / "v1" / "person-resolve-ambiguous.json",
    ROOT / "fixtures" / "v1" / "person-resolve-not-found.json",
)


class PersonResolveContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads(SCHEMA_PATH.read_text())
        Draft202012Validator.check_schema(cls.schema)
        cls.validator = Draft202012Validator(cls.schema)

    def test_fixtures_validate_against_v1_schema(self):
        for path in FIXTURE_PATHS:
            with self.subTest(fixture=path.name):
                payload = json.loads(path.read_text())
                self.validator.validate(payload)

    def test_ambiguity_never_selects_a_person(self):
        payload = json.loads(FIXTURE_PATHS[1].read_text())
        self.assertEqual(payload["status"], "ambiguous")
        self.assertNotIn("person", payload)
        self.assertGreaterEqual(len(payload["matches"]), 2)

    def test_not_found_uses_stable_public_error(self):
        payload = json.loads(FIXTURE_PATHS[2].read_text())
        self.assertEqual(payload["status"], "error")
        self.assertEqual(payload["error"]["code"], "PERSON_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
