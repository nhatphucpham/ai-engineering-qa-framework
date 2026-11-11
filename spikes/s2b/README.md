# S2-B lease/recovery persistence experiment v1

[Protocol](../../docs/S2-B-PROTOCOL.md), [results](../../docs/S2-B-RESULTS.md), [review](../../docs/S2-B-REVIEW.md). New model `s2b-1.0.0` in fresh `s2_<uuid>` schema; imports unchanged S2-A portable tooling, core derivation and byte handling. Never migrates S2-A schemas or rewrites its evidence. PostgreSQL18.6/Python3.14.8/psycopg3.3.8/tzdata2026.6 pins and source/integrity limits remain as [S2-A setup](../s2/README.md).

From repo root, with the retained marker-bound cluster stopped:

```text
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py start
py -3 -B spikes/s2b/run_b.py docs/s2b-results/<new-run-id>.json
py -3 -B spikes/s2/local.py stop
```

If no cache exists, use S2-A local-only setup first. Do not connect an existing work database/DSN, read secret environment values, overwrite evidence or install globally. `preflight` must say toolchainReady true; start only the cluster matching its retained marker. Each execution creates a new namespace and refuses an existing output file. Stop before handoff; retain ignored cache for inspection. On ERROR inspect `.cache/s2/s2b-last-error.txt` locally, preserve failed evidence, correct its cause and use a new filename. This diagnostic is for controlled synthetic inputs, not a production safe-error API.

`store_b.py` adds server-time heartbeat, expiry recovery, scoped cleanup requests/observations/incidents, bounded retries, cancel/revoke predicates and cleanup deadlines. Every lifecycle mutation locks the run; lease validity for renewal/result/completion is also a predicate of the actual write, because a row lock does not stop time. Heartbeat extends live expiry without changing stateVersion or canonical attempt inputs; their initial lease timestamp is a frozen historical binding, not current authorization. Each retry persists another immutable attempt-input row and receipt; previous anchors/bytes remain available. Report publication still checks current attempt plus independent anchors and commits report+completed+outbox atomically.

`recovering` is an internal experiment state, not a change to frozen P1 run enum. It means expired attempt fenced and cleanup unresolved. `cancelling` also fences old work; cleanup ack bound to exact request/run/attempt/original fence permits cancelled or queued as appropriate. The S2-A direct terminal-cancel helper is disabled. Cleanup observations must have explicit synthetic kind/scope and exact integers (bool/float rejected); a structurally matching observation is **not authenticated supervisor proof**. Per-run `policy_ok=false` models a durable revoke fact, not real project/account/session revocation.

Cleanup deadline is evaluated using one DB clock sample in the ack transition itself. An ack arriving after the deadline cannot avoid `failed/cleanup_unconfirmed` just because a sweeper has not run. Explicit timeout leaves incident open; late observation may resolve sidecar incident but never rewrite terminal run. Fixed maxAttempts2 bounds this experiment only. Restoring permission cannot revive terminal runs; no management/auth interface is provided.

`run_b.py` uses actual PostgreSQL clocks, independent processes/connections and DB immediate stop during an uncommitted recovery transaction. Four connections (two processes) race reclaim before/after exact ack. Two-process races exercise both cancel/revoke against complete, renew, expired reconcile and reclaim. A stale stop CAS is reported rejected; the harness may make one explicit retry with freshly read version and records it. Ordered cases test the opposite outcome where scheduling alone does not observe it. Test-only delay callbacks force server-clock expiry between check and write; they do not mock DB behavior. Assertions reject expired writes and any partial report graph.

Scope excludes real worker/container cleanup, authenticated live policy/revoke, capacity/fairness, backup/restore/external blobs, ordinary read/export, production runtime/DB choice, SLA and exactly-once execution. No model/provider/account/API calls. Full S2/P3-B/P4-A/P4-B remain partial after this subset. Core decisions/declared-effective constraints/human decision and legacy unsupported export remain unchanged.
