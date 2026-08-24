# StarIntel Bixby architecture

## Boundary

Samsung/Bixby is a presentation and conversational client of StarIntel. It does not own StarIntel schemas, intelligence state, target state, Auto-Dig state, infrastructure state, RabbitMQ topology, or internal service discovery.

```text
StarIntel Intelligence capsule
  guest: synthetic public-read authority
  user:  optional OAuth read/search authority
StarIntel Operations capsule
  user:  same StarIntel principal + additional mutation/control scopes
        |
        | versioned /v1/bixby contract
        v
public starintel-bixby-gateway   [owned by starintel-infra]
        |
        +--> StarIntel named client/capability adapter
        |
        +--> Quasar/Auto-Dig typed control adapter
        |
        +--> configured public-document link builder
```

## Identity and authority

There are four distinct identities/contexts and they must never be collapsed:

1. Samsung/Bixby runtime/user context;
2. optional authenticated StarIntel human principal represented by user OAuth;
3. Bixby gateway service identity;
4. gateway-to-StarIntel/Quasar upstream service identity.

The Samsung/Bixby user ID is not a StarIntel principal. A StarIntel principal exists only after canonical StarIntel OAuth authentication.

### Guest Intelligence

Guest person/document requests require no login. They execute under a server-owned synthetic public-read context. The caller cannot widen tenant or dataset authority with request fields.

### Signed-in Intelligence

Intelligence supports optional user OAuth. When a valid StarIntel user token is present, the same person/document actions may see exactly the resources that authenticated StarIntel principal can read/search. The capsule never manually places the access token in a request body, query, log, model, or user-visible output; Bixby's OAuth HTTP transport carries it.

An authenticated failure never silently retries as guest when the request selected authenticated transport. Invalid/expired/revoked credentials trigger Bixby reauthorization. Insufficient scope remains `FORBIDDEN`.

### Operations

Operations reuses the same StarIntel human-user identity and requests only the additional target/Auto-Dig scopes needed for each privileged behavior. It does not create a second account system or use a capsule-global credential to impersonate users.

## Two-capsule authority split

### StarIntel Intelligence

Owns only Bixby-facing concepts/actions/views/training for:

- person resolution and disambiguation;
- selected-person conversational context;
- document search and result selection;
- safe public document links;
- optional StarIntel account connection for user-authorized read/search data.

It must not request target write or Auto-Dig control authority.

### StarIntel Operations

Owns Bixby-facing concepts/actions/views/training for:

- target draft preparation and confirmed commit;
- Auto-Dig status/run selection;
- confirmed start/stop and confirmation-preferred pause/resume.

It requests only the additional scopes required by those behaviors.

## Core invariants

1. Capsule concepts are wire/presentation contracts, never canonical StarIntel schemas.
2. No StarIntel upstream credential exists in capsule source or Samsung-visible results.
3. Every mutation has a prepare/confirmation/commit boundary and is reauthorized/revalidated server-side.
4. Ambiguous people, actors, target types, and runs are elicited/disambiguated; never silently guessed.
5. Visual identity inference is out of scope: no camera, face recognition, OCR, foreground-app scraping, or visible-person guessing.
6. Internal hosts, `.star.intel`, private IPs, CouchDB/RabbitMQ/Valkey addresses, raw internal APIs and RMQ topology are never emitted to Bixby.
7. Document links are produced only by one server-side configured-origin component after validating the public origin and safely encoding the document ID.
8. Auto-Dig uses the owning typed/versioned Quasar/Auto-Dig control plane. Missing operations fail as capability unavailable until added at the owning boundary.
9. Target creation resolves user-facing actor/type values against canonical metadata. Voice input cannot select raw actor implementation/RMQ routing values.
10. Reasonable transport retry must not duplicate mutation; idempotency is enforced at the owning mutation boundary.
11. Guest and authenticated Intelligence authority are distinct. Public fallback cannot bypass a failed authenticated request for user-private data.
12. Raw `$vivContext`, `bixbyUserId`, Samsung profile/device/location data, and manual bearer-token material are never forwarded to StarIntel.
13. Token-bearing/private responses must never be shared through a cache keyed only by public request parameters.

## Conversational state

Bixby continuation/context is responsible for keeping a selected `PersonMatch`/`PersonProfile` or selected Auto-Dig run in the conversational plan. The backend still receives stable IDs and revalidates ownership/existence.

A cold-start follow-up such as "Who is this person?" has no valid selected person and must elicit a person query.

## Mutation lifecycle

```text
natural request
 -> prepare action
 -> immutable-ish display draft + opaque bounded idempotency/prepare token
 -> Bixby transactional confirmation-view
 -> commit action
 -> gateway reauth + scope check + revalidation
 -> owning StarIntel/Quasar mutation
 -> normalized receipt
```

Confirmation is a UX/security gate, not authority by itself. Commit cannot trust fields merely because they were displayed in the confirmation view.

## Failure model

The capsule contract uses stable client-safe errors. At minimum:

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

No stack trace, raw Lisp/Python condition, RabbitMQ/CouchDB error, secret, upstream body, or internal route is speech-visible.

## Rejected alternatives

### Anonymous-only Intelligence

Rejected as the final product architecture. Guest access is useful, but signed-in StarIntel users must be able to access their own authorized read/search data without moving those read-only features into Operations.

### One privileged capsule

Rejected. It expands read-only person/document flows into mutation authority and violates least privilege.

### Direct capsule-to-StarIntel internal API

Rejected. It would expose service credentials/internal routes to the Samsung boundary and bypass the public gateway's identity, rate-limit, normalization and link-safety responsibilities.

### Browser automation for Auto-Dig

Rejected. UI state is not runtime authority and cannot provide durable typed run semantics.

### Shared gateway-owned Auto-Dig state

Rejected. The gateway translates; Quasar/Auto-Dig owns runs and lifecycle.

### Hard-coded public document hostname

Rejected. Current infra inventory has no verified public Quasar service. Public origin must come from deployed inventory/configuration.

## Migration/compatibility constraints

- StarIntel machine-readable client operations are preferred whenever present; current search/target routes may remain behind one legacy adapter until promoted into the shared contract registry.
- Existing actor names are internal implementation identifiers unless explicitly exposed through canonical user-facing discovery metadata.
- The Bixby `/v1/bixby/...` contract is frozen before gateway implementation. If backend evidence later falsifies a shape, capsule fixtures and gateway contract change together explicitly.
- Samsung namespace and OAuth registration values are deployment/operator configuration, not repository constants.
- `authorization.bxb` must not be fabricated before `starintel-server#111` provides real authorize/token endpoints and a registered Bixby client.

## Gates

Before gateway implementation:

1. two capsule roots exist;
2. person/document/target/Auto-Dig Bixby models/actions/views/training are structurally coherent;
3. mutation actions have transactional confirmation definitions;
4. guest-vs-signed-in Intelligence behavior and Operations scope separation are fixture-tested;
5. real OAuth declarations are present once provider/client values exist, without committed secrets;
6. versioned request/response/error fixtures are frozen;
7. all locally available static/fixture/model checks pass;
8. proprietary Samsung checks not available locally remain an explicit manual gate in `docs/testing.md`.
