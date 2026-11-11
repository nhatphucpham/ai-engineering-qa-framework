# S2-A protocol v1 — disposable PostgreSQL transaction subset

Ngày 11/11/2026. Baseline `d73dce3d30a2ee9041b6633ce0fbfdcf78528332`, master sạch. Protocol chốt trước implementation; reviewer độc lập GPT-6 Astra high `/root/s2_review`. Đây là subset của [S2](adr/003-stack-and-spikes.md), không chọn production DB/control/worker runtime.

## Purpose, outputs, acceptance

Kiểm khả năng candidate PostgreSQL bảo toàn exact run/version/attempt khi tranh queue và commit internal report reference + completed + report_ready outbox cùng transaction. Outputs: `spikes/s2/` preflight/local setup/harness/tests, protocol này, [results](S2-A-RESULTS.md), evidence JSON mới trong `docs/s2-results/`, [review](S2-A-REVIEW.md), cập nhật plan/decision/handoff. Không đổi frozen schema/corpus/fixtures/goldens/S1 evidence hoặc core semantics.

Acceptance trước chạy:

- Chỉ cluster mới dưới `.cache/s2/`, loopback, port được cấp cho spike, database tên synthetic riêng. Không đọc environment connection strings hoặc kết nối DB/service có sẵn; fail closed khi không có marker/config/toolchain pin đúng. Stop chỉ cluster do harness tạo, không global install/service.
- 100 jobs synthetic, hai OS processes × hai threads/independent DB connections, barrier trước tranh claim; ghi process/backend IDs và phân bố claims, latency/queue age. Không serialize toàn workload trong một process. Unique occurrence và report/run/event keys do DB enforce.
- Claim row-lock `FOR UPDATE SKIP LOCKED`, tăng version/attempt/fencing token trong transaction; cleanup-unresolved hoặc synthetic live-policy denial chặn claim/publication. Đây là persistence predicates, không authenticated policy hoặc actual worker cleanup.
- Completion khóa current run, recheck version/attempt/token/lease expiry/policy/cleanup, kiểm package bằng caller-held anchors trong cùng transaction. Giữ canonical package bytes trong `bytea`, digest/length và frozen input anchors riêng; không dùng `jsonb` round-trip để giả bytes gốc. Canonical representation không giữ whitespace/key order của file nguồn.
- Report metadata + completed run + outbox atomic. Connection khác không thấy graph trước commit; rollback/crash trước commit để cả ba chưa published; crash sau commit phải thấy đủ graph sau reconnect/restart. Tamper và coherent input rewrite với anchors cũ bị reject. Whole raw package chỉ restricted internal replay, chưa ordinary read/export.
- Hai completions hoặc completion/cancel-state race chỉ một terminal winner. Synthetic cancellation chỉ kiểm CAS/state race, không chứng minh full cancelling/cleanup lifecycle. Terminal repeat/stale attempt/token/version/duplicate IDs bị reject, không tạo report/event khác.
- Delivery đọc committed outbox, retry sau crash trước ack; sink có thể nhận duplicate với stable event ID. Không claim exactly-once delivery. DB/backend fault và process kill ghi riêng; chưa inject điểm nào phải NOT RUN, không gộp thành pass.
- Evidence có versions/commands/code/input hashes/before-after state/actual fault points; test failure/error không bị đổi expected. Full regression và S2 checks thực pass, reviewer latest snapshot clean mới DONE đúng subset. Missing prerequisites → preparation-only DONE nếu review/checks đạt, DB gates NOT RUN/unknown.

## Failure matrix và phạm vi gate

| ID | Fault/probe | Expected observation |
|---|---|---|
| C01 | 2 processes/4 connections, 100 jobs | Mỗi initial occurrence/run chỉ một accepted claim, đủ 100; latency/queue age recorded |
| C02 | Duplicate occurrence/report/run/event identity | DB unique rejection, no partial graph |
| F01 | Wrong version/attempt/token, expired lease | Reject; graph counts/state unchanged |
| F02 | Cleanup unresolved / synthetic policy denied | No new claim/completion; no side effects |
| F03 | Package tamper, coherent rewrite with old anchors | Reject inside transaction, canonical bytes/anchors preserved |
| T01 | Stage completion, observer before commit, explicit rollback | Observer sees no graph; rollback leaves no subset |
| T02 | Two completions / completion vs synthetic cancel CAS | One terminal winner; completed iff exactly one report/outbox |
| T03 | Deferred foreign-key failure at transaction commit | Whole completion rolls back; no partial report/run/outbox |
| K01 | Kill child after graph writes before commit | DB rollback, reconnect shows original run/no graph; retry can complete |
| K02 | Kill child after commit before result acknowledgement | Reconnect sees full graph; repeat completion rejected |
| K03 | Kill after result acceptance before completion | Accepted facts persist independently, no report/completed/outbox until retry |
| K04 | Kill publisher before delivery / after delivery before ack / after ack | Pending replay; duplicate stable-ID delivery possible; ack suppresses further sends |
| R01 | Stop immediate/restart disposable PostgreSQL | Committed graph/bytes/outbox survive, uncommitted graph absent |

K03 chỉ là persisted synthetic result receipt, không trusted assessment acceptance. Package validation không chứng minh source truth/authority. Local DB `bytea` thay blob service trong spike: không kiểm external blob staging/orphan/backup/restore, power loss/fs durability, fairness, lease renewal/reclaim, live revoke/auth, full cancel/cleanup, scoped read/export hoặc full S2/P4-A/P4-B.

Timebox DB experiment 60 phút sau READY theo ADR-003; review loop không giới hạn số vòng. Kết quả pending/failed giữ nguyên và có bước khôi phục. Toolchain sources/version/integrity, commands và actual observations sẽ ghi tại results trước claim READY. Không chạy account/key/API/project thật, chọn distribution, commit/push/publish.
