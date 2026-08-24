# StarIntel Intelligence capsule

Read-only Samsung Bixby surface for person resolution, conversational person context, and StarIntel document search.

This capsule intentionally has no target or Auto-Dig mutation authority. The development capsule ID uses the `playground` namespace until the operator supplies the registered Developer Center namespace.

The aligned-NL files under `training/` are source seeds only. Bixby Developer Studio generates opaque `plan` data in compiled `*.training.bxb` files; those generated plans are not fabricated in CI.

The local JavaScript endpoints use Bixby JavaScript Runtime 2 and read the public gateway origin from Developer Center configuration key `starintel.gateway.origin`. They call only the read-only `/v1/bixby/person/resolve` and `/v1/bixby/documents/search` boundaries, clamp document result limits, normalize responses to the Bixby models, and reject private/internal gateway or document URLs.

The required user authority for this capsule is limited to `starintel.read` and `starintel.search`. A concrete `authorization.bxb` remains intentionally withheld until StarIntel exposes a real public OAuth 2 authorization-code authority with concrete authorize/token endpoints. Current Samsung syntax requires those real provider endpoints; fake OAuth URLs are forbidden. Developer Center stores the eventual client secret value; this repository may contain only the configured secret-key reference, never the secret itself.

Samsung Developer Studio compilation, Simulator validation, Developer Center registration/private submission, OAuth client registration, and Galaxy on-device validation remain manual gates and are not claimed by repository CI.
