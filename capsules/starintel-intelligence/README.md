# StarIntel Intelligence capsule

Read-only Samsung Bixby surface for person resolution, conversational person context, and StarIntel document search.

This capsule intentionally has no target or Auto-Dig mutation authority. The development capsule ID uses the `playground` namespace until the operator supplies the registered Developer Center namespace.

The aligned-NL files under `training/` are source seeds only. Bixby Developer Studio generates opaque `plan` data in compiled `*.training.bxb` files; those generated plans are not fabricated in CI.

The endpoint modules are fail-closed placeholders in the first TDD slice. They are replaced only after tests specify the configured public gateway adapter behavior. Concrete `authorization.bxb` is also withheld until a real public StarIntel OAuth authorize/token authority exists; fake OAuth URLs are forbidden.
