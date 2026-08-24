# StarIntel Bixby testing

This repository distinguishes automated validation that can run from source from Samsung validation that requires Bixby Developer Studio, Developer Center credentials, a private revision, or a Galaxy device.

Do not mark a Samsung-only gate complete from static inspection.

## Source-side gates

Run whenever the relevant source exists:

1. Validate contract and fixture JSON/JSON Schema.
2. Validate every capsule model reference and endpoint mapping with locally available Bixby tooling.
3. Validate JavaScript syntax under the capsule's configured JS runtime.
4. Verify mutation actions are transactional and define confirmation.
5. Verify Intelligence contains no target-write or Auto-Dig-control endpoint.
6. Verify Operations receives no raw RabbitMQ/internal routing input.
7. Verify no source/config/fixture contains `.star.intel`, a private IP, CouchDB/RabbitMQ/Valkey URL, StarIntel service credential, OAuth client secret, or backend admin credential.
8. Verify document-link fixtures use only the configured public origin and safely encoded `/documents/:id` routes.
9. Verify all normalized error fixtures use the stable Bixby-facing error vocabulary and contain no upstream stack/raw body.
10. Verify the frozen contract and capsule fixtures agree before gateway implementation begins.

## Samsung Developer Center manual gate

The following cannot be claimed complete until performed with the operator's Samsung account/team:

- [ ] Sign in to the Bixby Developer Center.
- [ ] Confirm/create the team namespace that will own both capsules.
- [ ] Register the production capsule ID for **StarIntel Intelligence**.
- [ ] Register the production capsule ID for **StarIntel Operations**.
- [ ] Replace `playground.starintelIntelligence` and `playground.starintelOperations` with the registered IDs before private submission.
- [ ] Configure the real public StarIntel OAuth authorization and token endpoints.
- [ ] Register Bixby's OAuth redirect URI for each OAuth-enabled capsule with the OAuth provider.
- [ ] Store OAuth client secret material in Developer Center Configuration & Secrets, never Git.
- [ ] Configure the StarIntel public gateway origin through Developer Center capsule configuration.
- [ ] Verify requested scopes match capsule authority: Intelligence read/search only; Operations only the additional target/Auto-Dig scopes it uses.
- [ ] Create a **private** capsule submission for each capsule.
- [ ] Review the private-submission technical and training reports and fix all blocking errors.

## Bixby Developer Studio / Simulator gate

- [ ] Open each capsule in the current supported Bixby Developer Studio.
- [ ] Compile/validate `capsule.bxb`, concepts, actions, `endpoints.bxb`, views, transaction support, activity support, and `authorization.bxb`.
- [ ] Enter/compile the approved training examples through Bixby Studio. Do not hand-edit generated training syntax and claim it compiled.
- [ ] Run the Device Simulator against the real public gateway.
- [ ] Authenticate through the real OAuth flow in the Simulator.
- [ ] Verify person success/not-found/ambiguity and contextual follow-up.
- [ ] Verify document search, bounded results, selection, and public document link.
- [ ] Verify target prepare -> confirmation -> exactly one commit.
- [ ] Verify Auto-Dig start -> confirmation -> durable run ID -> status refresh.
- [ ] Verify pause/resume/stop flows and confirmation behavior.
- [ ] Verify unauthenticated, forbidden, expired-token, rate-limit, timeout and unavailable-upstream speech/views are concise and do not expose backend errors.
- [ ] Inspect the Simulator execution graph for accidental planner paths from Intelligence into mutation actions.

## Galaxy on-device gate

- [ ] Load the private revision or current Bixby Studio Workspace onto a supported Galaxy device using Samsung's documented on-device test flow.
- [ ] Test real natural voice, not only aligned NL.
- [ ] Test `Ask StarIntel who Ada Lovelace is`.
- [ ] Test a same-name ambiguity and selection.
- [ ] After a selected person, test `Who is this person?`, `Tell me more about this person`, and `Show me documents about this person`.
- [ ] From a cold start, verify `Who is this person?` asks for identity instead of guessing.
- [ ] Test `Search StarIntel for documents about Flock Safety` and open a returned public link.
- [ ] Test `Create a BBPD target for example.com`, reject once, then confirm once; verify no mutation occurs before confirmation and exactly one target exists after confirmation/retry.
- [ ] Test `Start an Auto-Dig on Acme Corporation`, reject once, then confirm; verify the Bixby response returns without waiting for research completion.
- [ ] Test `What's that Auto-Dig doing?`, pause, resume, and stop against the same selected run.
- [ ] Test OAuth sign-out/expiry and reauthentication.
- [ ] Verify no spoken or visual response exposes internal hosts, credentials, stack traces, RabbitMQ/CouchDB errors, or private links.

## Current status

As of 2026-08-24, **no Samsung Developer Studio compile, Simulator run, private submission, or Galaxy on-device test has been performed by this branch**. Those remain explicit manual gates.
