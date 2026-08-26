# StarIntel Bixby research

Status: current Phase-0/contract-freeze evidence for issues #4 and #8, refreshed 2026-08-26. This document records documentation/repository evidence only. It is **not** evidence that Samsung Developer Center registration, Bixby Developer Studio Simulator execution, private submission, or Galaxy on-device validation has occurred.

## 2026-08-26 Samsung/Bixby revalidation

Current official Samsung/Bixby documentation was rechecked before freezing the v1 contract. The current platform still supports the capsule mechanics used here.

Primary official sources:

- Capsule metadata: https://corp.bixbydevelopers.com/dev/docs/reference/type/capsule
- Quick start / capsule project shape: https://corp.bixbydevelopers.com/dev/docs/get-started/quick-start
- Endpoints: https://corp.bixbydevelopers.com/dev/docs/reference/type/endpoints
- Remote endpoints: https://corp.bixbydevelopers.com/dev/docs/reference/type/endpoints.action-endpoints.action-endpoint.remote-endpoint
- Authorization: https://corp.bixbydevelopers.com/dev/docs/reference/type/authorization
- OAuth actions: https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.actions.using-oauth
- Views: https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/creating-ui.building-views.views
- Confirmation views: https://corp.bixbydevelopers.com/dev/docs/reference/type/confirmation-view
- Conversational continuation sample: https://corp.bixbydevelopers.com/dev/docs/sample-capsules/samples/continuation
- Attribution links: https://corp.bixbydevelopers.com/dev/docs/reference/type/attribution-link
- Developer Studio / IDE: https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/ide
- Testing: https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/testing
- On-device testing: https://bixbydevelopers.com/dev/docs/dev-guide/developers/testing.on-device
- Submission: https://bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.can-submission

### Capsule project shape

`capsule.bxb` remains the root capsule metadata file. Current examples use format 3 and explicit Bixby targets/locales. `endpoints.bxb` remains the action-to-local/remote endpoint mapping surface. Remote HTTP endpoints remain supported and can declare explicit methods.

The production capsule namespace must come from the registered Samsung Developer Center organization. `playground` is acceptable for development but is not a substitute for a registered namespace during private/public submission.

### Actions, views and confirmations

Bixby remains concept/action based. Result views and confirmation views remain current. Mutating StarIntel actions use Bixby's transactional/commit confirmation pattern: prepare data, render the proposed operation, require an affirmative confirmation, then execute the commit action. Confirmation is a Bixby UX gate only; StarIntel/Quasar owner boundaries still reauthenticate, reauthorize and revalidate the mutation.

Current confirmation evidence supports `type (Commit)` actions with a corresponding confirmation definition/view. StarIntel Operations therefore keeps confirmed target commit and confirmed Auto-Dig start/stop, with confirmation also used for pause/resume unless a later platform constraint requires otherwise.

### Conversational context

Bixby continuations remain current. Continuation goals can reuse selected conversational context, which is the appropriate mechanism for:

- `Who is this person?`
- `Tell me more about this person`
- `Show me documents about this person`
- `What's it doing?` after an Auto-Dig run is selected or started.

A cold-start contextual phrase has no valid selected entity and must elicit the missing person/run instead of guessing.

### Document navigation

Attribution links remain supported and are preferred for StarIntel document results. The user explicitly chooses to leave Bixby. Do not force browser/app launch after every result.

### OAuth and Configuration & Secrets

`authorization.bxb` remains a root-level capsule declaration. User OAuth supports `oauth2-authorization-code` with an authorize endpoint, client ID, `client-secret-key`, optional scope, and token endpoint. `client-secret-key` names a secret stored in Samsung Developer Center Configuration & Secrets; the secret value must never be committed here.

Endpoint authorization remains action-specific. Intelligence can therefore support public guest requests plus optional signed-in requests, while Operations requires signed-in user authorization.

The capsule must not treat `$vivContext.bixbyUserId` as StarIntel identity and must not forward raw `$vivContext`, Samsung profile/device/location context, access tokens in request bodies, or ambient Samsung metadata. StarIntel identity comes from the canonical OAuth principal.

Current authority split:

- Intelligence guest: server-owned synthetic public-read authority.
- Intelligence signed-in: optional StarIntel user OAuth, read/search scopes only.
- Operations: same StarIntel human principal with canonical `targets:dispatch` plus bounded Auto-Dig read/control scopes.

### Samsung manual boundary

Bixby Developer Studio remains the supported development/testing environment and includes Simulator-oriented testing. Private submission and on-device testing still require real Developer Center registration and a compatible Galaxy/Bixby device. No such proprietary/manual execution was performed in this environment; repository CI is limited to deterministic static/fixture/model/reference checks.

### Explicitly rejected Samsung paths

- Samsung Automation Studio Capsule Node shortcut.
- one giant privileged capsule.
- manual bearer-token plumbing in capsule request bodies.
- forwarding raw `$vivContext`.
- forced browser punch-out after every document result.
- browser/UI automation as StarIntel or Auto-Dig runtime authority.

## StarIntel server — current owner boundary

Remote GitHub state is authoritative.

The canonical StarIntel OAuth provider is merged in `lost-rob0t/starintel-server` at `4f2f70126bc59e18681844019460a33709e1eba6`. Core owns human principals, OAuth authorization/token handling, redirect/client/scope validation, PKCE, bearer verification and normal authorization semantics.

The generic target-create candidate is `lost-rob0t/starintel-server#127`. At the 2026-08-26 refresh it is **open/draft**, not merged authority. It implements the desired owner-side direction: generic `/api/v1/targets`, canonical `targets:dispatch`, principal-bound deterministic idempotency, changed-content conflict detection and narrow receipts. The Bixby contract may target those semantics, but gateway target commit must remain gated on an exact-head-green merged owner interface or an equivalent canonical successor. The gateway must not recreate idempotency locally as the authoritative target owner.

For person/document/search calls, prefer machine-readable named client/capability operations where available. Any unavoidable legacy route compatibility belongs in one gateway adapter, never scattered through capsule JavaScript.

Voice-facing `TargetActor`/`TargetType` values remain presentation inputs only. The gateway must resolve them against canonical StarIntel actor/type metadata. Speech cannot select queue names, exchanges, routing keys, shell commands, private URLs, or raw implementation identifiers.

## Quasar / Auto-Dig — current owner boundary

Quasar main still defines the typed/versioned envelope `quasar.control.v1` in `control-plane/src/protocol.lisp`.

A complete desired Auto-Dig lifecycle was implemented and exact-head tested on `lost-rob0t/quasar#43`, including:

- `autodig.status`
- `autodig.run.get`
- `autodig.run.list`
- `autodig.run.start`
- `autodig.run.pause`
- `autodig.run.resume`
- `autodig.run.stop`

That PR was closed **without merge**. Therefore those lifecycle commands are not production/main authority merely because their branch was green. Current Bixby Operations correctly keeps Auto-Dig lifecycle capability-gated and fail-closed. The public Bixby contract may define the presentation shape, but `starintel-bixby-gateway` must return `AUTODIG_CAPABILITY_UNAVAILABLE` until deployed capability discovery proves the corresponding owner operation is present.

No browser automation, UI state mutation, direct Auto-Dig database edits, RabbitMQ shortcuts, or shell compatibility layer may substitute for that missing owner capability.

Starting a run, once supported, must return a durable run ID immediately and must not keep a Bixby HTTP request open for research completion.

## Infrastructure — current owner boundary

`starintel-labs/starintel-infra` is the canonical owner of the deployed `starintel-bixby-gateway` and its Nix packaging/modules, public ingress, service identity/secrets, health/readiness, monitoring and deployment. Infra epic #34 records that ownership.

Public path:

```text
Samsung/Bixby
  -> StarIntel public edge
  -> starintel-bixby-gateway
  -> private StarIntel and Quasar/Auto-Dig owner services
```

The gateway is a translation/security boundary, not a new intelligence database, target state owner, Auto-Dig state owner, or schema authority.

Canonical infra conventions remain:

- `main` is desired state;
- services/ingress are declared through repository inventory/modules rather than ad-hoc deploy scripts;
- backend addresses come from inventory, not hard-coded host IPs;
- secrets stay outside Git and the Nix store using existing secret/systemd-credential conventions;
- validation includes repository-native scripts plus `nix flake check --show-trace`.

A verified public Quasar document origin/route is still not established by the capsule repository. `DocumentUrl` remains part of the Bixby response contract, but the gateway must build links through one configured public-origin component after infra/UI evidence establishes the real public document route. Never hard-code a guessed hostname or emit `.star.intel`, private IP, CouchDB/RabbitMQ, or raw backend API links.

## Frozen-contract consequences

1. Keep two capsules with separated authority.
2. Intelligence supports guest public read plus optional signed-in user read/search.
3. Operations requires the same signed-in StarIntel human principal with only additional target/Auto-Dig scopes.
4. Public Bixby API family is `/v1/bixby/...`.
5. Person ambiguity is explicit; no silent same-name selection.
6. Selected person/run context is conversational Bixby state backed by stable owner IDs.
7. Documents return bounded results (default 5, hard bounded by the frozen contract) and safe public attribution links.
8. Target flow is prepare -> confirmation -> commit -> narrow receipt; owning StarIntel target idempotency is mandatory.
9. Auto-Dig routes are capability-discovered and fail closed until real owner lifecycle support is deployed.
10. Stable client errors never expose stack traces, Lisp/Python conditions, worker/lease internals, backend topology or credentials.
11. The contract is frozen in `contracts/bixby-v1.json` plus fixtures before infra gateway implementation.
12. Samsung Simulator/private-submission/Galaxy validation remains a manual operator gate documented in `docs/testing.md`.
