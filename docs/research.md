# StarIntel Bixby research

Research date: 2026-08-24

This document records current-source findings that constrain the StarIntel Bixby implementation. It intentionally separates verified platform/repository facts from design decisions that still require implementation or Samsung/operator access.

## Samsung / Bixby platform status

### Current developer surface

Verified current sources:

- Bixby Developer Center: https://bixbydevelopers.com/
- Samsung Bixby developer landing page: https://developer.samsung.com/bixby
- Bixby Developer Studio guide: https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/ide

The Developer Center currently advertises Bixby Developer Studio `8.23.1-r24c.2843029` and continues to document capsule creation, Marketplace/private submission, Simulator, and on-device testing.

This project must use real Bixby capsules. Samsung Automation Studio's prebuilt Capsule Node flow exists, but it is explicitly not the architecture for this repository.

### `capsule.bxb`

Current reference:

- https://corp.bixbydevelopers.com/dev/docs/reference/type/capsule
- https://bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.prep-capsule

Facts:

- `capsule.bxb` is required at the capsule root.
- The root contains one `capsule { ... }` node.
- Current examples use `format (3)` and target declarations such as `bixby-mobile-en-US`.
- The `playground` namespace can be used during development, but private/public submissions must use a capsule registered under the operator/team namespace.

Repository decision:

- Initial source may use a `playground.*` development ID only while the real Developer Center namespace is unknown.
- Do not claim private submission readiness until the registered namespace replaces it and Bixby Studio validates the capsule.

### `endpoints.bxb`

Current reference:

- https://corp.bixbydevelopers.com/dev/docs/reference/type/endpoints

Facts:

- `endpoints.bxb` is required for action implementations.
- Endpoint files live under capsule resources, normally `resources/base/` or a locale such as `resources/en-us/`; they are not root-level files.
- An action endpoint can use either a local JavaScript endpoint or a remote endpoint.

Design consequence:

- Prefer local JavaScript action endpoints calling one StarIntel-owned HTTPS gateway through the Bixby `http` module. This keeps the gateway origin in configuration and centralizes response/error normalization.
- Do not copy gateway route strings into every action file.

### Capsule configuration and secrets

Current reference:

- https://bixbydevelopers.com/dev/docs/reference/capsule-config

Facts:

- Non-secret configuration may live in `capsule.properties` or Developer Center Configuration & Secrets.
- JavaScript reads configuration using `config.get()`.
- JavaScript reads secret values using the secrets API.
- Developer Center values override capsule properties.
- Secrets stored in Developer Center are encrypted/obfuscated and are not intended to be committed in capsule source.
- Endpoint URIs can be configuration values when consumed by local JavaScript; values from Configuration & Secrets are not interpolated into `endpoints.bxb` itself.

Design consequence:

- The StarIntel gateway base URL should be read by one local JS gateway client from configuration rather than hard-coded into every endpoint.
- StarIntel service credentials must never exist in the capsule. Bixby user OAuth is separate from the gateway's upstream StarIntel service identity.

### Actions and concepts

Current references:

- https://bixbydevelopers.com/dev/docs/reference/type/action
- https://bixbydevelopers.com/dev/docs/reference/type/action.type
- https://bixbydevelopers.com/dev/docs/reference/type/structure

Facts:

- Action models are `*.model.bxb` files under `models/action`.
- Structure concepts are `*.model.bxb` files under `models/concepts`.
- `Search` actions are explicitly side-effect free and are the correct class for person/document lookup.
- Transactional action types include `BeginTransaction`, `UpdateTransaction`, `CancelTransaction`, and `Commit`.
- Post-commit activity action types include `RefreshActivity`, `UpdateActivity`, and `CancelActivity`.

Design consequence:

- Person resolution and document search are `Search` actions.
- Target creation should use a transaction concept for the prepared target and a `Commit` action for the actual backend mutation.
- Auto-Dig maps naturally to Bixby transaction/activity semantics:
  - prepare/start request -> transactional draft;
  - start -> `Commit`;
  - returned run -> activity concept;
  - status -> `RefreshActivity`;
  - pause/resume -> `UpdateActivity`;
  - stop/cancel -> `CancelActivity`.

This gives Bixby native conversational continuity without inventing a second Auto-Dig state machine.

### Confirmation views

Current references:

- https://corp.bixbydevelopers.com/dev/docs/reference/type/confirmation-view
- https://bixbydevelopers.com/dev/docs/reference/type/confirmation-view.mode
- https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.actions.transactional-workflows

Facts:

- Actions requesting confirmation use `confirm { by (core.Confirmation) }`.
- Confirmation views live in `*.view.bxb` files under locale/base resources.
- `mode (Transactional)` is supported for transactional confirmation.
- A transactional confirmation view must correspond to a transactional action.

Design consequence:

- Target commit and Auto-Dig start/stop must have explicit confirmation views.
- Pause/resume should also use confirmation unless later usability testing provides a strong reason not to.
- No backend mutation occurs in the prepare action.

### OAuth

Current references:

- https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.actions.using-oauth
- https://corp.bixbydevelopers.com/dev/docs/reference/type/authorization
- https://bixbydevelopers.com/dev/docs/reference/type/authorization.user.oauth2-authorization-code
- https://bixbydevelopers.com/dev/docs/reference/apis/js_api.http

Facts:

- Bixby currently supports OAuth 2.0 authorization-code flow and documents PKCE support.
- `authorization.bxb` lives at capsule root.
- OAuth client secret material is referenced through `client-secret-key` and stored in Developer Center Configuration & Secrets.
- OAuth endpoints must be HTTPS.
- Local JavaScript can use `http.oauthGetUrl()`, `http.oauthPostUrl()`, `http.oauthPutUrl()`, and `http.oauthDeleteUrl()` to attach the current user's OAuth access key.
- Bixby's OAuth callback URI follows `https://<encoded-capsule-id>.oauth.aibixby.com/auth/external/cb` and must be registered with the OAuth provider.

Design consequence:

- Use user OAuth for Bixby -> gateway identity/authorization.
- The capsule never receives the gateway's upstream StarIntel service credential.
- Do not write `authorization.bxb` with guessed authorization/token endpoints. Freeze it only after the actual public OAuth authority and capsule IDs are known.
- Intended logical scopes are:
  - `starintel.read`
  - `starintel.search`
  - `starintel.targets.write`
  - `starintel.autodig.read`
  - `starintel.autodig.control`
- Intelligence requests only read/search scopes. Operations requests only the additional scopes required for the action.

### Training

Current reference:

- https://bixbydevelopers.com/dev/docs/dev-guide/developers/handling-nl.training-for-nl
- https://corp.bixbydevelopers.com/dev/docs/sample-capsules/walkthroughs/tutorial

Facts:

- Training examples connect natural utterances to goals, routes, and concept values.
- A few representative entries are preferred over mechanically enumerating hundreds of variants.
- Samsung explicitly cautions that training files are not meant to be hand-edited outside Bixby Developer Studio because syntax errors can be introduced.

Design consequence:

- Keep the required utterance/training matrix in repository fixtures/documentation.
- Final Bixby training source must be entered/compiled through Bixby Studio when that proprietary tooling is available; do not fabricate a hand-authored training file and claim it compiled.

### Simulator, private submissions, and device testing

Current references:

- https://corp.bixbydevelopers.com/dev/docs/dev-guide/developers/testing.simulator
- https://bixbydevelopers.com/dev/docs/dev-guide/developers/testing.on-device
- https://bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.can-submission

Facts:

- Bixby Studio provides a Device Simulator for natural and Aligned NL, OAuth sessions, and execution-graph debugging.
- Private submissions are the appropriate submission type for pre-release testing and generate technical/training reports.
- A private submission requires a registered team/capsule namespace.
- On-device testing can use a private revision or the current Bixby Studio Workspace through the Simulator QR-code flow on supported mobile devices.
- Samsung recommends real-device testing before Marketplace submission.

Manual boundary:

- No Simulator, private-submission, or Galaxy-device validation has been performed by this repository bootstrap.
- Exact operator steps are tracked in `docs/testing.md`.

## StarIntel / Quasar architecture findings

### StarIntel Server

Source: `lost-rob0t/starintel-server` `README.org` and `docs/http-api-docs.org` on current `master`.

Verified facts:

- `starintel-server` owns persistent StarIntel ingest/storage/search/routing and RabbitMQ integration.
- It must not be exposed directly to the public Internet.
- Current server auth is API-key based by default with allow-listed CORS and client-safe error envelopes.
- Requests support `X-Correlation-ID` and bounded `X-Request-Timeout-Ms`.
- `GET /openapi.json` and `GET /client-manifest.json` expose the stable machine-readable operation contract.
- The initial generated/client contract does **not yet** include document search or target operations.
- Legacy compatibility routes currently include `GET /search`, `POST /new/target/:actor`, and `GET /targets/:actor`.
- Repository guidance says clients should prefer named SDK operations where contracted operations exist.

Design consequence:

- The Bixby gateway must use the generated/client operation layer for contracted operations.
- Any temporary use of legacy search/target routes must be isolated inside one StarIntel backend adapter.
- Capsule models and gateway business logic must not contain those route strings.
- If this integration requires reliable remote idempotency/capability semantics not present in the legacy target route, the correct fix is at the StarIntel owning boundary, not in capsule code.

### Quasar

Source: `lost-rob0t/quasar` `README.md` and `docs/CAPABILITY-BOUNDARY.md`.

Verified facts:

- Quasar is the canonical Common Lisp control plane/runtime.
- Browser UI is a client/projection layer in connected mode.
- Commands/responses use versioned `quasar.control.v1` envelopes with correlated IDs and stable error codes.
- Quasar owns migrated command/revision authority, persistent Sento supervision, privileged integrations, reconnect/replay, and runtime capability discovery.
- Missing backend/external services reduce advertised capabilities; they must not silently become browser substitutes.

Design consequence:

- Samsung does not speak `quasar.control.v1` directly.
- The Bixby gateway maps the public `/v1/bixby/...` contract to the canonical Quasar runtime/control API.

### Auto-Dig Quasar

Source: `lost-rob0t/auto-dig-quasar` `README.md`.

Verified facts:

- Auto-Dig Quasar is explicitly the Auto-Dig specialization of the browser UI, not a second canonical runtime.
- It exposes presentation for datasets/research runs/agents and can operate in bounded standalone mode.
- Its current stable document route is `/documents/:id`.
- Long-running privileged/service-backed capabilities belong behind the canonical runtime/service boundary.

Design consequence:

- Public document links can target the verified public Quasar UI `/documents/:id` route once the canonical public origin is discovered from infrastructure.
- The gateway must URL-encode IDs and refuse private/internal origins.

### Current Auto-Dig control-plane gap

Source: open `lost-rob0t/quasar#2`.

Verified open migration work currently includes:

- move actor list/run/pause/resume/stop to supervised Common Lisp actors;
- move research run/pause/resume/retry/kill to the control plane;
- enforce bounded mailboxes, runtime budgets, permissions, and audit;
- add target submission/scheduling through canonical integrations.

Design consequence:

- Do not claim all required Auto-Dig control operations already exist in canonical Quasar.
- The capsule-facing contract may model required start/status/pause/resume/stop behavior, but realization must either bind to already-landed runtime commands discovered later or implement the smallest required Quasar control-plane extension at that owning boundary.
- Never fabricate a gateway-local Auto-Dig runtime.

### StarIntel GPT Auto-Dig

Source: `lost-rob0t/starintel-gpt-auto-dig` `README.md`.

Verified facts:

- This repository owns a Git-backed evidence/research corpus and canonical document validation tooling.
- It explicitly forbids inventing a second StarIntel JSON shape.

Design consequence:

- The Bixby gateway does not edit this repository/database directly as a runtime control mechanism.

## starintel-infra findings

Sources: current `starintel-labs/starintel-infra` `flake.nix` and open infrastructure epics/issues.

Verified facts:

- The flake has a first-class service model that maps `backendHost`, `backendPort`, `scheme`, `publicName`, and `edgeHost` into public routes.
- The host module stack already imports ingress and secrets modules.
- `nix flake check` includes inventory, service-model, deployment-entrypoint and host/module evaluation checks.
- Current public-edge work uses an explicit Ubuntu/Caddy edge over WireGuard into the `10.60.60.0/24` application network.
- Public service names use `*.starintel.actor`; private service names use `.star.intel` and must remain private.
- Existing edge issues require explicit hostname -> approved backend routes, reject catch-all forwarding, and pair public DNS with configured Caddy routes.

Design consequence:

- `starintel-bixby-gateway` must be one explicit service entry in the existing service/inventory model.
- Do not create a parallel Caddy/deploy script.
- Do not hard-code a backend IP or publish a `.star.intel` name.
- The exact public hostname remains an infrastructure decision and must not be guessed in capsule source.

## Initial contract implications

The public Bixby-facing HTTP API should remain small, versioned, normalized, and independent of internal StarIntel/Quasar wire formats. Current planned family:

```text
POST /v1/bixby/person/resolve
POST /v1/bixby/documents/search
POST /v1/bixby/targets/prepare
POST /v1/bixby/targets/commit
POST /v1/bixby/autodig/status
POST /v1/bixby/autodig/run
POST /v1/bixby/autodig/start
POST /v1/bixby/autodig/pause
POST /v1/bixby/autodig/resume
POST /v1/bixby/autodig/stop
```

This family is not frozen until the capsule models and fixtures agree and the discovered backend limitations have been reconciled.

## Open research / implementation gates

- Determine the final registered Bixby Developer Center namespace and capsule IDs.
- Determine the public OAuth authorization/token authority; do not guess URLs in `authorization.bxb`.
- Determine the canonical public Quasar origin from `starintel-infra` service inventory/deployed edge state.
- Inspect the exact current StarIntel person document shape/search behavior needed for conservative person resolution.
- Inspect exact target actor registry/discovery and target idempotency semantics.
- Re-pin Quasar after capsule contract work to determine which Auto-Dig control-plane operations have landed versus which still require owning-runtime implementation.
