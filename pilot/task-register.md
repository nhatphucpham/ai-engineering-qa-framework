# Task register — synthetic

Không chứa task thật. “Đã có execution” chỉ nói fixture đã chạy; không phải completed pilot. Snapshot IDs là nhãn synthetic. Các case cũ không được relabel thành holdout E1.

| ID / phiên bản | Vai trò trong phát triển | Nguồn | Tình trạng / thuộc E1? |
|---|---|---|---|
| MOCK-01–05 | Case thiết kế trạng thái/evidence | [Bộ mẫu](../examples/mock/README.md) | Có fixtures/outcome thiết kế; không thuộc nhóm đánh giá mới E1 |
| MOCK-06 v1 | Walkthrough nhiều lớp, biết đáp án | [Hồ sơ gốc](mock/MOCK-06-review.md) | Có execution; không thuộc E1 |
| MOCK-06 fixed-v1 | Vòng sửa reset/cache | [Hồ sơ sửa](mock/MOCK-06-remediation.md) | Có execution và feedback có hỗ trợ; không thuộc E1 |
| MOCK-06 fixed-v2 | Clarification dấu cách | [Hồ sơ v2](mock/MOCK-06-v2.md), [feedback](../docs/REVIEWER-CHECK.md) | 13 test pass, người dùng nhận xét hợp lý/dễ hiểu; không phải review độc lập, không thuộc E1 |
| MOCK-07 | Dùng lại bố cục, biết đáp án | [Hồ sơ 07](mock/MOCK-07-review.md) | Có execution, chưa thu feedback; không là holdout E1 |

## Đăng ký lượt E1 — chưa bắt đầu

Không có case đánh giá mới đã được chọn. Không tạo dòng completed hoặc count kết quả giả. Trước lượt đầu, thêm một dòng với các trường sau:

| Trường cần ghi | Trạng thái hiện tại |
|---|---|
| Run ID, case ID, chọn/loại và lý do | Chưa chọn; tiêu chí tại protocol |
| Case/requirement/snapshot version và vị trí input | Chưa có case mới |
| Protocol commit / freeze | Protocol commit cần ghi trước lượt; freeze tại manifest E1 |
| Người tạo, người đọc, người đối chiếu | Chưa chỉ định |
| Đã biết đáp án/hồ sơ trước đó, hỗ trợ | Chưa thu thập |
| Timebox được chọn / overhead chấp nhận được | Chưa xác nhận; đề xuất 20 phút không phải budget đã duyệt |
| Bắt đầu/kết thúc, thời gian theo từng hoạt động | Chưa thực hiện; effort unknown |
| Nhận định/action trước/sau, nguồn tự tìm, ghi nhận hỗ trợ | Chưa thu thập |
| Link execution, hồ sơ, adjudication và kết quả | Chưa có |

Ghi cả case được xét nhưng loại, không chỉ case thuận lợi. Với rerun sau sửa, dùng run ID/version riêng và giữ kết quả cũ. Xem [protocol E1](../docs/EVALUATION-PROTOCOL.md).
