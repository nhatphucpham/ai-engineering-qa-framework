# MOCK-07 — Giảm giá đơn hàng

`mock-req-07-v1`, synthetic-only. Snapshot `mock-07-head-v1` có lỗi cố ý; `mock-07-fixed-v1` minh họa sửa. Toàn bộ quy tắc/giá trị do tác giả đặt cho bài tập, không phải chính sách cửa hàng thật.

| AC | Yêu cầu |
|---|---|
| AC-01 | Tiền hàng dưới 100.000 không giảm giá. Tổng phải trả = tiền hàng + phí giao hàng. |
| AC-02 | Tiền hàng từ 100.000 trở lên, kể cả đúng 100.000, được giảm 10% tiền hàng. |
| AC-03 | Phí giao hàng không được giảm. Tổng phải trả = tiền hàng − giảm giá + phí giao hàng. |

Lý do của quy tắc giả lập: ngưỡng khuyến mãi bao gồm mức được công bố; giảm giá cho sản phẩm không thay đổi phí giao hàng. Số tiền là integer không âm theo đơn vị tiền giả lập; giảm 10% tính bằng `subtotal // 10` (làm tròn xuống). Không có thuế, nhiều coupon, thanh toán, tiền tệ thật, invalid input hoặc API/network. Không diễn giải kết quả thành tư vấn tài chính.

Risk medium trong bài tập: sai tổng tiền; phạm vi hàm thuần, không thanh toán thật và có thể revert. Cần kiểm tra đúng ngưỡng và phí giao hàng khác 0, không chỉ trường hợp dưới/trên ngưỡng thông thường.
