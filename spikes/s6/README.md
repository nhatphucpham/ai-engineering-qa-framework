# S6-A synthetic encrypted storage and raw-data denial v1

[Protocol](../../docs/S6-A-PROTOCOL.md), [results](../../docs/S6-A-RESULTS.md), [review](../../docs/S6-A-REVIEW.md). This is a private operator/library/DB experiment, **not an authenticated QA API, production secret broker, OS keystore or secured backup deployment**. No real credentials/accounts/provider/engine calls. Keys/data are generated dummy fixtures; ciphertext is not actor authority. S4 actual engine controls and full S6 identity/refresh/secret-taint pipeline remain open.

From repository root, Windows x64 CPython3.14.8:

```text
py -3 -m pip install --target .cache/s6/deps --no-deps --only-binary=:all: --require-hashes -r spikes/s6/requirements-win-py314.lock
py -3 -B spikes/s6/preflight.py
py -3 -B -m unittest discover -s spikes/s6 -p 'test_*.py' -v
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py start
py -3 -B spikes/s6/run_s6.py docs/s6-results/<new-id>.json
py -3 -B spikes/s2/local.py stop
```

Use a fresh local dependency directory or inspect existing files; do not overwrite unknown installations. Lock pins official PyPI wheels cryptography50.0.2/cffi2.1.1/pycparser3.12; no global install/upgrade. Preflight checks local metadata/origins before importing crypto, loaded local package/binary paths/versions, platform/Python. Missing/mismatched/incomplete or globally loaded modules return NOT READY, no fallback. `run_s6.py` exits before crypto import when prerequisites fail. The5 preflight tests use independent processes, including a simulated outside-loaded module and positive local path check.

Reuse only the retained marker-bound synthetic [S2 cluster](../s2/README.md), not an external DSN/service. Each run creates `s6_<uuid>` schema and generated/marked restore DB; existing evidence destination refused. `.cache/s6` contains dummy key files/probe fixtures/encrypted DB archives, all ignored. Dummy key backup is deliberately a plain test-only file outside the DB archive, **not a recommendation to store actual master keys there**. Stop the cluster before handoff; keep caches for inspection, then remove only after verifying workspace scope/stopped state. On ERROR preserve evidence, inspect `.cache/s6/last-error.txt` locally and fix cause before a new filename. Controlled synthetic diagnostics are not a production untrusted-input logging API.

`envelope.py` uses maintained AESGCM256 with one random DEK per content version, payload nonce and separately wrapped DEK. AAD binds envelope version/kind/project/ref/content version and layer purpose; wrap AAD also binds KEK ID. Strict integer/scope shape validation prevents bool/float aliases. No custom cipher, signature, trust attestation or memory zeroization claim. Ciphertext/nonce/context/wrong key fail closed. Library-only helpers do not own a persistent global nonce allocator.

`vault.py` is the controlled private operator path. Current project/head/version/epoch checked under row locks; stale caller anchors or revoked records cannot use normal private open. Secret rotation increments version/epoch and retains old ciphertext; rewrap changes only key wrapper/revision, not data ciphertext/nonce. Selected rewrapped row can open with only the new KEK; full-vault key retirement/migration is not implemented. Operator possession of historical master keys still permits low-level decrypt; revocation cannot erase bytes already disclosed.

Wrap nonce is reserved **before encryption** on a separate committed connection in append-only `nonce_history`; it remains consumed after outer rollback/rewrap. `key_identity` binds immutable KEK ID to a key tag and refuses aliases/reassigned material. Exact key bytes are snapshotted once per operation and reused for registry/encryption, so a changing provider cannot register one key and encrypt with another. Registry is scoped to one vault namespace: each run creates fresh dummy master material, never writable clones sharing a keyring. Restored Vault connections reject writes/rewrap until a future trusted latest-ledger/key-rollover protocol exists. Stale backup cannot prove lifetime uniqueness; cross-vault/global consensus is outside this experiment.

`quarantine` always encrypts supplied raw log as secret-tainted. The closed QA content boundary denies all4 roles across read/export/stream/attachment/source, including fake redaction/authorization flags, without accepting a client sanitizer claim. There is no general allow/read RBAC model, trusted sanitizer or actual container-output collector. Private operator helpers must never be routed as QA endpoints.

`run_s6.py` exercises actual DB CAS across two processes, wrapper rollback/burned nonce/forced collision, DB restart, raw-material absence checks, scope/cipher swaps with rollback, DB dump/restore and independent child recovery from external dummy key file. Restored private open requires caller-held policy anchors retained outside the archive; a newer anchor rejects an older restored snapshot. Lost trustworthy anchors/latest nonce ledger and real OS key availability remain production recovery gaps. No restore auto-enables writes or workers.

`probe_cli.py` is a private dummy-file diagnostic route used in subprocess tests for valid/missing/wrong key/tamper/unsupported/invalid input. Captured stdout/stderr, audit and evidence are scanned for raw/base64/hex canaries; it emits only fixed JSON codes/boolean match, never plaintext/key data. No real key file or external artifact should be passed to it. Actual results do not close login/refresh/reset, RBAC, TLS, broker injection, live account/project revoke or S4/S6/P4-B readiness.
