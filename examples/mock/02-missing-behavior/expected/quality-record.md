# MOCK-02 — Hồ sơ mong đợi (synthetic)
Snapshot: mock-02-head; requirement: mock-req-02-v1. Risk: medium vì thay đổi state.

| AC | Evidence ban đầu | Trước probe | Sau probe |
|---|---|---|---|
| AC-01 | matching_rows/no_matches tại head kiểm tra filtered rows | verified | verified |
| AC-02 | Không có assertion kiểm tra page; baseline chỉ dùng page=1 | unverified | failed: test_resets_page quan sát 3 thay vì 1 |

Lúc chỉ đọc evidence, ghi verification gap G-02, không kết luận suite pass nghĩa AC-02 verified. Diff giữ `page` là dấu hiệu có thể kiểm tra thêm.
Probe: từ page=3 áp dụng filter 'alpha'. Expected page=1; actual page=3. `expected/test_probe.py` cố ý có một failure.
Finding F-02: defect behavior, severity medium trong mock; nguồn after.py và probe nêu trên. Confirmed bằng synthetic reproduction, không phải human adjudication thật.
Hành động/owner: developer sửa reset page và thêm regression test ở môi trường phù hợp.
Verification sau probe: failed. Human decision: pending, đề nghị sửa rồi review lại revision mới. Effort: unknown.
Kết luận này chỉ cho toy state; không chứng minh UI thật, agent hoặc framework phát hiện được lỗi mới.
