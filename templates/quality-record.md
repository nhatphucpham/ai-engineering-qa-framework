# Hồ sơ kiểm chứng: <task ID>

Loại dữ liệu: synthetic/mock. Không dùng hồ sơ mẫu làm bằng chứng của task thật.
Snapshot code: <base/head hoặc snapshot ID>. Requirement: <nguồn/version>.
Người chuẩn bị: <vai trò>. Người quyết định: <vai trò hoặc pending>.

## Đọc nhanh

- Verification hiện tại: <complete / incomplete / failed trong scope; nếu failed và còn thiếu evidence, ghi cả hai>.
- Điều thay đổi sau kiểm tra: <behavior/evidence mới, hoặc không có thông tin mới>.
- Việc còn mở và hành động tiếp: <làm gì trước → sau / phụ thuộc / điều kiện xong / vai trò xử lý / người nhận hoặc unknown>.
- Human decision: <pending nếu chưa có quyết định thật; ghi riêng với verification>.

## Mục tiêu và risk

Behavior/constraint: <...>
Risk và lý do: <impact, blast radius, reversibility>.
Checks/review bắt buộc theo phạm vi này: <...>.

## Đối chiếu

| AC/constraint | Expected behavior và nguồn | Evidence / snapshot | Trạng thái | Gap / hành động / owner |
|---|---|---|---|---|
| AC-01 | ... | ... | verified / failed / unverified / not_applicable | ... |

Evidence dẫn tới assertion/source và execution đúng snapshot, không chỉ tên suite. Phân biệt trạng thái trước và sau khi bổ sung check. Evidence giả lập chỉ minh họa input; kết quả chạy local trên code synthetic chỉ chứng minh behavior của ví dụ đó.

Nếu người đọc chưa quen test, thêm diễn giải ngắn: check kiểm tra behavior gì, trước/sau khác nhau thế nào và kết quả còn giới hạn gì. Không chỉ đưa số pass/fail; phân biệt error và skipped. Chọn một chuỗi requirement → assertion → execution đúng snapshot để chỉ cách đọc khi cần.

## Finding và quyết định

- Finding nếu có: <ID, defect / ambiguity / verification gap / process observation, impact, evidence, cách tái hiện>. Không tạo finding giả khi evidence đủ.
- Trạng thái finding nếu có: <candidate / confirmed trong mock / disputed / rejected>.
- Giới hạn/context chưa kiểm tra: <...>.
- Effort: <phút thực đo hoặc unknown; không tự đặt số giả làm số đo>.

Kết luận và hành động chính ghi ở phần Đọc nhanh; bảng AC bổ sung chi tiết, không cần chép lại ở cuối. Tách phần rõ/mơ hồ của một AC nếu giúp tránh việc một phần pass che phần chưa kiểm chứng.
