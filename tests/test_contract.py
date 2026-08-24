import json
import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "contracts" / "v1.json").read_text())
FIXTURES = json.loads((ROOT / "fixtures" / "v1" / "fixtures.json").read_text())


class ContractTests(unittest.TestCase):
    def test_contract_is_https_json_camel_case(self):
        self.assertEqual(CONTRACT["transport"]["scheme"], "https")
        self.assertEqual(CONTRACT["transport"]["content_type"], "application/json")
        self.assertEqual(CONTRACT["wire_case"], "camelCase")

    def test_all_routes_are_versioned_and_post(self):
        for endpoint in CONTRACT["endpoints"]:
            self.assertTrue(endpoint["path"].startswith("/v1/bixby/"), endpoint)
            self.assertEqual(endpoint["method"], "POST", endpoint)

    def test_intelligence_has_no_mutation_authority(self):
        intelligence = CONTRACT["capsules"]["intelligence"]
        self.assertEqual(intelligence["mutation_scopes"], [])
        self.assertEqual(set(intelligence["scopes"]), {"starintel.read", "starintel.search"})
        for endpoint in CONTRACT["endpoints"]:
            if endpoint["capsule"] != "intelligence":
                continue
            self.assertFalse(endpoint["confirmation"])
            self.assertFalse(any(scope.endswith(".write") or scope.endswith(".control") for scope in endpoint["scopes"]))

    def test_mutations_require_confirmation(self):
        required = {
            "targets.commit",
            "autodig.start.commit",
            "autodig.pause",
            "autodig.resume",
            "autodig.stop",
        }
        by_id = {endpoint["id"]: endpoint for endpoint in CONTRACT["endpoints"]}
        for endpoint_id in required:
            self.assertTrue(by_id[endpoint_id]["confirmation"], endpoint_id)

    def test_retry_sensitive_commits_require_idempotency(self):
        by_id = {endpoint["id"]: endpoint for endpoint in CONTRACT["endpoints"]}
        self.assertEqual(by_id["targets.commit"]["idempotency"], "required")
        self.assertEqual(by_id["autodig.start.commit"]["idempotency"], "required")
        target_draft = FIXTURES["target"]["commit"]["request"]["draft"]
        autodig_draft = FIXTURES["autodig"]["start_commit"]["request"]["draft"]
        self.assertIn("draftId", target_draft)
        self.assertIn("idempotencyKey", target_draft)
        self.assertIn("draftId", autodig_draft)
        self.assertIn("idempotencyKey", autodig_draft)

    def test_document_result_limit_is_bounded(self):
        limits = CONTRACT["limits"]
        self.assertGreaterEqual(limits["document_results_default"], 1)
        self.assertLessEqual(limits["document_results_default"], limits["document_results_max"])
        self.assertLessEqual(limits["document_results_max"], 10)
        self.assertLessEqual(FIXTURES["documents"]["success"]["request"]["limit"], limits["document_results_max"])

    def test_public_document_urls_are_https_and_use_verified_route(self):
        for hit in FIXTURES["documents"]["success"]["response"]["hits"]:
            parsed = urlparse(hit["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertTrue(parsed.netloc)
            self.assertTrue(parsed.path.startswith("/documents/"))
            self.assertNotIn(".star.intel", parsed.netloc)

    def test_autodig_start_is_nonblocking_receipt(self):
        response = FIXTURES["autodig"]["start_commit"]["response"]
        self.assertTrue(response["runId"])
        self.assertIn(response["status"], {"queued", "running"})
        self.assertNotIn("result", response)
        self.assertNotEqual(response["status"], "completed")

    def test_person_ambiguity_is_explicit(self):
        response = FIXTURES["person"]["ambiguous"]["response"]
        self.assertEqual(response["status"], "ambiguous")
        self.assertGreaterEqual(len(response["candidates"]), 2)
        self.assertNotIn("selected", response)

    def test_every_fixture_error_is_declared(self):
        declared = set(CONTRACT["errors"])
        fixture_errors = {item["error"] for item in FIXTURES["errors"].values()}
        fixture_errors.add(FIXTURES["person"]["not_found"]["error"]["error"])
        fixture_errors.add(FIXTURES["documents"]["empty"]["error"]["error"])
        self.assertTrue(fixture_errors <= declared)

    def test_public_wire_fields_do_not_use_snake_case(self):
        def check(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key not in {"start_prepare", "start_commit", "not_found", "rate_limited", "actor_unsupported", "target_type_unsupported", "autodig_unavailable", "autodig_run_missing"}:
                        self.assertNotIn("_", key, key)
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        for section in (FIXTURES["person"], FIXTURES["documents"], FIXTURES["target"]["prepare"], FIXTURES["target"]["commit"], FIXTURES["autodig"]["status"], FIXTURES["autodig"]["run"], FIXTURES["autodig"]["start_prepare"], FIXTURES["autodig"]["start_commit"], FIXTURES["autodig"]["pause"], FIXTURES["autodig"]["resume"], FIXTURES["autodig"]["stop"]):
            check(section)

    def test_no_private_or_internal_transport_leakage(self):
        payload = json.dumps({"contract": CONTRACT, "fixtures": FIXTURES}).lower()
        forbidden = [
            ".star.intel",
            "rabbitmq://",
            "amqp://",
            "couchdb://",
            "valkey://",
            "127.0.0.1",
            "localhost",
            "10.0.0.",
            "192.168.",
            "172.16.",
        ]
        for value in forbidden:
            self.assertNotIn(value, payload)

    def test_contract_does_not_accept_backend_topology_fields(self):
        payload = json.dumps(CONTRACT).lower()
        for field in ["routing_key", "exchange", "queue", "shell_command", "backend_url"]:
            self.assertNotRegex(payload, re.escape(f'"{field}"'))


if __name__ == "__main__":
    unittest.main()
