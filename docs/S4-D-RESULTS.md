# Current pre-push recheck — 13/11/2026

S4-D **R4 actual D01–04 PASS19.379s/42 input hashes before=after=current**, [fresh evidence](s4d-results/2026-11-13-r4.json). Only source change since reviewed R3: remove extra blank line at end of new schema.sql so staged whitespace checks pass; SQL statements/behavior unchanged. Actual helper exit0/unit+cgroup absent, DB stopped; cleanup1.204–1.237s. R3 and its prior source hashes below remain historical, not current after normalization. Independent pre-push re-review pending; original selected semantics/limits and findings history retained. [Pre-push record](CDS5-PUSH-REVIEW-2026-11-13.md) tracks exact new snapshot.

# S4-D results and review

Status: **DONE — selected synthetic trusted-local lifecycle scope, independent R3 CLEAN**. [Protocol](S4-D-PROTOCOL.md) was written before implementation. [Actual R3](s4d-results/2026-11-12-r3.json) PASS D01–D04 in 18.113 seconds, 42 source inputs before/after matched, and credential metadata/diagnostic/evidence scans passed. Root reported disposable DB STOPPED; R3 records helper exit 0, transient unit absent and cgroup absent. Synthetic, trusted local controller/helper only.

- D01/D04: active cancel reserved before actual helper cleanup; legacy queued cancellation, forged request/generation and replay denied; original container remained running before cleanup; observed descendant/cgroup/container removal preceded cancelled.
- D02: controlled helper outage kept cleanup unresolved; DB-clock timeout produced failed cleanup and open incident, new execution denied; late actual cleanup closed the incident while preserving failed history, with no automatic retry.
- D03: separate processes and database connections held first transaction while the other waited on a PostgreSQL lock, in both cancel-first and complete-first orders; one reservation won each, two total request audit records, old worker check/renew denied and actual cleanup preceded terminal state. Fixed synthetic job completion is not an accepted report or publication.

[Historical R1](s4d-results/2026-11-12-r1.json) ERROR: test used scheduler credential for a worker renewal, producing E_AUTH instead of expected E_STALE. Corrected test uses worker credential and positive renewal before reservation; R1 retained, R2 is new evidence. DB and helper were cleaned up after R1 per root's actual checks.

| Finding | Status |
|---|---|
| S4D-RV-01 | CLOSED by independent R3 review: reserve atomically retires original assignment and advances its head fence; original binding retained in launch job; R3 checks old worker check/renew denial and actual cleanup. |
| S4D-RV-03 | CLOSED by independent R3 review: clarified trusted in-process methods and absence of a client-facing facade; protocol/README revised after R2; fresh R3 executed. |
| S4D-RV-02 | CLOSED by independent R3 review: R3 exercises both races with separate processes/connections and observed DB lock waits, one winner and actual cleanup. |

The prior IAP-A queued record remains a compatibility authority record; S4-D owns the active lifecycle and blocks its old cancellation shortcut. This bounded harness does not cover host/helper crash recovery, remote worker transport, production authentication, output/report acceptance or a retry policy. Full IAP/S4/product gates remain open. DONE requires required checks and latest independent CLEAN on the exact snapshot.

[R2](s4d-results/2026-11-12-r2.json) passed D01–D04 but preceded the S4D-RV-03 protocol and README clarification; it remains historical for that earlier input snapshot. R3 is the fresh execution of the revised snapshot. The direct acknowledgement negatives are trusted-method tests, not proof of an untrusted client interface.

Independent reviewer `/root/identity_contract_review` confirmed CLEAN on R3 for this selected scope, with S4D-RV-01, S4D-RV-02 and S4D-RV-03 closed and no remaining in-scope finding. The 42 input hashes are recorded before and after in R3 evidence. This verdict does not close product-wide gates.

Reviewer confirmed 42/42 input hashes before/after/current match; reviewed pre-administrative results record hash prefix `a659504a` (full value not supplied). These raw SHA256 values of the unchanged reviewed files match the reviewer's prefixes:

| File | SHA256 |
|---|---|
| `docs/S4-D-PROTOCOL.md` | `a452beed067385256777f3df004ba5a35e3f14fed897a320ec99f7fed3ac5a39` |
| `spikes/s4d/lifecycle.py` | `5456e855f4afedbe904600667ab484fc42b6ef737427c77b2aac386d89a87862` |
| `spikes/s4d/schema.sql` | `fe59ff4621e25cf4a19fe521776499e26bfe1f7c073ad194a146680323d1ab91` |
| `spikes/s4d/run_s4d.py` | `dfd68b57275abeb39df1504a97fe805dbabd7c6ed8eb8250098d985aa49e00cd` |
| `spikes/s4d/README.md` | `0f8d060b56b1a4c1d24d52b5b0203589f7a446472b10252b06a21a02b65c00ae` |
| `docs/s4d-results/2026-11-12-r3.json` | `860cbb2d00ef86ffe7cbc208e5448f7a09840fcc8f64fb7e1386265d4cca76c3` |

Root also reported 64 regression checks passed (`.cache/s6/parallel-2026-11-12/checks.json (ignored local log, not portable evidence; portable runtime evidence linked above)`), DB stopped, and R3 records helper exit 0 and unit/cgroup absence. Only this administrative verdict and ledger were updated following review; protocol, source and evidence are unchanged.
