# E2-01 — Requirement và điều kiện chuyển bước

`e2-export-req-v1`. Synthetic-only, do tác giả đặt cho bài tập bàn giao; không có app/dữ liệu khách hàng thật.

Task: xuất CSV danh sách đơn hàng theo bộ lọc đang chọn. Release candidate hiện tại `export-r12`; phiên bản trước `export-r11`. Nhãn là revision mô phỏng, không phải Git SHA. Thay đổi r11 → r12: sửa lọc khoảng ngày và bố cục nút xuất; cùng package ứng dụng được dựng lại.

| ID | Mong muốn |
|---|---|
| AC-01 | CSV chỉ chứa đơn hàng đúng khoảng ngày và trạng thái đang chọn. |
| AC-02 | File có các cột mã đơn, ngày, trạng thái, tổng tiền; dữ liệu có dấu phẩy hoặc xuống dòng được escape theo format CSV của ứng dụng. |
| AC-03 | Chỉ vai trò quản lý được xuất. Vai trò nhân viên bị từ chối bởi API, không chỉ ẩn nút trên UI. |
| AC-04 | Khi bộ lọc không có đơn hàng, file chỉ có header; UI thông báo không có dữ liệu. |

## Quy trình mô phỏng đã chọn cho case

Developer self-test → QC kiểm thử candidate → Reviewer/TL quyết định có chuyển sang triển khai staging nội bộ hay giữ để bổ sung/sửa. Staging ở đây là bước tiếp theo trong bài tập, chưa có deploy thật.

- Cần evidence cho từng AC trên candidate hiện tại `export-r12`; không dùng kết quả revision trước như đã kiểm chứng revision mới. Check bị blocked không thành pass.
- Không được chuyển bước nếu còn bug high/critical mở hoặc AC bắt buộc chưa có evidence phù hợp. Đây là điều kiện case do tác giả đặt, không tự áp cho mọi team.
- Bug low ngoài AC có thể được Reviewer/TL chấp nhận hoãn nếu ghi lý do, vai trò xử lý và điều kiện theo dõi. Quyền đó không miễn trừ các AC bắt buộc.

Risk giả lập: xuất dữ liệu sai hoặc sai quyền. Không có dữ liệu thật, không yêu cầu người đọc truy hệ thống hoặc tìm thêm code để quyết định.
