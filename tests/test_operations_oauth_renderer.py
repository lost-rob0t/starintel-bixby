import importlib.util
import pathlib
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "render_operations_oauth.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("render_operations_oauth", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load Operations OAuth renderer")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OperationsOauthRendererTests(unittest.TestCase):
    def test_renders_only_operations_scopes_without_secret_value(self):
        tool = load_tool()
        rendered = tool.render_authorization(
            "https://oauth.starintel.actor", "ops-client-1", "starintel_operations_oauth"
        )
        self.assertIn("oauth2-authorization-code (StarIntel)", rendered)
        self.assertIn("scope (targets:dispatch starintel.autodig.read starintel.autodig.control)", rendered)
        self.assertNotIn("starintel.targets.write", rendered)
        self.assertNotIn("client-secret (", rendered.lower())
        self.assertNotIn("documents:read", rendered)
        self.assertNotIn("search:read", rendered)

    def test_rejects_private_origin_playground_id_and_bxb_injection(self):
        tool = load_tool()
        for origin in ("http://oauth.example.com", "https://localhost", "https://oauth.star.intel", "https://10.0.0.2"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                tool.render_authorization(origin, "client-1", "secret_key")
        with self.assertRaises(ValueError):
            tool.bixby_redirect_uri("playground.starIntelOperations")
        with self.assertRaises(ValueError):
            tool.render_authorization("https://oauth.example.com", "client)\nadmin", "secret_key")

    def test_finalizer_registers_capsule_and_requires_user_auth_on_every_operation(self):
        tool = load_tool()
        capsule = "capsule {\n  id (playground.starIntelOperations)\n}\n"
        actions = (
            "PrepareTarget", "CommitTarget", "GetAutoDigStatus", "GetAutoDigRun",
            "ListAutoDigRuns", "StartAutoDig", "PauseAutoDig", "ResumeAutoDig", "StopAutoDig",
        )
        endpoints = "endpoints {\n  action-endpoints {\n" + "".join(
            f"    action-endpoint ({action}) {{ local-endpoint ({action}.js) }}\n" for action in actions
        ) + "  }\n}\n"
        result = tool.finalize_registered_sources(
            capsule, endpoints, "starintel-labs.starIntelOperations",
            "https://oauth.starintel.actor", "ops-client-1", "starintel_operations_oauth",
        )
        self.assertIn("id (starintel-labs.starIntelOperations)", result["capsule.bxb"])
        self.assertEqual(len(actions), result["endpoints.bxb"].count("authorization: user"))
        self.assertNotIn("authorization: user: optional", result["endpoints.bxb"])
        self.assertEqual(
            "https://starintel-labs-starIntelOperations.oauth.aibixby.com/auth/external/cb",
            result["redirect_uri"],
        )

    def test_write_finalizer_is_atomic_and_never_accepts_secret_value(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            endpoint = root / "resources" / "base" / "endpoints.bxb"
            endpoint.parent.mkdir(parents=True)
            (root / "capsule.bxb").write_text("capsule {\n  id (playground.starIntelOperations)\n}\n")
            actions = tool.OPERATIONS_ACTIONS
            endpoint.write_text("endpoints {\n  action-endpoints {\n" + "".join(
                f"    action-endpoint ({action}) {{ local-endpoint ({action}.js) }}\n" for action in actions
            ) + "  }\n}\n")
            result = tool.finalize_capsule_tree(
                root, "starintel-labs.starIntelOperations", "https://oauth.starintel.actor",
                "ops-client-1", "starintel_operations_oauth",
            )
            self.assertTrue((root / "authorization.bxb").is_file())
            self.assertEqual(len(actions), endpoint.read_text().count("authorization: user"))
            self.assertIn("redirect_uri", result)


if __name__ == "__main__":
    unittest.main()
