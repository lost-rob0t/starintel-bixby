# StarIntel Bixby research

Status: Phase 0 evidence for issue #4, with issue #11 dual-mode authentication/provider re-check. This document records current official Samsung/Bixby behavior and current StarIntel/Quasar/infra authority boundaries. It is not evidence of Simulator, private-submission, Developer Center, or on-device execution.

## Samsung/Bixby — current official findings

Research date: 2026-08-24.

Official documentation currently remains live at the Bixby Developer Center and advertises Bixby Developer Studio 8.23.1-r24c.2843029.

Primary sources:

- https://bixbydevelopers.com/
- https://corp.bixbydevelopers.com/dev/docs/reference/type/capsule
- https://corp.bixbydevelopers.com/dev/docs/reference/type/endpoints
- https://corp.bixbydevelopers.com/dev/docs/reference/type/authorization
- https://corp.bixbydevelopers.com/dev/docs/reference/capsule-config
- https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.actions.using-oauth
- https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.actions.configuring-endpoints
- https://bixbydevelopers.com/dev/docs/dev-guide/release-notes/sdk.2020-Q1-SDK-Release-Notes
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

Current endpoint authorization is opt-in. An action endpoint with no authorization annotation does not use OAuth. Samsung also documents optional user OAuth for endpoints: an endpoint may use optional user authorization so public-compatible actions do not automatically force login. Local JavaScript can detect whether `$vivContext.accessToken` exists, use ordinary `http` methods for anonymous execution, use `http.oauth*` methods for signed-in execution, and throw an `authorization-error` to trigger login/reauthorization when an authenticated credential is invalid or revoked.

Important privacy consequence: `$vivContext` contains Samsung/Bixby runtime context and must not be forwarded wholesale. For StarIntel, local JavaScript should inspect only the presence of the managed access token needed to select authenticated transport. It must not treat `$vivContext.bixbyUserId` as StarIntel identity, and it must not copy access tokens, Samsung profile/device/location metadata, or other ambient context into StarIntel request bodies, queries, logs, or returned models.

Current issue #11 decision for StarIntel Intelligence is therefore dual-mode, not anonymous-only and not mandatory-login-only:

1. Guest mode: no login; the gateway/server uses the server-owned synthetic public-read context from `starintel-server#109`.
2. Signed-in mode: optional Bixby user OAuth; the StarIntel OAuth provider maps the token to a real StarIntel human principal and normal server-side authorization determines that principal's readable/searchable datasets and tenants.

An authenticated request that receives invalid/expired/revoked credentials must fail closed and trigger reauthorization rather than silently retrying as guest. A valid token with insufficient scope remains forbidden. The public path remains available for requests that are genuinely guest-compatible.

The same human-user identity architecture is reused by Operations with additional scopes. Do not create a second Operations account system and do not substitute a capsule-global service credential for user identity.

The canonical StarIntel OAuth provider is now implemented and merged in `lost-rob0t/starintel-server` at `4f2f70126bc59e18681844019460a33709e1eba6`. Core StarIntel owns `/oauth/authorize`, `/oauth/token`, existing human principals, exact redirect/client/scope validation, S256 PKCE, one-time authorization codes, short-lived bearer tokens and downstream request-security-context authorization. The optional `starintel-bixby` Common Lisp add-on projects Samsung-specific configuration and explicitly creates a normal core OAuth client; it does not fork the auth system.

What remains before a real Intelligence `authorization.bxb` can be committed is registration/deployment data, not provider architecture: a deployed public HTTPS OAuth origin running that provider, the real registered Bixby capsule ID and exact callback URI, the public OAuth client ID returned by StarIntel client registration, and the Developer Center `client-secret-key` name containing the one-time client secret. These values must not be fabricated. Until they exist, `auth.requirements.json.registrationComplete` stays false and endpoint authorization annotations remain absent.

Keep four identities distinct:

1. Bixby/Samsung runtime/user context;
2. optional authenticated StarIntel human principal;
3. Bixby gateway service identity;
4. gateway-to-StarIntel/Quasar upstream service identity.

Capsule authority remains split:

- Intelligence guest: public synthetic read only.
- Intelligence signed-in: canonical read/search scopes only.
- Operations: only the additional scopes needed for target and Auto-Dig actions (`starintel.targets.write`, `starintel.autodig.read`, `starintel.autodig.control` or canonical server equivalents).

### Configuration and secrets

Developer Center Configuration & Secrets remains current. `config.get()` reads configuration and `secret.get()`/secret lookup reads secrets in local JavaScript. Dynamic configuration changes require a new Simulator conversation/reset/recompile before they are visible.

Important constraint: dynamic Developer Center endpoint URI values are not directly available inside `endpoints.bxb`; use local JavaScript when the gateway origin must be supplied by Developer Center configuration rather than hard-coded in the model file. Samsung's current OAuth declaration still requires a public `client-id` and a `client-secret-key` reference in capsule source; the secret value itself remains in Developer Center.

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
- anonymous-only Intelligence as the final architecture: loses real StarIntel user support.
- mandatory login for every Intelligence lookup: unnecessarily removes public guest search.
- manual bearer-token plumbing in capsule request bodies/headers: Bixby-managed OAuth HTTP methods are the safer supported path.
- app-launch after every document result: contrary to current punch-out guidance; attribution links are preferred.
- browser/UI automation as runtime authority: not a StarIntel or Bixby control plane.

## StarIntel server — current authority

Evidence source: `lost-rob0t/starintel-server` through merge `4f2f70126bc59e18681844019460a33709e1eba6`, with earlier Phase-0 route/schema evidence retained below where still applicable.

The server exposes machine-readable discovery at:

- `GET /openapi.json` — OpenAPI 3.1.2;
- `GET /client-manifest.json` — normalized StarIntel client manifest.

The contracted operation registry covers health/server metadata, auth/user/credential lifecycle, contract discovery and the growing versioned public surface. Legacy document/search/target routes remain implemented but are not yet all migrated into the generated named-operation registry.

Important boundary: the Bixby gateway must discover and prefer named generated/client operations when available. Any unavoidable legacy StarIntel routes must be isolated behind one adapter rather than copied into capsule logic or scattered through the gateway.

Current HTTP behavior includes:

- legacy API-key and OAuth bearer authentication through the shared bearer/request-security-context boundary;
- public `/oauth/authorize` and `/oauth/token` protocol endpoints with exact client/redirect/scope validation and S256 PKCE;
- public synthetic-context `/api/v1/search` and aggregate stats from #109 without weakening mutation authorization;
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

Crucially, Phase 0 did not find canonical Auto-Dig run lifecycle commands (start/pause/resume/stop/status) in that core registry. `auto-dig-quasar` currently exposes UI/agent-supervisor code, which is not sufficient authority for Bixby runtime control.

Design consequence: the Bixby contract may model desired Auto-Dig operations, but the gateway must capability-discover them. If the required durable run lifecycle is absent, the smallest correct extension belongs in the owning Quasar/Auto-Dig control-plane repository before gateway implementation. No UI automation, direct Auto-Dig DB edits, RabbitMQ shortcuts, or shell compatibility layer.

## StarIntel infrastructure — current authority

Evidence source: `starintel-labs/starintel-infra` main.

Canonical service exposure is declared in `inventory/services.nix`. Public services declare a backend host/port/scheme, a `publicName`, and an ingress-capable `edgeHost`; Caddy routes are derived from inventory and backend addresses come from host inventory. Public DNS is a separate provider concern.

The private `.star.intel` namespace must never be published publicly or used for public ACME. The existing public edge model uses `starintel.actor` names through the declared edge.

Current inventory declares the public `ingest.starintel.actor` service through `ord-edge`, but that declaration alone is not proof that the newly merged OAuth provider build is deployed there. The adopted `starintel-ingest` profile deliberately preserves existing application service definitions until live unit/Nix state has been captured, so provider deployment must be verified against the live service before the hostname is committed as OAuth authority.

There is still no declared public Quasar service and therefore no currently verified canonical public Quasar document origin in infra. The example in docs is explicitly commented/private and is not deployed authority.

Design consequence: document results can carry `DocumentUrl` in the frozen Bixby contract, but the gateway must build it from one configured public origin only after infra declares/validates the real public Quasar document route. Never hard-code `quasar.starintel.actor` from an example.

Infra epic authority: `starintel-labs/starintel-infra#34`. Gateway work remains blocked until capsule contract/fixtures are coherent and frozen.

## Phase-0 design consequences

1. Build two actual capsules with separated authority.
2. Intelligence is dual-mode: guest public search plus optional StarIntel user OAuth for read/search; Operations reuses the same user identity with additional scopes.
3. Use local JavaScript endpoint adapters to read Developer Center configuration, select guest vs Bixby-managed OAuth transport, normalize the gateway boundary, and avoid forwarding ambient Bixby context; the capsule never receives StarIntel service credentials.
4. Use continuation training for selected-person and selected-run follow-up; never infer visual/screen identity.
5. Use transactional confirmation views for target creation and Auto-Dig mutations.
6. Use attribution links for public document navigation by default.
7. Freeze `/v1/bixby/...` request/response fixtures before infra implementation, including guest/authenticated variants and fail-closed token behavior.
8. Treat person/document/target capsule concepts as Bixby contracts only. Backend canonical schemas remain owned by StarIntel.
9. Capability-discover StarIntel and Quasar operations. The current StarIntel machine-readable registry is incomplete for legacy search/target, and the current Quasar core registry does not prove Auto-Dig lifecycle support.
10. Keep Auto-Dig mutations disabled at integration time until an owning typed control-plane operation exists for each requested behavior.
11. Public document URL generation remains a gateway/infra concern; no public Quasar origin has yet been verified from current infra inventory.

## Open risks that must be resolved before production mutation

- issue #11 still needs the real Bixby registration tuple: verified deployed OAuth origin, registered capsule ID/callback, StarIntel OAuth client ID and Developer Center secret-key name before `authorization.bxb` and optional endpoint authorization can be committed;
- canonical person-search result schema/operation must be identified or added at its owning StarIntel boundary;
- target actor discovery suitable for user-facing selection must be identified; raw actor/RMQ identifiers are not acceptable;
- target idempotency under HTTP retry must be proven or fixed at the owning StarIntel boundary;
- durable Auto-Dig run lifecycle control commands must be identified or implemented in the owning control plane;
- public Quasar document origin and stable route must be declared/verified in infra before any `DocumentUrl` is emitted;
- Developer Center namespace, OAuth client registration/secret storage, private submission, Simulator and Galaxy testing remain manual operator gates.
