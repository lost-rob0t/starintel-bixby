from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
CAPSULE = ROOT / "capsules" / "starintel-operations"


def read(path: str) -> str:
    return (CAPSULE / path).read_text()


def test_operations_auth_requests_only_needed_autodig_scopes():
    auth = json.loads(read("auth.requirements.json"))
    assert auth["requiredScopes"] == [
        "starintel.targets.write",
        "starintel.autodig.read",
        "starintel.autodig.control",
    ]
    assert auth["principalMode"] == "user"
    assert auth["forwardVivContext"] is False


def test_autodig_actions_exist_and_use_bounded_public_contract():
    expected = {
        "GetAutoDigStatus": "/v1/bixby/autodig/status",
        "GetAutoDigRun": "/v1/bixby/autodig/run",
        "ListAutoDigRuns": "/v1/bixby/autodig/runs",
        "StartAutoDig": "/v1/bixby/autodig/start",
        "PauseAutoDig": "/v1/bixby/autodig/pause",
        "ResumeAutoDig": "/v1/bixby/autodig/resume",
        "StopAutoDig": "/v1/bixby/autodig/stop",
    }
    endpoints = read("resources/base/endpoints.bxb")
    for action, route in expected.items():
        assert (CAPSULE / f"models/action/{action}.model.bxb").exists()
        assert (CAPSULE / f"code/{action}.js").exists()
        assert f"action-endpoint ({action})" in endpoints
        assert route in read(f"code/{action}.js")


def test_mutating_autodig_actions_are_commit_and_confirmation_gated():
    for action in ("StartAutoDig", "PauseAutoDig", "ResumeAutoDig", "StopAutoDig"):
        model = read(f"models/action/{action}.model.bxb")
        assert "type (Commit)" in model
        assert "confirm" in model
        assert (CAPSULE / f"resources/en/views/{action}.confirmation.bxb").exists()


def test_read_actions_are_not_commit_actions():
    for action in ("GetAutoDigStatus", "GetAutoDigRun", "ListAutoDigRuns"):
        assert "type (Commit)" not in read(f"models/action/{action}.model.bxb")


def test_autodig_run_models_preserve_public_identity_only():
    run_model = read("models/structures/AutoDigRun.model.bxb")
    for field in ("runId", "requestId", "status", "target"):
        assert field in run_model
    forbidden = ("workerId", "leaseId", "routingKey", "queue", "exchange", "workspaceId")
    for field in forbidden:
        assert field not in run_model


def test_training_covers_status_start_pause_resume_stop_and_contextual_run():
    training = read("training/operations-autodig.aligned.txt").lower()
    for phrase in (
        "start auto dig",
        "what is auto dig doing",
        "pause auto dig",
        "resume auto dig",
        "stop auto dig",
        "what is this run doing",
    ):
        assert phrase in training


def test_capsule_never_mentions_internal_quasar_protocol_or_private_topology():
    for path in CAPSULE.rglob("*"):
        if not path.is_file():
            continue
        text = path.read_text(errors="ignore").lower()
        assert "quasar.control.v1" not in text
        assert ".star.intel" not in text
        assert "rabbitmq" not in text
        assert "couchdb" not in text
