# E1 — Hủy đặt chỗ (synthetic)

Requirement `e1-seat-req-v1`; base `e1-seat-base-v1`, head `e1-seat-head-v1`. Tất cả quy tắc/dữ liệu do tác giả đặt cho bài tập; không có khách hàng hoặc hệ thống đặt vé thật.

Task: thêm khả năng hủy một lượt đặt chỗ vào mô phỏng hiện có.

| AC | Yêu cầu |
|---|---|
| AC-01 | Đặt 2 chỗ từ 10 chỗ còn trống thì còn 8; số chỗ của lượt đặt là 2. |
| AC-02 | Hủy một lượt đang active: trả lại đúng số chỗ đã đặt, đổi trạng thái thành cancelled. |
| AC-03 | Nếu cùng yêu cầu hủy được gửi lại cho lượt đã cancelled, số chỗ trống và trạng thái phải giữ nguyên. |

Lý do AC-03: người dùng có thể bấm lại hoặc ứng dụng gửi lại yêu cầu; một lượt đặt chỉ giải phóng số chỗ của nó một lần. Đây là quy tắc bài tập đã chốt, không có ambiguity cần người đọc quyết định.

Scope: một lượt đặt, số chỗ integer dương, đủ chỗ khi khởi tạo, một process, không concurrency, HTTP, persistence, tiền hoặc auth. Risk medium trong mô phỏng: số chỗ trống phải đúng; thay đổi nhỏ có thể revert. Không có booking thật.
