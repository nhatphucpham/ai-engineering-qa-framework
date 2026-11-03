# MOCK-03 — Hồ sơ mong đợi (synthetic)
Snapshot: mock-03-head; requirement: mock-req-03-v1. Risk: low trong toy.

| Criterion | Evidence | Trạng thái |
|---|---|---|
| AC-01: reject chuỗi rỗng | test_empty_rejected | verified |
| AC-02: giữ tên thông thường | test_normal_preserved | verified |
| Q-03: whitespace thuộc "trống" hay hợp lệ? | Requirement chưa xác định; after.py hiện giữ nguyên whitespace | unverified |

Finding G-03: requirement ambiguity, chưa phải defect. Không tự tạo AC mới "space phải bị reject" rồi đánh implementation failed.
Hành động/owner: product/domain owner xác nhận space/tab, trim và expected outcome; developer chỉ thêm regression test sau khi chốt rule.
Không có probe pass/fail cho whitespace vì chưa có oracle. Biết actual behavior không đủ quyết định expected behavior.
Verification tổng thể: incomplete do ambiguity còn mở; hai AC rõ vẫn verified. Human decision: pending.
Không tính G-03 thành confirmed software defect hoặc false positive. Effort: unknown.
