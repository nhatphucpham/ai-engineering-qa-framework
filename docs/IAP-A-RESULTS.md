# IAP-A queued-command subset — actual results / review

12/11/2026. Status **DONE IAP-A queued-command synthetic subset sau independent CLEAN R5 và required checks PASS**. Baseline master **e8b47a18925dc1c64d817e1facd27dc83250f69c**, previous docs/evidence push actual verified HEAD/origin/master/remote; clean tree sau action. User yêu cầu tiếp phát triển. [Protocol](IAP-A-PROTOCOL.md) chọn subset trước code; [README](../spikes/iap/README.md) nêu cách chạy. Reviewer GPT-6.1 Terra high `/root/identity_contract_review` read-only từ đầu, stable IAPA-RV IDs; fix/check/re-review đến CLEAN, không tự cắt vòng. Output IAP-A mới chưa commit/push.

## Outputs / authority / doneWhen

New `spikes/iap/application.py/schema.sql/run_iap.py/README.md`, protocol này có version trước implementation, new R1–R5 JSON, record results/review này, current5 plan/decision/handoff docs. Trusted fresh `id_<uuid>` namespace reuses unchanged S6-B identity/schema + new application_identity version; identity/policy/application writers share held DB identity control mutex. `Application.dispatch` exact whitelist/version/fields, host setup/SQL/hooks không routable. Đây là local trusted Python host/DB experiment, chưa network authentication/Python sandbox/production composition.

DoneWhen subset: Q01–08 actual selected behaviors PASS có DB observer/process/order/fault evidence; hashes/current refs và old source preservation PASS; core45 + relevant prerequisite checks PASS; independent latest CLEAN, findings old/recurrent/new không còn open. Full IAP matrix và product gates không nằm trong DONE. Source core/S2/S6/schema/fixtures cũ giữ nguyên, không thay expected để xanh.

## Actual executions / evidence provenance

| Evidence | Actual result | Meaning / snapshot |
|---|---|---|
| [R1](iap-results/2026-11-12-r1.json) |8 groups PASS15.183s/36 inputs before=after|Initial code; Q04 chưa credential ordering, replay/audit-facade gaps. Historical PASS không chứng minh latest acceptance |
| [R2](iap-results/2026-11-12-r2.json) |8 groups PASS17.832s/36 inputs before=after|Thêm actual disable/start hai ordering; trước fixes reviewer01/02 |
| [R3](iap-results/2026-11-12-r3.json) |8 groups PASS18.876s/36 inputs before=after|Fix replay read authority và actual audit/deferred-FK facade behavior |
| [R4](iap-results/2026-11-12-r4.json) |8 groups PASS19.595s/36 inputs before=after|Thêm observer23503; Q08 replay/read-narrowing claim chưa tách stale epoch, historical snapshot |
| **[R5 latest](iap-results/2026-11-12-r5.json)** |**8 groups PASS18.014s/36 inputs before=after/current match**|Tách current-epoch receipt denial sau narrowing khỏi old-epoch start replay bị fence trước prior; RV03 correction |

Commands thực: `py -3 --version` Python3.14.8; `py -3 -B spikes/s6b/preflight_b.py` READY local pins; `py -3 -B spikes/s2/local.py preflight` toolchainReady/archive/extracted integrity true PostgreSQL18.6 + local driver3.3.8. `py -3 -B spikes/s2/local.py start` actual STARTED. Mỗi evidence run dùng `py -3 -B spikes/iap/run_iap.py docs/iap-results/<new-id>.json`, exit0; harness Q08 tự stop/start DB sau actual commit. R1 xong stop, R2 start→run→stop, R3 start→run, R4 dùng same own cluster còn chạy từ R3→run→stop; R5 start→run→stop. Không chạy chung fixture DB khác; core tests độc lập offline. Final marker-bound pg_ctl status exit3 sẽ recheck trước chốt.

Core regression command `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`:45 PASS33.527s ban đầu và **45 PASS33.631s latest sau fixes**. Prerequisites: S6-B5 PASS0.794s, S2-common6 PASS0.043s; no failures/errors/skips. Không rerun S1 benchmark/S2/S6-A/full S6-B workloads, không cần engine/network cho queued-only subset. Actual logs retained ignored `.cache/s6/iap-a/` (`core-final.log`, checks.json), không portable runtime prerequisite; actual counts/commands ghi ở đây và raw source manifest trong JSON.

| Group | Latest actual selected proof | Limits |
|---|---|---|
| Q01 | Atomic run/delegation/receipt/success-audit/queued-outbox graph; same payload replay;2 processes/collision both payload orders + observed DB lock wait; principal key isolation; start-only replay denied, new authorized grant replays same immutable receipt |No exactly-once external execution/delivery |
| Q02 | Wrong-kind/forged token, extra authority/hook/helper/version/bool fields, grant-subject/project refs/receipt denial through facade |No service authentication/HTTP or full A02 |
| Q03 | Old snapshot promotion ceiling, live role downgrade/remove/project/account disable, explicit grant revoke, reset/relogin old credential epoch denial |No background dispatch/revocation fan-out/member epoch/restore anti-rollback |
| Q04 | Two actual processes/connections, actual second DB lock wait; command-before-policy vs narrowing-before-command; command-before-disable vs disable-before-command |No external release permit/IO cutover proof |
| Q05 | Authenticated tentative run exists inside tx, DB access expiry→whole graph rollback; grant expiry→same rollback, independent observer sees0 graph |Trusted harness hooks, no client hook exposed |
| Q06 | Runner own/Owner other queued cancel, version conflict, replay stable; cancel-only replay denied, new current grant replays; exact2 receipts/outbox/audit graph |No assignment/claim exists, so queued cancel not actual cleanup proof |
| Q07 | Actual trigger injects deferred FK violation, facade returns E_DEPENDENCY, trusted observer confirms23503, all graph0 after rollback; same-key retry creates one graph; audit+denial-audit trigger outage fails closed; missing policy blocks |No deployed outage/restore/distributed transaction proof |
| Q08 | Actual commit→simulated caller drop→actual DB restart→authenticated receipt/replay same graph; budget denied no partial graph; current-epoch receipt request denied after read narrowing (combined snapshot/live ceiling), old-epoch start replay fenced before prior; app tables/parent output/evidence raw/base64/hex dummy credential/hash scan |Response loss simulated at caller boundary; no actual network crash, no model/sink/secret taint pipeline |

36 input hashes identify working bytes at each run; R1–R4 may differ from latest legitimately. Không rewrite historical hashes, không claim Git-EOL normalization là raw hash match. Snapshot digests trong command là synthetic selectors do caller supplied, **không trusted artifact resolver**. Delegation rows metadata only, no service/worker port. Core report/declared-effective constraints/provenance/human pending semantics untouched.

## Finding ledger / root fixes

Current **IAPA-RV-01/02/03 CLOSED** theo independent CLEAN R5; không finding cũ/tái xuất hiện/mới chưa xử lý trong scope. Required checks PASS; DONE chỉ queued-command synthetic subset. Reviewer được giao từ trước code, read sớm source/protocol và xác nhận hai findings trước official R4 snapshot.

| ID | Expected / actual / impact | Fix + actual recheck; điều kiện đóng |
|---|---|---|
| IAPA-RV-01 / P1 |IAP §5.1 replay cần current read authorization; initial prior trả receipt chỉ từ start/cancel grant, có thể đọc receipt khi current grant không cho read|`prior` reauthorizes receipt action with authenticated subject/live policy/current persisted grant before digest/result; R3/R4 start-only/cancel-only committed replay negatives + new valid grant positives + policy receipt narrowing; reviewer R4 xác nhận CLOSED, no recurrence |
| IAPA-RV-02 / P2 |Initial Q07 raw trusted FK hook chưa chứng minh safe facade error/audit-outage paths như acceptance|Actual DB trigger injects FK at facade commit; response E_DEPENDENCY + trusted observer23503, independent graph0 and retry exactly1. Audit success/denial outage trigger makes both requests fixed E_DEPENDENCY/no graph. R3/R4 probes PASS; reviewer R4 xác nhận CLOSED, no recurrence |
| IAPA-RV-03 / P2 |Q08 initial combined claim read-policy narrowing denied replay, nhưng replay dùng grant/payload epoch5 khi policy epoch7 nên bị fence trước prior; chưa isolate read gate|R5 tách current-epoch receipt request denial (combined snapshot/live read ceiling) với old-epoch start replay fenced-before-prior. Không sửa expected/epoch để giả đã tới read gate. Q01/Q06 cùng-epoch start-only/cancel-only và new valid grant positive vẫn proof riêng cho RV01; reviewer R5 xác nhận CLOSED;01/02 không tái xuất hiện, không new finding |

No self-closing findings. Required source/body manifests/docs checks và reviewer verdict bổ sung sau actual execution; record self ngoài body hash. Thay substantive output sau CLEAN phải re-review; chỉ status/verdict hành chính được ghi sau verdict theo workflow.

## Product gaps / next action

Chỉ **selected interactive/queued DB subparts** của IAP-A01/A02/A04–A07/A09/A10/A11/A14. Không full24 cases PASS. Background continuation/session-vs-delegation/service auth/worker/attempt/lease/actual cleanup, common external release permits, scoped content/export/source streams, broker/OS keys/sink/collector/taint và restore latest authority đều NOT RUN/chưa có. Full S2/S4/S6/P3-B/P4-A/P4-B–E/P5/P6/readiness vẫn mở. Prior S4 discovery không là inventory host mới; engine chưa cần cho subset này.

Next bounded slice: service enrollment + run delegation/assignment authority trước claim/worker/broker, protocol/schema/fault matrix/prerequisites mới và actual evidence. Không tự triển khai full runtime hoặc gọi real accounts/keys/API/project, chọn production stack/pilot/publish. Output sau push e8b47a1 hiện chưa commit/push.


## Root exact snapshot checks — IAPA-R4 / official review1

`py -3 -B .cache/s6/iap-a/check_output.py official-r1` **PASS**:326 original tracked paths exact unchanged,5 current docs original bytes preserved as suffix (331 paths protected total),170 local links/fences/newlines/whitespace/sensitive-pattern/Python AST checks; latest8 groups/36 input hashes before=after/current match; core45 + prereq11 transcript checks; final marker-bound pg_ctl status3; `git diff --check` exit0. Before current-doc prepend,331/331 tracked paths exact unchanged after executions. Current sources/old evidence/corpus/goldens/frozen protocols untouched; output paths confined to new IAP source/docs/evidence +5 current docs.

Fourteen-body raw working-byte manifest excluding this record: sorted `path + ASCII space + SHA256(raw bytes)`, join LF without trailing LF, SHA256 UTF-8 `9212387a41ecb3a56a93aafee2e1d2bf229f96711b2b3d78d53f6fbbd8bd1eb7`.

| Body path | Raw SHA256 |
|---|---|
| `docs/DECISION-LOG.md` | `3dcd916dcd610c39d020c892558ec3d3a6da4546a22a92465a4959a75fefc2d2` |
| `docs/IAP-A-PROTOCOL.md` | `d5db0127a07c6d3270edc260d5fd95a9b126343b89bbde067720bf90dd0dda88` |
| `docs/IMPLEMENTATION-PLAN.md` | `c92a4fa4de12bb94787392d889dd81b62f7f404c9cf9ef4b52f1ce43a68a54b9` |
| `docs/NEXT-SESSION.md` | `73a0ac5b8b47acfee307111da6b96b54ce5ca9b04a95d8edd79b9f048c7309a4` |
| `docs/SESSION-HANDOFF.md` | `0a463003c273ef8f72b6771766633c4c0692e6d69d56b3fd5bd53d6399186cf6` |
| `docs/SESSION-PLAN.md` | `a46e1b53969d916802e57f3a86c929f37b7c8c0059f0cc82347449a9a1d8ac9e` |
| `docs/iap-results/2026-11-12-r1.json` | `f0ba68d68d7ba1b81e18c1de0f32bbaa8b3a11bdf2b22f705e280111d95b944c` |
| `docs/iap-results/2026-11-12-r2.json` | `d8ef0daf204170d901a5a93b529ef22dcca5abdca3dd5d05c9abefbac7a548d2` |
| `docs/iap-results/2026-11-12-r3.json` | `6dea413fe10c298302fa3429fb2fd42208cbfa3481091cc470fc60170f87f219` |
| `docs/iap-results/2026-11-12-r4.json` | `de1aea0517439d22f2ce07aeea0f104ddac13f51c97c6468df3fa25dd703d293` |
| `spikes/iap/README.md` | `f8d5abc903305afcd35f48bfd0998e4b7f931224a5cac43d335f0f37856a3972` |
| `spikes/iap/application.py` | `5514035188bc7fa126d0badd92c45b37ccbe2ada7fbcd2e1371c8fd15eaa9e8b` |
| `spikes/iap/run_iap.py` | `4149d98f67e85b3a0c07bc4164afa2fe7006478e465744f20d14135ce506cc58` |
| `spikes/iap/schema.sql` | `b11fae47d2a53d7d87b3d9298e24f3ccf459e3123fa518bd6a6e61e3543ea963` |

Root actual regression/prereq logs and baseline/checker remain ignored local `.cache/s6/iap-a`; evidence JSON carries all36 source/input hashes, baseline, command, pins, timings and safe observations. Send exact14 body files+record+findings ledger to independent reviewer; no self-closure/DONE until latest CLEAN. Body changes after review require new manifest/re-review, old manifests retained.


## Independent review R4 và correction RV03 / snapshot R5

Reviewer độc lập đọc full R4 body/record, checker PASS cùng manifest, xác nhận **IAPA-RV-01/02 CLOSED**, không tái xuất hiện. Phát hiện RV03 như ledger: phải tách nguyên nhân denial, không dùng generic E_DENIED làm proof của một gate chưa tới. Root đổi Q08 field/assertion wording và record/current entries, **không đổi authority behavior/expected**, new R5 actual8 PASS18.014s/36 inputs before=after/current match. R1–R4 evidence nguyên vẹn. Source application/schema/core/prerequisites không đổi sau R4; chỉ runner claim labels thay, targeted harness rerun phù hợp, core45/prereq11 actual checks giữ như trên. Chưa tự đóng03/DONE.

R5 không khẳng định isolate live-policy-only read denial: grant mới epoch7 có start ceiling và policy không receipt; request receipt bị từ chối trong combined effective authority. Request start replay epoch5 bị từ chối trước prior; actual prior/read-authority negatives riêng ở Q01/Q06 dùng same-epoch admissible start/cancel grants và immutable committed receipts, positive new full grant trả cùng receipt. Đây là các observations khác nhau, không gộp thành một proof.


## Root exact snapshot checks — IAPA-R5 / official review2

`py -3 -B .cache/s6/iap-a/check_output.py official-r2` **PASS**:326 original tracked paths exact +5 old-doc suffixes,171 local links/fences/whitespace/AST/pattern checks; latest R5 eight groups/36 inputs before=after/current match; retained unchanged-core45/prereq11 evidence, DB stopped/status3, diff0. Source application/schema/protocol/README unchanged since R4; only runner denial-label/assertion wording changed, plus new R5 evidence and accurate current docs/ledger. RV01/02 remain reviewer CLOSED;03 pending re-review, no self DONE.

Fifteen-body manifest (same algorithm, record self excluded) `7022cdf3296ac031dd6b17437e019f2f99b94e5b6de915552074bdf6e2933b77`:

| Body path | Raw SHA256 |
|---|---|
| `docs/DECISION-LOG.md` | `ef02d5e22b365cfa7f9e9f15403728575150869382b9e70f3f440b72ff25acf4` |
| `docs/IAP-A-PROTOCOL.md` | `d5db0127a07c6d3270edc260d5fd95a9b126343b89bbde067720bf90dd0dda88` |
| `docs/IMPLEMENTATION-PLAN.md` | `b5887b404a9468135117b26a4088b923670ae2bc22e2c7ba0163d06a752534ee` |
| `docs/NEXT-SESSION.md` | `ea0ba0b8c5548b3bf4ac6ffec2ce319a31b8cbd8cebc656fc9bdb98d33c193f0` |
| `docs/SESSION-HANDOFF.md` | `67a085f5c498ef9b1a7f85afa88ead61f3e4f2af60d111cd32db6bf579ce6736` |
| `docs/SESSION-PLAN.md` | `e94840bac5e3db66b085ed57f183becf63a81f36bea9fb45798895bae22565c2` |
| `docs/iap-results/2026-11-12-r1.json` | `f0ba68d68d7ba1b81e18c1de0f32bbaa8b3a11bdf2b22f705e280111d95b944c` |
| `docs/iap-results/2026-11-12-r2.json` | `d8ef0daf204170d901a5a93b529ef22dcca5abdca3dd5d05c9abefbac7a548d2` |
| `docs/iap-results/2026-11-12-r3.json` | `6dea413fe10c298302fa3429fb2fd42208cbfa3481091cc470fc60170f87f219` |
| `docs/iap-results/2026-11-12-r4.json` | `de1aea0517439d22f2ce07aeea0f104ddac13f51c97c6468df3fa25dd703d293` |
| `docs/iap-results/2026-11-12-r5.json` | `1e9f9002b29a98f1c295bd90425b1f9d03eabe2abf096ea8de77b44a80d8cde1` |
| `spikes/iap/README.md` | `f8d5abc903305afcd35f48bfd0998e4b7f931224a5cac43d335f0f37856a3972` |
| `spikes/iap/application.py` | `5514035188bc7fa126d0badd92c45b37ccbe2ada7fbcd2e1371c8fd15eaa9e8b` |
| `spikes/iap/run_iap.py` | `880f3b285e6452b98435bfc22efffcd59ade4b45bbe3a1089557115cf33bcdc5` |
| `spikes/iap/schema.sql` | `b11fae47d2a53d7d87b3d9298e24f3ccf459e3123fa518bd6a6e61e3543ea963` |


## Final independent verdict — IAPA-R5 CLEAN

12/11/2026. GPT-6.1 Terra high `/root/identity_contract_review` confirmed **CLEAN** trên exact15-body manifest `7022cdf3296ac031dd6b17437e019f2f99b94e5b6de915552074bdf6e2933b77` và self-record raw SHA256 `62f2429fd5e6937ed8615e9ca9d708eee8c85e94ea59c7f6eb5e2feb29099d3f`. IAPA-RV-03 CLOSED,01/02 vẫn CLOSED; không regression/new finding trong scope. Independent `py -3 -B .cache/s6/iap-a/check_output.py reviewer-r5` PASS326 paths/5 suffixes/171 links/8 groups/36 input hashes/core45/prereq11/DB status3/diff0.

**DONE chỉ IAP-A selected queued-command synthetic subset**. Chỉ status/ledger/verdict hành chính trong self-record và5 current-doc prefixes cập nhật sau CLEAN; source/schema/protocol/README/evidence/history raw hashes giữ nguyên, không sửa historical manifests để giả post-admin bytes đã review. Không product gate đóng mới: background/service/worker/attempt/lease/actual cleanup, broker/external release/content/OS keys và full IAP24 vẫn mở/NOT RUN. Actual push đã hoàn tất là e8b47a1 trước IAP-A; output mới hiện chưa commit/push.


Final post-verdict administrative check `py -3 -B .cache/s6/iap-a/check_output.py final` **PASS**:326 unchanged tracked paths +5 exact old-doc suffixes,171 links,8 groups/36 input hashes/core45/prereq11, DB stopped/status3,diff0. Administrative15-body manifest `670a60d18374c55dd19683acfee31ce57fb40207789fe5e19299b37fbadc3263`; đây là post-status snapshot, không thay independent reviewed R5 manifest. Source/application/schema/protocol/README và R1–R5 evidence nguyên vẹn. No additional runtime run/Git action sau verdict.
