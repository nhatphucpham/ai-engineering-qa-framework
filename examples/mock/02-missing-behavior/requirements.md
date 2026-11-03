# MOCK-02 — Lọc danh sách và reset trang (synthetic)
Requirement version: mock-req-02-v1. Input: rows là list string, query là chuỗi không rỗng; page là số nguyên dương.
- AC-01: khi áp dụng filter, chỉ giữ row chứa query, phân biệt hoa thường.
- AC-02: mỗi lần áp dụng filter, page phải trở về 1.
Scope: hàm state toy, không có UI/router/backend thật.
Risk: medium cho thay đổi behavior. Review status: pending.
