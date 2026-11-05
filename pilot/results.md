# Tổng kết hiện tại — synthetic và phản hồi người dùng

Ngày cập nhật 05/11/2026. Không có pilot task thật. Không có adjudication độc lập, effort người đọc hoặc ROI đã đo. Kết quả dưới tách rõ fixture kỹ thuật, phản hồi cách trình bày và thiết kế thử chưa đạt mục tiêu.

## Những gì đã thực hiện

| Phần | Evidence | Kết luận được phép |
|---|---|---|
| MOCK-01–05 | [Mẫu/kết quả](../examples/mock/README.md) | Fixture minh họa trạng thái đủ/thiếu/cũ/mơ hồ/review pending; không là đánh giá verifier |
| MOCK-06 và vòng sửa | [Hồ sơ sửa](mock/MOCK-06-remediation.md) | Hai lỗi mock tái hiện được và targeted checks pass trên bản sửa |
| MOCK-06 v2 | [Hồ sơ v2](mock/MOCK-06-v2.md), [feedback](../docs/REVIEWER-CHECK.md) | Clarification người dùng được version hóa; 13 test pass. Người dùng nhận xét hồ sơ hợp lý/khá dễ hiểu sau các giải thích trong chat |
| MOCK-07 | [Hồ sơ 07](mock/MOCK-07-review.md) | Bố cục áp dụng được vào ví dụ giảm giá; head 2 pass/2 fail, fixed 4 pass. Chưa có feedback người đọc trên case này |
| E1-01 | [Đăng ký](task-register.md), [input](../examples/evaluation/e1-seat-cancellation/INPUT.md), [định hướng](../examples/evaluation/e1-seat-cancellation/ORIENTATION.md) | Đã gửi input và nhận phản hồi về thiếu bối cảnh; chưa thực hiện so sánh trước/sau hồ sơ |
| E2-01 | [Input](../examples/evaluation/e2-qc-handoff/INPUT.md), [hồ sơ](e2-01-review.md), [nhận định trước/sau](e2-01-observations.md) | Điểm bàn giao QC → TL rõ hơn; trước đã chọn cấp tài khoản và sửa UI, sau phản hồi “đã ổn”. Benefit tăng thêm chưa xác nhận |

## E1-01: điều thực sự quan sát được

Người dùng chọn 10 phút tổng đọc/review trước/sau. Thời gian thực đọc không được cung cấp; ghi unknown, không kết luận vượt timebox. Chỉ có hai test local pass; không có developer thật tự test hoặc QC thật được xác nhận.

Phản hồi trong chat, theo thứ tự:

1. “cần nêu ra thêm tình trang hiện tại để dễ hình dung vị trí đứng hiện tại”. Tác giả bổ sung định hướng về vị trí review; lượt tiếp theo có hỗ trợ.
2. “developer ko có tự test trước à, có thông qua QC chưa?” Tác giả giải thích provenance của execution và việc chưa có QC độc lập.
3. “đúng, tôi cảm thấy input đang chỉ dừng lại ở feature và unit test”. Tác giả thừa nhận điểm bàn giao/quyết định chưa đủ rõ, sau đó điều chỉnh kết luận: QC không phải điều kiện mặc định của mọi review.

Người dùng đồng ý với việc ghi nhận giới hạn và thiết kế lại. Lượt E1-01 **kết thúc chưa đánh giá được mục tiêu vì thiếu bối cảnh đầu vào**: chưa có nhận định/action trước-sau hồ sơ, chưa có chuỗi evidence do người dùng tự truy, chưa có finding adjudication. Không tính thiếu phản hồi thành 0 finding, false negative, G1 fail hoặc framework không hiệu quả.

## Bài học và quyết định tiếp

Input review code có thể đủ cho bài tập code nhỏ, nhưng mục tiêu repo là hỗ trợ Reviewer/TL tại một điểm bàn giao. Lượt này chưa nói rõ điểm bàn giao và quyết định cần hỗ trợ. Thêm unit test hoặc ép người đọc tìm lỗi không giải quyết được thiếu sót đó.

Giữ bố cục hồ sơ đã được phản hồi tốt. Lượt mới cần chốt: bàn giao từ ai sang ai; developer tự kiểm tra gì; QC đã làm/chưa làm/không thuộc bước này; evidence của ai, snapshot/môi trường nào; quyết định người đọc cần đưa ra. Trạng thái chưa biết phải ghi rõ, không tạo QC pass giả làm execution thật.

Theo protocol frozen, đã thay thiết kế ở **E2**, giữ kết quả E1. Không mặc định tất cả feature phải qua QC trước review. Việc QC có cần hoàn tất phụ thuộc điểm bàn giao được chọn.

## E2-01: quyết định và giới hạn quan sát

Người dùng chọn QC → Reviewer/TL. Input cung cấp self-test developer 4 pass, QC 3 pass/1 blocked ở r12, auth check cũ r11 và issue UI low. Đây hoàn toàn là record do tác giả soạn, không phải test đã thực chạy như fixture MOCK-06/07.

Trước hồ sơ, người dùng đề xuất quản lý tài khoản cấp tài khoản cho QC và Frontend sửa UI-17 trước bước tiếp. Sau hồ sơ tổng hợp bằng core/template frozen, trả lời “đã ổn”. Có thể ghi nhận cách trình bày được chấp nhận ở mức chung; chưa có lời xác nhận action thay đổi, hiểu revision/evidence độc lập hoặc thông tin mới ngoài baseline. Không nói hồ sơ cải thiện quyết định khi dữ liệu chưa cho thấy điều đó.

Thời gian thực đọc, overhead chuẩn bị, nguồn tự truy và action thực hiện đều unknown. Lượt thu phản hồi kết thúc; không hỏi thêm chỉ để có kết quả thuận lợi. G1 có tín hiệu từng phần, chưa xác nhận đầy đủ; chưa có effectiveness hoặc pilot thật. Bước tiếp chuyển sang [đề xuất vòng sau](../docs/MANAGEMENT-PROPOSAL.md), không tiếp tục sinh case mặc định.

## Phần còn thiếu

G1 đầy đủ, usability độc lập, effectiveness, budget áp dụng thật, thời gian chuẩn bị/review/triage và useful findings ngoài baseline đều chưa xác nhận. Vòng tiếp phải ghi trước/sau và effort thực tế nếu đo được. Proposal tiếp theo phải nêu đúng các giới hạn này; không đề xuất platform/rollout chỉ từ mock.
