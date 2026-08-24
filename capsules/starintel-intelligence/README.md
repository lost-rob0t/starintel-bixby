# StarIntel Intelligence capsule

Read-only Samsung Bixby surface for person resolution, conversational person context, and StarIntel document search.

This capsule intentionally has no target or Auto-Dig mutation authority. The development capsule ID uses the `playground` namespace until the operator supplies the registered Developer Center namespace.

The aligned-NL files under `training/` are source seeds only. Bixby Developer Studio generates opaque `plan` data in compiled `*.training.bxb` files; those generated plans are not fabricated in CI.

The local JavaScript endpoints use Bixby JavaScript Runtime 2 and read the public gateway origin from Developer Center configuration key `starintel.gateway.origin`. They call only the read-only `/v1/bixby/person/resolve` and `/v1/bixby/documents/search` boundaries, clamp document result limits, normalize responses to the Bixby models, and reject private/internal gateway or document URLs.

StarIntel Intelligence is deliberately public and auth-free. It has no `authorization.bxb`, no OAuth scopes, and no capsule service credential. The gateway/server must execute these read-only requests under the server-owned synthetic public-read context defined by `starintel-server#109`; caller-supplied tenant or dataset authority must not widen that context.

The local JavaScript adapter is also a privacy boundary: it constructs the narrow StarIntel request body itself and does not forward Bixby `$vivContext`, Samsung account/session context, OAuth tokens, or Developer Center secrets. Public-edge rate limiting, bounded results, public-dataset filtering, response projection, and safe public document URLs provide the abuse/data-exposure controls for this capsule.

Privileged user-delegated OAuth belongs to the separate StarIntel Operations capsule, where target and Auto-Dig actions require backend authorization in addition to Bixby confirmation.

Samsung Developer Studio compilation, Simulator validation, Developer Center registration/private submission, and Galaxy on-device validation remain manual gates and are not claimed by repository CI.
