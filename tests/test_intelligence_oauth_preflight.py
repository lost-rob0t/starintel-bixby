import importlib.util
import pathlib
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "preflight_intelligence_oauth.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("preflight_intelligence_oauth", TOOL)
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load OAuth preflight tool")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class IntelligenceOauthPreflightTests(unittest.TestCase):
    def test_accepts_live_provider_when_only_authorize_and_token_surfaces_exist(self):
        tool = load_tool()
        responses = {
            ("GET", "https://oauth.starintel.actor/oauth/authorize"): tool.ProbeResult(400, b"missing client_id"),
            ("POST", "https://oauth.starintel.actor/oauth/token"): tool.ProbeResult(400, b"missing grant_type"),
            ("GET", "https://oauth.starintel.actor/"): tool.ProbeResult(404, b"not found"),
            ("GET", "https://oauth.starintel.actor/api/v1/search"): tool.ProbeResult(404, b"not found"),
        }

        def fake_request(method, url, **_kwargs):
            return responses[(method, url)]

        report = tool.preflight("https://oauth.starintel.actor", request=fake_request)
        self.assertTrue(report.ok)
        self.assertEqual("https://oauth.starintel.actor", report.origin)
        self.assertEqual(400, report.authorize_status)
        self.assertEqual(400, report.token_status)
        self.assertEqual(404, report.root_status)
        self.assertEqual(404, report.unapproved_status)

    def test_reports_dns_failure_without_leaking_resolver_details(self):
        tool = load_tool()

        def fail_request(_method, _url, **_kwargs):
            raise OSError("Name or service not known: resolver-internal.example")

        report = tool.preflight("https://oauth.starintel.actor", request=fail_request)
        self.assertFalse(report.ok)
        self.assertEqual("DNS_UNRESOLVED", report.error_code)
        self.assertEqual("public OAuth hostname does not resolve", report.public_message)
        self.assertNotIn("resolver-internal", report.public_message)

    def test_fails_closed_on_unknown_network_error_without_leaking_details(self):
        tool = load_tool()

        def fail_request(_method, _url, **_kwargs):
            raise OSError("opaque transport failure from internal adapter")

        report = tool.preflight("https://oauth.starintel.actor", request=fail_request)
        self.assertFalse(report.ok)
        self.assertEqual("UNREACHABLE", report.error_code)
        self.assertEqual("public OAuth origin is not reachable over HTTPS", report.public_message)
        self.assertNotIn("internal adapter", report.public_message)

    def test_rejects_unapproved_route_exposure_even_if_oauth_routes_work(self):
        tool = load_tool()
        responses = {
            ("GET", "https://oauth.starintel.actor/oauth/authorize"): tool.ProbeResult(400, b"missing client_id"),
            ("POST", "https://oauth.starintel.actor/oauth/token"): tool.ProbeResult(400, b"missing grant_type"),
            ("GET", "https://oauth.starintel.actor/"): tool.ProbeResult(404, b"not found"),
            ("GET", "https://oauth.starintel.actor/api/v1/search"): tool.ProbeResult(401, b"unauthorized"),
        }

        report = tool.preflight(
            "https://oauth.starintel.actor",
            request=lambda method, url, **_kwargs: responses[(method, url)],
        )
        self.assertFalse(report.ok)
        self.assertEqual("UNAPPROVED_ROUTE_EXPOSED", report.error_code)

    def test_never_sends_credentials_and_bounds_requests(self):
        tool = load_tool()
        calls = []

        def fake_request(method, url, **kwargs):
            calls.append((method, url, kwargs))
            if url.endswith("/oauth/authorize") or url.endswith("/oauth/token"):
                return tool.ProbeResult(400, b"expected validation error")
            return tool.ProbeResult(404, b"not found")

        report = tool.preflight("https://oauth.starintel.actor", request=fake_request)
        self.assertTrue(report.ok)
        for _method, _url, kwargs in calls:
            headers = kwargs.get("headers", {})
            self.assertNotIn("Authorization", headers)
            self.assertLessEqual(kwargs.get("timeout", 99), 5)
            self.assertLessEqual(len(kwargs.get("body", b"")), 128)

    def test_reuses_renderer_public_origin_validation(self):
        tool = load_tool()
        for origin in (
            "http://oauth.starintel.actor",
            "https://localhost",
            "https://10.0.0.1",
            "https://oauth.star.intel",
        ):
            with self.subTest(origin=origin):
                with self.assertRaises(ValueError):
                    tool.preflight(origin, request=mock.Mock())


if __name__ == "__main__":
    unittest.main()
