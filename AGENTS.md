# StarIntel Bixby repository rules

This repository is the canonical home of Samsung/Bixby-facing StarIntel integration code.

## Ownership

- Samsung/Bixby capsule source, capsule-local JavaScript, Bixby presentation/input models, training, views, contract fixtures, and Samsung testing documentation live here.
- Generic StarIntel authentication, authorization, person/document/search behavior, target lifecycle/idempotency, and generic Auto-Dig/Quasar client boundaries belong to their owning StarIntel/Quasar repositories.
- The optional `starintel-bixby` add-on in `lost-rob0t/starintel-server` owns only Samsung/Bixby-specific HTTP projection, Bixby-safe response shaping, callback/client configuration helpers, and add-on route lifecycle.
- `starintel-labs/starintel-infra` owns declarative deployment, public-edge exposure, TLS/DNS, secret wiring, health checks, and monitoring for StarIntel Server with that add-on enabled. There is no standalone Bixby gateway service.
- Canonical StarIntel document, person, target, relation, actor, and Auto-Dig runtime schemas remain owned by their existing repositories. Capsule concepts are presentation/input contracts only and must not redefine those schemas.

## Authority and security

- The **StarIntel Intelligence** capsule is read-only. It must not receive target-write or Auto-Dig-control authority.
- The **StarIntel Operations** capsule is privileged and must request only the additional scopes required for target and Auto-Dig operations.
- All state-changing operations require an explicit Bixby confirmation before commit.
- StarIntel must independently authenticate, authorize, validate, and idempotently commit every mutation after confirmation.
- Never commit StarIntel API keys, OAuth client secrets, private tokens, backend admin credentials, private certificates, or generated private Samsung metadata.
- Never return CouchDB URLs, RabbitMQ URLs, Valkey endpoints, `.star.intel` names, private IPs, raw backend API URLs, raw actor implementation identifiers, queue names, exchanges, or routing keys to users.
- Voice input must never become a shell command, backend URL, RabbitMQ topology value, or raw implementation identifier.

## Runtime boundaries

- Discover backend capabilities instead of assuming they exist.
- Use canonical StarIntel capability/client operations when available.
- Samsung-specific `/v1/bixby/...` adapters must delegate to generic owner APIs; never duplicate target, auth, search, or Auto-Dig semantics inside the add-on.
- Isolate unavoidable legacy StarIntel route compatibility in one owner-side adapter rather than copying legacy route strings into capsule logic.
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
- Freeze the Bixby-facing HTTP contract and fixtures before implementing the corresponding Bixby-specific server projection.
- Contract changes caused by real backend constraints must update capsule models/fixtures and the server add-on projection together.
- Do not weaken, skip, swallow, or false-green tests.
- Keep manual Samsung testing requirements explicit in `docs/testing.md`.
- Keep commits coherent. Capsule code stays here; generic server behavior stays in core; deployment stays in infra.

## RAGE work order

1. Current Samsung + StarIntel/Quasar architecture research.
2. Capsule repository bootstrap and comprehensive epic.
3. Intelligence capsule models/actions/views/training.
4. Operations capsule models/actions/views/training and confirmation flows.
5. Freeze versioned `/v1/bixby/...` contract + fixtures.
6. Run every locally available capsule/contract validation gate.
7. Implement only the Samsung-specific projections in the optional `starintel-bixby` server add-on, delegating to exact-head-green generic owner APIs.
8. Expose StarIntel Server + add-on through existing `starintel-infra` ingress; do not create a parallel gateway service.
9. Verify exact-head CI and document the remaining Samsung Developer Center/Simulator/Galaxy manual gate truthfully.