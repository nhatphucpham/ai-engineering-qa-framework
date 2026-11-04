# Decision log

## D-04 — 04/11/2026: giải thích từng lỗi ngay trong hồ sơ

Nền `dbf1582`. Phản hồi tự diễn giải cho thấy người dùng chưa phân biệt hai cách sửa và phải mở file khác để hiểu vì sao reset trang. Theo yêu cầu người dùng, trình bày riêng mỗi lỗi bằng mong muốn → lý do → thực tế → cách sửa → kết quả. Cập nhật template và ghi phản hồi; giữ requirement/code/evidence nguyên trạng. Kiểm tra lý do với catalog, quy tắc với requirement, outcome với execution. Chưa có phản hồi sau sửa; G1 vẫn chưa xác nhận.

## D-01 — 04/11/2026: vòng sửa và kiểm chứng synthetic

Cơ sở: [implementation plan](IMPLEMENTATION-PLAN.md), [core v0](CORE-FRAMEWORK.md), [review MOCK-06](../pilot/mock/MOCK-06-review.md). Commit nền: `9bc27f6`.

- Bottleneck làm việc: H2, thiếu sequence checks trong fixture; chưa phải kết luận về tổ chức.
- Chọn targeted regression checks và snapshot sửa riêng để hoàn tất luồng finding → sửa → evidence mới → hành động review.
- Input: requirement `mock-req-06-v1`, source head, baseline/historical/probe hiện có. Output phục vụ Reviewer/TL: [hồ sơ sau sửa](../pilot/mock/MOCK-06-remediation.md).
- Acceptance kỹ thuật: baseline 6, historical 1, probe 2 đều pass trên bản sửa; cùng checks trên head gốc vẫn tái hiện hai behavior lỗi; không errors/skipped; fixture gốc không đổi.
- Reuse assertions và worker hiện có; thêm runner nhỏ chỉ để chạy đối chứng và lưu execution/hash cho bài tập. Đây không phải helper đánh giá hồ sơ hoặc generic verifier; Python là runtime fixture, chưa chọn stack sản phẩm.
- Không chọn platform/AI adapter/report engine: chưa có evidence về nhu cầu hoặc lợi ích vượt targeted checks và hồ sơ thủ công.
- Tradeoff: phụ thuộc cấu trúc fixture gốc, case đã biết đáp án và chưa có reviewer độc lập. Test xanh chưa giải quyết ambiguity whitespace hay approval.
- G1 với reviewer thật còn pending. Vòng này chỉ xác minh feasibility; bước tiếp theo là rà hồ sơ/core/template với người dùng, ghi trường nào giúp quyết định trước khi chọn can thiệp S2 tiếp theo.

## D-02 — 04/11/2026: chuẩn bị thử khả năng sử dụng hồ sơ

Commit nền `be0e84c`. H3 là giả thuyết cần thử, chưa được xác nhận: người đọc có thể mất công truy kết luận tới assertion hoặc tìm action. Tự rà thấy template đặt kết luận ở cuối và hồ sơ sau sửa thiếu link trực tiếp tới assertion.

Chọn chỉnh bố cục template, thêm đường truy nguồn vào hồ sơ sau sửa và [phiếu thử G1](REVIEWER-CHECK.md). Không đổi semantics verification, requirement, code/tests hoặc evidence đã chạy. Không ép sửa hồi tố mọi walkthrough cũ chỉ để đồng nhất bố cục.

Acceptance phiên chuẩn bị: status/action xuất hiện ở đầu; claim hai lỗi có đường tới assertion và execution đúng snapshot; phiếu ghi được câu trả lời/nguồn/hỗ trợ/thông tin mới mà không điền giả kết quả. G1 vẫn pending cho đến khi có phản hồi thật; không chọn automation dựa trên tự rà này.

## D-03 — 04/11/2026: sửa hướng dẫn theo phản hồi có gợi ý

Nền `17e8e4f`. Người dùng cho biết chưa quen đọc test, truy evidence còn khó và cần thứ tự việc/điều kiện hoàn thành. Ghi nguyên đáp án tại [phiếu review](REVIEWER-CHECK.md), nêu rõ câu hỏi trắc nghiệm có gợi ý và chưa thu được diễn giải độc lập.

Chọn thêm giải thích test, một chuỗi truy evidence và bảng thứ tự/phụ thuộc/điều kiện xong vào hồ sơ; bổ sung chỉ dẫn tương ứng vào template. Không đổi code, requirement hoặc execution; không tự chốt whitespace. Acceptance của thay đổi tài liệu là khớp execution đang có, link tồn tại và các bước tương lai không được ghi đã hoàn thành. G1 chờ thử lại; chưa có căn cứ kết luận bố cục mới hữu ích.
