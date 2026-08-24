import json
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

    def test_auth_manifest_preserves_guest_authority_and_declares_optional_user_boundary(self):
        requirements = json.loads(self.read("auth.requirements.json"))
        self.assertEqual("none", requirements["authorizationType"])
        self.assertEqual("starintel-server#109", requirements["publicAuthority"])
        self.assertEqual("optional-user", requirements["signedInMode"])
        self.assertEqual("starintel-server-core-oauth", requirements["signedInAuthority"])
        self.assertEqual(
            "4f2f70126bc59e18681844019460a33709e1eba6",
            requirements["providerMerge"],
        )
        self.assertTrue(requirements["providerImplemented"])
        self.assertEqual(["documents:read", "search:read"], requirements["signedInScopes"])
        self.assertFalse(requirements["forwardVivContext"])
        self.assertFalse(requirements["manualTokenForwarding"])
        self.assertFalse(requirements["useBixbyUserIdAsPrincipal"])

    def test_provider_declaration_waits_for_real_bixby_client_registration(self):
        requirements = json.loads(self.read("auth.requirements.json"))
        self.assertEqual(
            [
                "deployedPublicOauthOrigin",
                "registeredCapsuleId",
                "registeredRedirectUri",
                "oauthClientId",
                "developerCenterClientSecretKey",
            ],
            requirements["registrationRequired"],
        )
        self.assertFalse(requirements["registrationComplete"])
        self.assertFalse(
            (CAPSULE / "authorization.bxb").exists(),
            "authorization.bxb must not contain invented provider/client registration values",
        )


if __name__ == "__main__":
    unittest.main()
