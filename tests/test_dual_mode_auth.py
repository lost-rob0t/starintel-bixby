import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPSULE = ROOT / "capsules" / "starintel-intelligence"


class DualModeAuthWiringTests(unittest.TestCase):
    def read(self, relative: str) -> str:
        path = CAPSULE / relative
        self.assertTrue(path.is_file(), f"missing {path.relative_to(ROOT)}")
        return path.read_text(encoding="utf-8")

    def test_local_endpoints_accept_only_needed_viv_context_for_optional_user_auth(self):
        endpoints = self.read("resources/base/endpoints.bxb")
        self.assertIn("accepted-inputs (query, $vivContext)", endpoints)
        self.assertIn("accepted-inputs (query, personId, dtype, limit, $vivContext)", endpoints)
        self.assertNotIn("remote-endpoint", endpoints)

    def test_actions_use_dual_mode_policy_without_manual_token_or_identity_forwarding(self):
        for relative in ("code/ResolvePerson.js", "code/SearchDocuments.js"):
            with self.subTest(relative=relative):
                source = self.read(relative)
                self.assertIn("postJsonOptionalUser", source)
                self.assertIn("input && input.$vivContext", source)
                self.assertNotIn("accessToken", source)
                self.assertNotIn("bixbyUserId", source)
                self.assertNotIn("Authorization", source)
                self.assertNotIn("Bearer", source)

    def test_provider_declaration_is_not_fabricated_before_server_111(self):
        self.assertFalse(
            (CAPSULE / "authorization.bxb").exists(),
            "authorization.bxb must contain real StarIntel provider endpoints from server #111, not placeholders",
        )


if __name__ == "__main__":
    unittest.main()
