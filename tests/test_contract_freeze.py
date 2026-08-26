import json
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts" / "bixby-v1.json"
AGENTS = ROOT / "AGENTS.md"
OPERATIONS = ROOT / "fixtures" / "operations"
ERRORS = ROOT / "fixtures" / "errors"

REQUIRED_ROUTES = {
    "/v1/bixby/person/resolve",
    "/v1/bixby/documents/search",
    "/v1/bixby/targets/prepare",
    "/v1/bixby/targets/commit",
    "/v1/bixby/autodig/status",
    "/v1/bixby/autodig/run",
    "/v1/bixby/autodig/runs",
    "/v1/bixby/autodig/start",
    "/v1/bixby/autodig/pause",
    "/v1/bixby/autodig/resume",
    "/v1/bixby/autodig/stop",
}

REQUIRED_ERRORS = {
    "UNAUTHORIZED",
    "FORBIDDEN",
    "INVALID_REQUEST",
    "PERSON_NOT_FOUND",
    "AMBIGUOUS_PERSON",
    "DOCUMENTS_NOT_FOUND",
    "TARGET_TYPE_UNSUPPORTED",
    "ACTOR_UNSUPPORTED",
    "AUTODIG_CAPABILITY_UNAVAILABLE",
    "AUTODIG_RUN_NOT_FOUND",
    "RATE_LIMITED",
    "UPSTREAM_TIMEOUT",
    "UPSTREAM_UNAVAILABLE",
    "INTERNAL_ERROR",
}

REQUIRED_OPERATION_FIXTURES = {
    "target-prepare-success.json",
    "target-commit-success.json",
    "autodig-status-success.json",
    "autodig-run-success.json",
    "autodig-runs-success.json",
    "autodig-start-success.json",
    "autodig-pause-success.json",
    "autodig-resume-success.json",
    "autodig-stop-success.json",
}

FORBIDDEN_TEXT = (
    ".star.intel",
    "rabbitmq",
    "couchdb",
    "routingkey",
    "exchange",
    "leaseid",
    "workerid",
    "workspaceid",
    "stack trace",
)


def load(path):
    return json.loads(path.read_text())


def walk_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)
    elif isinstance(value, str):
        yield value


class ContractFreezeTests(unittest.TestCase):
    def test_repository_rules_assign_gateway_to_infra(self):
        text = AGENTS.read_text().lower()
        self.assertIn("starintel-bixby-gateway", text)
        self.assertIn("starintel-labs/starintel-infra", text)
        self.assertNotIn("there is no standalone bixby gateway service", text)
        self.assertNotIn("no standalone bixby gateway", text)

    def test_contract_declares_exact_public_v1_surface_and_authority_split(self):
        contract = load(CONTRACT)
        self.assertEqual(contract["version"], "v1")
        self.assertEqual(contract["owner"], "starintel-labs/starintel-infra:starintel-bixby-gateway")
        routes = {route["path"]: route for route in contract["routes"]}
        self.assertEqual(set(routes), REQUIRED_ROUTES)

        self.assertEqual(routes["/v1/bixby/person/resolve"]["authorization"], "optional-user")
        self.assertEqual(routes["/v1/bixby/documents/search"]["authorization"], "optional-user")
        self.assertEqual(routes["/v1/bixby/targets/prepare"]["authorization"], "required-user")

        for path in REQUIRED_ROUTES - {
            "/v1/bixby/person/resolve",
            "/v1/bixby/documents/search",
        }:
            self.assertEqual(routes[path]["authorization"], "required-user")

        mutation_paths = {
            "/v1/bixby/targets/commit",
            "/v1/bixby/autodig/start",
            "/v1/bixby/autodig/pause",
            "/v1/bixby/autodig/resume",
            "/v1/bixby/autodig/stop",
        }
        for path in mutation_paths:
            self.assertIs(routes[path]["confirmationRequired"], True)

        self.assertEqual(routes["/v1/bixby/targets/commit"]["upstreamScope"], "targets:dispatch")
        self.assertEqual(set(contract["errors"]), REQUIRED_ERRORS)

    def test_contract_never_exposes_internal_authority_or_transport_fields(self):
        contract = load(CONTRACT)
        text = "\n".join(walk_strings(contract)).lower()
        for forbidden in FORBIDDEN_TEXT:
            self.assertNotIn(forbidden, text)

    def test_operations_success_fixture_inventory_is_complete_and_safe(self):
        names = {path.name for path in OPERATIONS.glob("*.json")}
        self.assertTrue(REQUIRED_OPERATION_FIXTURES <= names)

        for path in OPERATIONS.glob("*.json"):
            fixture = load(path)
            self.assertIn(fixture["status"], {200, 201, 202})
            self.assertIn("request", fixture)
            self.assertIn("response", fixture)
            text = "\n".join(walk_strings(fixture)).lower()
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, text, f"{path}: leaked {forbidden}")

    def test_error_fixture_inventory_is_stable_and_client_safe(self):
        names = {path.stem for path in ERRORS.glob("*.json")}
        self.assertTrue(REQUIRED_ERRORS <= names)

        for code in REQUIRED_ERRORS:
            fixture = load(ERRORS / f"{code}.json")
            self.assertEqual(fixture["response"]["error"]["code"], code)
            self.assertIn(fixture["status"], {400, 401, 403, 404, 409, 413, 429, 500, 502, 503, 504})
            text = "\n".join(walk_strings(fixture)).lower()
            for forbidden in FORBIDDEN_TEXT:
                self.assertNotIn(forbidden, text, f"{code}: leaked {forbidden}")


if __name__ == "__main__":
    unittest.main()
