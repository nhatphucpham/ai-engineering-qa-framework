# S6-B independent review

11/11/2026. **S6-B synthetic subset DONE after final independent CLEAN WT-S6B-R4-D2 and required checks PASS**. Reviewer GPT-6.1 Terra high `/root/s2_final_review`, read-only and assigned before implementation. Scope: [protocol](S6-B-PROTOCOL.md), `spikes/s6b/` dependency/preflight/schema/facade/store/diagnostic/harness/tests/README, [results](S6-B-RESULTS.md), new evidence and current plan/handoff. Baseline e61be7e plus S2-C/S6-A working tree preserved. Prior S2/S6-A findings remain CLOSED. Full S6/P3-B/P4-B, production auth, worker/broker/TLS/OS keys and actual S4 excluded/open.

## Stable findings

| ID | Severity/state | Expected/actual + impact | Fix and actual verification |
|---|---|---|---|
| S6B-RV-01 | P1/CLOSED WT-S6B-R4-D2 | Public issuance/helper boundary could let requests select trusted minting without authentication | Split trusted `_Store` from sole `Identity.dispatch` route/field whitelist; helpers/bootstrap/SQL/TTL/hooks unavailable to requests. R4 I02/I09 actual negative helper impersonation and override tests PASS; Python host trust explicit |
| S6B-RV-02 | P2/CLOSED WT-S6B-R4-D2 | CLI scans ran before collecting stored account hashes and omitted dummy hash, overstating encoded-hash coverage | Collect current accounts + control dummy hash before subprocesses, retain/re-scan buffers with full raw/base64/hex canaries. R4 I09 new coverage markers PASS, parent/evidence also scanned; historical R1 preserved |
| S6B-RV-03 | P2/CLOSED WT-S6B-R4-D2 | Disabled login alone did not prove preissued access/refresh invalidation or durable restart rejection | R4 I05 rejects both pre-disable tokens before/after DB restart; also reset-old access after restart and change-old refresh |
| S6B-RV-04 | P2/CLOSED WT-S6B-R4-D2 | Owner assignment escalation probes did not cover demoting/removing current Owner | R4 I06 attempts Owner→Viewer/remove, both deny and Owner row stays unchanged; Admin transfer still succeeds |
| S6B-RV-05 | P3/CLOSED WT-S6B-R4-D2 | Rehash state only tested the current-profile false case | R4 I01 actual older-parameter dummy Argon2id hash verifies and check_needs_rehash=True, while current profile=False; legacy fixture not used for accounts |

R1 actual9 groups PASS14.516s covers historical source/workload. R4 latest actual9 groups PASS13.260s,31 input hashes before=after,5 prerequisite subprocess methods PASS0.893s. Source/schema/protocol/README used by latest run are immutable while executing. Full core regression45 methods PASS34.430s. Final source/protected-hash/links/syntax/DB-stop checks recorded below when complete. Required final review must read latest exact snapshot, confirm all five IDs closed/no regression/new finding, and inspect evidence versus claims before DONE subset. No fixed maximum rounds.

No UI changes/screenshots. No commit/push/publish or real accounts/keys/API. Review does not replace actual tests/human approval or close full product gates.

## Submitted final review package — WT-S6B-R4 (historical pre-verdict)

R4 actual9 groups PASS13.260s;31 inputs before=after=current; core45 PASS34.430s; prerequisites5 PASS0.893s. Final root verification: Python AST PASS;19 changed/new Markdown files local246 links/fences PASS; protected tracked core/tools/schema/corpus/S1/S2-A/B source/protocol/evidence unchanged; old S2-A33/S2-B37/S2-C42/S6-A42 input hashes all exact. `git diff --check` PASS. DB `local.py stop` successful and `pg_ctl status` expected exit3, cache untracked/ignored. No actual S4 checks or new full S6 gate claim.

[Exact snapshot](s6b-results/review-snapshot-r2.json) inventories current changed tracked/untracked files excluding itself. Algorithm sorted path + ASCII space + SHA256(file bytes), join LF without trailing LF, SHA256 UTF-8 string. Historical prior manifests remain untouched; current docs will only receive administrative verdict/status after clean review. Reviewer must inspect this current code/evidence/docs and all5 IDs, not infer CLEAN from root's tests. Snapshot r1 is historical: root caught an overbroad docs revision substitution and restored unrelated P4-A/S2-A/B history references before verdict; implementation/protocol/R4 evidence unchanged. R2 snapshot captures those corrected current docs.


## Final verdict — WT-S6B-R4-D2

11/11/2026. GPT-6.1 Terra high `/root/s2_final_review` confirmed **CLEAN**, S6B-RV-01..05 CLOSED, no new/regressed finding in scope. Read latest protocol/schema/identity/facade/harness/tests/results/current docs including restored historical references; checked real R4 coverage for helper denial, full captured hash canaries, change/reset/disable old tokens before/after restart, Owner demote/remove versus Admin transfer and rehash true/false. **S6-B synthetic identity/session/RBAC subset DONE** after required checks; full S6/auth deployment/service-worker/broker/P3-B/P4-B remain open, S4 actual NOT RUN.

Reviewer independently rehashed55 files in snapshot r2, manifest `20be48e4398cf03c5ba103cba20030a48e445efd80af3d7438b50698799c5cf0`;31 R4 inputs before=after=current plus S6-A42/S2-C42/S2-B37/S2-A33 exact. Independent prerequisite5 methods PASS0.692s and diff-check PASS. R4 DB9 groups/core45 are root actual, reviewer did not rerun them. Root final links/fences/syntax/protected hashes/DB-stop/cache checks PASS; latest19 Markdown files contain247 local links at submission.

Only administrative verdict/ledger/status recorded after CLEAN; code/protocol/README/evidence and31 R4 inputs remain unchanged. Historical55-file manifest is not rewritten to pretend administrative docs retain its bytes. Baseline e61be7e unchanged, S2-C/S6-A/S6-B outputs remain uncommitted/unpushed; no new Git action. DB stopped, expected status exit3.
