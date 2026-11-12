# S2-C metadata capacity/fairness and restore experiment v1

[Protocol](../../docs/S2-C-PROTOCOL.md), [results](../../docs/S2-C-RESULTS.md), [review](../../docs/S2-C-REVIEW.md). Fresh s2c-1.0.0 namespace extends unchanged [S2-B](../s2b/README.md) using the same pinned project-local PostgreSQL18.6/Python3.14.8/psycopg3.3.8 tooling. No production runtime/DB decision or schema migration. Full S2/P3-B/P4-A/P4-B remain open.

From repo root, reuse retained stopped synthetic cluster; if missing, follow [S2-A setup](../s2/README.md) without global installation or external DSN:

```text
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py start
py -3 -B spikes/s2c/run_c.py docs/s2c-results/<new-id>.json
py -3 -B spikes/s2/local.py stop
```

Require preflight toolchainReady and archive/extracted/driver pins. Every run creates new namespaces, a generated `s2_restore_<uuid>` database, and a new evidence file. Dumps/identity markers/truncated fixtures/sinks remain only in ignored `.cache/s2`. No real DB/account/key/API, existing target overwrite, global service or provider call. On ERROR preserve evidence and inspect `.cache/s2/s2c-last-error.txt` locally; diagnose before a new execution. Stop the marker-bound server before handoff; retained caches/databases support inspection and can later be removed only after verifying their workspace scope and stopped state.

`store_c.py` locks one scheduler row for admission/configuration, then probes project queue heads under `SKIP LOCKED`. That serializes the critical section in PostgreSQL, not the independent processes; throughput tradeoff is explicit and not benchmarked. Global3/project2/1/1 caps are fixture bounds. Occupancy includes expired checking, recovering/cancelling and failed-but-cleanup-pending; late exact synthetic ack frees the slot without rewriting terminal run. Successful completion releases only the metadata slot; real container/process quiescence remains outside this model.

Fairness chooses the least-recently-served currently eligible project, tie project ID. Queue head follows queued_at/id among jobs eligible by policy/cleanup/budget; if that head is locked, this project is temporarily ineligible and another project can advance. A later job in the locked project does not jump its eligible head. One candidate per project is briefly locked while determining the actual eligible set; all locks release at transaction end. Admission logs store eligible set, occupied counts, turn and queue age atomically. Specific-run claim requests restrict the project for isolated fixture probes but still cannot skip its FIFO head; they are not a production scheduler API. All fairness evidence uses untargeted claims.

`run_c.py` executes 100 synthetic jobs skewed90/5/5 across3 projects using2 processes/4 connections. It separately checks ordered fairness, capacity/config rejection, locked-project and locked-head progress, unresolved cleanup occupancy through restart, and rollback of claim/turn/attempt/log. Fairness claims concern this finite eligible-set model; no production SLA, workload superiority or actual physical execution cap.

`backup.py` uses trusted locally generated schema-scoped custom `pg_dump`, restores via `pg_restore --single-transaction --exit-on-error` into a fresh marked database and refuses an existing namespace or mismatched caller-held archive hash. The harness creates a truncated local fixture to exercise actual restore failure and verifies no partial namespace. It compares all model tables from repeatable-read fingerprints, exact package bytea, independent source-held input anchors, attempt history, report refs/outbox state. A child holds uncommitted completion writes during dump; those writes must be absent after restore. No restore operation sends outbox events; a separate test sink checks pending replay/duplicate stable ID and acknowledged-event suppression, while the source remains unchanged.

This is metadata-only backup/restore of a trusted synthetic schema. It excludes external blob files, secrets/master keys, roles/cluster settings, PITR, power loss, retention/migrations and production disaster recovery. Never restore an external/untrusted archive through this harness: PostgreSQL restore executes source-defined SQL. Official [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html) / [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html) docs describe these tools; measured results and scope are recorded separately. Whole canonical replay packages stay restricted internal data, not authorized QA exports. Authenticated live policy/revoke and actual worker/container cleanup remain S4/S6 prerequisites.
