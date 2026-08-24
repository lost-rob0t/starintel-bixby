# StarIntel Bixby architecture

## Ownership split

```text
Samsung Bixby
  |
  | HTTPS + Bixby user OAuth
  v
StarIntel public edge
  |
  v
starintel-bixby-gateway               starintel-infra owns deploy/identity/ingress
  |
  +--> StarIntel client adapter ------> starintel-server canonical capabilities
  |
  `--> Quasar adapter ----------------> quasar canonical control plane/runtime
                                         |
                                         `--> Auto-Dig owning services/actors
```

`lost-rob0t/starintel-bixby` owns only the two Samsung capsules, Bixby-local presentation/input models, training intent, views, the normalized public contract and fixtures.

`starintel-labs/starintel-infra` owns the deployed gateway, packaging, systemd/NixOS integration, service identity, secrets, public edge route, health, monitoring and deployment.

The gateway is an adapter, not a new database or runtime authority.

## Capsule authority split

### StarIntel Intelligence

Read-only capabilities:

- resolve/disambiguate a person;
- carry selected `PersonProfile` context across a conversation;
- search documents;
- select/display document results;
- produce canonical public Quasar document links.

It has no target-write or Auto-Dig-control actions and receives only logical read/search OAuth scopes.

### StarIntel Operations

Privileged capabilities:

- prepare and commit canonical StarIntel targets;
- inspect Auto-Dig status/runs;
- prepare/start Auto-Dig;
- pause/resume/stop a selected run when the owning runtime exposes those capabilities.

It receives only the additional scopes needed for these operations.

## Person context

`ResolvePerson` is a side-effect-free Bixby `Search` action. It accepts at least one of:

- a `PersonQuery` from the current utterance; or
- an existing selected `PersonProfile` from conversational context.

The normalized result separates one selected profile from candidate matches. Same-name ambiguity is represented explicitly and must be resolved by the user. A cold-start `Who is this person?` has no selected `PersonProfile`, so Bixby must collect a person query rather than inventing visual/screen context.

V1 has no facial recognition, camera recognition, OCR, foreground-app scraping, or visible-person inference.

## Document context

Document search is a side-effect-free Bixby `Search` operation. It accepts a text query and/or selected `PersonProfile`, plus bounded optional filters. Results are normalized presentation records and are never raw StarIntel documents.

The gateway constructs public document links through one configured public-origin component. The current verified Quasar UI route is `/documents/:id`; the public origin is discovered from infrastructure, not hard-coded in either capsule.

## Target transaction

```text
utterance
  -> prepare/normalize TargetDraft
  -> canonical actor/type validation
  -> Bixby transaction concept
  -> transactional confirmation view
  -> Commit action
  -> gateway re-auth/re-validation/idempotent commit
  -> TargetReceipt
```

Preparing a target never mutates StarIntel. Voice input cannot provide internal routing topology or implementation identifiers.

## Auto-Dig transaction and activity

Bixby's native transaction/activity model is used instead of a capsule-local state machine:

```text
prepare AutoDigDraft      BeginTransaction
confirm + start           Commit
returned AutoDigRun       activity concept
status                    RefreshActivity
pause/resume              UpdateActivity
stop/cancel               CancelActivity
```

The `Commit` returns a durable run identifier immediately. Research execution continues behind the owning Quasar/Auto-Dig runtime and is observed through later activity refreshes.

Current Quasar migration state must be checked before advertising each control operation. Missing canonical capabilities are implemented at the Quasar/owning runtime boundary, not simulated in the gateway.

## Public contract boundary

The public Bixby-facing API is versioned independently of internal StarIntel or `quasar.control.v1` envelopes. Planned family:

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

This is frozen only after the capsule models and versioned fixtures agree. Internal route/protocol details never leak into capsule training or user-visible models.

## Identity boundary

Three identities remain separate:

1. **Bixby user identity** — OAuth access token presented to the gateway.
2. **Gateway service identity** — infrastructure identity used to run the gateway.
3. **StarIntel upstream service identity** — narrowly scoped credential used by the gateway's backend adapter where required.

No upstream service credential is sent to Samsung or stored in this repository.

## Failure boundary

The gateway normalizes backend failures into stable public error codes. Capsules convert those codes into concise dialog/views. Raw StarIntel/Quasar/RabbitMQ/CouchDB errors, stack traces, credentials and private endpoints never cross the boundary.

## Implementation order

1. Finish Bixby models/actions/views and realistic training plan.
2. Define and validate versioned contract fixtures.
3. Validate every locally available capsule gate and record proprietary Samsung gates as pending.
4. Only then implement the gateway in `starintel-infra`.
5. Extend StarIntel/Quasar owning boundaries only where verified capability gaps require it.
