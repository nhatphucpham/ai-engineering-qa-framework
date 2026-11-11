# S2-A disposable PostgreSQL experiment v1

Windows x64 + Python 3.14.8 experiment, PostgreSQL 18.6, psycopg/psycopg-binary 3.3.8, Windows dependency tzdata 2026.6. Existing core development dependencies: `jsonschema==4.26.0` (see `tools/requirements-contracts.txt`), observed `referencing==0.37.0`. Not a deployment/support matrix or production storage adapter. [Protocol](../../docs/S2-A-PROTOCOL.md) defines scope/acceptance; [results](../../docs/S2-A-RESULTS.md) records actual runs and gaps.

## Reproduce from repository root

No global installation, existing database, account or DSN. Cache must stay inside this checkout. Download/expand only when these destination paths do not already exist; do not overwrite a previous local toolchain/cluster. The official [PostgreSQL Windows page](https://www.postgresql.org/download/windows/) points to [EDB archives](https://www.enterprisedb.com/download-postgresql-binaries); EDB currently lists 18.6 and [PostgreSQL version policy](https://www.postgresql.org/support/versioning/) lists 18 as supported. Selection applies only to this experiment.

```powershell
New-Item -ItemType Directory -Path .cache/s2 -Force
Invoke-WebRequest -Uri 'https://sbp.enterprisedb.com/getfile.jsp?fileid=1260609' -OutFile .cache/s2/postgresql-18.6-windows-x64.zip
Get-FileHash .cache/s2/postgresql-18.6-windows-x64.zip -Algorithm SHA256
Expand-Archive -LiteralPath .cache/s2/postgresql-18.6-windows-x64.zip -DestinationPath .cache/s2/runtime
py -3 -m pip install --target .cache/s2/deps --only-binary=:all: --no-deps --require-hashes -r spikes/s2/requirements-win-py314.lock
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py setup
py -3 -B -m unittest discover -s spikes/s2 -p 'test_*.py' -v
py -3 -B spikes/s2/run.py docs/s2-results/<new-run-id>.json
py -3 -B spikes/s2/local.py stop
```

Verify archive SHA256 **before executing binaries**: `e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2`. This is a local pin measured on the archive downloaded over official HTTPS on 11/11/2026, not an independently signed publisher checksum. `postgres.exe` Authenticode observed **NotSigned**. Preflight rehashes archive and compares extracted bin/lib/share files with its contents before running `--version`; it detects later local changes, not a compromised upstream. Driver wheel hashes come from official PyPI metadata; [psycopg install docs](https://www.psycopg.org/psycopg3/docs/basic/install.html) document Python/Windows/PostgreSQL compatibility. Lock targets Windows CPython 3.14 only; no implicit global dependency update.

`setup` refuses an existing marker or cluster. Uses loopback on a newly selected port, new `s2_synthetic` DB/user and a random identity marker. Trust authentication is for dummy local data only; not an auth/security proof. `connect` takes no external DSN, strips PG* environment variables in its process, checks local pg_ctl/PID/port/path and random database marker before schema writes. Each run creates a fresh `s2_<uuid>` schema, preserves previous evidence and never overwrites an evidence file. Schema model intentionally covers only this subset. `local.py start` restarts the retained cluster; `stop` targets only the marker-bound cluster. No background DB should remain after handoff.

Failure: inspect `.cache/s2/last-error.txt` locally and the new evidence `status/errorType`; fix the cause and use a new evidence filename. It is not a safe diagnostic API for untrusted production data. If setup stopped after starting the fresh cluster but before database creation, inspect marker/status and use `local.py initialize-database`; this command only creates the named database/identity and refuses when it already exists. Otherwise preserve the cache and diagnose rather than resetting it. If binaries/driver missing, preflight reports NOT READY; no mock substitutes a DB PASS. `test_preflight.py` tests prerequisite rejection with filesystem/environment fixtures, not database correctness.

Cleanup: `local.py stop` releases server processes/port; binary cache/cluster/test sinks are retained under ignored `.cache/s2` for inspection/restart. To reclaim disk later, first verify the resolved absolute cache path is inside this checkout and the marker-bound server is stopped; remove only that disposable cache. There is no automatic recursive-delete command. No services, PATH changes, work DB or credentials are touched.

## Model boundaries

Preflight verifies the exact local versions of psycopg, psycopg-binary and tzdata, their loaded module paths under `.cache/s2/deps`, and the binary implementation. Missing/mismatched metadata or a globally loaded fallback is NOT READY. The lock includes the Windows tzdata dependency; `--no-deps` installs only the three hashed experiment wheels. Core dependencies must already be available (or installed project-locally from `tools/requirements-contracts.txt`); the experiment does not update global packages.

`store.py` locks run rows and revalidates package against independently persisted input digests inside completion transaction. Lease uses DB server time, rechecked after validation before writes. Completion inserts report canonical `bytea`, updates terminal run and inserts outbox atomically; deferred report FK allows a genuine commit-failure probe. Claim uses [PostgreSQL row locks/SKIP LOCKED](https://www.postgresql.org/docs/18/sql-select.html), unique constraints and current synthetic policy/cleanup predicates. No lease renewal/reclaim/fairness, real policy/auth, network worker, external blob or ordinary read/export is implemented.

The run's `bundle/assessment` bytes are frozen **pre-completion inputs**; separate columns hold current persisted lifecycle state. This is not a new P1 completed bundle. Canonical representation preserves raw values/mappings/provenance/constraints/human decision but not source-file whitespace/key order; `bytea` round-trip and independent anchors are checked. Whole replay package stays internal. `receipts` is only a synthetic current-result receipt, never proof of trusted assessment.

`run.py` uses actual processes/threads/connections and process termination. A test sink appends only stable event IDs, demonstrates duplicate delivery after crash before ack, and replays pending outbox after DB restart. Synthetic cancel is a terminal CAS competitor, not full cancelling/cleanup implementation. WAL recovery after immediate DB stop is distinct from OS/power failure or backup/restore. Results never imply full S2/P4-A/P4-B DONE, SLA, exactly-once external execution or authorization to publish.
