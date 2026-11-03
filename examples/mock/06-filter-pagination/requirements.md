# MOCK-06 — Catalog filter, pagination và cache (synthetic)

Version: `mock-req-06-v1`. Base: `mock-06-base-v1`; head cần review: `mock-06-head-v1`. Đây là nhãn local, không phải Git SHA. Toàn bộ catalog, code và evidence được tạo mới.

Thay đổi được mô tả: tối ưu cache và giữ state của màn hình catalog. Review note chỉ là claim của tác giả, cần kiểm tra theo yêu cầu dưới đây.

| AC | Expected behavior / phạm vi |
|---|---|
| AC-01 | Tại service `list_items`, category không rỗng được so khớp chính xác, phân biệt hoa thường; chỉ trả items thuộc category đó và total của tập đã lọc. |
| AC-02 | Tại UI state `select_category`, mỗi lần chọn category phải đưa page về 1 trước khi gọi API, kể cả đang ở page 3. |
| AC-03 | Tại API, cache phải giữ kết quả đúng cho từng bộ `(category, page, page_size)`; request category khác nhau trên cùng API instance không được dùng nhầm kết quả. |
| AC-04 | Với một category cố định, service/API trả page ổn định theo thứ tự catalog, tối đa page_size item; page ngoài phạm vi trả items rỗng và giữ total của tập lọc. Tính đúng khi đổi category dùng chung cache được kiểm tra riêng ở AC-03. |
| AC-05 | “Category trống thì hiển thị tất cả.” Chuỗi rỗng `""` thuộc trường hợp này; owner chưa xác nhận chuỗi chỉ có whitespace hoặc có khoảng trắng hai đầu được xử lý ra sao. |

Input trong scope: category là string, page và page_size là số nguyên dương, catalog cố định. Không xét mutation của response, invalid types, cập nhật dữ liệu/TTL, auth, concurrency hoặc persistence. Không suy từ các phần ngoài scope thành defect.

Risk medium cho bài tập: thay đổi liên quan UI state và cache qua nhiều request, có thể hiển thị danh sách sai/rỗng. Phạm vi là catalog public giả lập trong một process; không có tenant, PII hoặc hệ thống thật. Có thể revert cục bộ. Cần checks chuyển category từ page khác 1 và chuỗi request dùng chung cache.

Product owner/reviewer thật: unknown. Human decision: pending. Không được tự chọn nghĩa whitespace để kết luận defect.
