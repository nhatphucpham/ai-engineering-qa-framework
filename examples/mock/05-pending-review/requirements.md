# MOCK-05 — Quyền xóa tài liệu (synthetic)
Requirement version: mock-req-05-v1. actor_role là string; same_workspace là bool đã cung cấp.
- AC-01: admin ở cùng workspace được xóa.
- AC-02: mọi role khác admin bị từ chối.
- AC-03: admin khác workspace cũng bị từ chối.
Risk: high vì authorization. Chính sách mock P-05: domain/security owner phải review trước approval.
Human approval: pending; chưa có reviewer thật. Không có identity, token hay tài liệu thật.
Scope: pure decision function, không kiểm chứng nguồn dữ liệu role/workspace hoặc endpoint enforcement.
