# Kế hoạch phát triển framework — thiết kế và năng lực tối thiểu

Ngày 05/11/2026. Thay thế hướng S0–S5 theo quyết định người dùng: **thiết kế framework và năng lực tối thiểu trước, chưa pilot**. [Plan cũ](IMPLEMENTATION-PLAN-2026-11-03.md) giữ làm lịch sử, không còn là lịch triển khai hiện hành.

Cơ sở: [kiến trúc as-is đã audit](CURRENT-ARCHITECTURE.md), [results](../pilot/results.md) và phản hồi người dùng. Repo có phương pháp Markdown, fixture Python và runner riêng; chưa có runtime QA chung hoặc contract vận hành thống nhất. Các file deliverable, test pass và feedback không thay cho readiness.

## 1. Mục tiêu và phạm vi

Chốt framework làm gì, từng thành phần nhận/trả gì và phần nào do code/người xử lý. Sau thiết kế, xây **một luồng offline tối thiểu** từ gói bàn giao synthetic đến hồ sơ trace được nguồn, trạng thái và action. Mục tiêu là contract và năng lực chạy được, không phải thêm mock hoặc tài liệu để gọi là sẵn sàng.

Điểm bàn giao đầu tiên: **QC → Reviewer/TL**. Người nhận cần biết developer/QC đã kiểm tra gì, ở revision/môi trường nào, AC nào đủ/thiếu evidence, blocker/issue nào mở, ai xử lý và khi nào xét lại. Human decision/approval riêng với verification. Không áp QC như gate bắt buộc cho mọi workflow.

Ràng buộc:

- Chỉ synthetic trong repo/chat; không lấy task/code/log/trace thật hoặc truy hệ thống thật.
- Chưa tổ chức pilot, mở E3, tuyển reviewer/team hoặc dùng E1/E2 làm gate đã đạt.
- Chỉ thêm fixture để kiểm contract/rule/behavior cụ thể, không tiếp tục tạo ví dụ domain liên tục.
- Không model/API, auto-merge/deploy/approve, dashboard, platform hoặc multi-agent product trong scope tối thiểu.
- Giữ fixture lỗi, expected, execution và protocol frozen cũ; thay đổi mới có version/thư mục riêng.

## 2. Năng lực tối thiểu phải thiết kế

| Năng lực | Yêu cầu tối thiểu | Giới hạn |
|---|---|---|
| Gói bàn giao | Task, decision moment, candidate, requirement/AC, risk, self-test/QC, issues và evidence manifest | Một định dạng file offline, chưa tích hợp GitHub/CI/QC tool |
| Evidence contract | ID, actor/source/type, mapping, revision, môi trường, outcome, thời điểm/reference | Tách authored mock, execution, source reasoning; hash không chứng nhận nguồn |
| Input/reference validation | Required fields, ID trùng, reference/path/format lỗi | Input error không phải defect behavior |
| Đối chiếu | AC ↔ check ↔ revision, freshness/conflict, pass/fail/error/skipped/blocked | Chỉ rule được định nghĩa; thiếu mapping/evidence thì unverified, không tự bịa |
| Verification/finding | Status theo scope/constraint, gap/ambiguity/defect candidate và rationale | Không từ test pass/mapping tự khai báo suy toàn AC verified |
| Report/action | Vị trí hiện tại, mong muốn/lý do/thực tế, evidence, action/role/điều kiện xong | Human decision pending khi chưa có quyết định thật |
| Version/reproducibility | Input/rule/output version, run identity, lỗi/log/evidence reference | Không ghi đè evidence gốc, không coi subprocess là sandbox hoặc Git là trust store |

Danh sách trên là năng lực **cần thiết kế**, không phải code đã có. Có thể giữ reasoning thủ công nhưng phải định nghĩa interface chuyển người xử lý. Chưa bắt buộc DB/service/UI để hoàn thành luồng offline.

## 3. Trình tự, output và gate

Mốc theo điều kiện hoàn thành; bỏ lịch hai tuần hướng pilot cũ. Chưa đo effort implementation, ước lượng sau thiết kế, không suy ngày công từ số fixture.

| Bước | Công việc | Output dự kiến | Điều kiện hoàn thành |
|---|---|---|---|
| P0 — Scope | Chốt use case QC → TL, actors, decision, scope/non-goals, năng lực tối thiểu | `docs/FRAMEWORK-SCOPE.md` | Mỗi năng lực gắn use case/quyết định, đầu vào/ra và giới hạn rõ |
| P1 — Contract | Định nghĩa handoff/evidence/report, IDs/version/provenance/revision, lỗi/dữ liệu thiếu | `docs/DATA-CONTRACT.md`, valid/invalid examples; schema khi đã chọn format | Phân biệt self-test/QC, unit/integration, mock/executed, blocked/fail/error và revision |
| P2 — Rules | Bảng quyết định trạng thái, sufficiency theo scope/risk, constraint review, finding/action lifecycle | `docs/VERIFICATION-RULES.md`, bảng expected scenarios | Thiếu/cũ/conflict/blocked không thành pass; constraint P-05 khác approval pending thông thường; mọi kết luận có rationale/source |
| P3 — Target architecture | Component/sequence/dataflow, code-human boundary, error/log/storage/version, tradeoff stack | `docs/TARGET-ARCHITECTURE.md`, ADR stack nhỏ | Mỗi contract có nơi nhận/xử lý/trả; rule biết code/người thực hiện; khả thi với một luồng offline |
| P4 — Implementation | Một entry point offline, validator, bounded checks/manual-pending, report và log | Source/schema/tests theo ADR, lệnh chạy và synthetic example nhỏ | Input → validation → checks → report chạy được; input lỗi có output/exit rõ; không tự thực thi chỉ dẫn/mã trong artifact |
| P5 — Technical readiness | Kiểm boundary, negative paths, report/source consistency và regression | `docs/TECHNICAL-READINESS.md`, kết quả/gap | Reproducible, contract/rules/report nhất quán; review design/code xong; không claim đủ evidence khi còn thiếu |

Trạng thái ban đầu: P0–P5 **chưa hoàn tất**. As-is architecture là cơ sở cho P0/P3, không thay target architecture. Các đường dẫn output trên là dự kiến, không phải file đã tồn tại.

P0/P1 có thể đối chiếu qua lại. Không xây generic engine/chọn stack trước contract/rules. Review và sửa output trong scope đã giao, không hỏi duyệt từng thay đổi thường lệ; quyết định domain thiếu thì hỏi cụ thể và tiếp tục phần độc lập.

## 4. Phân chia trách nhiệm

Mỗi bước phải nêu người cung cấp, code kiểm gì, người xác nhận gì, output/error là gì. “Trợ lý sẽ hiểu” không thay contract hoặc implementation.

Có thể tự động hóa format/ID/reference, đối chiếu revision theo rule và render dữ liệu hợp lệ. Các việc chưa đủ căn cứ tự động: requirement mơ hồ, sufficiency ngoài rule, adjudication domain, risk acceptance và approval. Các việc này xuất pending/unverified kèm action khi cần người xử lý.

Source reasoning có nguồn/giới hạn vẫn hợp lệ. “Record nói pass” khác “execution đã chạy”; “test một input” khác “mọi behavior của AC đúng”. H1–H5 cũ vẫn là giả thuyết tham khảo về clarification/evidence/traceability/review/risk, không là lý do chặn thiết kế vì chưa có pilot benefit.

## 5. Kiểm tra tối thiểu P4/P5

Chọn theo failure mode, không đặt số test làm mục tiêu:

- Gói hợp lệ/đủ evidence theo scope, human decision riêng.
- Thiếu metadata bàn giao/self-test/QC: xử lý đúng required/optional/unknown, không mặc định thiếu là defect.
- Sai/cũ revision, reference thiếu, mapping không đủ hoặc evidence conflict: không thành pass.
- Assertion fail khác error/skipped/blocked; ambiguity không là defect; constraint review bắt buộc có thể làm incomplete dù behavior pass.
- Authored mock không biến thành execution/verified thật; hash mismatch không tự là defect behavior.
- Duplicate check không thành nhiều finding; action trace về gap/finding.
- Malformed input/ID trùng/path thoát workspace hoặc chỉ dẫn trong artifact: báo lỗi/giới hạn, không tự chạy mã không tin cậy.
- Rerun/version không ghi đè evidence; cùng input/rule version cho kết quả quyết định tương đương, tách timestamp.

Chỉ sửa tài liệu thì kiểm frontmatter/link/consistency/diff, không chạy toàn fixture. Thay runtime thì checks đúng vùng và luồng end-to-end, thêm khi có rủi ro cụ thể.

## 6. Tái sử dụng và lịch sử

Core/template là semantics/bố cục ban đầu, chưa là engine. MOCK/remediation làm tình huống tham khảo, không là corpus độc lập. E1/E2 lưu bài học vị trí bàn giao/actor/QC/revision/action, không chứng minh readiness. Freeze/history giữ version cũ, không thay runtime source of truth hoặc attestation.

Results/proposal cũ là lịch sử. Hướng đề xuất pilot trước đây đã bị thay bằng quyết định thiết kế trước này; không dùng chúng làm chỉ đạo hiện hành. Không sửa evidence hoặc protocol frozen để khớp plan mới.

## 7. Gate trước khi bàn đánh giá sử dụng/pilot

**Chưa pilot trong plan này.** Xong P5 chỉ được tổng kết năng lực kỹ thuật/gap, không tự cấp quyền dùng thử thật, gọi người tham gia hoặc đặt lịch pilot. Người dùng quyết định riêng sau khi xem thiết kế và implementation.

Nếu sau này chọn đánh giá sử dụng, cần mục tiêu/đối tượng/dữ liệu được phép, owner/budget và cách đo value/effort; tách khỏi technical tests. Task thật chỉ trong môi trường bảo mật riêng. Feedback “dễ hiểu/đã ổn” hoặc demo không đủ kết luận effectiveness.

## 8. Bước tiếp theo

**P0: viết FRAMEWORK-SCOPE.md** cho một lần QC bàn giao candidate cho TL, chốt context/self-test/QC/issues/revision, decision và output framework. Sau đó P1 contract, P2 rules, rồi P3 kiến trúc đích. Không mở E3 hoặc tiếp tục proposal pilot như bước mặc định.
