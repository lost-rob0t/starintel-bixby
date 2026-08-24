import importlib.util
import pathlib
import unittest


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


if __name__ == "__main__":
    unittest.main()
