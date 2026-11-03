# MOCK-04 — Giữ số lượng tồn kho (synthetic)
Requirement version: mock-req-04-v1. Input: stock là integer >=0, quantity integer >0.
- AC-01: quantity không vượt stock thì có thể reserve (True).
- AC-02: quantity vượt stock thì phải từ chối (False).
Scope: pure function; không có kho hàng/database/concurrency thật.
Risk: medium trong toy; dùng thật có thể high do data integrity.
Evidence hiện có chạy trên base, chưa có CI head. Review status pending.
