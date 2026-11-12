# S6-B synthetic internal identity/session/RBAC v1

[Protocol](../../docs/S6-B-PROTOCOL.md), [results](../../docs/S6-B-RESULTS.md), [review](../../docs/S6-B-REVIEW.md). Disposable dummy users/passwords only. This is an explicit in-process request facade over a trusted Python host/DB, not an HTTP authentication deployment, process sandbox or production security decision. Full S6 and worker/broker integration remain open.

From repository root, Windows x64 CPython3.14.8:

```text
py -3 -m pip install --target .cache/s6b/deps --no-deps --only-binary=:all: --require-hashes -r spikes/s6b/requirements-win-py314.lock
py -3 -B spikes/s6b/preflight_b.py
py -3 -B -m unittest discover -s spikes/s6b -p 'test_*.py' -v
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py start
py -3 -B spikes/s6b/run_b.py docs/s6b-results/<new-id>.json
py -3 -B spikes/s2/local.py stop
```

Use a fresh local dependency directory or inspect existing files before installing. Official PyPI wheels are hash-pinned; no global installation/fallback. Preflight checks metadata/origins before imports, then loaded library/binary paths/versions. Five subprocess tests distinguish missing/mismatched/incomplete/outside-loaded prerequisites from the local READY case. Reuse only the retained marker-bound synthetic [S2 cluster](../s2/README.md), never a service/environment DSN. Each execution creates `id_<uuid>` schema; existing evidence filenames are refused. Cache holds dummy request files, dependencies and local error details, all ignored; it is not a credential store. Preserve ERROR evidence, diagnose locally, then use a new evidence filename. Stop the cluster before handoff.

`Identity.dispatch` is the sole untrusted request entry point with explicit operation/field whitelists. `_Store` contains trusted bootstrap/SQL/short-expiry/fault fixtures; never dynamically expose its methods as routes. Python introspection/host compromise is outside this boundary. Bootstrap is a one-time local operator action, not a public route; no default password/recovery backdoor. Admin-created/reset accounts must change password before other privileged operations.

Actual Argon2id uses RFC9106 low-memory profile:64MiB/time3/parallelism4, random16-byte salts,32-byte hash. Passwords retain spaces/Unicode; accepted encoded length16..1024 bytes is a fixture rule. Five sequential timings are observations, not production parameter sizing or concurrent throughput. Tokens contain256 random bits with access/refresh prefixes; DB persists only SHA256 digests. Fixture TTLs access60s/refresh10min/family1h and login windows3 attempts/name/second,30 global/second are not product defaults. Generic errors/dummy verification do not prove timing indistinguishability or distributed abuse protection.

A singleton DB mutex serializes all identity mutations; final authenticated conditional checkpoint tests captured access/family DB expiries before commit. Other actors cannot change roles/credentials under that held mutex. Intentional own logout/password-change can revoke the current session without rolling back that valid operation. Reset/change/disable/admin-change increments credential epoch and revokes families. Refresh consumes once and advances generation, invalidating old access; replay revokes the entire family. Two concurrent same-refresh requests may return one pair before the second request revokes it. Reauthenticate after uncertain refresh responses; no retry grace/idempotency guarantee.

Admin is global, Owner/Runner/Viewer project-scoped. Admin alone assigns/transfers Owner/Admin; last enabled Admin is protected. Owner manages Runner/Viewer in own project. Persisted grants intersect snapshot actions with live role/epoch/project state. Promotion does not expand old grants; downgrade/removal/disable blocks the next operation. Runner can start/cancel own queued run; Owner/Admin can cancel others in the project. Initiator comes from the DB principal. This is a queued-resource persistence probe, not a worker lifecycle. Secret reveal and automatic human approval actions are denied for all roles.

Harness exercises real DB expiry/rollback/restart and two-process refresh/last-admin races. `probe_b.py` is a dummy-file diagnostic; only fixed status/error JSON is emitted, no successful session pair. Captured failure subprocess/parent output and evidence are scanned for raw/base64/hex password/token/sample-hash/current-account-hash/dummy-hash canaries; no timing, memory-zeroization or arbitrary downstream logging guarantee. Full HTTP/TLS/cookie/CSRF, SSO, OS keystore, authenticated service/worker/broker binding and actual S4 controls remain unimplemented.
