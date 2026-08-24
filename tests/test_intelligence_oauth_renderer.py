import importlib.util
import pathlib
import tempfile
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "render_intelligence_oauth.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("render_intelligence_oauth", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntelligenceOauthRendererTests(unittest.TestCase):
    def test_renders_real_optional_user_oauth_contract_without_secret_value(self):
        tool = load_tool()
        rendered = tool.render_authorization(
            oauth_origin="https://auth.starintel.example",
            client_id="star-client-123",
            client_secret_key="starintel_intelligence_oauth",
        )

        self.assertIn("oauth2-authorization-code (StarIntel)", rendered)
        self.assertIn('authorize-endpoint ("https://auth.starintel.example/oauth/authorize")', rendered)
        self.assertIn('token-endpoint ("https://auth.starintel.example/oauth/token")', rendered)
        self.assertIn("client-id (star-client-123)", rendered)
        self.assertIn("client-secret-key (starintel_intelligence_oauth)", rendered)
        self.assertIn("scope (documents:read search:read)", rendered)
        self.assertNotIn("targets", rendered.lower())
        self.assertNotIn("autodig", rendered.lower())
        self.assertNotIn("client-secret (", rendered.lower())

    def test_rejects_non_https_or_private_oauth_origins(self):
        tool = load_tool()
        for origin in (
            "http://auth.example.com",
            "https://localhost",
            "https://10.1.2.3",
            "https://auth.star.intel",
            "https://192.168.1.2",
        ):
            with self.subTest(origin=origin):
                with self.assertRaises(ValueError):
                    tool.render_authorization(origin, "client-1", "secret_key")

    def test_rejects_values_that_can_break_bxb_syntax_or_smuggle_secret_material(self):
        tool = load_tool()
        bad_cases = (
            ("https://auth.example.com", "client id", "secret_key"),
            ("https://auth.example.com", "client)\nadmin", "secret_key"),
            ("https://auth.example.com", "client-1", "secret key"),
            ("https://auth.example.com", "client-1", "secret)value"),
        )
        for origin, client_id, secret_key in bad_cases:
            with self.subTest(client_id=client_id, secret_key=secret_key):
                with self.assertRaises(ValueError):
                    tool.render_authorization(origin, client_id, secret_key)

    def test_derives_exact_samsung_callback_from_registered_capsule_id(self):
        tool = load_tool()
        self.assertEqual(
            "https://starintel-labs-starIntelIntelligence.oauth.aibixby.com/auth/external/cb",
            tool.bixby_redirect_uri("starintel-labs.starIntelIntelligence"),
        )
        for capsule_id in ("playground.starIntelIntelligence", "bad id", "bad/id", ""):
            with self.subTest(capsule_id=capsule_id):
                with self.assertRaises(ValueError):
                    tool.bixby_redirect_uri(capsule_id)

    def test_finalizer_updates_registered_capsule_and_optional_user_endpoints_atomically(self):
        tool = load_tool()
        capsule = "capsule {\n  id (playground.starIntelIntelligence)\n  version (0.1.0)\n}\n"
        endpoints = (
            "endpoints {\n"
            "  action-endpoints {\n"
            "    action-endpoint (ResolvePerson) {\n"
            "      accepted-inputs (query, $vivContext)\n"
            "      local-endpoint (ResolvePerson.js)\n"
            "    }\n"
            "    action-endpoint (SearchDocuments) {\n"
            "      accepted-inputs (query, personId, dtype, limit, $vivContext)\n"
            "      local-endpoint (SearchDocuments.js)\n"
            "    }\n"
            "  }\n"
            "}\n"
        )

        finalized = tool.finalize_registered_sources(
            capsule_source=capsule,
            endpoints_source=endpoints,
            capsule_id="starintel-labs.starIntelIntelligence",
            oauth_origin="https://auth.starintel.example",
            client_id="client-123",
            client_secret_key="starintel_intelligence_oauth",
        )

        self.assertIn("id (starintel-labs.starIntelIntelligence)", finalized["capsule.bxb"])
        self.assertNotIn("playground.", finalized["capsule.bxb"])
        self.assertEqual(2, finalized["endpoints.bxb"].count("authorization: user: optional"))
        self.assertIn("oauth2-authorization-code (StarIntel)", finalized["authorization.bxb"])
        self.assertEqual(
            "https://starintel-labs-starIntelIntelligence.oauth.aibixby.com/auth/external/cb",
            finalized["redirect_uri"],
        )

    def test_finalizer_is_idempotent_and_rejects_conflicting_endpoint_authority(self):
        tool = load_tool()
        capsule = "capsule {\n  id (playground.starIntelIntelligence)\n}\n"
        endpoints = (
            "endpoints {\n"
            "  action-endpoints {\n"
            "    action-endpoint (ResolvePerson) {\n"
            "      local-endpoint (ResolvePerson.js)\n"
            "    }\n"
            "    action-endpoint (SearchDocuments) {\n"
            "      local-endpoint (SearchDocuments.js)\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        args = dict(
            capsule_id="starintel-labs.starIntelIntelligence",
            oauth_origin="https://auth.starintel.example",
            client_id="client-123",
            client_secret_key="starintel_intelligence_oauth",
        )
        first = tool.finalize_registered_sources(capsule, endpoints, **args)
        second = tool.finalize_registered_sources(
            first["capsule.bxb"], first["endpoints.bxb"], **args
        )
        self.assertEqual(first, second)

        conflicting = endpoints.replace(
            "local-endpoint (ResolvePerson.js)",
            "local-endpoint (ResolvePerson.js)\n      authorization { global }",
        )
        with self.assertRaises(ValueError):
            tool.finalize_registered_sources(capsule, conflicting, **args)

    def test_write_finalizer_requires_expected_capsule_tree_and_never_accepts_secret_value(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "resources" / "base").mkdir(parents=True)
            (root / "capsule.bxb").write_text(
                "capsule {\n  id (playground.starIntelIntelligence)\n}\n", encoding="utf-8"
            )
            (root / "resources" / "base" / "endpoints.bxb").write_text(
                "endpoints {\n  action-endpoints {\n"
                "    action-endpoint (ResolvePerson) { local-endpoint (ResolvePerson.js) }\n"
                "    action-endpoint (SearchDocuments) { local-endpoint (SearchDocuments.js) }\n"
                "  }\n}\n",
                encoding="utf-8",
            )

            result = tool.finalize_capsule_tree(
                root,
                capsule_id="starintel-labs.starIntelIntelligence",
                oauth_origin="https://auth.starintel.example",
                client_id="client-123",
                client_secret_key="starintel_intelligence_oauth",
            )
            self.assertEqual(
                "https://starintel-labs-starIntelIntelligence.oauth.aibixby.com/auth/external/cb",
                result["redirect_uri"],
            )
            self.assertTrue((root / "authorization.bxb").is_file())
            endpoint_text = (root / "resources" / "base" / "endpoints.bxb").read_text(encoding="utf-8")
            self.assertEqual(2, endpoint_text.count("authorization: user: optional"))
            combined = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.bxb"))
            self.assertNotIn("client-secret (", combined.lower())

    def test_write_finalizer_rolls_back_every_file_if_commit_fails_mid_transaction(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            endpoints_path = root / "resources" / "base" / "endpoints.bxb"
            endpoints_path.parent.mkdir(parents=True)
            capsule_path = root / "capsule.bxb"
            capsule_before = "capsule {\n  id (playground.starIntelIntelligence)\n}\n"
            endpoints_before = (
                "endpoints {\n  action-endpoints {\n"
                "    action-endpoint (ResolvePerson) { local-endpoint (ResolvePerson.js) }\n"
                "    action-endpoint (SearchDocuments) { local-endpoint (SearchDocuments.js) }\n"
                "  }\n}\n"
            )
            capsule_path.write_text(capsule_before, encoding="utf-8")
            endpoints_path.write_text(endpoints_before, encoding="utf-8")

            real_replace = tool._replace_text
            calls = 0

            def fail_second_write(path, content):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("synthetic write failure")
                return real_replace(path, content)

            with mock.patch.object(tool, "_replace_text", side_effect=fail_second_write):
                with self.assertRaises(OSError):
                    tool.finalize_capsule_tree(
                        root,
                        capsule_id="starintel-labs.starIntelIntelligence",
                        oauth_origin="https://auth.starintel.example",
                        client_id="client-123",
                        client_secret_key="starintel_intelligence_oauth",
                    )

            self.assertEqual(capsule_before, capsule_path.read_text(encoding="utf-8"))
            self.assertEqual(endpoints_before, endpoints_path.read_text(encoding="utf-8"))
            self.assertFalse((root / "authorization.bxb").exists())


if __name__ == "__main__":
    unittest.main()
