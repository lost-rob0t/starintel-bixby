# StarIntel Bixby testing

## Truth boundary

Repository checks can validate capsule source, models, endpoint/view references, training fixtures and frozen HTTP contracts. They cannot substitute for Samsung Developer Center registration, Bixby Developer Studio NL compilation/Simulator execution, private-submission acceptance, or Galaxy on-device voice testing.

Do not mark those proprietary/manual gates complete unless they were actually performed.

## Automated gate before Samsung tooling

Run the repository-native CI/static suites and require deterministic checks for:

- both capsule roots and `capsule.bxb` files;
- action/concept/view references and `endpoints.bxb` mappings;
- Intelligence/Operations scope separation;
- no raw `$vivContext` forwarding or Bixby user ID substitution for StarIntel identity;
- transactional confirmation definitions for target and Auto-Dig mutations;
- realistic training coverage for success, ambiguity, not-found, context, auth and upstream failures;
- frozen versioned `/v1/bixby/...` contract and fixtures;
- bounded document result counts and safe link shapes;
- forbidden private/internal host and transport-topology leakage;
- no committed OAuth secrets, StarIntel keys, tokens or backend credentials.

## Samsung Developer Center operator checklist

### 1. Account, team and namespace

- Sign in to Bixby Developer Center with the intended developer team.
- Register **StarIntel Intelligence** and **StarIntel Operations** as separate capsules under the real organization namespace.
- Replace development `playground` IDs only through the real registered/submission configuration path.
- Record each exact registered capsule ID and derive/confirm the Samsung OAuth callback URI expected for that capsule.

### 2. Public OAuth provider and client registration

The canonical OAuth provider belongs to `lost-rob0t/starintel-server`; provider logic is already merged at `4f2f70126bc59e18681844019460a33709e1eba6`. Infrastructure must expose the verified provider over intended public HTTPS without exposing unrelated internal services.

For each capsule that needs account linking:

1. Verify the intended public HTTPS OAuth origin actually serves the canonical `/oauth/authorize` and `/oauth/token` endpoints.
2. Do not use `.star.intel`, localhost, private IPs, CouchDB/RabbitMQ/Valkey endpoints, or guessed service URLs.
3. Register the exact Samsung callback URI with the canonical StarIntel OAuth client-registration/operator flow.
4. Record the returned **public client ID**.
5. Store the one-time client secret only in Samsung Developer Center Configuration & Secrets under the exact key referenced by `client-secret-key` in `authorization.bxb`.
6. Never commit the client-secret value to this repository or infra.
7. Intelligence requests only read/search authority (`documents:read`, `search:read`, or their exact canonical successors).
8. Operations reuses the same StarIntel human account and requests only canonical target/Auto-Dig authority required by its actions (`targets:dispatch` plus current owner-approved Auto-Dig read/control scopes).
9. Verify invalid, expired and revoked credentials trigger reauthorization/fail closed rather than silently downgrading a private-data request to guest mode.
10. Verify insufficient scope remains `FORBIDDEN`.

`auth.requirements.json.registrationComplete` must remain false until the real public origin, registered capsule ID/callback, client ID and Developer Center secret-key name exist. Do not fabricate placeholders and call them complete.

### 3. Gateway configuration

`starintel-labs/starintel-infra` owns the deployed `starintel-bixby-gateway`.

- Configure the capsule's local JavaScript adapter with the verified public gateway origin through the supported Samsung configuration path.
- Keep Bixby user identity, gateway service identity and upstream StarIntel/Quasar service identity separate.
- Verify no `.star.intel` hostname, private IP, raw upstream API route or backend transport endpoint is visible to Samsung.
- Start a new Simulator conversation/reset/recompile after Developer Center configuration or secret changes when required by current Studio behavior.

Before claiming public gateway readiness, verify:

- `GET /healthz` and `GET /readyz` on the intended gateway origin;
- only intended `/v1/bixby/...` routes are public;
- unknown hosts/routes do not fall through to raw StarIntel/Quasar services;
- bounded request sizes, result counts, timeouts and rate-limit behavior;
- correlation IDs propagate safely without credentials or internal errors;
- target retries create exactly one canonical target once the owner target API is merged/deployed;
- Auto-Dig routes return `AUTODIG_CAPABILITY_UNAVAILABLE` unless capability discovery proves the required deployed owner operation exists;
- Auto-Dig start, once available, returns a durable run ID promptly without waiting for research completion.

## Bixby Developer Studio validation

For each capsule:

- open the workspace in the current Bixby Developer Studio;
- resolve Warnings & Errors;
- compile the NL model for every declared target/locale;
- run model/action/endpoint/view reference validation;
- execute stories/assertions where present;
- use Device Simulator with realistic typed/natural utterances;
- inspect Debug Console output without copying credentials into evidence.

### Intelligence Simulator scenarios

- guest exact person lookup without account linking;
- optional signed-in person lookup using a real StarIntel human principal;
- signed-in access to user-authorized data not visible to guest mode;
- exact person result;
- ambiguous same-name candidates and explicit selection;
- person not found;
- warm `Who is this person?` after selection;
- cold-start `Who is this person?` elicitation rather than guessing;
- `Tell me more about this person` continuation;
- `Show me documents about this person` continuation;
- free-form and dtype-filtered document search;
- bounded result list near the default of five;
- no documents;
- result selection and public attribution-link rendering;
- invalid/expired/revoked OAuth reauthorization;
- insufficient scope, rate-limited, timeout and unavailable paths.

### Operations Simulator scenarios

- prepare a generic target;
- prepare actor-qualified target such as BBPD only when canonical actor discovery supports it;
- unsupported/ambiguous actor or target type;
- inspect target draft before confirmation;
- affirmative target confirmation commits once;
- abort/no confirmation performs no commit;
- repeat transport attempt reuses the same idempotency identity;
- Auto-Dig status/get/list when capability is available;
- unavailable lifecycle returns capability-unavailable rather than fake success;
- prepare/confirm start and receive durable run ID;
- pause/resume confirmation behavior;
- prepare/confirm stop;
- missing run;
- contextual `What's it doing?` against selected/recent run;
- multiple plausible runs trigger disambiguation;
- unauthorized/forbidden/upstream unavailable errors remain client-safe.

## Private submission

Using Samsung's current submission flow:

- create a new submission in Developer Studio;
- select **Private**;
- submit using the registered organization namespace;
- inspect validation/training reports and fix all technical failures;
- record the private revision ID used for device testing.

Do not call a locally green repository branch a private-submission success.

## Galaxy on-device testing

On a compatible Bixby-enabled Galaxy device signed into the appropriate Samsung account:

- enable Bixby Developer Options using the current documented process;
- open Developer Options -> On-device testing;
- load the intended private revision or Studio workspace using the supported QR flow;
- confirm the matching device code when prompted;
- exercise the required Intelligence and Operations scenarios with actual voice/ASR/TTS;
- verify ambiguous people/runs are spoken/visualized clearly enough to choose safely;
- verify mutation confirmation text describes the actual pending operation;
- verify no mutation occurs on abort/no confirmation;
- verify document links are public HTTPS and open only after explicit user interaction;
- verify OAuth login, expiry/re-auth and scope-denied paths;
- disable on-device testing after the session.

## Evidence to record

For each manual Samsung test session record only non-secret evidence:

- Bixby Developer Studio version;
- exact capsule repository commit SHA;
- capsule ID/namespace/version/target/locale;
- private revision ID if used;
- Galaxy model and Bixby version;
- scenarios exercised and pass/fail notes;
- OAuth public origin, public client ID and Developer Center secret-key **name only**;
- public gateway hostname;
- exact StarIntel/Quasar/infra deployment commits tested.

Never record the OAuth client secret, access/refresh tokens, StarIntel service credentials, private backend addresses, or internal transport topology.
