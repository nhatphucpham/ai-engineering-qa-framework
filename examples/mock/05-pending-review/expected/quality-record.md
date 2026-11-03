# MOCK-05 — Hồ sơ mong đợi (synthetic)
Head: mock-05-head; requirement: mock-req-05-v1. Risk high: authorization.

| Criterion | Evidence | Trước probe | Sau probe |
|---|---|---|---|
| AC-01 | test_admin_same_workspace | verified | verified |
| AC-02 | test_non_admin_denied + branch inspection | verified trong scope toy | verified trong scope toy |
| AC-03 | Không có baseline check cross-workspace | unverified | verified: test_cross_workspace_denied |
| P-05: mandatory human review | Không có approval | pending | pending |

Không tạo code defect chỉ vì approval thiếu. G-05 là verification/process gap: cần domain/security owner review; chưa có approval thật.
Behavior checks sau probe đều pass, nhưng verification tổng thể incomplete do P-05 chưa hoàn tất. Human decision pending; không tự cho phép merge.
Action/owner: domain/security owner review trong môi trường bảo mật; developer cung cấp context identity/workspace và enforcement ở đó.
Residual risk: toy nhận role/workspace đã tính sẵn; chưa kiểm tra token, identity trust, endpoint wiring, isolation hoặc hệ thống authorization thật.
Không được dùng kết quả này tuyên bố hệ thống thật an toàn. Effort: unknown.
