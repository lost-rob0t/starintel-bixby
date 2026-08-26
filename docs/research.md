# StarIntel Bixby research

Status: current Phase-0 and frozen-contract evidence, refreshed 2026-08-26 from official Samsung documentation plus exact GitHub owner state. This is **not** evidence that Samsung Developer Center registration, Bixby Developer Studio Simulator execution, private submission, or Galaxy on-device validation has occurred.

## Samsung/Bixby platform revalidation — 2026-08-26

Current official Samsung/Bixby documentation still supports the capsule model used by this repository.

Primary official sources:

- Capsule project metadata / initialization: https://bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.prep-capsule
- Developer Studio: https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/ide
- Quick start / actions, concepts and views: https://bixbydevelopers.com/dev/docs/get-started/quick-start
- Developer workflow / training / local-vs-remote endpoint choice: https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/life-cycle.developer-workflow
- Authorization reference: https://corp.bixbydevelopers.com/dev/docs/reference/type/authorization
- Continuations / conversational context: https://corp.bixbydevelopers.com/dev/docs/sample-capsules/samples/continuation
- User-context sample / private submission namespace note: https://corp.bixbydevelopers.com/dev/docs/sample-capsules/samples/user-context
- Release testing requirements: https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.prep-marketplace
- Samsung Bixby landing page: https://developer.samsung.com/bixby

Samsung's Automation Studio pages still describe Bixby remote endpoints, but Automation Studio's prebuilt Capsule/Capsule Node path is not the StarIntel architecture. StarIntel uses real capsules and a normal remote endpoint owned by StarIntel infrastructure.

### Capsule shape

`capsule.bxb` remains the root capsule metadata file. Current examples use format 3 and explicit targets such as `bixby-mobile-en-US`. `endpoints.bxb` remains the action endpoint mapping surface; remote HTTP endpoints remain supported. The production capsule ID must use the namespace registered to the operator/team in Samsung Developer Center; `playground` remains development-only.

### Actions, views, confirmations and conversational context

Bixby remains concept/action based, with result views for presentation. StarIntel Operations keeps a transactional prepare -> confirmation -> commit flow for mutations. Bixby confirmation is a UX gate only; StarIntel/Quasar must independently authenticate, authorize, validate and idempotently commit after confirmation.

Bixby continuation training remains the correct mechanism for context-dependent follow-ups. StarIntel uses it for selected-person and selected/recent-run follow-ups such as `Who is this person?`, `Tell me more`, `Show me documents about this person`, and `What's it doing?`. A cold-start contextual request must elicit the missing person/run instead of guessing.

### OAuth and Configuration & Secrets

`authorization.bxb` remains a root-level declaration. Current user authorization supports `oauth2-authorization-code` with concrete authorize/token endpoints, client ID, optional scope and a `client-secret-key` reference. `client-secret-key` names secret material configured in Samsung Developer Center Configuration & Secrets; the secret value must never be committed here.

StarIntel identity is the canonical OAuth human principal. `$vivContext.bixbyUserId` is not StarIntel identity. Capsules must not forward raw `$vivContext`, Samsung profile/device/location context, or access tokens inside arbitrary request bodies.

Authority split remains:

- Intelligence guest: server-owned synthetic public-read context.
- Intelligence signed-in: optional StarIntel user OAuth with read/search only.
- Operations: the same StarIntel human principal with canonical `targets:dispatch` plus bounded Auto-Dig read/control authority.

### Samsung manual boundary

Developer Studio/Simulator, Developer Center registration and Configuration & Secrets, private submission, and real Galaxy/Bixby testing remain manual/proprietary gates. Repository CI must not claim they were performed.

Explicitly rejected Samsung paths:

- Automation Studio Capsule Node shortcut;
- one giant privileged capsule;
- manual bearer-token plumbing in capsule request bodies;
- forwarding raw `$vivContext`;
- forced browser launch after every document result;
- UI/browser automation as StarIntel or Auto-Dig runtime authority.

## StarIntel server owner boundary

Remote GitHub state is authoritative.

StarIntel OAuth authorization-code support is canonical server authn/authz authority, not a Bixby-only identity system. Human principals, OAuth credential lifecycle, bearer verification, scopes, PKCE/redirect/client checks and request security context remain server-owned.

Generic target creation is still gated on `lost-rob0t/starintel-server#127` or a canonical merged successor. The intended owner semantics are a generic target-create operation, canonical `targets:dispatch`, principal-bound idempotency, changed-content conflict detection and narrow receipts. The Bixby gateway must not become the authoritative target state/idempotency owner.

Voice-facing target actor/type concepts are presentation inputs only. They must resolve against canonical StarIntel actor/type metadata; speech never controls RabbitMQ routing, exchanges, queues, shell commands, private URLs or implementation IDs.

## Quasar / Auto-Dig owner boundary

The typed/versioned lifecycle owner is Quasar `quasar.control.v1`.

Current Quasar main now contains the durable lifecycle from merged PR #43:

- `autodig.status`
- `autodig.run.get`
- `autodig.run.list`
- `autodig.run.start`
- `autodig.run.pause`
- `autodig.run.resume`
- `autodig.run.stop`

Merged PR #51 (`3acef088009137a737647b79c404dde615b96c1d`) additionally adds a generic delegated-human Auto-Dig session model: canonical `starintel.autodig.read` maps only to status/get/list; `starintel.autodig.control` adds start/pause/resume/stop; worker-only authority stays separate; run visibility/control is isolated by the server-authenticated human principal even inside one workspace.

A post-merge transport audit found one remaining P0 owner gap: the live WebSocket handler still submits commands without propagating the authenticated connection principal/authority kind into the control-plane actor path. That is tracked in `lost-rob0t/quasar#52` with tests-first PR #53. Until that transport provenance and the trusted StarIntel credential -> Quasar delegated-session registration adapter are exact-head green and merged/deployed, the Bixby gateway must continue to fail closed with `AUTODIG_CAPABILITY_UNAVAILABLE` rather than advertising lifecycle commands prematurely.

No gateway-local lifecycle DB, browser/Playwright authority, direct Auto-Dig storage edit, RabbitMQ shortcut or shell compatibility path is permitted. Once enabled, start returns a durable run ID promptly; Bixby never waits for research completion in one HTTP request.

## Infrastructure owner boundary

`starintel-labs/starintel-infra` owns deployed `starintel-bixby-gateway`, Nix package/module, public ingress, service identity/secrets, health/readiness, monitoring and deployment. Current realization is draft infra PR #72.

Public path:

```text
Samsung/Bixby
  -> StarIntel public edge
  -> starintel-bixby-gateway
  -> private StarIntel + Quasar/Auto-Dig owner services
```

The gateway is a translation/security boundary only. It is not an intelligence database, target owner, Auto-Dig state owner or alternate schema authority.

Infra requirements remain:

- declarative Nix/inventory/service ownership;
- no hard-coded backend IPs;
- credentials outside Git and the Nix store;
- bounded bodies/deadlines/results and client-safe errors;
- public document links built from a configured verified public origin and safely encoded IDs;
- `.star.intel`, private IPs, CouchDB/RabbitMQ/Valkey and raw owner control endpoints never returned to Samsung clients;
- repository-native validation plus exact-head CI before merge/deployment.

## Frozen-contract consequences

1. Keep two capsules with separated authority.
2. Intelligence supports guest public read plus optional signed-in user read/search.
3. Operations uses the same signed-in StarIntel human principal and only required target/Auto-Dig scopes.
4. Public Bixby API family remains `/v1/bixby/...`.
5. Person ambiguity is explicit; never silently choose same-name matches.
6. Selected person/run context is Bixby conversational state backed by stable owner IDs.
7. Document results remain bounded (default near 5) and use safe public attribution links.
8. Target flow remains prepare -> explicit confirmation -> commit -> narrow receipt with owning-boundary idempotency.
9. Auto-Dig is capability-discovered and fail-closed until the live delegated control path is proven.
10. Stable client errors never expose stack traces, Lisp/Python conditions, worker/lease internals, backend topology or credentials.
11. The frozen Bixby contract remains `contracts/bixby-v1.json` plus fixtures; owner-state evidence updates do not silently mutate that contract.
12. Simulator/private-submission/Galaxy validation remains a truthful manual operator gate in `docs/testing.md`.
