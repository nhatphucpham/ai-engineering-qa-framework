# S2-B protocol v1 — lease/recovery/cleanup persistence subset

11/11/2026. User yêu cầu tiếp sau S2-A DONE. Baseline `master d73dce3` + output S2-A chưa commit; giữ nguyên code/lock/protocol/evidence S2-A và frozen core/fixtures. Reviewer GPT-6.1 Terra high `/root/s2_final_review` đã được chỉ định trước implementation. [Architecture §6/§9](TARGET-ARCHITECTURE.md) và [ADR-003](adr/003-stack-and-spikes.md) là nguồn invariants.

## Purpose / outputs / acceptance trước implementation

Chứng minh trên PostgreSQL synthetic rằng stale attempt không renew/submit/publish sau expiry/recovery, và retry không bắt đầu khi cleanup attempt trước chưa được xác nhận. Outputs version mới: `spikes/s2b/` schema/model/harness/README, protocol này, results/review, `docs/s2b-results/<new-id>.json`, current plan/decision/handoff. Reuse S2-A portable cluster/driver/core bằng imports; **không sửa S2-A code/schema/inputs/evidence**. Không production runtime/DB decision hoặc full S2.

Chỉ cluster marker-bound synthetic đã tạo ở `.cache/s2`, preflight exact pinned versions/integrity trước start; mỗi run schema mới có model identity `s2b-1.0.0`, không migrate schema S2-A. Evidence dùng destination mới, hashes before/after và before/after DB state. Timebox experiment60 phút sau READY theo ADR-003; review fix/recheck không giới hạn rounds. Nếu thiếu prerequisite: preparation-only, DB gates NOT RUN; không mock PASS.

Model/invariants:

- DB server clock cho claim/renew/expiry/deadline. Renew chỉ exact active version/attempt/fence chưa hết hạn; expiry không thể hồi sinh bằng heartbeat. Renew không đổi stateVersion/raw attempt input/package anchors hoặc làm receipt hiện tại stale. Renewal chỉ gia hạn (không rút ngắn).
- Expired checking → `recovering` (internal spike state) + monotonic version/fence + durable cleanup request/incident trong cùng transaction. Invalidate old receipts/packages; no new claim/execution while request pending. Các attempt-input canonical bytes/digests giữ lịch sử riêng; new attempt snapshot không overwrite prior attempt.
- Cleanup ack gắn exact request ID/run/attempt/original attempt fence, shape explicit synthetic observation; reject boolean, wrong/missing scope và replay. Ack chỉ persistence predicate, không authenticated executor proof. Khi recovery cleanup đã ack và policy/budget còn hợp lệ → queued; reclaim atomically tăng attempt/version/fence, giữ prior receipts/anchors. Fixed maxAttempts2 chỉ engineering fixture bound.
- Cancel/revoke persistence operations CAS/row-lock cạnh tranh complete/renew/recovery/reclaim. Active run vào cancelling, invalidate old fence/expiry và tạo/reuse cleanup request; cancelled chỉ sau exact ack. Revoke trong model là per-run denial fact, không real account/project revocation. Completed/cancelled/failed run immutable.
- Cleanup deadline hết mà chưa ack → failed `cleanup_unconfirmed`, incident còn mở; no retry/cancelled giả. Late ack chỉ cập nhật sidecar cleanup/incident, không mutate terminal run. Attempt-budget exhausted sau cleanup → failed, không attempt3.
- Complete giữ atomic package bytes + report + completed + outbox của S2-A, current attempt receipt và caller-held anchors. Old receipt/package không được tái dùng cho attempt2. Whole raw package restricted internal replay; không ordinary export/trust acceptance.

## Failure matrix

| ID | Actual probe cần chạy | Expected |
|---|---|---|
| B01 | Live renew + current receipt/package, DB time | Expiry extends, version/attempt/fence/anchors unchanged; complete still atomic |
| B02 | Expired/stale version/attempt/token renew/result/complete | Reject; no graph; heartbeat không revive |
| B03 | Expiry reconcile + pending cleanup, wrong/replayed ack | Durable request/incident; no claim until exact ack; new attempt fenced; old canonical inputs preserved |
| B04 | Attempt2 receipt/package vs old attempt1 receipt/anchors | Reject stale; new report round-trip valid, exactly1 report/outbox |
| B05 | Two processes/four connections tranh reclaim sau ack | Exactly1 accepted attempt2; all loser claims empty; no overlap before ack |
| B06 | Cancel/revoke trước complete và concurrent complete/stop | Either atomic completion wins or cancelling/no report until ack; no renewal/receipt/new claim after stop |
| B07 | Cleanup timeout + late ack; ack-vs-timeout race | Failed+open incident or ack path; late cleanup không mutate terminal run; no silent cancelled/retry |
| B08 | Retry budget exhausted | Cleanup resolved but run failed; never attempt3 |
| B09 | DB immediate crash/restart with uncommitted recovery writes; committed cleanup request survives | No partial recovery graph; restart reconcile idempotent; pending cleanup vẫn chặn claim, eventual exact ack/reclaim works |
| B10 | Renewal-vs-expiry reconcile / stop-vs-reclaim races | Lock/CAS serializable outcome, monotonic fencing, old work rejected; no bypass cleanup |

Concurrency/fault evidence phải actual processes/connections/DB server clock; không clock mock. Explicit ordered cases chứng minh cả hai nhánh khi scheduler race chỉ quan sát một nhánh. Persisted cleanup observations là synthetic facts kiểm scope/replay, **chưa proof worker/container thực đã dừng**. Không gọi key/account/API/project thật; không global install/service/commit/push/publish/pilot.

Full S2 còn real auth/revoke/worker cleanup (S4/S6), capacity/fairness, backup/restore/external blobs và integration deployment; S2-B DONE không đóng các gate đó. Human decision/raw declared/effective constraint/mapping/provenance và legacy `projection_unsupported` giữ nguyên.
