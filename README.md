# StarIntel Bixby

Canonical Samsung Bixby capsule source for StarIntel.

This repository owns **Samsung/Bixby-facing capsule code only**. The deployed `starintel-bixby-gateway`, public ingress, secrets, Nix packaging, and deployment state belong in `starintel-labs/starintel-infra`.

Two capsules intentionally split authority:

- `capsules/intelligence` — read-only person resolution and document search.
- `capsules/operations` — confirmed target creation and Auto-Dig control.

The Bixby-facing HTTP contract is frozen under `contracts/` and `fixtures/` before gateway implementation.

See `docs/research.md`, `docs/architecture.md`, and `docs/testing.md` for current design and validation status.
