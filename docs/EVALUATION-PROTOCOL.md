# Vòng đánh giá synthetic E1

Trạng thái: **chuẩn bị xong protocol, chưa bắt đầu thu kết quả**. Ngày 04/11/2026. Đây là protocol của vòng E1; sửa protocol sau khi bắt đầu phải tạo E2, không ghi đè kết quả E1.

## Bản dùng thử được chốt

Can thiệp: core hướng dẫn review thủ công + template hồ sơ, gồm giải thích từng defect theo mong muốn → lý do → thực tế → cách sửa → kết quả. Không thử AI verifier hoặc engine mới.

Đóng băng core và template tại commit `8c03ad55f41811c2539c44cbcb049322530501a2`. [Manifest](../pilot/e1-freeze.json) ghi Git blob ID và SHA-256 nội dung trong Git, không phụ thuộc line ending của checkout Windows. Đọc đúng bản bằng `git show <commit>:<path>` hoặc checkout riêng; không dùng file hiện tại nếu đã khác manifest. Protocol E1 chính là phiên bản file này trong commit đưa protocol vào repo; ghi SHA commit đó trước khi chạy.

Mock cũ, remediation và MOCK-07 đều là **case thiết kế/đã công khai đáp án**. Không đưa vào nhóm đánh giá mới; có thể dùng đào tạo nhưng phải ghi việc đó. Không cần sao chép core/template thành nhiều bản Markdown khó bảo trì.

## Câu hỏi và phạm vi

H3 là giả thuyết chính: hồ sơ có giúp người đọc hiểu trạng thái, truy bằng chứng và chọn hành động không? Ghi riêng đóng góp H2 từ targeted checks; không quy hết lợi ích cho bố cục.

Đối tượng: một case synthetic mới có requirement/version, snapshot, code/diff và test/evidence đủ đối chiếu. Chọn họ task behavior change Python nhỏ để hạn chế khác biệt stack. Case phải có ít nhất một quyết định review cụ thể; không bắt buộc phải có defect. Ghi case được xét nhưng loại và lý do trong [task register](../pilot/task-register.md).

Người viết case biết đáp án không được tự nhận đang review mù. Nếu không có người đọc tách khỏi tác giả, vẫn thực hiện walkthrough có hỗ trợ và gọi đúng là exploratory case study. Không đổi nhãn để lấp thiếu đánh giá độc lập. Không lấy task thật vào repo.

## Điều kiện trước lượt đầu

- Ghi commit protocol, core/template freeze, case/version và vai trò người tạo/người đọc/người đối chiếu; mức đã biết đáp án và các hỗ trợ trước đó.
- Ghi timebox và overhead chấp nhận được do người tổ chức chọn **trước khi bắt đầu**. Đề xuất để lựa chọn: tối đa 20 phút đọc/review mỗi lượt; hiện chưa được người dùng xác nhận, không phải chuẩn ngành hoặc kết luận overhead chấp nhận được.
- Ghi mục tiêu cải thiện đáng giá: người đọc truy được một claim tới requirement + check/source + execution/snapshot và chọn hành động có lý do, hoặc giải thích vì sao không cần thêm hành động. Đây là tiêu chí quan sát, không phải điểm benchmark.
- Nếu thiếu người đọc/budget, giữ trạng thái chưa bắt đầu; vẫn hoàn thành tổng kết và proposal với phần thiếu. Không tạo thêm mock liên tục để thay kết quả đánh giá.

## Cách tiến hành một lượt

1. **Trước hồ sơ:** đưa requirement, code/diff và evidence ban đầu, chưa mở hồ sơ bổ sung. Ghi người đọc đã biết gì, nhận định/action và thời gian review ban đầu. Nếu đã thấy hồ sơ/đáp án thì ghi exposure, không tái dựng một baseline mù giả.
2. **Chuẩn bị hồ sơ:** dùng đúng bản frozen; ghi thời gian chuẩn bị, thu evidence và chạy checks riêng. Snapshot/requirement đổi thì tạo version mới. Không gán test error/skipped thành pass hoặc defect behavior.
3. **Sau hồ sơ:** người đọc tự diễn giải trạng thái, một chuỗi bằng chứng và action/owner/điều kiện xong. Dùng câu hỏi tự do trước; nếu có lựa chọn gợi ý hoặc lời giải thích thì lưu nguyên nội dung và đánh dấu assisted.
4. **Đối chiếu:** mỗi candidate có nguồn và verdict tại [adjudication log](../pilot/adjudication-log.md). Người tạo case tự đối chiếu được ghi là self-check, không là independent adjudication. Duplicate liên kết finding gốc; disputed/pending chưa là false positive.
5. **Kết thúc:** lưu câu trả lời thực tế, action có đổi không và vì sao. Hết timebox thì ghi chưa hoàn tất; không viết tiếp rồi tính như hoàn thành trong hạn. Chỉnh template sau feedback thành version mới, không sửa frozen E1.

## Bộ ghi nhận tối thiểu cho mỗi lượt

| Nhóm | Cách ghi |
|---|---|
| Nhận dạng | Run ID, case/requirement/snapshot, protocol commit và freeze commit |
| Exposure | Vai trò, biết đáp án chưa, nguồn/hồ sơ đã xem, gợi ý nhận được |
| Trước/sau | Nhận định, action, lý do thay đổi hoặc không đổi; nguồn người đọc tự tìm |
| Thời gian | Phút chuẩn bị, thu evidence/chạy check, review trước/sau, triage; setup tách riêng. Không đo thì unknown |
| Finding | Unique defect, ambiguity/gap, duplicate, verdict và rationale; action/owner hoặc pending |
| Giới hạn | Thất bại, thiếu context, errors/skipped, phần cần tác giả giải thích |

Không có kết quả thì ghi “chưa thực hiện”, không điền 0 phút hoặc 0 finding. Không tính pass rate AC thành chất lượng phần mềm, số test thành số defect hoặc validity thành recall. Mẫu số 0 là N/A. Không dùng wall-clock tool runtime để thay effort người đọc.

## Điều kiện kết thúc vòng và quyết định

Timebox vòng đầu: một lượt trên một case mới; nếu có phản hồi thì sửa phương pháp ở vòng kế tiếp, không mở rộng E1 vô hạn. Kết quả một case chỉ áp dụng case đó.

Chốt `pilot/results.md` dù lượt chưa chạy được: tách feasibility fixture, phản hồi đã có và dữ liệu E1; nêu missing/bất lợi. Sau đó viết `docs/MANAGEMENT-PROPOSAL.md` với lựa chọn tiếp tục giới hạn/đổi/dừng và nguồn lực cần có. Pilot 3–5 task thật là nhánh riêng trong môi trường bảo mật, chưa được thực hiện hoặc cam kết.

G1 chỉ được cân nhắc từ quan sát truy claim, hiểu trạng thái, action và nhu cầu cụ thể; lời nhận xét dễ hiểu là tín hiệu một phần. G4 kỹ thuật synthetic không chứng minh effectiveness thực tế. Thiếu điều kiện chạy không được gọi là chứng minh framework không có giá trị, cũng không là lý do mặc định xây automation.
