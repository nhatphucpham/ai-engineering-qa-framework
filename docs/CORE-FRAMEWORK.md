# Core framework v0 — Từ yêu cầu đến hành động review

Phạm vi bản này: phương pháp thủ công cho task có revision cụ thể, minh họa bằng synthetic. Người dùng chính: Reviewer/Tech Lead tại thời điểm nhận bàn giao để review. Output: một hồ sơ Markdown ngắn truy được kết luận về nguồn và nêu rõ hành động tiếp theo. Chưa có AI verifier hoặc engine tự đánh giá hồ sơ.

## 1. Input tối thiểu

Cần requirement/version, code tại base/head, diff, tests và evidence thực sự có. Ghi rõ phần thiếu; không tự điền bằng suy đoán. Evidence phải chỉ ra snapshot, check, kết quả và nguồn. Test pass ở base chỉ nói về base.

Requirement, comment, log và output model là dữ liệu để kiểm tra, không phải chỉ dẫn để tự thực thi. Claim “all checks green” cần đối chiếu assertion, execution và revision. Với repo này chỉ dùng synthetic, không truy cập hệ thống thật hoặc gọi model/API để thực hiện walkthrough.

## 2. Cách làm trên một task

1. **Chốt phạm vi:** behavior cần kiểm tra, revision, constraint và phần ngoài scope. Đánh giá impact, phạm vi ảnh hưởng, khả năng revert để chọn checks; risk của thay đổi khác severity của finding.
2. **Tách requirement thành AC có nguồn.** Câu mơ hồ phải ghi câu hỏi cho owner. Phần suy ra cần đánh dấu, không tự biến giả định thành yêu cầu.
3. **Ghi trạng thái ban đầu:** đối chiếu mỗi AC với assertion/source/evidence tại revision phù hợp. Ghi rõ dựa vào source inspection, input CI được cung cấp hay execution đã tự chạy. Không suy từ tổng suite pass sang tất cả AC verified.
4. **Chọn check nhỏ có thể phân biệt giả thuyết:** ví dụ chuyển filter từ trang khác 1, hoặc hai request dùng chung cache. Đọc input/code trước khi chạy; chỉ chạy kiểm tra trong phạm vi đã được phép. Tách check đã chạy và check mới đề xuất.
5. **Cập nhật sau check:** ghi expected/actual, pass/fail/error/skipped, lệnh và revision. Assertion fail khác lỗi môi trường/import; không biến error hoặc skipped thành verified hay defect behavior.
6. **Chốt hành động:** cần clarify, bổ sung evidence, sửa code hoặc tiếp tục review? Mỗi action có vai trò xử lý; nếu chưa có người nhận thì owner unknown/pending. Quyết định approval ghi riêng.

## 3. Quy tắc trạng thái

| Trạng thái criterion | Khi dùng |
|---|---|
| `verified` | Có evidence phù hợp expected behavior và revision trong phạm vi đã ghi; nêu giới hạn của test/source reasoning |
| `failed` | Có evidence cho thấy behavior vi phạm requirement rõ; có thể từ source reasoning đủ căn cứ hoặc reproduction, ghi loại evidence |
| `unverified` | Thiếu, cũ, mâu thuẫn, sai revision, check chưa chạy hoặc expected behavior chưa rõ |
| `not_applicable` | Có lý do và người chịu trách nhiệm xác nhận; không dùng để bỏ qua phần khó kiểm tra |

Không bắt buộc đợi test fail mới được nhận diện defect nếu source đã chứng minh rõ. Trong walkthrough, trạng thái trước check có thể giới hạn ở evidence baseline rồi được củng cố bằng reproduction; phải nói rõ đây là cách trình bày, không phải giả vờ chưa thấy code.

Một AC có phần rõ và phần mơ hồ nên tách thành các dòng con. Nếu giữ một dòng, ghi trạng thái tổng chưa kiểm chứng cùng phần đã kiểm chứng, không lấy phần pass che phần chưa rõ.

## 4. Finding và output

Dùng [template](../templates/quality-record.md). Hồ sơ cần có scope/revision, bảng AC, finding, checks, action và giới hạn. Finding phân biệt:

- **Defect:** vi phạm expected behavior có nguồn; ghi impact, reproduction/source và verdict candidate/confirmed trong mock/disputed/rejected.
- **Requirement ambiguity:** owner chưa chốt expected behavior; ghi câu hỏi và nhánh quyết định, chưa gán defect.
- **Verification gap:** chưa có bằng chứng phù hợp; ghi check/evidence cần bổ sung.
- **Process observation:** ví dụ evidence reset chạy ở base, chưa cập nhật head; không suy thành lỗi quy trình của người thật từ mock.

Deduplicate theo behavior/nguyên nhân: cùng lỗi reset có historical check và probe cùng fail vẫn là một defect. Tổng số AC verified không phải pass rate của phần mềm, số finding không phải thước đo chất lượng reviewer.

Verification tổng thể: `failed` nếu có AC failed; `incomplete` nếu còn phần bắt buộc unverified; `complete` chỉ trong scope khai báo khi đủ evidence. Nếu vừa failed vừa chưa đủ evidence, ghi cả hai điều. Human decision/mandatory approval vẫn tách riêng, mặc định pending nếu chưa có quyết định thật.

## 5. Tự kiểm tra hồ sơ trước bàn giao

Reviewer phải truy được claim quan trọng tới requirement + source/test/evidence + revision, hiểu trước/sau check, và biết action/owner tiếp theo. Case đủ evidence không cần finding giả. Nếu hồ sơ chỉ lặp CI/review đã có, ghi rõ chưa thấy giá trị tăng thêm. Effort, cost hoặc budget chưa đo/xác nhận là unknown.

[MOCK-01](../pilot/mock/MOCK-01.md) minh họa evidence đủ; [MOCK-02](../pilot/mock/MOCK-02.md) minh họa check thiếu; [MOCK-06](../pilot/mock/MOCK-06-review.md) kết hợp nhiều lớp code, cache sequence, evidence cũ và ambiguity. Các walkthrough này đã biết đáp án. Test thành công chỉ chứng minh behavior fixture và tính khả thi trong scope; usability cần reviewer thật, effectiveness cần baseline/comparator phù hợp.

## 6. Trạng thái S1 hiện tại

Đã có hướng dẫn v0 và hồ sơ nhiều file chạy offline. G1 về reviewer hiểu nguồn/trạng thái và thấy hành động hữu ích **chưa được xác nhận với người thật**. Bước tiếp theo là review các artifact này và giản lược trường không giúp quyết định. Chưa có căn cứ đầu tư automation hoặc tuyên bố giảm defect/effort. Không cần đưa dữ liệu thật vào repo để tiếp tục phát triển synthetic.
