# S2-A independent review record

Ngày 11/11/2026, baseline master `d73dce3d30a2ee9041b6633ce0fbfdcf78528332`. **DONE trong S2-A subset — final independent CLEAN WT-S2A-R5.** Scope: protocol/preflight/local setup, actual disposable PostgreSQL queue/transaction/fault harness, results và current handoff/plan; [acceptance](S2-A-PROTOCOL.md), [results/evidence](S2-A-RESULTS.md). Không full S2/P3-B/P4-A/P4-B, production DB/runtime decision, real auth/worker/blob/export.

Reviewer ban đầu GPT-6 Astra high `/root/s2_review`, read-only, được chỉ định trước implementation. Reviewer bị usage limit trước final verdict; chuyển đầy đủ ledger/evidence cho reviewer độc lập GPT-6.1 Terra high `/root/s2_final_review`, không reset finding IDs. Root hiện thực fixes; reviewers không sửa output nghiệm thu.

## Ledger, giữ stable IDs

| ID | Severity / status | Expected/actual, impact | Fix và actual verification |
|---|---|---|---|
| S2A-RV-01 | P2 / CLOSED bởi reviewer trên WT-S2A-R5 | Preflight chỉ check thư mục psycopg; wrong/global driver có thể vẫn READY. Windows tzdata required nhưng thiếu lock; không tái lập exact toolchain | Pin tzdata2026.6 + wheel hash, kiểm local distribution metadata, loaded versions/path và binary implementation; tests missing/mismatch/global fallback reject. R5 preflight READY đúng pins, DB14 groups pass và 6 prerequisite tests pass; reviewer độc lập chạy 6 methods PASS/0.052s |

Ghi nhận **trước final verdict (lịch sử)**: root xử lý server-clock lease thay client time, expiry recheck sau core validation; R01 stop DB khi child giữ transaction mở thay vì chỉ sau rollback. R4/R5 có actual expiry-during-validation reject, open-transaction DB stop/recovery và pending outbox replay; lúc chuyển reviewer chưa nhận final verdict. Verdict CLEAN đã được nhận và ghi tại mục Final verdict bên dưới. Không tạo finding mới cho cùng lỗi qua vòng.

## Snapshot/checks gửi review (ghi trước verdict)

`WT-S2A-R5` = new spikes/s2 code/README/lock/preflight tests, protocol/results/review/evidence R1–R5, `.gitignore`, README/current plan/ADR note/decision/handoff/NEXT-SESSION. R5 contains 33 source/input paths với working-file SHA256 before=after; review snapshot manifest bổ sung docs/current state khi gửi review, không thay hash historical evidence.

Root actual checks lúc gửi review: DB experiment latest R5 **14 groups PASS / 22.872s**, prerequisite suite **6 methods PASS / 0.066s**, full regression **45 methods PASS / 36.754s**. R2 ERROR được giữ và giải thích trong results, không đếm thành pass; R3/R4/R5 là new executions trên source snapshots mới. Không frozen artifacts mutation hoặc S1 benchmark rerun. Final doc/link/diff/manifest checks và reviewer verdict sau đó đã được bổ sung tại mục Final verdict bên dưới.

Reviewer phải kiểm latest files, evidence/code hashes, correctness/practicality, S2A-RV-01 + mọi regression/lỗi mới, current docs và scope gaps. Fix → recheck → re-review đến clean, không giới hạn vòng. Chỉ sau clean và required checks pass mới administrative mark DONE đúng subset; review không cấp commit/push/publish hoặc human approval.

## Final verdict — WT-S2A-R5, 11/11/2026

GPT-6.1 Terra high `/root/s2_final_review` xác nhận **CLEAN**, đóng S2A-RV-01, không có finding mới/tái xuất hiện trong scope. Reviewer rehash độc lập 23 files của [snapshot](s2-results/review-snapshot-r1.json), manifest `622dc30f5b0ec42a63a4a9682bab67756d53f772659f7aa0e7efc1c5d88a8f84`, và 33 inputs R5: tất cả khớp working tree/before/after. Algorithm: sorted path + ASCII space + SHA256(file bytes), join LF không trailing LF; SHA256 UTF-8 chuỗi. Snapshot file không nằm trong chính inventory của nó.

Reviewer chạy mới 6 preflight methods PASS/0.052s và `git diff --check` PASS; đọc actual DB14 groups PASS/R2 ERROR và root regression45 PASS, **không tự rerun DB workload hoặc tools45**. Kiểm lại lease server clock/expiry trong validation, genuine deferred commit failure, DB stop lúc transaction mở/WAL recovery/pending replay, core semantics, results/plan/brief/handoff và gaps. Không lấy root checks làm independent execution claim.

Root links/fences/whitespace, frozen tracked artifacts unchanged, current33-input rehash đều PASS. Đã `local.py stop` thành công, `pg_ctl status` báo no server running (expected exit3); cluster/binaries/sinks retained ignored cache, không global service. Required checks và clean verdict đạt, nên **S2-A subset DONE**. Full S2/P3-B/P4-A/P4-B vẫn partial; còn lease renewal/reclaim, live auth/revoke/worker cleanup, full cancel/fairness/restore/blob/export.

Sau verdict chỉ ghi ledger/verdict/DONE hành chính trong current docs. Manifest 23-file lịch sử vẫn nhận diện đúng bản đã review trước status updates, không giả là hash docs hậu verdict. Code/lock/protocol/evidence R1–R5 và 33 source/input hashes không đổi. Chưa commit/push/pilot/publish.
