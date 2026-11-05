# Task register — synthetic

## E2-01 — chuẩn bị bàn giao QC → Reviewer/TL, chờ nhận định trước

- Điểm bàn giao do người dùng chọn ngày 05/11/2026: xem self-test, kết quả QC và lỗi còn mở để quyết định tiếp.
- Case xuất CSV: [input](../examples/evaluation/e2-qc-handoff/INPUT.md), `e2-export-req-v1`, candidate `export-r12`, record cũ `export-r11`. Chọn case vì có self-test/QC/blocked/issue và quyết định chuyển bước cụ thể; không xét/loại case mới khác ở lượt này.
- Tác giả: trợ lý, biết thiết kế; người đọc: người dùng. Không có developer/QC hoặc adjudicator độc lập thật. Evidence do tác giả soạn, **không phải execution**.
- Protocol: [E2](../docs/EVALUATION-PROTOCOL-E2.md), phiên bản tại commit giới thiệu file; ghi full SHA khi lưu phản hồi. Core/template vẫn theo manifest E1; không thay E1 frozen.
- Budget đọc dự kiến tiếp tục 10 phút như lựa chọn gần nhất; đã thông báo cho người đọc có thể đổi trước khi đọc. Phút thực tế, exposure case mới và chi phí chuẩn bị chưa đo: unknown.
- Nhận định trước đã thu: cấp tài khoản cho QC và Frontend sửa UI-17 trước bước tiếp; [nguyên văn/giới hạn](e2-01-observations.md). Protocol commit `98171e1a4361779a8aeca13b710d002fa98c4292`. Đã chuẩn bị [hồ sơ bổ sung](e2-01-review.md), chưa thu nhận định sau hoặc benefit. Phút đọc/nguồn đã mở unknown. Không dùng record pass mô phỏng để tuyên bố app đã được kiểm chứng.

Không chứa task thật. “Đã có execution” chỉ nói fixture đã chạy; không phải completed pilot. Snapshot IDs là nhãn synthetic. Các case cũ không được relabel thành holdout E1.

| ID / phiên bản | Vai trò trong phát triển | Nguồn | Tình trạng / thuộc E1? |
|---|---|---|---|
| MOCK-01–05 | Case thiết kế trạng thái/evidence | [Bộ mẫu](../examples/mock/README.md) | Có fixtures/outcome thiết kế; không thuộc nhóm đánh giá mới E1 |
| MOCK-06 v1 | Walkthrough nhiều lớp, biết đáp án | [Hồ sơ gốc](mock/MOCK-06-review.md) | Có execution; không thuộc E1 |
| MOCK-06 fixed-v1 | Vòng sửa reset/cache | [Hồ sơ sửa](mock/MOCK-06-remediation.md) | Có execution và feedback có hỗ trợ; không thuộc E1 |
| MOCK-06 fixed-v2 | Clarification dấu cách | [Hồ sơ v2](mock/MOCK-06-v2.md), [feedback](../docs/REVIEWER-CHECK.md) | 13 test pass, người dùng nhận xét hợp lý/dễ hiểu; không phải review độc lập, không thuộc E1 |
| MOCK-07 | Dùng lại bố cục, biết đáp án | [Hồ sơ 07](mock/MOCK-07-review.md) | Có execution, chưa thu feedback; không là holdout E1 |

## Lượt E1-01 — kết thúc chưa đánh giá được mục tiêu do thiếu bối cảnh đầu vào

Sau hỗ trợ định hướng, người dùng hỏi developer đã tự test và qua QC chưa, rồi nhận xét input chỉ dừng ở feature/unit test. Chưa thu nhận định trước/sau hồ sơ; không tiếp tục coi đây là lượt đánh giá hiệu quả hồ sơ. Kết quả/giới hạn tại [results](results.md). Input, code, evidence và protocol E1 giữ nguyên. Những dòng dưới lưu việc chuẩn bị và phản hồi theo diễn tiến, không phải trạng thái chờ hiện tại.

Đã chọn case hủy đặt chỗ vì có requirement/source/checks nhỏ, cùng họ behavior change Python. Không có candidate mới khác được xét rồi loại trong lượt này. Input được tạo sau khi chốt protocol; tác giả biết thiết kế, chưa gọi là đánh giá mù hoặc độc lập.

| Trường cần ghi | Trạng thái hiện tại |
|---|---|
| Run ID, case ID, chọn/loại và lý do | E1-01, E1-seat-cancellation; chọn theo tiêu chí nêu trên |
| Case/requirement/snapshot version và vị trí input | e1-seat-req-v1, e1-seat-head-v1; [input](../examples/evaluation/e1-seat-cancellation/INPUT.md) |
| Protocol commit / freeze | Protocol `183b477752ce819934896c03abd7bef74cd88dee`; freeze `8c03ad55f41811c2539c44cbcb049322530501a2` |
| Người tạo, người đọc, người đối chiếu | Tác giả: trợ lý; người đọc: người dùng trong chat đã chọn tham gia; người đối chiếu độc lập chưa có |
| Đã biết đáp án/hồ sơ trước đó, hỗ trợ | Người dùng từng đọc walkthrough 06/07; chưa xác nhận nguồn đã mở ở case mới. Input có giải thích từ Python. Sau phản hồi đầu, cung cấp thêm ORIENTATION.md về vị trí/quy trình; hồ sơ phân tích chưa gửi. Nhận định tiếp theo là có hỗ trợ định hướng |
| Timebox được chọn / overhead chấp nhận được | Người dùng chọn tổng 10 phút đọc trước/sau hồ sơ. Đây là ngân sách lượt thử, chưa là ngưỡng overhead chấp nhận được khi áp dụng thật |
| Bắt đầu/kết thúc, thời gian theo từng hoạt động | Chưa có số đo người đọc; tự báo thời gian đọc, không tính thời gian chờ trợ lý. Effort chuẩn bị/triage chưa đo: unknown |
| Nhận định/action trước/sau, nguồn tự tìm, ghi nhận hỗ trợ | Phản hồi đầu: “cần nêu ra thêm tình trang hiện tại để dễ hình dung vị trí đứng hiện tại”. Chưa có nhận định behavior/action, nguồn tự tìm hoặc phút đọc. Đã chuẩn bị [hỗ trợ định hướng](../examples/evaluation/e1-seat-cancellation/ORIENTATION.md); nhận định sau hồ sơ chưa có |
| Link execution, hồ sơ, adjudication và kết quả | [Baseline local](../examples/evaluation/e1-seat-cancellation/baseline.local.json): 2 pass, không errors/skipped; chưa có hồ sơ bổ sung hoặc kết quả review/adjudication |

Ghi cả case được xét nhưng loại, không chỉ case thuận lợi. Với rerun sau sửa, dùng run ID/version riêng và giữ kết quả cũ. Xem [protocol E1](../docs/EVALUATION-PROTOCOL.md).
