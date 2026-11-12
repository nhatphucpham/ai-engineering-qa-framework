# S2-C independent review

11/11/2026, baseline **e61be7e** đã push origin/master trước implementation. **S2-C subset DONE sau final independent CLEAN WT-S2C-R4 và required checks PASS.** Reviewer read-only GPT-6.1 Terra high `/root/s2_final_review` chỉ định trước implementation; root sửa/test. Scope [protocol](S2-C-PROTOCOL.md), `spikes/s2c/` model/schema/backup/harness/README, [results](S2-C-RESULTS.md), new evidence/current plan/decision/handoff. Prior findings S2A-RV-01/S2B-RV-01..04/S2AB-RV-01 giữ CLOSED.

## Stable ledger

| ID | Severity/state | Expected/actual + impact | Fix/check |
|---|---|---|---|
| S2C-RV-01 | P2/CLOSED trên WT-S2C-R4 | Project least-served bị khóa toàn queued rows làm claim returnNone dù project khác eligible; head-of-line blocking | Probe queue heads across eligible projects under admission guard, exclude locked project khỏi actual eligible set. C02 giữ whole project a bằng separate connection, project khác vẫn claim; reviewer xác nhận |
| S2C-RV-02 | P2/CLOSED trên WT-S2C-R4 | SKIPLOCKED trực tiếp có thể claim tail trước locked head; targeted filter cũng có thể skip earlier head, trái FIFO | Materialized FIFO head trước lock/specific filter; locked head bỏ project, không bỏ head. C02 head-only lock với unlocked tail; C04 targeted-tail reject + ordered RR. Targeted fixture project restriction rõ trong protocol/README, không fairness evidence; reviewer xác nhận |

Checks gửi review (ghi trước verdict): root R1 OperationalError do connection còn giữ qua actual DB restart được preserve/fix/recheck, không đổi expectations. R2/R3 snapshots PASS có hạn coverage; latest R4 **9 DB groups PASS/38.708s**,42 source/input hashes before=after. Full45 PASS34.619s/preflight6 PASS0.059s, syntax PASS. Actual final links/fences/rehash/protected artifacts/DB stop + reviewer verdict sau đó đã được bổ sung bên dưới.

Yêu cầu lúc gửi final review: đọc latest snapshot, kiểm RV01/RV02 và lỗi mới/regression, matching raw project identity/anchors, atomic capacity/fairness scope, occupancy/cleanup through restart, dump consistency/truncated rollback/exact restored bytes/outbox replay/source immutability. Fix→recheck→re-review đến CLEAN, stable IDs, không giới hạn vòng; không dùng R2/R3 hoặc historical DONE thay latest gate. Reviewer đã hoàn tất yêu cầu này theo verdict bên dưới.

Full S2/P3-B/P4-A/P4-B và actual auth/worker/container/blob/key recovery vẫn mở. Commit/push quyền user vừa dùng cho output trước S2-C, output mới chưa commit/push. Review không cấp human approval/platform/pilot/publication.

## Final verdict — WT-S2C-R4

GPT-6.1 Terra high `/root/s2_final_review` xác nhận **CLEAN** ngày11/11/2026, đóng S2C-RV-01/02, không finding mới/tái xuất hiện trong scope. Reviewer đọc protocol/model/backup/harness/results/current docs, actual R4 capacity/fairness bounds, cleanup occupancy/restart, consistent committed dump, truncated transactional restore,13 tables/100 exact bytea packages/source-held anchors/outbox replay/source unchanged. S2A-RV-01/S2B-RV-01..04/S2AB-RV-01 giữ CLOSED. **S2-C subset DONE**, không full S2/P3-B/P4-A/P4-B hoặc production recovery.

Reviewer rehash độc lập19 paths của [snapshot](s2c-results/review-snapshot-r1.json), manifest `808200397a04297445c9327c06df96dcc076dc9df9a7d3cfb992d34d9c5af6aa`;42 R4 inputs before=after=current,33 S2-A R5 và37 S2-B R4 inputs đều khớp. Algorithm sorted path + ASCII space + SHA256(file bytes), join LF không trailing LF, SHA256 UTF-8 chuỗi; snapshot tự nó không nằm inventory. `git diff --check` PASS. Reviewer **không rerun DB/full45/preflight6**; các execution checks là root actual, không giả independent execution.

Root links/fences/syntax/rehash và protected tracked paths PASS; DB `local.py stop` thành công, cluster/dumps/marked restore DBs retained ignored cache. Sau verdict chỉ ghi trạng thái/ledger/DONE hành chính; code/protocol/README/evidence R1–R4/42 inputs không đổi. Manifest19-file lịch sử vẫn nhận diện snapshot trước status updates, không đổi để giả hash docs hậu verdict. Pushed baseline e61be7e giữ nguyên; output S2-C chưa commit/push.
