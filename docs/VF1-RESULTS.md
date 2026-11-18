# Yêu cầu hiện hành — commit/push VF1, 18/11/2026

User yêu cầu **“commit và push”** output VF1 đã independent CLEAN. Cho phép commit/push gói VF1 cùng current-doc handoff, exact-byte Git policy và pre-push verification; [pre-push record](VF1-PUSH-REVIEW-2026-11-18.md) lưu checks/snapshot/verdict. Các câu no-Git/chưa commit bên dưới là lịch sử trước quyền mới. Actual commit/remote/clean-tree xác minh sau Git action, không suy từ intent. Giữ VF1 DONE selected bounded scope và full product gates OPEN; không triển khai connector mới trong lượt Git này.

# VF1 — actual synthetic QA value flow

18/11/2026, baseline `470bd8bf12a23e4472c907f313a9f03d9ed699d6`. **DONE selected bounded scope — independent CLEAN R2.** Independent reviewer `/root/ux_review`, configured GPT-6.2 Astra high. [Protocol1.0.0](VF1-PROTOCOL.md) was written before implementation/execution; [source and commands](../spikes/vf1/README.md). User approved a bounded real value flow because the previous dashboard only displayed authored data.

## Observed result

Fresh [A](vf1-results/vf1-20261118-r1/a/execution.json) and [B](vf1-results/vf1-20261118-r1/b/execution.json) each executed9 fixed checks in its own rootless readonly/no-network container: **6 pass,3 assertion fail,0 error,0 skipped**. Exit0 means observations collected successfully, not all tests passed. The two reset assertions reproduce one behavior, and the cross-category cache assertion a second. Original source/tests were not repaired.

| Selected criterion | A: all offered observations | B: API page/size observation withheld before reasoning |
|---|---|---|
| AC01 exact service category/case | verified | verified |
| AC02 reset page before request | failed | failed |
| AC03 full-tuple cache correctness | failed | failed, with open coverage for page/size |
| AC04 fixed-category pagination | verified in explicitly bounded composite scope | unverified, required integration evidence missing |

Both summaries remain **failed / humanDecision pending**. B also retains `hasUnverifiedMandatory=true` and `hasOpenMandatoryCoverage=true`; the gap does not erase proven defects. No UI status override exists. Actual derived [A view](vf1-results/vf1-20261118-r1/a/view.json), [B view](vf1-results/vf1-20261118-r1/b/view.json), [read-only dashboard](vf1-results/vf1-20261118-r1/dashboard-r3.html).

AC04's A judgment is a **composition inference**: direct unit execution checked service order/out-of-range empty payload and total; direct in-process API execution checked fixed-category pages/page sizes; source inspection showed API returns the service response unchanged. There is **no direct API out-of-range assertion**. A's scope says this explicitly; it is not a claim of exhaustive API/HTTP/e2e coverage. B lacks the required API page/size runtime observation even though its test source is visible. Further API boundary checks would strengthen confidence; this experiment cannot measure general agent accuracy or product usefulness.

## Actual reasoning and provenance

Root staged only the eight allowlisted inputs plus trusted wrapper, executed fixed authorized checks and delivered separate source+observation requests to two fresh-context agents. AssessorA `/root/vf1_reason_a`, assessorB `/root/vf1_reason_b`, both launched with `model=gpt-6.2-astra`, `reasoning_effort=high`, `fork_turns=none`. Exact model IDs are orchestration metadata, not child self-report. No external provider SDK/key/account invocation, measured token/cost or unattended connector is claimed. Agent plans/bindings were supplied live through this host-mediated file port; core alone derives statuses.

Each request binds its own run/job, requirement/candidate revision, source byte hashes, execution byte hash and canonical job digest. Full raw private execution, limited offered job and anchors are separate files. Full internal bundle/prepared report stays out of the narrow viewer. AC05 is excluded, with historical v1 labels; whitespace decision v2 remains valid.

B's first proposal overused the repeat-request integration check for AC04 and was **rejected E_VF1_POLICY**. The same independent assessor corrected mappings, preserving [attempt1](vf1-results/vf1-20261118-r1/b/host-response-attempt-1.json); root did not author replacements or prescribed statuses. Root initially misattributed the batch failure to A, then inspected disk and corrected it. A's [archive](vf1-results/vf1-20261118-r1/a/host-response-attempt-1.json) is byte-identical administrative backup, not a rejected judgment. Initial batch derive had already written A before B rejection. Orchestrator now validates the whole batch before any writes; explicit exact-byte resume preserved A and added B.

## Checks and preservation

- Actual worker records pin image IDs, interpreter/stdlib/library file manifests and tar hashes; local Python3.12.3, Podman4.9.3/crun1.14.1. Built only from existing system bytes, no installation/pull. Host Windows Python3.14.8.
- Both container/process/cgroup cleanup observations true. Each [supervisor record](vf1-results/vf1-20261118-r1/a/supervisor.json) shows workerExit0, transient unit not-found and cgroup absent (B has its own record). Marker-owned private image/cache directories remain intentionally recorded; this is not whole-supervisor/host-crash recovery.
- Adapter8 tests PASS0.288s; after review fixes, all11 VF1 boundary/adapter tests PASS0.438s; unchanged core regression45 PASS42.600s. Audit checks actual/pair, duplicate no-overwrite, wrong revision/held digest/sibling/nonoffered/hash rejection, error/skipped remain unverified. Authored negative inputs are separate from actual observations. New source-drift/concurrent-writer regression tests do not manufacture new execution evidence.
- [Browser r4 checks](vf1-results/vf1-20261118-r1/browser-r4/checks.json):18 scenario records PASS on current dashboard-r3,1024/320 widths, both runs/four ACs, own-run provenance, source disclosure, retained focus through keyboard-only run→criterion→source journey, visible failed+gap, no horizontal overflow/page errors/application network. Fragment/preview/checker SHA256 bound. Offline wrapper CDN requests separately blocked. Historical r1 mobile screenshot capture was truncated; r2 fixed capture, r3 added explicit open-coverage text, r4 verifies focus fix. Screenshot height is capture-only after real viewport interaction checks.
- Frozen [424-path baseline](vf1-results/vf1-20261118-r1/baseline-paths.json); audit-r2 verified all424 byte-identical before current-doc prefixes. [Audit r3](vf1-results/vf1-20261118-r1/audit-r3.json) verifies420 unchanged paths plus only four byte-preserving current-document prefixes.

## Review ledger

Independent review assigned from protocol; reviewer read exact code, actual results, viewer and documentation. R1 found three issues; root fixed them; independent R2 confirmed all three CLOSED with no unresolved/new in-scope finding. **DONE selected bounded scope.** Reviewed [71-path snapshot](vf1-results/vf1-20261118-r1/review-snapshot-r2.json) SHA256 `5e7b463593c87609b95d8b851e9fa8bfb977b7468cc876a9415003d4b65acc67`; [closure record](vf1-results/vf1-20261118-r1/review-closure.json) records administrative status updates separately, preserving that snapshot. Latest11 tests PASS0.393s, prior unchanged core45 PASS, audit13 and browser18 records PASS. Do not count this slice as full product readiness.

| Stable ID | R1 issue and impact | Fix / verification for re-review | Status |
|---|---|---|---|
| VF1-RV-01 HIGH | Job builder reread mutable checkout after execution, allowing newer source to label old results. | Build only from staged byte pins. Derive/audit reconstruct complete offered job against worker input hashes, raw record, held identities/hash/timestamp and permitted mask. Regression changes original after stage, changes staged bytes and self-consistently tampers source/outcome/timestamp/IDs. Actual A/B offered hashes already matched worker pins offline. | CLOSED — independent R2 |
| VF1-RV-02 MED | File appearing between preflight/write could be silently skipped. | Exclusive `xb`; FileExistsError rejects default or compares exact bytes only for explicit resume. Concurrent same-byte/default, different-byte/resume reject; same-byte/resume accepts without overwrite. | CLOSED — independent R2 |
| VF1-RV-03 MED | Rerender removed focused run/criterion controls; keyboard navigation restarted. | Restore activated control focus; new browser journey checks retained focus and Tab/Enter/Space to source disclosure at both widths. Current fragment/checker hashes and B AC03/04 gap visibility recorded. | CLOSED — independent R2 |

## What remains

This proves a bounded synthetic execution→live host reasoning→existing core→derived view path and missing-evidence behavior. It does not implement a deployed authenticated background agent connector, arbitrary project intake, native Windows dashboard, ordinary content/export authorization or full autonomous service. Next value step is a versioned host-connector/orchestration contract that removes the session's file-port mediation while preserving these invariants, alongside required S4-F durable supervision/recovery and the existing security gates. Production stack/provider target, real account/project/pilot and publishing remain unchosen/not authorized. No new commit/push performed.
