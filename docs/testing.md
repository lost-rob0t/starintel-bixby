# StarIntel Bixby testing

## Truth boundary

Automated repository checks can validate files, fixtures, endpoint/model references and contract invariants. They cannot substitute for Samsung Developer Center registration, Bixby Developer Studio NL compilation/Simulator execution, private submission acceptance, or Galaxy on-device testing.

Do not mark those proprietary/manual gates complete unless they were actually performed.

## Local/CI gate before Samsung tooling

The repository should provide deterministic checks for:

- both capsule roots and required `capsule.bxb` files;
- referenced action/concept/view files;
- endpoint declarations;
- no forbidden internal/private host patterns;
- no committed credentials/secrets;
- Intelligence/Operations scope separation;
- transactional confirmation definitions for mutations;
- training fixture coverage for required success/failure utterance classes;
- versioned `/v1/bixby/...` request/response/error fixtures;
- bounded search/result limits and URL/link contract shape.

As capsule work lands, these checks become the TDD-first executable gate.

## Samsung Developer Center operator checklist

### 1. Account/team/namespace

- Sign in to the Bixby Developer Center.
- Ensure the operator belongs to the intended developer team.
- Register the two capsules under the organization's real namespace:
  - StarIntel Intelligence
  - StarIntel Operations
- Replace any development `playground` capsule IDs only in the submission/operator configuration path required for the registered namespace.

### 2. OAuth

For each capsule as required:

- register the StarIntel OAuth authorization-code client;
- configure the authorize endpoint and token endpoint expected by `authorization.bxb`;
- enter the OAuth client secret in Developer Center Configuration & Secrets under the exact `client-secret-key` referenced by the capsule;
- configure only the scopes assigned to that capsule;
- verify Intelligence cannot obtain target-write or Auto-Dig-control scope;
- verify Operations cannot exceed its declared additional scopes;
- verify reauthorization after revocation/expiry.

Never paste StarIntel upstream service credentials into Developer Center capsule configuration. Those belong only on the server-side gateway deployment boundary.

### 3. Gateway configuration

- Set the public Bixby gateway origin/config required by the capsule's local JavaScript adapter.
- Start a new Simulator conversation/reset/recompile after changing Developer Center Configuration & Secrets because current Samsung documentation says existing Simulator conversations may retain old values.
- Verify no `.star.intel` hostname, private IP, CouchDB/RabbitMQ/Valkey endpoint, or raw upstream API route is configured for Samsung.

### 4. Bixby Developer Studio validation

- Open each capsule workspace in the current Bixby Developer Studio.
- Resolve Warnings & Errors.
- Compile the NL model for each declared target/locale.
- Run model/endpoint reference validation.
- Run stories/assertions where present.
- Exercise the Device Simulator with realistic natural utterances.

Required Intelligence Simulator scenarios:

- exact person lookup;
- ambiguous same-name lookup and explicit selection;
- person not found;
- `Who is this person?` after selecting a person;
- cold-start `Who is this person?` elicitation;
- `Tell me more about this person` continuation;
- `Show me documents about this person` continuation;
- free-form document search;
- dtype-filtered document search;
- no documents;
- selection and attribution-link rendering;
- unauthenticated/forbidden/upstream unavailable errors.

Required Operations Simulator scenarios:

- prepare a generic target;
- prepare an actor-qualified target such as BBPD when canonical actor discovery supports it;
- unsupported/ambiguous actor/type handling;
- confirm target commit and abort target confirmation;
- verify no commit occurs before confirmation;
- Auto-Dig status/get/list run;
- prepare/confirm start;
- pause/resume with confirmation behavior;
- prepare/confirm stop;
- missing capability/run;
- authn/authz and backend unavailable failures;
- contextual `What's it doing?` against selected/recent run;
- run disambiguation when more than one plausible run exists.

### 5. Private submission

Samsung's current documented path:

- open Submissions in Bixby Developer Studio;
- create a new submission;
- select **Private**;
- submit a capsule using the registered organization namespace;
- inspect submission validation/training reports and fix all technical rejection reasons;
- record the private revision ID.

Use a single capsule per private revision where practical; Samsung warns that all utterances may be directed to capsules loaded in the private revision during on-device testing.

### 6. Galaxy on-device testing

- Use a compatible Bixby-enabled Galaxy device signed into the appropriate Samsung account.
- Enable Bixby Developer Options (current Samsung docs describe tapping the Bixby version five times).
- Open Developer Options -> On-device testing.
- Load either the private revision or the current Bixby Studio workspace using its QR code.
- Confirm the matching device confirmation code when prompted.
- Run the natural voice scenarios above with ASR/TTS, not just typed intents.
- Verify confirmation prompts are understandable and no mutation happens on abort/no-confirmation.
- Verify document links are public HTTPS links and open only after explicit user interaction.
- Verify OAuth login, token expiry/re-auth, and scope-denied paths.
- Disable on-device testing after the session so normal Bixby routing resumes.

## Public endpoint verification

Before claiming end-to-end readiness:

- public DNS resolves only the intended Bixby gateway hostname;
- TLS certificate is valid;
- `GET /healthz` and `GET /readyz` behave as designed;
- only intended `/v1/bixby/...` routes are public;
- unknown hostnames do not route to the gateway or another internal service;
- private `.star.intel` names and backend addresses are absent from responses;
- OAuth scopes are enforced server-side;
- target retry produces exactly one target;
- Auto-Dig start returns a durable run ID promptly rather than waiting for completion;
- correlation IDs propagate through gateway/upstream errors without leaking secrets.

## Evidence to record

For every manual Samsung test session record:

- Bixby Developer Studio version;
- capsule revision/commit SHA;
- capsule namespace/version/target/locale;
- private revision ID if used;
- Galaxy model + Bixby version;
- scenarios exercised and pass/fail notes;
- OAuth configuration identifiers only (never secret values);
- public gateway hostname;
- exact backend/infra deployment commit tested.
