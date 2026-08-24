# Testing

## Truth rule

Only mark a Samsung validation gate complete when it actually ran against the exact candidate revision. Repository static tests are not substitutes for Bixby Developer Studio, Simulator, private submission, or device tests.

## Automated repository gates

The repository test suite validates what can be checked without Samsung credentials:

- contract JSON parses;
- every declared public route has success/error fixtures;
- result limits stay bounded;
- Intelligence contract does not declare mutation scopes;
- Operations mutation endpoints are listed in the confirmation policy;
- no contract/fixture contains `.star.intel`, RFC1918/private localhost origins, RabbitMQ/CouchDB/Valkey URLs, raw queue/routing values, or shell commands;
- document fixtures use HTTPS public URLs and `/documents/<encoded-id>` route shape;
- target commit fixtures carry idempotency identity;
- Auto-Dig start receipts contain a durable run ID and represent immediate acceptance rather than completion.

Run:

```sh
python -m unittest discover -s tests -v
```

## Bixby Developer Studio gate

For each capsule, on the exact candidate revision:

1. Open the capsule root in the current Bixby Developer Studio.
2. Confirm `capsule.bxb`, model references, endpoint declarations, OAuth declaration, views, dialogs, and confirmations have no model errors.
3. Confirm compile targets:
   - `bixby-mobile-en-US`
   - `bixby-watch-en-US`
4. Use Training Editor 2.1 to add/verify the planned examples from `training-intents/*.json`.
5. Compile the NL model for each supported target where tooling permits.
6. Run Simulator scenarios from the matrices below.

Do not hand-edit generated training source to force a green compile.

## Intelligence Simulator matrix

- “Ask StarIntel who is John Smith.”
- “Who is John Smith?”
- one clear person -> profile result;
- same-name ambiguity -> candidate selection, no silent winner;
- unknown person -> not-found response;
- cold-start “Who is this person?” -> asks which person;
- selected person -> “Tell me more about this person.”;
- “Search StarIntel for documents about Palantir.”;
- search with dtype;
- selected person -> “Find documents about this person.”;
- no documents;
- backend unavailable;
- unauthenticated / revoked authorization.

## Operations Simulator matrix

- “Create a BBPD target for example.com.” -> prepare -> confirmation -> commit receipt;
- unsupported actor -> safe error;
- repeated commit transport retry -> same logical receipt;
- “Start Auto-Dig on this target.” -> prepare -> confirmation -> immediate run receipt;
- “What’s it doing?” with one selected run;
- multiple plausible runs -> disambiguation;
- pause -> confirmation -> paused receipt;
- resume -> confirmation -> running/queued receipt;
- stop -> confirmation -> stopped receipt;
- missing run;
- capability unavailable;
- missing OAuth scope / forbidden.

## Private submission / on-device gate

Samsung documentation currently describes on-device testing for `bixby-mobile` targets. To perform it:

1. Ensure capsule IDs use the real registered Developer Center organization namespace.
2. Ensure the operator is on a Developer Center team and is a collaborator on both capsules.
3. Configure OAuth client ID/secret references in Developer Center Configuration & Secrets.
4. Register Bixby OAuth redirect URI for each capsule:
   `https://<encoded-capsule-id>.oauth.aibixby.com/auth/external/cb`.
5. Create a **Private** submission in Bixby Studio.
6. Enable on-device testing on the Galaxy device using the documented QR/revision flow.
7. Repeat the mobile acceptance matrix against the deployed gateway.
8. Record capsule revision, device model, Bixby version, gateway revision, date, and pass/fail evidence below.

Watch target validation must not be inferred from the mobile test. Run watch Simulator coverage and record actual watch Marketplace/device evidence separately when available.

## Evidence log

No Samsung Simulator, private submission, or on-device validation has been completed by this repository bootstrap yet.
