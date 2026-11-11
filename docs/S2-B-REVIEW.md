# S2-B independent review

11/11/2026, baseline `master d73dce3` + WT-S2A-R5 đã DONE/chưa commit. **S2-B subset DONE sau final independent CLEAN WT-S2B-R4 và required checks PASS.** Scope: [protocol](S2-B-PROTOCOL.md), `spikes/s2b/` versioned fresh-namespace model/harness, [results](S2-B-RESULTS.md), new evidence/current plan/brief/handoff. Reviewer độc lập read-only GPT-6.1 Terra high `/root/s2_final_review` được chỉ định trước implementation; root sửa/check. S2A-RV-01 giữ CLOSED, không sửa code/lock/protocol/evidence S2-A.

## Stable ledger

| ID | Severity / status | Expected/actual và impact | Fix / verification |
|---|---|---|---|
| S2B-RV-01 | P2 / CLOSED trên WT-S2B-R4 | Python True==1 có thể qua exact attempt equality của cleanup ack; protocol reject boolean | Exact type int cho args/observation attempt/fence, current claims và stop version. B03 real-request bool/float probes + unchanged pending run, exact ack sau đó works; reviewer xác nhận |
| S2B-RV-02 | P1 / CLOSED trên WT-S2B-R4 | Ack trễ có thể queued/cancelled nếu sweeper chưa gọi timeout | One materialized DB clock sample ngay lifecycle UPDATE, quá deadline → failed cleanup_unconfirmed; late ack sidecars only. B07 real deadline/no-sweeper, timeout race và terminal row unchanged; reviewer xác nhận |
| S2B-RV-03 | P1 / CLOSED trên WT-S2B-R4 | Expiry có thể đi qua giữa current SELECT và renewal UPDATE; row lock không dừng clock | Conditional expires>clock_timestamp ngay renewal UPDATE; cùng guard cho receipt INSERT SELECT và final completed UPDATE, no-row reject rolls back. B02 real DB time delay hooks renew/receipt/complete reached, unchanged graph; reviewer xác nhận |
| S2B-RV-04 | P2 / CLOSED trên WT-S2B-R4 | Acceptance stop-vs-renew/recovery/reclaim cho cả cancel/revoke chưa có đủ actual independent-connection races | Giữ scope, thêm B10 two-process races đủ cả reason và ordered opposite cases thay vì hạ acceptance; B06 already stop-vs-complete. R4 PASS và reviewer xác nhận coverage |

R1 SyntaxError tại cleanup COALESCE được giữ nguyên evidence ERROR; sửa nguyên nhân không thay expected. R2/R3 actual PASS trên snapshot tương ứng nhưng coverage RV04/ordered cases chưa cuối; không dùng pass cũ để đóng latest gate. Không nhân bản finding cũ qua vòng; khi regression reopen đúng ID.

## Checks/snapshot gửi review (ghi trước verdict)

Root actual full regression45 methods PASS34.940s, S2-A preflight6 PASS0.051s, AST parse và unchanged33 S2-A source/input hashes PASS. Latest DB evidence R4 **10 groups PASS/32.140s**,37 code/input hashes before=after. Đây là gói checks/yêu cầu gửi reviewer trước verdict: đọc latest code/results/current docs, rehash before/after/current, kiểm cả4 findings/lỗi mới/tái xuất hiện và scope boundaries; fix → verify → re-review đến CLEAN. Quá trình này đã hoàn tất, verdict/manifest/doc checks được ghi tại mục Final verdict bên dưới.

Quy tắc nghiệm thu: full S2/P3-B/P4-A/P4-B vẫn partial; no auth/container/production/DB stack decision. Chỉ ghi DONE subset sau CLEAN và required checks pass; review không cấp quyền commit/push/approve/publish. Verdict thực tế bên dưới đã đạt điều kiện DONE riêng S2-B.

## Final verdict — WT-S2B-R4

11/11/2026, reviewer GPT-6.1 Terra high `/root/s2_final_review` xác nhận **CLEAN** trên latest snapshot; S2B-RV-01..04 CLOSED, S2A-RV-01 giữ CLOSED. Đã đối chiếu strict integer/bool-float probes, late-ack/no-sweeper/immutable terminal, conditional write timing và real-clock crossing hooks, cả cancel/revoke races cùng ordered opposite cases. Không finding mới/tái xuất hiện trong scope. **S2-B subset DONE**, full S2/P3-B/P4-A/P4-B vẫn mở.

Reviewer rehash độc lập toàn35 files của [snapshot](s2b-results/review-snapshot-r1.json), manifest `c6905193dc44600b1f7ea52539c099a17d6786b363448c157379ccd12f396e83`;37 R4 inputs before=after=current và33 S2-A R5 inputs khớp. Algorithm sorted path + ASCII space + SHA256(file bytes), join LF không trailing LF; SHA256 UTF-8 chuỗi, snapshotfile tự nó không nằm inventory. `git diff --check` PASS; reviewer đọc protocol/schema/code/harness/results/current docs và actual evidence R4 PASS10 groups/32.140s. Reviewer **không rerun DB/full45/preflight6** trong vòng này;45/6 là actual checks của root, không giả independent execution.

Root links/fences/syntax/frozen tracked artifacts và old S2-A source/evidence hashes PASS; DB `local.py stop` thành công, `pg_ctl status` no server running(expected exit3), cache retained. After-verdict chỉ ghi status/ledger/verdict hành chính; code/README/protocol/evidence R1–R4 và37 input hashes giữ nguyên. Manifest lịch sử35-file không bị sửa để giả là hash docs hậu verdict. Không commit/push/pilot/publish hoặc human approval.
