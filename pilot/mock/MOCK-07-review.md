# MOCK-07 — Review cách tính giảm giá đơn hàng

Ngày 04/11/2026. Synthetic-only; requirement, lỗi và đáp án do tác giả tạo, đã biết trước. Commit nền `b7d84de`; snapshot `mock-07-head-v1` và `mock-07-fixed-v1` là nhãn local. Người chuẩn bị: trợ lý; reviewer/owner thật unknown, human decision pending. Đây là case bổ sung để thử dùng lại bố cục, không phải đánh giá độc lập hoặc bằng chứng tìm defect mới.

## Kết luận và việc cần làm

**Bản lỗi có 4 test: 2 pass, 2 fail, tương ứng 2 lỗi. Bản sửa cả 4 test pass.** Hai lỗi là bỏ giảm giá tại đúng ngưỡng và giảm nhầm cả phí giao hàng. Verification head: failed. Verification fixed: complete trong scope requirement và assertions/source reasoning đã nêu; chưa có human approval.

Việc tiếp theo: người đọc xem hai giải thích bên dưới, cho biết có phân biệt được hai lỗi và hiểu vì sao kết quả phải như vậy không. Hoàn thành bước thử bố cục khi ghi được phản hồi thực tế; chưa cần sửa code khác nếu chưa có gap mới. Vai trò đề xuất: người dùng đọc hồ sơ, người chuẩn bị sửa phần khó hiểu, Reviewer/TL quyết định sau khi đối chiếu evidence. Người nhận thật chưa được chỉ định.

Risk medium trong bài tập: sai số tiền phải trả; chỉ là hàm thuần với dữ liệu giả, không giao dịch thật, có thể revert. Hai check bổ sung tập trung đúng ngưỡng và phí giao hàng khác 0.

## F-07-01 — Bỏ giảm giá khi tiền hàng đúng 100.000

- **Mong muốn:** từ 100.000 tiền hàng trở lên được giảm 10%, bao gồm đúng 100.000, theo AC-02 của requirement v1.
- **Lý do:** quy tắc khuyến mãi giả lập dùng “từ 100.000”, nên mức đúng ngưỡng cũng đủ điều kiện. Đây là quy tắc do tác giả đặt cho ví dụ, không phải chính sách cửa hàng thật.
- **Thực tế bản lỗi:** đơn tiền hàng 100.000, phí giao hàng 0 phải trả 90.000 nhưng hàm trả 100.000; khách không được giảm 10.000.
- **Cách sửa:** điều kiện so sánh đổi từ lớn hơn (`>`) sang lớn hơn hoặc bằng (`>=`).
- **Kết quả kiểm tra:** `Probe.test_threshold_is_inclusive` fail tại head (`100000 != 90000`), pass tại fixed. Check không có phí giao hàng nên tách lỗi ngưỡng khỏi lỗi phía dưới.

## F-07-02 — Giảm nhầm cả phí giao hàng

- **Mong muốn:** chỉ giảm 10% tiền hàng, giữ nguyên phí giao hàng, theo AC-03.
- **Lý do:** ưu đãi giả lập dành cho sản phẩm; phí vận chuyển là khoản riêng không được giảm theo requirement.
- **Thực tế bản lỗi:** tiền hàng 150.000, giao hàng 20.000. Đúng phải là 150.000 − 15.000 + 20.000 = **155.000**. Bản lỗi giảm 10% trên tổng 170.000 nên chỉ còn **153.000**, thấp hơn yêu cầu 2.000.
- **Cách sửa:** tính giảm giá từ tiền hàng trước, sau đó cộng nguyên phí giao hàng. Sửa này khác với sửa điều kiện ngưỡng; tiền hàng 150.000 vốn đã vượt ngưỡng ở cả hai bản.
- **Kết quả kiểm tra:** `Probe.test_shipping_is_not_discounted` fail tại head (`153000 != 155000`), pass tại fixed.

## Evidence và yêu cầu đã đối chiếu

[Requirement mock-req-07-v1](../../examples/mock/07-order-discount/requirements.md) quy định input/scope, ngưỡng và cách làm tròn xuống. [Head](../../examples/mock/07-order-discount/head/pricing.py) và [fixed](../../examples/mock/07-order-discount/fixed/pricing.py) là hai snapshot riêng.

Đã chạy trên Python 3.14.8, từ root repo:

```text
py -3 -X utf8 -B examples/mock/07-order-discount/run.py
```

Exit 0; [execution local](../../examples/mock/07-order-discount/execution.local.json) lưu snapshot/module, số test, failure IDs/traceback và SHA-256 input. Không phải CI evidence hoặc approval.

| Nhóm test | Head | Fixed | Ý nghĩa |
|---|---|---|---|
| 2 baseline | 2 pass | 2 pass | Dưới ngưỡng và trên ngưỡng không có phí giao hàng đều đạt, nhưng chưa kiểm tra hai lỗi |
| 2 probe | 2 fail | 2 pass | Hai tình huống riêng ở đúng ngưỡng và có phí giao hàng đã được sửa |

Không errors/skipped. Runner `MATCH`/exit 0 chỉ nói outcome đúng thiết kế trên cả hai bản, gồm cả failure cố ý ở head. `pass` chỉ xác nhận những trường hợp kiểm tra, không chứng minh mọi input đều đúng.

| AC | Assertion/source | Head → fixed |
|---|---|---|
| AC-01: dưới ngưỡng không giảm | [Baseline.test_below_threshold](../../examples/mock/07-order-discount/tests/test_baseline.py), source | verified → verified |
| AC-02: từ ngưỡng giảm 10% | Baseline.test_above_threshold_without_shipping và [Probe.test_threshold_is_inclusive](../../examples/mock/07-order-discount/tests/test_probe.py), source | failed → verified trong scope |
| AC-03: giữ nguyên phí giao hàng | Probe.test_shipping_is_not_discounted, Baseline.test_below_threshold, source | failed → verified trong scope |

Finding F-07-01/02 confirmed bằng execution trong mock và được sửa tại fixed; chưa có adjudication độc lập. Source fixed dùng `subtotal // 10`, đúng cách làm tròn đã định; tests minh họa số tiền chia hết cho 10, chưa có assertion riêng cho phần dư.

## Giới hạn

Input là integer không âm, một đơn hàng, một quy tắc; ngoài scope: tax, nhiều coupon, invalid inputs, tích hợp thanh toán, currency hoặc hệ thống thật. Effort/cost, usefulness và effectiveness unknown. Case được viết sau phản hồi MOCK-06 nên không gọi là holdout; chỉ thử khả năng dùng lại bố cục trên một ví dụ khác. Chưa tự xác nhận G1 đầy đủ hoặc ROI.
