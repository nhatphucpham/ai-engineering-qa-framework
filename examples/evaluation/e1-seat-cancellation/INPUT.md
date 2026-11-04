# E1 — Tài liệu ban đầu cho người đọc

Synthetic-only, task thêm chức năng hủy đặt chỗ. Đây là input trước hồ sơ phân tích; chưa có quyết định review hoặc approval.

## Yêu cầu

1. Đặt 2 chỗ từ 10 chỗ trống thì còn 8.
2. Hủy lượt đang active phải trả lại 2 chỗ, về 10 chỗ trống và trạng thái cancelled.
3. Nếu cùng yêu cầu hủy được gửi lại, số chỗ trống và trạng thái phải giữ nguyên. Lý do: ứng dụng hoặc người dùng có thể gửi lại yêu cầu; một lượt đặt chỉ giải phóng chỗ của nó một lần.

Quy tắc do tác giả đặt cho bài tập. Một lượt đặt, đủ chỗ ban đầu, không concurrency/network/tiền/auth. [Requirement đầy đủ](requirements.md).

## Thay đổi được bàn giao

Base chỉ hỗ trợ đặt chỗ. Head thêm hàm `cancel` để hủy. Source head đầy đủ:

```python
class Booking:
    def __init__(self, available, quantity):
        self.available = available - quantity
        self.quantity = quantity
        self.status = 'active'

    def cancel(self):
        self.available += self.quantity
        self.status = 'cancelled'
```

`available` là số chỗ trống, `quantity` là số chỗ đã đặt. `+=` nghĩa cộng thêm; gán `status` đổi trạng thái. Đây là giải thích cách đọc source, không phải kết luận review. [Base](base/booking.py), [head](head/booking.py), [diff](change.diff).

## Bằng chứng đang có

Hai test đã thực chạy tại head trên máy cục bộ:

| Test | Kết quả mong đợi đã kiểm tra | Kết quả |
|---|---|---|
| test_reserve | Đặt 2 từ 10: còn 8, quantity=2, status active | Pass |
| test_cancel_once | Đặt 2 rồi gọi cancel một lần: còn 10, status cancelled | Pass |

Tổng 2 pass, 0 fail/error/skipped. [Assertions](tests/test_baseline.py), [execution và hash input](baseline.local.json). Không có CI thật hoặc review trước đó được cung cấp. Không suy diễn từ dữ liệu chưa có; bạn có thể nêu check muốn chạy mà chưa cần tự chạy code.

## Nhận định trước hồ sơ

Chỉ đọc tài liệu này và nguồn input nếu cần. Ghi nhận định hiện tại, bằng chứng bạn dựa vào, hành động nên làm tiếp và thời gian đọc thực tế. Không cần đoán ý tác giả hoặc tìm đủ số lỗi. Nếu chưa biết, ghi đúng phần chưa biết.

Ngân sách bạn đã chọn: tổng tối đa 10 phút đọc/review trước và sau hồ sơ, không gồm thời gian chờ trợ lý chuẩn bị. Gợi ý chia tối đa 4 phút input này, dành phần còn lại cho hồ sơ; đây là hướng dẫn chia thời gian, không phải số đo thực tế. Tự ghi phút đã dùng và nguồn nào đã mở; thời gian chat trôi qua không tự được tính là thời gian đọc.
