# MOCK-04 — Hồ sơ mong đợi (synthetic)
Head: mock-04-head; evidence: mock-04-base; requirement: mock-req-04-v1.
Risk: medium trong bài tập, integrity scope chỉ là pure function.

| AC | Evidence ban đầu | Trước probe tại head | Sau probe |
|---|---|---|---|
| AC-01 | test_within_stock chạy trên before.py | unverified: sai snapshot | unverified: probe chưa kiểm tra AC-01 |
| AC-02 | test_over_stock chạy trên before.py | unverified: sai snapshot | failed: head cho reserve 6 khi stock=5 |

G-04: stale evidence. Baseline pass là hợp lệ cho base; không đổi nhãn snapshot để dùng cho head.
F-04: regression, severity medium trong mock. change.diff bỏ upper bound; expected/test_probe.py tái hiện `can_reserve(5,6)==True` ở head.
Action/owner: developer khôi phục upper bound; CI owner chạy cả bộ kiểm tra trên head mới và ghi snapshot thực tế.
Verification: failed sau probe. AC-01 chưa được verify bởi một probe không liên quan. Human decision: pending.
Bài tập chỉ minh họa mismatch; nhãn mock-* không có cơ chế xác thực provenance thực tế. Effort: unknown.
