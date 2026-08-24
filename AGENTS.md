# StarIntel Bixby repository rules

This repository is the canonical home of Samsung/Bixby-facing StarIntel integration code.

## Ownership

- Samsung/Bixby capsule source, capsule-local code, Bixby presentation/input models, Bixby training, views, contract fixtures, and Samsung testing documentation live here.
- StarIntel infrastructure, public-edge configuration, deployed gateway services, Nix/NixOS modules, deployment inventory, and service credentials do **not** live here. Those belong in `starintel-labs/starintel-infra`.
- Canonical StarIntel document, person, target, relation, actor, and Auto-Dig runtime schemas remain owned by their existing StarIntel/Quasar repositories. Capsule models are presentation/input contracts only and must not redefine those schemas.

## Authority and security

- The **StarIntel Intelligence** capsule is read-only. It must not receive target-write or Auto-Dig-control authority.
- The **StarIntel Operations** capsule is privileged and must request only the additional scopes required for target and Auto-Dig operations.
- All state-changing operations require an explicit Bixby confirmation before commit.
- The backend must independently authorize and validate every request after confirmation.
- Never commit StarIntel API keys, OAuth client secrets, private tokens, backend admin credentials, private certificates, or generated private Samsung metadata.
- Never return CouchDB URLs, RabbitMQ URLs, Valkey endpoints, `.star.intel` names, private IPs, raw backend API URLs, raw actor implementation identifiers, queue names, exchanges, or routing keys to users.
- Voice input must never become a shell command, backend URL, RabbitMQ topology value, or raw implementation identifier.

## Runtime boundaries

- Discover backend capabilities instead of assuming they exist.
- Use canonical StarIntel capability/client operations when available.
- Isolate unavoidable legacy StarIntel route compatibility behind a single gateway adapter; do not duplicate legacy route strings in capsule logic.
- Auto-Dig operations must use the owning Quasar/Auto-Dig control plane. Do not automate a browser, use Playwright against the UI, edit the Git-backed Auto-Dig corpus directly, access CouchDB/RabbitMQ directly, or add a shell-script compatibility runtime.
- Long-running Auto-Dig work must return a durable run identifier promptly and be queried separately for status.

## Samsung/Bixby rules

- Research current official Samsung/Bixby documentation before relying on syntax or tooling behavior. Do not assume old tutorials are current.
- Use real Bixby capsules; do not implement this through Samsung Automation Studio's Capsule Node shortcut.
- Keep the two capsules distinct: `StarIntel Intelligence` and `StarIntel Operations`.
- Model user-facing data with Bixby concepts/actions/views rather than opaque JSON blobs.
- Do not claim Simulator, private-submission, Developer Center, or on-device validation unless it actually occurred.
- The development namespace may be `playground` until the operator supplies/registers the real Developer Center namespace. Public/private submission artifacts must use the registered namespace.

## Testing and delivery

- TDD/fixtures first: failing deterministic test or contract validation -> minimal implementation -> local verification -> integration verification.
- Freeze the Bixby-facing HTTP contract and fixtures before gateway implementation begins.
- Contract changes caused by real backend constraints must update capsule models/fixtures and the gateway contract together.
- Do not weaken, skip, swallow, or false-green tests.
- Keep manual Samsung testing requirements explicit in `docs/testing.md`.
- Keep commits coherent and do not mix infrastructure changes into this repository.

## RAGE work order

1. Current Samsung + StarIntel/Quasar architecture research.
2. Capsule repository bootstrap and comprehensive epic.
3. Intelligence capsule models/actions/views/training.
4. Operations capsule models/actions/views/training and confirmation flows.
5. Freeze versioned `/v1/bixby/...` contract + fixtures.
6. Run every locally available capsule/contract validation gate.
7. Only then implement the deployed gateway in `starintel-labs/starintel-infra`.
8. Verify exact-head CI and document the remaining Samsung Developer Center/Simulator/Galaxy manual gate truthfully.
