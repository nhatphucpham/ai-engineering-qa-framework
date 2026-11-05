# P1 — Đối chiếu audit và sửa contract v2

Ngày 05/11/2026. Audit gốc dùng GPT-6 Astra high trên commit `872c498`: P1 đạt có điều kiện, chưa đóng gate. Người dùng yêu cầu sửa. Bản sửa version hóa contract thành `2.0.0`; không đổi ngầm schema hoặc JSON specimen v1.

| Finding | Sửa | Regression / positive control |
|---|---|---|
| Thiếu stable task identity/source/diff | tasks, taskRef trên handoff/artifact; typed source/diff IDs, task/project/candidate checks | Multi-task cùng revision, nhiều handoff một task; reject missing/foreign task và wrong source kind/revision |
| Artifact/evidence revision mâu thuẫn, failed từ evidence cũ | Candidate-bound source revision phải khớp evidence; conclusive decisive refs đúng candidate; context refs riêng | Reject source revision mismatch/stale decisive failure; accept old artifact/evidence khớp và stale context |
| execution_supported chỉ dùng authored mock | Cần decisive execution provenance hiện tại có ref/time; context execution không thay decisive | Reject mock-only/context-only, accept execution-shaped specimen; không claim attestation |
| report_ready trỏ report run khác | Kiểm exact report.runId; đúng một report ID | Reject foreign-run report, empty/multiple IDs; accept manual rerun report đúng run |
| Một event tạo nhiều accepted run | Unique event → initial run trong bundle; explicit rerun có lineage, trigger null và graph không cycle | Reject duplicate trigger/rerun consume trigger/cyclic lineage; accept explicit rerun cùng handoff/task |
| Done thiếu assignee; duplicate cycle | Done cần assignee; duplicate chains không cycle/dangling/self | Reject done thiếu người nhận và 2/3-node cycles; accept assigned done và chain về canonical root |

Tool P1 không thực thi job, gọi model, chạy container hoặc làm auth. Việc reject duplicate event trong bundle không chứng minh runtime exactly-once; fencing vẫn chỉ kiểm against snapshot, expiry/atomic claim ở P3/P4. Assignment tồn tại không chứng minh action thực tế đã hoàn thành; completion evidence/sufficiency vẫn cần P2/runtime.

Migration: consumer dùng v2 phải bổ sung fields; chưa biết task/source thì explicit gap theo intake, không tự suy task từ commit hoặc nối theo thứ tự array. Không dùng raw delivery ID làm domain event identity. Rerun có ID mới, root event association không đổi; retries do lease nằm trong cùng logical run.

## Kiểm tra bản sửa

- 9 valid bundles, 58 negative scenarios; CLI valid/invalid/malformed/missing và explicit legacy-version rejection.
- Bốn unittest methods với subtests đều pass. Các số này là kiểm thử contract, không phải QA app thật hoặc số lỗi phát hiện trên task thật.
- Schema và JSON v1, fixtures MOCK/E1/E2, evidence và frozen protocol cũ giữ nguyên; README v1 có banner lịch sử để tránh chạy nhầm.
- Subagent GPT-6 Astra high đã replay độc lập sáu nhóm gốc và phát hiện edge case report_ready rỗng; edge case đã có schema constraint và regression. Lượt rà cuối đọc code/docs, chạy bốn test methods và kiểm trực tiếp report_ready rỗng/nhiều/đúng ID, kết luận không còn mâu thuẫn trọng yếu trong phạm vi đã rà, có thể đóng gate sửa P1 và dùng v2 cho P2.

**Gate sửa P1 đã đóng trong phạm vi contract offline/self-consistency.** Không suy kết luận audit thành runtime security, đủ evidence cho AC, readiness sản phẩm hoặc approval pilot. P2 vẫn cần thiết kế sufficiency/status/finding/action và P3/P4 cần implementation/enforcement.

Nguồn hiện hành: [DATA-CONTRACT](DATA-CONTRACT.md), [schema v2](../schemas/qa-contract-v2.schema.json), [specimens](../examples/contracts/v2/README.md), [validator](../tools/validate_contracts.py), [tests](../tools/test_contracts.py).
