# Decision log

## D-11 — 05/11/2026: thay plan bằng thiết kế và năng lực tối thiểu, chưa pilot

Người dùng xác nhận điều chỉnh theo kiến trúc as-is đã audit: thiết kế framework/năng lực tối thiểu trước. Lưu nguyên plan S0–S5 thành `IMPLEMENTATION-PLAN-2026-11-03.md`, thay plan hiện hành bằng P0 scope, P1 contract, P2 rules, P3 kiến trúc đích/ADR, P4 luồng offline, P5 kỹ thuật. Không tự đánh dấu gate đã đạt hoặc chốt stack trong lượt đổi plan.

Proposal pilot trước audit chuyển lịch sử, không có quyền khởi động pilot/E3. Cập nhật repo skill/README để phiên sau không quay lại vòng mock/feedback liên tục. Giữ nguyên core/template, fixture, execution, freeze/protocol E1/E2 và kết quả đã ghi. Bước kế tiếp P0 FRAMEWORK-SCOPE, không triển khai runtime trước design.

## D-10 — 05/11/2026: tổng kết E2 và đề xuất vòng sau

Sau hồ sơ E2, người dùng trả lời “đã ổn”. Lưu nguyên văn, không suy benefit/action thay đổi/approval hoặc effort. Kết thúc một lượt phản hồi, cập nhật results và hoàn thành MANAGEMENT-PROPOSAL theo plan thay vì tạo thêm mock. Đề xuất tiếp tục có giới hạn nếu có owner/budget; các nguồn lực là con số thương lượng, chưa đo từ vòng synthetic. Chưa triển khai pilot thật hoặc automation.

## D-09 — 05/11/2026: E2 tại điểm QC → Reviewer/TL

Người dùng chọn QC → Reviewer/TL. Chuẩn bị protocol E2 và gói xuất CSV với vị trí, self-test, QC/revision/môi trường, issue/blocked và quyết định cần đưa ra. Evidence do tác giả soạn được đánh dấu mô phỏng; không dựng thêm app/runner rồi giả làm QC thật. Core/template frozen và E1 giữ nguyên.

Acceptance thiết kế: input đủ để biết ai test/cái gì/ở revision nào, phần còn mở và tiêu chí chuyển bước của case; số liệu khớp record; chưa có nhận định người đọc bị điền giả. Đánh giá H3 về quyết định trên artifact, không là đánh giá behavior app hoặc effectiveness thật. Chưa gửi hồ sơ phân tích trước khi lưu nhận định đầu.

## D-08 — 04/11/2026: ghi nhận giới hạn E1 và thiết kế lại điểm bàn giao

Người dùng nhận xét E1 chỉ có feature/unit test, hỏi developer self-test và QC. Đánh giá lại: input thiếu điểm bàn giao và quyết định cần hỗ trợ, không đủ để thử mục tiêu Reviewer/TL như dự định. QC không bắt buộc đi trước mọi review; không tự thêm gate tổ chức chưa được xác nhận.

Kết thúc E1-01 với kết quả chưa đánh giá được mục tiêu, giữ input/evidence/protocol frozen và feedback trong `pilot/results.md`. Không coi người dùng thiếu kỹ năng hoặc framework thất bại. Lượt thiết kế mới là E2, phải chốt điểm bàn giao, vai trò, provenance self-test/QC và quyết định trước khi tạo thêm case. Không gán QC pass thật cho evidence synthetic. Người dùng đã đồng ý hướng điều chỉnh này; chưa chọn điểm bàn giao cụ thể cho E2.

## D-07 — 04/11/2026: chốt bản dùng thử E1 trước đánh giá

Đóng băng core/template tại commit `8c03ad55f41811c2539c44cbcb049322530501a2` bằng Git blob ID và hash nội dung Git trong `pilot/e1-freeze.json`. Tạo protocol, task register và adjudication log theo plan; các walkthrough cũ được ghi đúng vai trò design/self-check, không thành holdout hoặc adjudication độc lập.

Chọn một lượt/case mới để giới hạn vòng E1; budget 20 phút là đề xuất cần chốt trước chạy, không giả làm budget người dùng duyệt. Người đọc/case mới chưa chỉ định. Acceptance phiên chuẩn bị: phiên bản frozen truy lại được và hash khớp, protocol ghi tiêu chí/exposure/effort trước-sau, sổ phân biệt dữ liệu đã có với chưa thực hiện. Chưa tạo thêm case hay automation; bước tiếp là bố trí lượt E1 hoặc hoàn thành results/proposal với giới hạn nếu thiếu điều kiện.

## D-06 — 04/11/2026: dùng lại bố cục trên MOCK-07

Nền `b7d84de`. Sau phản hồi hồ sơ v2 hợp lý/dễ hiểu và người dùng đồng ý tiếp tục, chọn một case hàm thuần về giảm giá. H2 là bottleneck giả lập: baseline bỏ boundary và phí giao hàng; H3 là câu hỏi về khả năng dùng lại cách giải thích. Không kết luận về workflow tổ chức.

Đầu ra: requirement synthetic, head/fixed, 2 baseline/2 probe, execution local và hồ sơ theo bố cục đã được phản hồi tốt. Acceptance kỹ thuật: head baseline 2 pass/probe 2 fail đúng IDs, fixed 4 pass, không errors/skipped; file/link hợp lệ; mẫu cũ không đổi. Runner chỉ kiểm tra fixture này, không mở rộng engine/stack sản phẩm. Quy tắc do tác giả đặt rõ, không mạo nhận quyết định của owner thật. Case mới không là holdout vì viết sau feedback và biết đáp án. Phản hồi usability trên MOCK-07 chưa thu thập, không nâng G1/effectiveness.

## D-05 — 04/11/2026: requirement v2 theo lựa chọn người dùng

Nền `1064b2f`. Người dùng chọn toàn dấu cách hiển thị tất cả, category có dấu cách hai đầu được bỏ dấu cách trước khi tìm. Ghi `mock-req-06-v2` và tạo snapshot fixed-v2 riêng; không đổi requirement/evidence v1. Phạm vi clarification là ASCII space ở hai đầu, không tự mở rộng tab/newline/Unicode.

Chọn chuẩn hóa tại service để áp dụng cho kết quả service/API/UI; không đòi cache entry được gộp hoặc UI lưu chuỗi chuẩn hóa. Acceptance: 4 check mới pass cùng 9 check cũ ở v2; đối chứng v1 vẫn pass 9 cũ và fail 4 mới, không errors/skipped. Đây là clarification mới, không kết luận v1 có defect trước khi yêu cầu được chốt. Kết quả tại [hồ sơ v2](../pilot/mock/MOCK-06-v2.md). Human approval/G1 vẫn tách riêng.

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
