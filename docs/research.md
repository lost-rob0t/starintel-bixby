# Research — Samsung Bixby + StarIntel

Checked: **2026-08-24**.

This file records evidence used to design the StarIntel Bixby capsules. It deliberately separates current Samsung behavior from StarIntel backend reality.

## Samsung/Bixby findings

Official sources:

- Capsule initialization / `capsule.bxb`: https://bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.prep-capsule
- Capsule reference: https://bixbydevelopers.com/dev/docs/reference/type/capsule
- Current targets: https://bixbydevelopers.com/dev/docs/reference/type/capsule.targets.target
- Endpoint configuration: https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.actions.configuring-endpoints
- OAuth: https://bixbydevelopers.com/dev/docs/dev-guide/developers/modeling.actions.using-oauth
- Confirmation views: https://bixbydevelopers.com/dev/docs/reference/type/confirmation-view
- Views: https://bixbydevelopers.com/dev/docs/dev-guide/developers/creating-ui.building-views.views
- NL training: https://bixbydevelopers.com/dev/docs/dev-guide/developers/handling-nl.training-for-nl
- Private/public submissions: https://bixbydevelopers.com/dev/docs/dev-guide/developers/deploying.can-submission
- On-device testing: https://bixbydevelopers.com/dev/docs/dev-guide/developers/testing.on-device

### Capsule format/runtime

Current official examples use capsule format `3`. Runtime version `9` is the newest runtime listed by the current reference. JavaScript runtime v2 is current and is explicitly selectable with:

```bxb
runtime-version (9) {
  js-runtime-version (2)
}
```

The initial StarIntel capsules target US English mobile and watch:

- `bixby-mobile-en-US`
- `bixby-watch-en-US`

Samsung currently lists both as valid targets. Public Marketplace submission is available for mobile/watch in the US, while on-device testing is documented as mobile-only. Watch behavior therefore requires Simulator validation and, ultimately, Marketplace/device evidence; do not claim watch on-device validation from a mobile private submission.

### Remote endpoints

Bixby remote endpoints:

- are declared in `endpoints.bxb` under `resources/...`;
- accept/return JSON shaped like Bixby concepts;
- must be publicly accessible;
- use POST/PUT when concept parameters are sent in the request body.

StarIntel capsules therefore call only a public StarIntel-owned Bixby gateway. They never call `.star.intel`, CouchDB, RabbitMQ, Valkey, or private Quasar services.

### OAuth

Bixby supports OAuth 2.0 authorization-code flow and PKCE. OAuth configuration lives in root-level `authorization.bxb`. Client secrets are referenced by `client-secret-key` and stored in Bixby Developer Center Configuration & Secrets rather than capsule source.

OAuth endpoints must use HTTPS.

Planned user scopes:

**Intelligence**

- `starintel.read`
- `starintel.search`

**Operations**

- `starintel.read`
- `starintel.targets.write`
- `starintel.autodig.read`
- `starintel.autodig.control`

The exact OAuth provider URLs/client IDs are deployment configuration, not hard-coded secrets. Capsule source will reference configured values.

### Confirmations / transactions

Bixby actions support `confirm { by (...) }`, with presentation/controls in a `confirmation-view`. Transactional actions can use `type (Commit)` and transactional confirmation views.

StarIntel requires this for:

- target commit;
- Auto-Dig start;
- Auto-Dig stop.

Pause/resume should also confirm by default because they change run state. The server still authorizes every mutation independently after Bixby confirmation.

### Training

Current Bixby Studio uses Training Editor 2.1; the legacy training editor was removed in Bixby Studio 8.21.1. Samsung explicitly warns against hand-editing generated training files.

Repository policy:

- model actions/concepts first;
- add training in Bixby Studio;
- keep examples representative and small;
- use continuation training only for utterances that actually require prior context;
- record aligned-NL/test intent expectations in human-readable fixtures before Studio training, but do not fabricate generated training source.

### Submission / device validation

Private submissions are the supported pre-release submission type and enable on-device testing. A submission requires the capsule to use the organization namespace registered in Developer Center and requires team/collaborator access.

The repository currently uses `starintel.*` as the intended capsule namespace. If Developer Center registers a different organization namespace, change the IDs before submission and update the OAuth redirect URIs accordingly.

## StarIntel server findings

Inspected `lost-rob0t/starintel-server` at commit `8f6e50701081f0335c7552082dba5ff392b859e5`.

### Machine-readable contract

The server publishes public:

- `/openapi.json`
- `/client-manifest.json`

and mounts contracted operations by operation ID. At the inspected commit, the machine-readable contracted surface is primarily system/authentication operations. Person search, document search, and target creation have not yet been migrated into that operation registry.

This matters: the Bixby gateway must not pretend the legacy routes are the durable StarIntel client contract.

### Current legacy search / target routes

Current implementation evidence exists for:

- `GET /search` — bounded CouchDB FTS-backed search;
- `POST /new/target/:actor` — target document creation.

These are compatibility evidence only. The gateway adapter may temporarily isolate them if required, but the intended direction is named/canonical operations in the StarIntel client contract.

### Authentication/error behavior

The contracted surface carries authority/scopes and correlation IDs, and defines a normalized error envelope. The Bixby gateway should preserve correlation IDs internally and translate upstream errors into the stable Bixby error set rather than proxying raw StarIntel conditions/bodies.

## Quasar document links

Inspected `lost-rob0t/quasar` at commit `560208d0906cf564dd59050bca9a0f9341a3c55d`.

The current frontend route is:

```text
/documents/:id
```

This is the verified route shape for the public document-link builder. The gateway must still obtain the **configured public Quasar origin** from infrastructure and safely encode the document ID. It must reject private origins, private IPs, `.star.intel`, and upstream API URLs.

## Quasar / Auto-Dig control findings

The inspected Quasar frontend contains an `AgentSupervisor` with durable-looking run records and lifecycle transitions including:

- create run;
- get run;
- list runs;
- pause;
- stop;
- retry (which accepts paused runs).

However, this implementation is frontend-side code and is **not evidence of an authoritative public/server control API**. A search for the proposed `quasar.control.v1` server boundary did not identify an owning typed/versioned control service in the inspected repositories.

Therefore:

1. the capsule contract may model start/status/get/list/pause/resume/stop semantics;
2. the Bixby gateway must not call browser state, local frontend records, Playwright, CouchDB, RabbitMQ, or UI internals to implement them;
3. before gateway Auto-Dig realization, the owning Quasar/Auto-Dig runtime needs a typed/versioned service boundary if one is still absent;
4. `resume` must be a first-class semantic operation even if an implementation internally maps it to a safe retry/continue transition.

## Design consequences

- Keep the public Bixby API versioned at `/v1/bixby/...`.
- Freeze Bixby response/request fixtures independently of legacy backend route shapes.
- Separate Intelligence and Operations authority at both capsule and OAuth-scope level.
- Treat person matching as conservative: one clear match, explicit ambiguity list, or not found.
- Return bounded document results and canonical public Quasar links.
- Target workflow is prepare -> Bixby confirmation -> commit -> receipt, with retry-safe idempotency.
- Auto-Dig start returns a durable run ID immediately; long research never holds open the Bixby request.
- Gateway work in `starintel-infra` remains blocked until this capsule contract/fixture slice is coherent and frozen.
