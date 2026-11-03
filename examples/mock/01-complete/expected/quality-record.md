# MOCK-01 — Hồ sơ mong đợi (synthetic)
Snapshot: mock-01-head; requirement: mock-req-01-v1. Risk: low, hàm toy cô lập.

| AC | Evidence | Trước probe | Sau probe |
|---|---|---|---|
| AC-01 | test_below_threshold: shipping(20)=5; nhánh total<100 trong after.py | verified | verified |
| AC-02 | test_exact_threshold: shipping(100)=0; nhánh >=100 trong after.py | verified | verified; bổ sung shipping(101)=0 |

`evidence.mock.json` là input CI giả lập đúng snapshot. Runner cho phép tái chạy assertion trên code synthetic; không phải CI thật.
Finding: không có trong phạm vi bài tập. Không thêm finding chỉ vì số test ít; nếu muốn kiểm tra loại input ngoài scope thì phải thỏa thuận requirement trước.
Hành động: tiếp tục quy trình review thông thường; không yêu cầu thêm QA layer nếu hồ sơ này chỉ lặp thông tin reviewer đã có.
Verification: complete cho behavior/scope đã khai báo, không phải chứng minh mọi đầu vào hay hệ thống checkout.
Human decision: pending, chưa có approval thật. Effort/cost: unknown.
