# IAP-B service/delegation/attempt authority experiment

[Protocol](../../docs/IAP-B-PROTOCOL.md), [results/review](../../docs/IAP-B-RESULTS.md). Fresh namespace builds unchanged S6-B + IAP-A fixtures then adds versioned authority tables. Trusted local host/DB only; no HTTP/TLS/network worker enrollment, actual workload/cleanup, broker/secret/content release or production stack decision.

```text
py -3 -B spikes/s6b/preflight_b.py
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py start
py -3 -B spikes/iapb/run_iapb.py docs/iapb-results/<new-id>.json
py -3 -B spikes/s2/local.py stop
```

Require retained pinned local S2/S6-B setup, marker-bound stopped synthetic cluster before start. No external DSN/credentials/global installation; no other DB fixture may run concurrently because B08 restarts this disposable DB. Evidence destination must be new; preserve ERROR and inspect ignored `.cache/s6/iap-b/last-error.txt` before new execution. Stop DB before handoff. Do not copy local dummy keys/tokens/credential fixtures into Git.

`AdminServices` authenticates live user Admin for enrollment/rotation/revocation. `ServiceAuthority` has separate exact route/version/field whitelist and service-token namespace/kind/audience/project ceiling. Only hashed service tokens stored; raw credentials returned only to authorized issuing caller. Public request cannot select trusted `_AuthorityStore.issue`, SQL/setup/hooks or impersonate audience/authority. Python introspection/host compromise remains outside boundary.

Common held identity mutex orders user/project/policy/grant/service changes and assignment checks. Final DB-clock checkpoint includes token/delegation/grant/assignment deadlines; metadata graph rolls back on crossing expiry/audit/commit failure. Old rotation/revoke epochs, wrong worker/project/attempt/fence and expired assignments deny. User logout/access expiry need not stop durable delegation; credential reset/live role/project/policy/grant revoke still restrict it. No general member-epoch or restored latest-authority proof.

Assignment and retirement are **authority metadata only**. No workload can start through these methods; `retiredMetadata` is never a cleanup acknowledgement. New attempt after metadata retirement does not authorize retry of actual work without future S4/worker cleanup integration. Existing IAP-A run remains queued/cancelled, and current queued state is rechecked. Do not route this reservation model into an executor as a finished claim protocol.

Harness probes DB concurrency/order, real time expiry, service/user separation, live delegation, actual constraint/audit failure and DB restart; captures no real API or worker activity. Results can DONE only selected subset after actual checks + high-model CLEAN, not full IAP24/S4/S6/P3-B/P4-B/product readiness.
