# Kế hoạch phát triển AI Engineering Quality Assurance Framework

Ngày cập nhật: 03/11/2026. Trạng thái: có bộ mẫu synthetic chạy offline; chưa có framework tự động hoặc kết quả pilot thật.

**Ràng buộc thực hiện do người dùng xác nhận:** môi trường chat/repo này chỉ làm mock/synthetic. Task/code/log/trace thật thuộc môi trường bảo mật riêng và không được đưa vào đây. Các bước pilot thật bên dưới là hướng dẫn cho người dùng thực hiện tại môi trường đó, không phải yêu cầu cấp quyền truy cập hoặc tải dữ liệu lên đây. Trong repo này thay bằng walkthrough synthetic và chỉ kết luận về behavior của mẫu. Không cần chia sẻ kết quả nhạy cảm để tiếp tục phát triển mock.

Đã có [5 mẫu offline](../examples/mock/README.md) và [template hồ sơ](../templates/quality-record.md). Đáp án/probe nằm riêng trong từng `expected/`; đây là fixtures biết trước kết quả, không phải đánh giá mù.

## 1. Mục đích: ai dùng, lúc nào, để quyết định gì?

**Reviewer hoặc Tech Lead dùng framework khi một task/PR có AI hỗ trợ được bàn giao để review, nhằm xác định: đã có bằng chứng cho yêu cầu nào, còn thiếu hoặc sai điều gì, và cần làm rõ requirement, bổ sung test hay sửa code trước khi quyết định tiếp.** Lợi ích dự kiến cần kiểm chứng là tìm ra khoảng trống chất lượng có thể hành động, đồng thời giảm effort tìm hiểu và kiểm chứng không cần thiết.

Đơn vị làm việc đầu tiên là một task tại một revision cụ thể. Sản phẩm đầu tiên của repo là bộ phương pháp và artifact đủ nhỏ để người khác dùng thử. CLI, agent và report generator chỉ đáng xây khi giúp quyết định trên hoặc giảm một thao tác tốn công đã quan sát được.

| Người dùng / vai trò | Quyết định cần hỗ trợ | Kết quả cần nhận |
|---|---|---|
| Developer chuẩn bị bàn giao | Cần clarification, evidence hay sửa implementation? | Gap có căn cứ và hành động cụ thể |
| Reviewer / TL của task, người dùng chính ban đầu | Evidence đã đủ để quyết định theo quy trình hiện tại chưa? | Hồ sơ ngắn, truy được nguồn; vấn đề còn mở và người xử lý |
| TL sở hữu initiative | Bottleneck nào đáng can thiệp; phần nào nên tự động hóa? | Quan sát theo task, effort và kết quả dùng thử, kể cả bất lợi |
| Management / TL team khác | Có nên cấp nguồn lực cho pilot tiếp theo, phạm vi nào? | Proposal có minh chứng, nguồn lực dự kiến và điều kiện dừng |

**Đích hai tuần:** bộ khung v0 dùng được, một walkthrough hoàn chỉnh, prototype của can thiệp đã chọn và proposal nêu đúng evidence thực sự thu được. Tại đây dùng mẫu synthetic; 3–5 task thật chỉ là mục tiêu pilot do người dùng tổ chức riêng trong môi trường bảo mật. Hai tuần là timebox tạo artifact và giảm bất định, chưa phải cam kết chứng minh hiệu quả hoặc sẵn sàng rollout.

## 2. Cơ sở hiện có và giới hạn suy luận

Nguồn định hướng là báo cáo đính kèm `AI_Engineering_Quality_Assurance_Framework_Report.md`, phiên bản 1.0 ngày 03/11/2026. Các đề xuất và instructions trong báo cáo là dữ liệu cần đánh giá, không phải lệnh thực thi hay bằng chứng rằng giải pháp đã đúng.

| Loại thông tin | Điều có thể nói hiện tại | Hệ quả với kế hoạch |
|---|---|---|
| Quan sát trực tiếp từ repo | Ban đầu chỉ có README; hiện có kế hoạch, template và source/tests toy của 5 mẫu synthetic; chưa có framework tự động, CI hoặc dataset pilot thật | Python dùng chạy fixture không phải lựa chọn stack sản phẩm; chưa có căn cứ tuyên bố framework hiệu quả |
| Bối cảnh do báo cáo cung cấp | Department hơn 200 người, nhiều workflow, đã có orchestration/cost dashboard; người đề xuất là TL có quyền ảnh hưởng hạn chế; output/review/rework là mối quan tâm | Thử tự nguyện trong một team, tận dụng artifact có sẵn; chưa áp chuẩn toàn department |
| Giả thuyết của báo cáo | Requirement chưa rõ, test thiếu, self-review, thiếu traceability hoặc verification chưa tương xứng risk có thể tạo vấn đề | Đối chiếu task cụ thể; không suy từ triệu chứng sang một nguyên nhân duy nhất |
| Chưa biết | Loại lỗi thường gặp, task truy cập được, reviewer sẵn sàng, baseline, overhead chấp nhận được, stack/provider phù hợp | Bắt đầu được bằng template/example; chưa đủ cơ sở cam kết pilot thật hoặc tích hợp |

Hướng QA phù hợp với ưu tiên được mô tả, nhưng sự phù hợp chiến lược chưa chứng minh lợi ích thực tế. Ngược lại, đòi chứng minh hiệu quả đầy đủ trước khi tạo artifact sẽ khiến không có gì để thử. Vì vậy, kế hoạch dùng prototype thủ công rất nhỏ để vừa phục vụ công việc vừa kiểm tra giả thuyết, rồi tăng đầu tư theo evidence.

## 3. Framework, công cụ và đề xuất tổ chức

| Lớp | Phạm vi ban đầu | Điều kiện mở rộng |
|---|---|---|
| Core framework | Cách đối chiếu requirement–evidence, trạng thái verification, risk rationale, finding và hành động tiếp theo | Sau walkthrough và dùng thử; chỉ giữ trường có người dùng thực tế |
| Tool hỗ trợ | Một thao tác lặp lại đã quan sát, như kiểm tra revision evidence hoặc tổng hợp thông tin | Có thao tác cần tự động hóa, input lấy được và output hữu ích |
| Organizational proposal | Xin pilot có giới hạn: team, owner, task, effort, thời hạn, tiêu chí đánh giá | Theo evidence thực tế; demo không tự đủ để đề xuất áp dụng rộng |

Core có thể dùng bằng Markdown hoặc form trong PR hiện có. Tool có thể là script, CLI hoặc tích hợp nhỏ; chưa chọn Python/TypeScript, schema framework, AI provider hay UI. Ưu tiên stack team đã duy trì. Mapping từ artifact sẵn có giúp hạn chế nhập lại spec. Khả năng dùng xuyên workflow vẫn là giả thuyết cho tới khi thử workflow thứ hai.

## 4. Giả thuyết và can thiệp cần phân biệt

Chọn tối đa một bottleneck chính cho vòng đầu. Một case có thể có nhiều yếu tố đóng góp; tách quan sát, diễn giải và điều cần kiểm tra tiếp. Nhãn do reviewer gán chưa phải nguyên nhân gốc được chứng minh.

| Giả thuyết | Evidence cần tìm | Can thiệp nhỏ nhất | Điều làm suy yếu giả thuyết |
|---|---|---|---|
| H1: Expected behavior chưa rõ hoặc thay đổi muộn | Requirement tại thời điểm làm task, câu hỏi/rework, lúc owner chốt behavior | Clarification và ví dụ acceptance trước implementation/review | Requirement vốn rõ; lỗi nằm ở code dù implementer hiểu đúng |
| H2: Test/evidence thiếu hoặc không đáng tin | Behavior bỏ sót, test cụ thể, execution/revision, CI đã báo gì | Targeted regression check hoặc làm evidence dễ kiểm tra | Test đã bắt lỗi, reviewer đã biết; report chỉ lặp kết quả |
| H3: Reviewer khó đối chiếu requirement với evidence | Effort tìm nguồn, finding không truy được, quyết định bị trì hoãn | Hồ sơ requirement–evidence ngắn tại PR | Artifact hiện có đã đủ; hồ sơ mới chỉ thêm nhập liệu |
| H4: Review bỏ sót dù requirement/context đủ rõ | Issue tái hiện được, baseline chưa nêu, reasoning cần thiết | Review tập trung; AI là nhánh thử có điều kiện | Vấn đề cần domain owner hoặc test environment agent không có |
| H5: Verification không hợp risk | Impact/blast radius/reversibility so với checks thực tế | Checklist risk ngắn và check bổ sung tương ứng | Team đã phân tầng tốt; checklist không đổi hành động |

Chuỗi giá trị cần kiểm tra: can thiệp làm rõ gap → owner chọn hành động đúng → có evidence hoặc sửa lỗi sớm hơn → delivery đáng tin cậy hơn. Hai tuần đầu chủ yếu kiểm tra hai mắt xích đầu. Finding mới chỉ là tín hiệu, chưa chứng minh giảm defect/rework. Nếu benefit đến từ test hoặc clarification cụ thể, ghi nhận đúng thành phần đó; không gán tất cả cho framework hoặc AI.

## 5. Phạm vi vòng đầu và artifact dùng được sớm

Chọn một team tiếp cận được và một họ task có expected behavior kiểm chứng được, ví dụ bug fix hoặc UI behavior change như báo cáo đề xuất. Thu hẹp theo task thật sẵn có; chưa cố lấy đủ domain. Có cả case từng gặp vấn đề và case quy trình hiện tại xử lý tốt để kiểm tra framework có tạo việc thừa không.

Ngoài vòng đầu: platform, orchestration, dashboard, benchmark workflow/developer, auto-fix/merge/release, chuẩn toàn department và verifier tổng quát. Task high/critical chỉ thử khi có domain owner và cơ chế kiểm chứng hiện có.

**Artifact đầu tiên là “hồ sơ kiểm chứng và hành động tiếp theo” cho một task.** Dùng mẫu sau ngay, chưa cần parser/schema; dẫn nguồn hiện có thay vì chép toàn bộ spec.

```markdown
# Hồ sơ kiểm chứng: <task / PR>
Snapshot: <base/head revision hoặc snapshot ID>; requirement: <link/version>
Người chuẩn bị: <...>; reviewer/owner quyết định: <...>
Mục tiêu: <behavior và constraint quan trọng>
Risk: <impact, phạm vi ảnh hưởng, reversibility, lý do>; checks cần thêm: <...>

| AC/constraint | Nguồn và expected behavior | Evidence + revision | Trạng thái | Gap / hành động / owner |
|---|---|---|---|---|
| AC-01 | ... | ... | verified/failed/unverified/not_applicable | ... |

Finding: <ID, category, impact, source/reproduction, candidate/confirmed/disputed/rejected>
Giới hạn: <context/environment chưa kiểm tra, ambiguity còn mở>
Đề nghị: <clarify / bổ sung evidence / sửa code / tiếp tục quy trình review>
Quyết định của người có thẩm quyền: <pending hoặc quyết định + lý do + thời điểm>
Effort: <chuẩn bị, checks, đọc/triage; phút thực tế hoặc unknown>
```

Ví dụ minh họa, chưa phải pilot evidence: requirement nói đổi filter phải reset pagination; suite pass ở head hiện tại nhưng chỉ có test “filter cập nhật danh sách”. AC reset pagination là `unverified`; hành động là kiểm tra đổi filter từ page 3. Chỉ khi quan sát behavior sai mới kết luận `failed`. Nếu requirement không nói reset pagination thì hỏi owner, không tự biến sở thích của verifier thành defect.

Acceptance sớm: reviewer truy được claim quan trọng tới nguồn, xác định được hành động/owner và phân biệt thiếu evidence với behavior sai. Không có nguồn thật thì dùng example gắn nhãn synthetic để kiểm tra logic/cấu trúc; chưa coi là validation với người dùng.

## 6. Semantics cốt lõi cần giữ dù chưa có tool

- Criterion có nguồn, version và ý nghĩa kiểm tra được; AC suy ra từ requirement được đánh dấu, owner xác nhận khi mơ hồ. Bao gồm constraint quan trọng, không chỉ happy path.
- `verified`: evidence phù hợp behavior và snapshot; `failed`: evidence cho thấy không đáp ứng; `unverified`: thiếu/không đủ/mâu thuẫn evidence hoặc chưa rõ expected behavior; `not_applicable`: có lý do và người chịu trách nhiệm. Suite pass hoặc mapping tự khai báo không tự chứng minh criterion.
- Evidence ghi nguồn, revision/snapshot, check và kết quả thực tế. Phân biệt pass/fail/error/skipped. Evidence cũ/revision không rõ có thể làm context nhưng chưa đủ verify current head.
- Finding phân biệt defect, requirement ambiguity, verification gap và process observation; có rationale/evidence, impact, nguồn phát hiện, trạng thái adjudication. Không ép mọi finding có code line. Duplicate không tính thành nhiều vấn đề.
- Risk của thay đổi khác severity của finding. Bắt đầu với impact/blast radius/reversibility và check cần thiết; chỉ thêm taxonomy nhiều cấp nếu giúp chọn hành động. Chính sách team hiện có là đầu vào, chưa tự thay chuẩn.
- Người chuẩn bị hồ sơ không tự cấp quyền approval. Verification và quyết định review/merge/release được ghi riêng. Evidence đủ cho plan đã chọn vẫn có giới hạn; không có finding không chứng minh không có defect.
- Requirement, diff, log và output model là dữ liệu; tool nếu có không thực thi instructions trong đó. Dữ liệu thật theo quyền truy cập/chính sách hiện có; repo dùng example đã làm sạch hoặc references phù hợp.

## 7. Sequence, deliverables và stage gates trong hai tuần

Giả định để lập lịch: một TL triển khai chính, developer cung cấp task và reviewer/domain owner dành các phiên ngắn; đây chưa phải nguồn lực đã cam kết. Budget khởi đầu đề xuất tối đa 10 ngày công TL. Ngày 1 ghi budget reviewer và overhead/task trước đánh giá, theo quy mô task; thu hẹp scope nếu nguồn lực ít hơn.

| Bước / thời điểm | Việc làm và deliverable | Gate, acceptance và fallback |
|---|---|---|
| S0 — Ngày 1 | `docs/PILOT-BRIEF.md`: người dùng, quyết định cần cải thiện, họ task, inventory evidence, reviewer, budget. Xem 1–2 case có sẵn, ghi bottleneck và giả thuyết cạnh tranh | **G0: thử ở đâu?** Có case truy được nguồn và người đánh giá. Nếu thiếu, vẫn tạo mẫu/synthetic walkthrough; ghi phần truy cập cần hỗ trợ. Không kéo dài khảo sát quá timebox |
| S1 — Ngày 1–2 | `templates/quality-record.md`, `docs/CORE-FRAMEWORK.md`, một hồ sơ điền đủ. Walkthrough với reviewer nếu có; ghi điều họ đã biết, điều mới và hành động thay đổi | **G1: giúp quyết định gì?** Reviewer truy được claim, hiểu status, nêu được hành động hoặc lý do không cần thêm. Có nhu cầu/bottleneck cụ thể. Nếu chưa rõ, sửa mẫu một vòng; giữ prototype thủ công |
| S2 — Ngày 3 | Chọn một H1–H5 và một can thiệp; ghi decision log, bỏ trường dư, chốt protocol đo, task selection, budget và version | **G2: đầu tư gì?** Mỗi phần định xây có input, người dùng output, tiêu chí pass/fail. Chọn build/reuse/manual cùng tradeoff. Chưa có evidence cho automation thì tiếp tục template/protocol và targeted check |
| S3 — Ngày 4–5 | Prototype can thiệp: clarification workflow, test pattern, hồ sơ/helper hoặc focused review. Example đủ/thiếu/sai evidence. Có code thì ADR stack và một luồng end-to-end | **G3: feasibility.** Chạy được từ artifact tới hành động trên một case; thiếu evidence không thành pass; có hướng dẫn lặp lại. Synthetic chỉ qua gate kỹ thuật |
| S4 — Ngày 6–8 | Tại đây thử bản đóng băng trên synthetic cases, thêm case chưa dùng thiết kế. Pilot 3–5 task thật chỉ do người dùng thực hiện riêng trong môi trường bảo mật | **G4:** mock chỉ xác nhận behavior của mẫu. Usability/giá trị/overhead thật vẫn chưa xác minh nếu chưa có thử nghiệm riêng phù hợp; không đổi nhãn synthetic thành live pilot |
| S5 — Ngày 9–10 | `pilot/results.md`, core/template đã chỉnh, demo và `docs/MANAGEMENT-PROPOSAL.md`. Rerun sau sửa có version mới, tách khỏi đánh giá bản đóng băng | **G5: quyết định.** Tiếp tục có giới hạn / đổi / dừng. Claim dẫn về evidence, limitation, next step, owner và effort. Proposal hoàn thành dù chưa đủ evidence xin mở rộng |

Đây là điều kiện vận hành kiểm soát đầu tư, không phải ngưỡng thống kê. Không chờ “validate toàn bộ vấn đề” mới viết prototype; không dùng việc prototype chạy được thay cho usability/effectiveness.

Nếu hết ngày 2 chưa có task/reviewer, ưu tiên core, synthetic walkthrough và proposal xin tiếp cận pilot cụ thể. Nếu ngày 5 prototype chưa hoàn chỉnh, bỏ automation để hoàn thành luồng thủ công. Không có case đánh giá mới thì gọi kết quả là exploratory case study, kiểm tra case mới ở vòng sau. Không bù thiếu evidence bằng thêm tính năng.

## 8. Chọn prototype và kiểm chứng kỹ thuật

| Quan sát | Prototype phù hợp | Tradeoff / giới hạn |
|---|---|---|
| Hiểu nhầm expected behavior | Clarification template + examples + owner confirmation | Cần cải thiện bàn giao; report sau implementation ít giải quyết nguyên nhân |
| Thiếu kiểm tra behavior cụ thể | Một test pattern/check trong stack hiện có | Giá trị trực tiếp nhưng chưa khái quát xuyên domain; chưa cần engine |
| Tốn công tìm/ghép evidence | PR template hoặc helper kiểm tra reference/revision và tổng hợp | Automation chỉ đáng làm khi giảm effort vượt phần chuẩn bị input |
| Review bỏ sót từ context đã đủ | Focused review protocol; AI adapter là thử nghiệm riêng | False positives/lỗi tương quan; cần adjudication, đo giá trị tăng thêm |

Nếu chọn helper có code, MVP nhận artifact đã xuất, kiểm tra input/reference/revision và tạo report dễ đọc. Quy tắc evidence chạy offline, không phụ thuộc provider. Chưa làm generic policy engine hoặc nhiều adapters. JSON/schema thêm khi cần trao đổi máy đọc và input ổn định; contract ban đầu là semantics ở mục 6.

Kiểm chứng helper tập trung tránh kết luận sai: input thiếu, evidence cũ/sai revision, fail/error/skipped, AC mơ hồ, reference không tồn tại, duplicate và report không khớp dữ liệu. Fixture hợp lệ và fixture có gap phải cho kết quả giải thích được. Test logic quyết định và luồng end-to-end cần thiết; không lấy số lượng test làm mục tiêu.

Nếu thử AI review: dùng provider được phép, requirement gốc, actual diff, source context và test evidence trong context riêng. Output là candidate; lưu model/prompt version và context đã dùng. Provider lỗi/context thiếu/reference bịa được báo rõ. Model khác không tự tạo độc lập; kết luận implementer không là ground truth. Chưa có provider phù hợp thì human review vẫn dùng được protocol.

## 9. Đánh giá: feasibility, usability, effectiveness

| Câu hỏi | Evidence phù hợp | Kết luận được phép |
|---|---|---|
| **Feasibility:** lấy/đối chiếu artifact đáng tin được không? | Walkthrough, fixture, end-to-end, provenance/revision | Thực hiện được trong điều kiện đã thử |
| **Usability:** người khác hiểu và dùng được không? | Reviewer truy claim, chọn hành động; ghi mọi hỗ trợ tác giả phải cung cấp | Dùng được với người/loại task đã quan sát, nêu phần cần hướng dẫn |
| **Effectiveness:** cải thiện quyết định/kết quả so với hiện tại với effort phù hợp không? | Baseline trước treatment, adjudication, action/effort; pilot tiến cứu cho rework/defect | Tín hiệu giá trị tại task; kết luận rộng hơn cần thiết kế/mẫu phù hợp |

### Protocol cho vòng đầu

1. Đăng ký tiêu chí chọn: một họ task, độ lớn/phạm vi tương đương, tình trạng AI hỗ trợ nếu biết. Lưu task được xét nhưng loại và lý do. Mẫu có chủ đích không đại diện department, cũng chưa chứng minh lỗi do AI gây ra.
2. Dùng 1–2 case thiết kế; dành case mới cho bản đóng băng. Mục tiêu 3–5 task thật là mức khả thi, không phải sample size có statistical power. Báo số task mỗi nhóm, không tính synthetic vào task thực tế.
3. Historical task giữ requirement/diff/evidence tại thời điểm review; tách known defects/comments khỏi người chạy treatment khi khả thi. Công bố nếu đã biết đáp án. Requirement sửa về sau chưa từng tồn tại ở baseline thì không được dùng để kết luận baseline bỏ sót.
4. Task đang làm: ghi finding/quyết định của review hiện tại trước khi mở hồ sơ bổ sung, sau đó ghi điều thay đổi. Đây là so sánh bổ sung trên cùng task, vẫn có bias do thêm thời gian/chú ý. Không trì hoãn sửa issue thật để giữ thiết kế thử nghiệm.
5. Adjudicator có domain knowledge đối chiếu evidence, ghi confirmed/rejected/duplicate/disputed và rationale; che nguồn finding khi khả thi. Nếu không có reviewer độc lập, ghi limitation. Chưa adjudicate không đồng nghĩa false positive.
6. Mọi extra check, test mới, clarification/review sâu ghi riêng effort và contribution. Claim AI/helper tốt hơn manual review cần comparator cùng budget ở vòng sau; không thử mọi biến thể trên mẫu nhỏ.

### Số liệu tối thiểu

| Số liệu | Cách ghi và ý nghĩa |
|---|---|
| Quyết định/hành động thay đổi | Trước/sau, lý do, owner, có thực hiện không; phân biệt thông tin mới với trình bày lại điều đã biết |
| Useful findings / actionable gaps | Unique issue được xác nhận mà baseline chưa nêu; gap ghi riêng, hữu ích khi dẫn tới hành động/quyết định cụ thể |
| Finding validity | Confirmed / (confirmed + rejected) trên unique candidates có verdict; báo duplicate/disputed/pending riêng. Không phải recall |
| Trạng thái criterion | Số verified/failed/unverified/N/A với evidence; coverage không là pass rate hay bằng chứng quality tăng |
| Misses quan sát được | Issue domain reviewer xác nhận nhưng treatment bỏ sót, kèm impact. Thiếu ground truth thì không gọi là miss rate toàn hệ thống |
| Effort/cost | Phút chuẩn bị, thu evidence, review/triage, test/clarification; runtime/model cost nếu có. Tách setup với effort/task; missing là unknown |
| Kết quả sau hành động | Test được thêm, ambiguity được chốt, code được sửa; rework/escaped defect chỉ đo khi có thời gian quan sát và baseline phù hợp |

Mẫu số 0 là N/A; báo theo task/số đếm trước tỷ lệ. Không quy đổi defect “có thể đã xảy ra” thành tiền tiết kiệm. Hồ sơ evidence tốt hơn có thể hữu ích nhưng chưa đồng nghĩa phần mềm ít lỗi hơn.

## 10. Điều kiện tiếp tục, đổi hướng hoặc dừng

Trước đánh giá, TL/reviewer ghi trong pilot brief effort/task, tổng thời gian triage chấp nhận được và loại improvement đáng giá. Đây là budget vận hành có owner, không phải benchmark ngành. Chưa chốt budget thì báo mô tả, không tự tuyên bố overhead chấp nhận được.

- **Tiếp tục pilot giới hạn:** feasibility/usability đạt ở phạm vi đã thử; có hành động/decisional benefit cụ thể ngoài baseline; effort trong budget; issue nghiêm trọng bỏ sót đã phân tích; có owner muốn dùng tiếp. Một useful finding có thể đủ để thử tiếp, chưa đủ chuẩn hóa/rollout.
- **Đổi can thiệp:** gap chủ yếu ở requirement, test environment hoặc domain knowledge; ưu tiên sửa bottleneck đó. Giữ core hữu ích, bỏ phần không tạo giá trị. Artifact hiện có đã giải quyết tốt thì tái dùng/cải thiện chúng.
- **Dừng automation hoặc initiative hiện tại:** output chủ yếu lặp CI/review, không đổi hành động, nhập liệu quá nhiều, overhead vượt budget sau một vòng giản lược hoặc không có người dùng tiếp. Không lấy việc thiếu dữ liệu làm bằng chứng framework không hiệu quả; đó là giới hạn triển khai hoặc lý do chưa đầu tư.
- **Chưa đủ evidence:** hoàn thành proposal ghi phần demo đã chứng minh, điều chưa biết và thử nghiệm tiếp theo có owner/timebox/quyết định cụ thể. Không kéo dài discovery vô hạn.

## 11. Deliverables trong repo và acceptance cuối vòng

Các đường dẫn sau là cấu trúc đích; template và bộ mẫu mock đã có, các deliverable còn lại chưa tồn tại nếu chưa được tạo ở bước tương ứng:

```text
docs/CORE-FRAMEWORK.md           # mục đích, semantics, protocol ngắn và giới hạn
docs/PILOT-BRIEF.md              # task, giả thuyết, baseline, budget, owner, protocol
docs/DECISION-LOG.md             # chọn/loại can thiệp; tool/stack nếu cần
docs/MANAGEMENT-PROPOSAL.md      # evidence và yêu cầu đầu tư tiếp theo
templates/quality-record.md
examples/                       # walkthrough làm sạch; synthetic được gắn nhãn
pilot/task-register.md
pilot/adjudication-log.md
pilot/results.md
# src/, schemas/, tests/, CI chỉ thêm theo prototype thực sự chọn
```

Core v0 hoàn thành khi người khác có hướng dẫn đi từ requirement/evidence tới hồ sơ kiểm tra được, status đúng nghĩa và next action rõ. Prototype hoàn thành khi can thiệp chạy hết luồng trên một case và limitation được ghi; có thể là quy trình với template/checks, chưa bắt buộc thành software package. Pilot report phải tách case thiết kế/đánh giá/synthetic, công bố cả kết quả/effort bất lợi, truy claim về case.

Proposal nêu vấn đề quan sát được; can thiệp đã thử; điều hoạt động/chưa biết; lựa chọn tiếp tục/đổi/dừng; nguồn lực và owner. Cấu trúc request vòng sau: một team tự nguyện, một họ task, tối đa bốn tuần, budget TL và số phiên reviewer bằng con số dựa vòng đầu, checkpoint giữa kỳ và điều kiện dừng. Chưa có sponsor thì đây là yêu cầu đề xuất, chưa phải phê duyệt.

## 12. Sau hai tuần và việc có thể bắt đầu ngay

Nếu có tín hiệu, pilot tiến cứu tiếp theo kiểm tra case mới và effort đầy đủ. Chốt outcome, baseline, thời gian quan sát và comparator; chọn sample size theo lưu lượng task và claim, không mặc định 30 ngày đủ chứng minh giảm defect. Sau đó thử mapping ở workflow thứ hai. Tích hợp sâu khi input ổn định và nhập liệu đã là bottleneck được đo. Chưa cam kết rollout 30–60–90 ngày theo lịch cố định.

**Bắt đầu ngay mà chưa cần stack sản phẩm:** dùng template và 5 mock đã có để walkthrough pass/fail/unknown, tạo pilot brief với ô chưa biết và inventory synthetic cases. Chọn một decision moment và một bottleneck giả lập sau walkthrough. Đây là đầu việc cụ thể để dùng thử; bottleneck của task thật vẫn cần xác thực riêng trong môi trường bảo mật.

Thông tin cần lấy ở S0–S2: team/task tiếp cận được, reviewer/domain owner, artifact/revision xuất được, budget effort, can thiệp đã có trong workflow, chính sách dữ liệu/provider nếu thử AI. Các điểm này chặn nhánh pilot/tích hợp tương ứng, không chặn core v0/example.
