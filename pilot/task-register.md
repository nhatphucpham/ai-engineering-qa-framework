# Task register — synthetic

Không chứa task thật. “Đã có execution” chỉ nói fixture đã chạy; không phải completed pilot. Snapshot IDs là nhãn synthetic. Các case cũ không được relabel thành holdout E1.

| ID / phiên bản | Vai trò trong phát triển | Nguồn | Tình trạng / thuộc E1? |
|---|---|---|---|
| MOCK-01–05 | Case thiết kế trạng thái/evidence | [Bộ mẫu](../examples/mock/README.md) | Có fixtures/outcome thiết kế; không thuộc nhóm đánh giá mới E1 |
| MOCK-06 v1 | Walkthrough nhiều lớp, biết đáp án | [Hồ sơ gốc](mock/MOCK-06-review.md) | Có execution; không thuộc E1 |
| MOCK-06 fixed-v1 | Vòng sửa reset/cache | [Hồ sơ sửa](mock/MOCK-06-remediation.md) | Có execution và feedback có hỗ trợ; không thuộc E1 |
| MOCK-06 fixed-v2 | Clarification dấu cách | [Hồ sơ v2](mock/MOCK-06-v2.md), [feedback](../docs/REVIEWER-CHECK.md) | 13 test pass, người dùng nhận xét hợp lý/dễ hiểu; không phải review độc lập, không thuộc E1 |
| MOCK-07 | Dùng lại bố cục, biết đáp án | [Hồ sơ 07](mock/MOCK-07-review.md) | Có execution, chưa thu feedback; không là holdout E1 |

## Đăng ký lượt E1-01 — đã chuẩn bị input, chờ nhận định ban đầu

Đã chọn case hủy đặt chỗ vì có requirement/source/checks nhỏ, cùng họ behavior change Python. Không có candidate mới khác được xét rồi loại trong lượt này. Input được tạo sau khi chốt protocol; tác giả biết thiết kế, chưa gọi là đánh giá mù hoặc độc lập.

| Trường cần ghi | Trạng thái hiện tại |
|---|---|
| Run ID, case ID, chọn/loại và lý do | E1-01, E1-seat-cancellation; chọn theo tiêu chí nêu trên |
| Case/requirement/snapshot version và vị trí input | e1-seat-req-v1, e1-seat-head-v1; [input](../examples/evaluation/e1-seat-cancellation/INPUT.md) |
| Protocol commit / freeze | Protocol `183b477752ce819934896c03abd7bef74cd88dee`; freeze `8c03ad55f41811c2539c44cbcb049322530501a2` |
| Người tạo, người đọc, người đối chiếu | Tác giả: trợ lý; người đọc: người dùng trong chat đã chọn tham gia; người đối chiếu độc lập chưa có |
| Đã biết đáp án/hồ sơ trước đó, hỗ trợ | Người dùng từng đọc walkthrough 06/07; chưa xác nhận nguồn đã mở ở case mới. Input có giải thích từ Python; hồ sơ phân tích chưa gửi, câu trả lời baseline chưa có |
| Timebox được chọn / overhead chấp nhận được | Người dùng chọn tổng 10 phút đọc trước/sau hồ sơ. Đây là ngân sách lượt thử, chưa là ngưỡng overhead chấp nhận được khi áp dụng thật |
| Bắt đầu/kết thúc, thời gian theo từng hoạt động | Chưa có số đo người đọc; tự báo thời gian đọc, không tính thời gian chờ trợ lý. Effort chuẩn bị/triage chưa đo: unknown |
| Nhận định/action trước/sau, nguồn tự tìm, ghi nhận hỗ trợ | Chưa thu thập |
| Link execution, hồ sơ, adjudication và kết quả | [Baseline local](../examples/evaluation/e1-seat-cancellation/baseline.local.json): 2 pass, không errors/skipped; chưa có hồ sơ bổ sung hoặc kết quả review/adjudication |

Ghi cả case được xét nhưng loại, không chỉ case thuận lợi. Với rerun sau sửa, dùng run ID/version riêng và giữ kết quả cũ. Xem [protocol E1](../docs/EVALUATION-PROTOCOL.md).
