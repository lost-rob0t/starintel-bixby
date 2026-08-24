# StarIntel Bixby research

Status: Phase 0 evidence for issue #4. This document records current official Samsung/Bixby behavior and current StarIntel/Quasar/infra authority boundaries. It is not evidence of Simulator, private-submission, Developer Center, or on-device execution.

## Samsung/Bixby — current official findings

Research date: 2026-08-24.

Official documentation currently remains live at the Bixby Developer Center and advertises Bixby Developer Studio 8.23.1-r24c.2843029.

Primary sources:

- https://bixbydevelopers.com/
- https://corp.bixbydevelopers.com/dev/docs/reference/type/capsule
- https://corp.bixbydevelopers.com/dev/docs/reference/type/endpoints
- https://corp.bixbydevelopers.com/dev/docs/reference/type/authorization
- https://corp.bixbydevelopers.com/dev/docs/reference/capsule-config
- https://corp.bixbydevelopers.com/dev/docs/get-started/quick-start
- https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/creating-ui.building-views.views
- https://corp.bixbydevelopers.com/dev/docs/reference/type/confirmation-view
- https://corp.bixbydevelopers.com/dev/docs/sample-capsules/samples/continuation
- https://corp.bixbydevelopers.com/dev/docs/reference/type/attribution-link
- https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/testing
- https://bixbydevelopers.com/dev/docs/dev-guide/developers/testing.on-device
- https://bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.can-submission

### Capsule project shape

`capsule.bxb` is still the required root capsule metadata file. Current examples use `format (3)` and explicit targets such as `bixby-mobile-en-US`. The exact production namespace must come from the operator's registered Developer Center team/capsule. Development may use `playground`; private/public submission must use the registered organization namespace.

`endpoints.bxb` is still required and belongs under a resources locale/base directory. It maps actions to local JavaScript endpoints or remote HTTP endpoints. Remote HTTP endpoints remain a supported first-class model, but this project should keep a thin local endpoint adapter where it materially helps inject OAuth/configuration, normalize gateway errors, and keep the public gateway origin configurable.

Bixby models remain concept/action based. Training examples bind natural utterances to goals and annotated concepts, and the NL model must be compiled before Simulator training validation.

### Authentication

`authorization.bxb` remains the current supported authorization declaration. User-scoped `oauth2-authorization-code` is explicitly documented with authorize endpoint, client ID, `client-secret-key`, optional scope, and token endpoint.

The `client-secret-key` is a lookup key for a secret entered in Developer Center Configuration & Secrets. The secret value must not be committed to this repository.

Decision for StarIntel: use user OAuth 2 authorization-code unless later Developer Center constraints falsify it. Keep three identities distinct:

1. Bixby/Samsung user authorization context;
2. Bixby gateway service identity;
3. gateway-to-StarIntel/Quasar upstream service identity.

Capsule authority is split:

- Intelligence: `starintel.read`, `starintel.search` only.
- Operations: only the additional scopes needed for target and Auto-Dig actions (`starintel.targets.write`, `starintel.autodig.read`, `starintel.autodig.control`).

### Configuration and secrets

Developer Center Configuration & Secrets remains current. `config.get()` reads configuration and `secret.get()`/secret lookup reads secrets in local JavaScript. Dynamic configuration changes require a new Simulator conversation/reset/recompile before they are visible.

Important constraint: dynamic Developer Center endpoint URI values are not directly available inside `endpoints.bxb`; use local JavaScript when the gateway origin must be supplied by Developer Center configuration rather than hard-coded in the model file.

### Views, links, and confirmation

`result-view` and locale resource views remain current. For public StarIntel document links, prefer `attribution-link` in a result view. Samsung explicitly recommends attribution links over unconditional app launch for most cases because the user makes an explicit decision to leave Bixby.

Do not make every document result force a browser/app launch. `app-launch` is policy-constrained and can cause marketplace rejection when misused.

For mutating operations, `confirmation-view` remains current. Samsung documents a corresponding action with the `confirm` key, and `mode (Transactional)` requires a corresponding transactional action. This directly supports StarIntel's required prepare -> confirmation -> commit split.

### Conversational context

Bixby still supports continuation training. A continuation goal explicitly reuses previous conversational context. This is the correct platform mechanism for follow-ups such as:

- "Who is this person?"
- "Tell me more about this person"
- "Show me documents about this person"
- "What's it doing?" after selecting/starting an Auto-Dig run.

Cold-start follow-ups must elicit the missing person/run rather than guess.

### Testing and submission

Bixby Developer Studio still provides Device Simulator, Debug Console, stories/assertions, training compilation, revision loading, and submission tooling.

On-device testing requires Developer Center registration and a compatible Bixby device. Samsung recommends private submissions or local workspace builds until public release. A private submission requires the registered organization namespace and Developer Center capsule registration. Current on-device docs support loading either a private revision or a local Studio workspace via QR code.

No proprietary Samsung validation has been run from this environment. Therefore this repository may only claim static/fixture checks until an operator performs the documented Studio/Developer Center/device gate.

### Explicitly rejected Samsung paths

- Samsung Automation Studio Capsule Node shortcut: not the Bixby capsule architecture required here.
- one giant privileged capsule: violates least privilege and epic #1.
- app-launch after every document result: contrary to current punch-out guidance; attribution links are preferred.
- browser/UI automation as runtime authority: not a StarIntel or Bixby control plane.

## StarIntel server — current authority

Evidence source: `lost-rob0t/starintel-server` at commit `8f6e50701081f0335c7552082dba5ff392b859e5`.

The server exposes machine-readable discovery at:

- `GET /openapi.json` — OpenAPI 3.1.2;
- `GET /client-manifest.json` — normalized StarIntel client manifest.

The initial contracted operation registry currently covers health/server metadata, auth/user/credential lifecycle, and contract discovery. Legacy document/search/target routes remain implemented but are not yet all migrated into the generated named-operation registry.

Important boundary: the Bixby gateway must discover and prefer named generated/client operations when available. Any unavoidable legacy StarIntel routes must be isolated behind one adapter rather than copied into capsule logic or scattered through the gateway.

Current HTTP behavior includes:

- bearer API-key auth by default;
- allow-listed CORS;
- `X-Correlation-ID` support;
- bounded `X-Request-Timeout-Ms` support;
- client-safe errors with status/message/correlation ID and generally stable codes;
- bounded JSON request bodies.

Current legacy routes relevant to discovery include `GET /search`, `GET /document/:id`, `POST /new/target/:actor`, and `GET /targets/:actor`. These are compatibility facts, not the desired public Bixby contract.

### Targets and actors

Current actor docs describe target rows with legacy fields such as `actor`, `target`, `delay`, `recurring`, and `options`, plus normal StarIntel metadata. Actor routing supports registered in-process actors and external actor names which route to RabbitMQ internally.

This proves a critical security boundary: Bixby must never accept an arbitrary raw actor implementation name or RMQ topology from speech. The Operations capsule uses a presentation-level `TargetActor`; the gateway must resolve it against canonical actor discovery/allow-list metadata and then translate to the owning StarIntel target operation.

The current server documentation does not establish a safe Bixby idempotency contract for target creation. Exactly-once-under-retry must be verified at the owning target boundary before Operations commit is enabled. Do not fake idempotency in the capsule.

## Quasar / Auto-Dig — current authority

Evidence source: `lost-rob0t/quasar` at commit `560208d0906cf564dd59050bca9a0f9341a3c55d`.

Quasar has a real typed/versioned control envelope: `quasar.control.v1`. The envelope carries protocol, command ID, command name, payload, client, and workspace metadata; responses are typed success/error envelopes and events carry workspace revision/operation IDs.

The current core control-plane command registry found during Phase 0 includes system capability discovery plus workspace/document/graph operations. It is actor-backed and owns canonical workspace state through a single-writer command actor.

Crucially, Phase 0 did **not** find canonical Auto-Dig run lifecycle commands (start/pause/resume/stop/status) in that core registry. `auto-dig-quasar` currently exposes UI/agent-supervisor code, which is not sufficient authority for Bixby runtime control.

Design consequence: the Bixby contract may model desired Auto-Dig operations, but the gateway must capability-discover them. If the required durable run lifecycle is absent, the smallest correct extension belongs in the owning Quasar/Auto-Dig control-plane repository before gateway implementation. No UI automation, direct Auto-Dig DB edits, RabbitMQ shortcuts, or shell compatibility layer.

## StarIntel infrastructure — current authority

Evidence source: `starintel-labs/starintel-infra` main.

Canonical service exposure is declared in `inventory/services.nix`. Public services declare a backend host/port/scheme, a `publicName`, and an ingress-capable `edgeHost`; Caddy routes are derived from inventory and backend addresses come from host inventory. Public DNS is a separate provider concern.

The private `.star.intel` namespace must never be published publicly or used for public ACME. The existing public edge model uses `starintel.actor` names through the declared edge.

At Phase 0, `inventory/services.nix` contains only the public `ingest` service. There is no declared public Quasar service and therefore **no currently verified canonical public Quasar document origin in infra**. The example in docs is explicitly commented/private and is not deployed authority.

Design consequence: document results can carry `DocumentUrl` in the frozen Bixby contract, but the gateway must build it from one configured public origin only after infra declares/validates the real public Quasar document route. Never hard-code `quasar.starintel.actor` from an example.

Infra epic authority: `starintel-labs/starintel-infra#34`. Gateway work remains blocked until capsule contract/fixtures are coherent and frozen.

## Phase-0 design consequences

1. Build two actual capsules with separate OAuth scopes.
2. Use local JavaScript endpoint adapters where needed to read Developer Center configuration/secrets and normalize the gateway boundary; the capsule never receives StarIntel service credentials.
3. Use continuation training for selected-person and selected-run follow-up; never infer visual/screen identity.
4. Use transactional confirmation views for target creation and Auto-Dig mutations.
5. Use attribution links for public document navigation by default.
6. Freeze `/v1/bixby/...` request/response fixtures before infra implementation.
7. Treat person/document/target capsule concepts as Bixby contracts only. Backend canonical schemas remain owned by StarIntel.
8. Capability-discover StarIntel and Quasar operations. The current StarIntel machine-readable registry is incomplete for legacy search/target, and the current Quasar core registry does not prove Auto-Dig lifecycle support.
9. Keep Auto-Dig mutations disabled at integration time until an owning typed control-plane operation exists for each requested behavior.
10. Public document URL generation remains a gateway/infra concern; no public Quasar origin has yet been verified from current infra inventory.

## Open risks that must be resolved before production mutation

- canonical person-search result schema/operation must be identified or added at its owning StarIntel boundary;
- target actor discovery suitable for user-facing selection must be identified; raw actor/RMQ identifiers are not acceptable;
- target idempotency under HTTP retry must be proven or fixed at the owning StarIntel boundary;
- durable Auto-Dig run lifecycle control commands must be identified or implemented in the owning control plane;
- public Quasar document origin and stable route must be declared/verified in infra before any `DocumentUrl` is emitted;
- Developer Center namespace, OAuth client registration, secret keys, private submission, Simulator and Galaxy testing remain manual operator gates.
