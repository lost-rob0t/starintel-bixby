# Architecture

## Repository boundary

`lost-rob0t/starintel-bixby` owns the Samsung-facing layer only. `starintel-labs/starintel-infra` owns the deployed gateway and public ingress.

```text
Bixby Intelligence capsule ─┐
                            ├─ HTTPS/OAuth ─> starintel-bixby-gateway
Bixby Operations capsule  ──┘                  ├─> StarIntel canonical client operations
                                               └─> Quasar/Auto-Dig canonical control plane
```

No capsule receives StarIntel service credentials.

## Capsule split

### StarIntel Intelligence

Authority: read/search only.

Actions:

- `ResolvePerson`
- `SearchDocuments`

Conversation state may preserve a selected `PersonMatch` so continuations such as “who is this person?”, “tell me more”, and document searches about the selected person can be planned without re-guessing identity.

### StarIntel Operations

Authority: target mutation + Auto-Dig read/control.

Actions:

- `PrepareTarget`
- `CommitTarget`
- `GetAutoDigStatus`
- `GetAutoDigRun`
- `ListAutoDigRuns`
- `PrepareAutoDigStart`
- `CommitAutoDigStart`
- `PauseAutoDigRun`
- `ResumeAutoDigRun`
- `StopAutoDigRun`

Mutations are not combined with discovery. Prepare actions return a normalized draft. A distinct confirmed commit action performs the mutation.

## Public HTTP contract

The capsule-facing API is versioned independently of backend implementation details.

```text
POST /v1/bixby/person/resolve
POST /v1/bixby/documents/search
POST /v1/bixby/targets/prepare
POST /v1/bixby/targets/commit
POST /v1/bixby/autodig/status
POST /v1/bixby/autodig/run
POST /v1/bixby/autodig/runs
POST /v1/bixby/autodig/start/prepare
POST /v1/bixby/autodig/start/commit
POST /v1/bixby/autodig/pause
POST /v1/bixby/autodig/resume
POST /v1/bixby/autodig/stop
```

`contracts/v1.json` is authoritative for this repository slice. Fixtures provide executable examples.

## Stable errors

The public contract uses a small explicit error code set:

- `UNAUTHORIZED`
- `FORBIDDEN`
- `INVALID_REQUEST`
- `PERSON_NOT_FOUND`
- `AMBIGUOUS_PERSON`
- `DOCUMENTS_NOT_FOUND`
- `TARGET_TYPE_UNSUPPORTED`
- `ACTOR_UNSUPPORTED`
- `AUTODIG_CAPABILITY_UNAVAILABLE`
- `AUTODIG_RUN_NOT_FOUND`
- `RATE_LIMITED`
- `UPSTREAM_TIMEOUT`
- `UPSTREAM_UNAVAILABLE`
- `INTERNAL_ERROR`

Errors never contain stack traces, internal hostnames, queue names, database URLs, or raw upstream bodies.

## Person resolution

The gateway maps canonical StarIntel search/person data into:

```text
PersonSearchResult
  status = matched | ambiguous | not_found
  query
  selected? PersonMatch
  candidates[] PersonMatch
```

A `PersonMatch` contains only public presentation fields: stable StarIntel ID, display name, aliases/identifiers suitable for disambiguation, short summary, and confidence/ranking metadata that is safe to expose.

The capsule never silently chooses among materially ambiguous same-name candidates.

Cold-start contextual requests such as “who is this person?” must prompt for a person rather than guessing from camera, foreground app, OCR, or screen contents.

## Document search

`SearchDocuments` accepts:

- query;
- optional dtype;
- optional selected person ID/context;
- bounded limit.

Default: 5 results. Contract maximum: 10.

Each result includes a public canonical Quasar URL built by the gateway from configured public origin + encoded document ID. Current verified frontend route shape is `/documents/:id`.

## Targets

`PrepareTarget` accepts user-facing subject/type/actor intent. Actor values are discovered/mapped server-side; raw routing topology is never accepted.

`TargetDraft` includes a gateway-generated `draft_id`, normalized actor/type/subject summary, and an idempotency token. `CommitTarget` accepts the draft identity/token, not a second arbitrary target payload.

Retrying the commit with the same idempotency identity must yield the same logical target receipt rather than create duplicates.

## Auto-Dig

The Bixby contract describes semantic operations, not current frontend implementation details.

Run states are normalized to a stable presentation vocabulary such as:

- queued
- running
- paused
- completed
- failed
- stopped

`start` is a prepare/commit transaction and returns a durable run ID immediately. Status/control requests refer to that run ID or a conversation-selected run.

The gateway implementation is forbidden from using Quasar browser state or frontend-local persistence as authority. If the owning runtime lacks a typed control service, that runtime must be extended first.

## OAuth

Intelligence requests require only read/search scopes. Operations requests use only the mutation/control scopes needed by the action.

Bixby user access tokens represent the user at the gateway. The gateway exchanges/uses its own narrowly scoped upstream service identity separately. Upstream credentials never flow back to Bixby.

## Confirmation policy

Mandatory confirmation:

- target commit;
- Auto-Dig start commit;
- Auto-Dig stop.

Default confirmation:

- pause;
- resume.

Read-only status/search actions do not require confirmation.
