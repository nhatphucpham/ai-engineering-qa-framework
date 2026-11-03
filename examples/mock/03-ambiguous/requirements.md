# MOCK-03 — Tên không được để trống (synthetic)
Requirement version: mock-req-03-v1. Input: string; không xử lý database thật.
- AC-01: chuỗi rỗng "" phải bị từ chối bằng ValueError.
- AC-02: tên thông thường như "Ada" phải được giữ nguyên.
Câu stakeholder: "Không được để tên trống". Chưa nói tên chỉ gồm space/tab có là trống không, có trim hay không.
Chưa có owner confirmation cho whitespace. Không tự thêm quy tắc dựa vào sở thích reviewer.
Risk: low cho toy validation; review status pending.
