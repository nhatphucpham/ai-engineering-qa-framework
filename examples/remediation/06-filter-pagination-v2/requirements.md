# MOCK-06 — Requirement v2: dấu cách ở hai đầu category

Version `mock-req-06-v2`; snapshot `mock-06-fixed-v2`. Synthetic-only. Kế thừa [requirement v1](../../mock/06-filter-pagination/requirements.md) với AC-01/05 được làm rõ bên dưới. Quyết định do người dùng chọn trong chat ngày 04/11/2026, chỉ áp dụng ví dụ mock; không phải approval hệ thống thật.

Người dùng chọn: category toàn dấu cách hiển thị tất cả; `" books "` bỏ dấu cách hai đầu và tìm books. Trước khi lọc, bỏ dấu cách ASCII U+0020 ở hai đầu category. Phạm vi clarification là dấu cách trong hai ví dụ này; tab, newline và các whitespace Unicode khác chưa được mở rộng thành yêu cầu.

| AC | Expected behavior |
|---|---|
| AC-01 | Service so khớp category sau bỏ dấu cách hai đầu, vẫn phân biệt hoa thường; `" books "` trả books, `" Books "` không có kết quả. Không xóa dấu cách ở giữa chuỗi. |
| AC-02 | Giữ nguyên v1: đổi category đưa page về 1 trước request. |
| AC-03 | Giữ nguyên v1: cache không dùng nhầm dữ liệu giữa category/page/page_size. Không yêu cầu các cách viết tương đương dùng chung một cache entry. |
| AC-04 | Giữ nguyên v1: pagination ổn định trong catalog cố định, ngoài trang trả danh sách rỗng và total đúng. |
| AC-05 | Sau bỏ dấu cách hai đầu, category rỗng nghĩa tất cả. `""` và `"   "` đều total=8; `" books "` total=6. Quy tắc áp dụng tại service và kết quả đi qua API/UI. Không yêu cầu UI lưu category dạng chuẩn hóa. |

Giữ scope/risk của v1: string category, page/page_size nguyên dương, dữ liệu cố định, không HTTP/browser/auth/concurrency/TTL/response mutation. Requirement v1 và evidence v1 vẫn giữ nguyên; không gọi hành vi v1 là defect hồi tố vì v1 chưa chốt dấu cách.
