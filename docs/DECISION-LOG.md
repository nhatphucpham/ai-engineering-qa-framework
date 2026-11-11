# Decision log

## D-25 — 10/11/2026: staged publication/replay contract trước storage

User yêu cầu tiếp các bước. Giữ WT-P4A-R2 đã review, chọn slice P4-A package tự chứa + typed manifest/graph và anchored replay validator. Whole raw bundle có thể chứa nhiều project/task nên envelope restricted internal replay ghi toàn contained scopes, không giả target-only export hoặc outbound permission. Caller-held input digests/IDs ngăn coherent substitution; self-consistency không là trust. Không đổi P1 v2/runtime-v1 schemas/goldens và không tự chọn DB/server. [Scope/acceptance](P4-A-PUBLICATION.md), [review](P4-A-PUBLICATION-REVIEW.md) CLEAN, slice DONE xác nhận 11/11; tiếp runtime-storage decision prerequisites/transaction adapter và scoped read/export. Không commit/push/pilot/public publish.

## D-24 — 10/11/2026: P4-A internal report/core slice, chưa publication

Theo yêu cầu tiếp P4-A, chọn slice bounded: tách implementation Python dùng chung khỏi tooling và thêm versioned internal report/completion proposal v1 giữ nguyên offline content, exact run binding và raw/effective constraint semantics. Không chọn full P1 v3 trong phiên này vì production storage/publication/export còn cần contract riêng; P1 v2 và legacy exporter giữ fail-closed, không mutate handoff hoặc AC để hợp validator. Đây là phân rã mục tiêu P4-A, không đổi hướng ADR-004 hoặc tuyên bố persistence/lifecycle runtime đã xong.

Scope/acceptance/checks/review tại [P4-A-RUNTIME-REPORT](P4-A-RUNTIME-REPORT.md) và [review](P4-A-RUNTIME-REVIEW.md). Slice DONE sau review R2 sạch, P4A-RV-01..06 closed và 38 methods pass; full P4-A partial. Không chọn server/worker/DB/shell/agent host hoặc quyền commit/push/pilot/publication.

## D-23 — 10/11/2026: S1 parity và pure-core baseline Python

Người dùng yêu cầu tiến hành S1 sau `c4149bd`. Đã dựng native TypeScript/Node candidate riêng, pinned local Node LTS/deps, không gọi Python từ candidate hoặc sửa fixture/reference để khớp. Official workload 356/356 + 28/28 CLI, ba trials mỗi runtime và source/fixture immutable; evidence tại S1-RESULTS. Reviewer high-model kiểm độc lập và dùng stable S1-RV IDs; output chưa DONE trước final verdict.

ADR-004 chọn Python làm implementation baseline cho pure shared core/report P4-A kế tiếp, dựa trên reuse semantics/versioned artifacts và không cần duy trì second rules engine/compat layer ở production. Node nhanh hơn ở workload official và tốn RSS cao hơn; không dùng performance number để suy service SLA/ROI hoặc khẳng định Python tối ưu. Đây là reversible engineering direction, không chọn server/worker/DB/shell/agent target. Tiếp versioned runtime report/constraint integration; S2–S6 và P3-B tổng thể vẫn mở, không pilot/API thật.

## D-22 — 10/11/2026: reviewer thường trực và vòng sửa đến clean

Người dùng yêu cầu luôn có một agent review output hiện tại về độ chính xác/tính thực dụng, kèm suy luận cải thiện; sửa findings rồi lặp trên bản mới đến khi không còn lỗi cũ/lặp/mới được tìm, sau đó mark done. Ghi thành quy tắc repo trong AGENTS.md và REVIEW-WORKFLOW; plan/handoff phải dùng cùng gate. Dùng ít nhất một reviewer độc lập mô hình cao, stable finding IDs, không dừng theo số vòng tùy ý hoặc lấy suite xanh thay clean verdict.

Áp dụng ngay cho output P2 v2/reference report/plan đang có, mở lại review dù phiên trước đã pass targeted checks. Record tại OUTPUT-REVIEW-LOOP. DONE chỉ cho scope output đã kiểm, không claim toàn sản phẩm hoàn tất hoặc quyền publish/commit/push. Reviewer hiện tại Astra high; root xử lý fixes và kiểm chứng rồi gửi bản mới để đóng findings, không tự đóng chỉ từ lời tác giả.

## D-21 — 10/11/2026: rules v2 sau independent audit

Review GPT-6 Astra high tìm hai lỗi trong P2 v1; root đã replay bằng synthetic copies trong memory. (1) Scenario source-proof đổi requiredLevels và evidence.level sang integration vẫn được v1 đánh verified/complete dù provenance chỉ source_reasoning, không có execution. (2) Có clear violation và comparable conflict cùng lúc thì v1 giữ failed/open coverage nhưng thiếu reason EVIDENCE_CONFLICT.

Sửa bằng assessment/rules v2 explicit, không đổi nghĩa v1 hoặc sửa corpus lịch sử: source_reasoning chỉ tính source_review cho positive/open coverage; source counterexample vẫn có thể chứng minh violation có nguồn. Conflict reason độc lập với status precedence. Shape migration chỉ đổi version fields, không tự nâng authority/trust hoặc chấp nhận domain judgment. Reference report mới chỉ nhận v2; v1 chỉ để replay lịch sử có known limitations, không làm oracle corrected flow. Kiểm tra/review kết quả tại P2-V2-REVIEW và P4-A-REFERENCE-REVIEW; chưa coi bản sửa có tests là production readiness.

## D-20 — 10/11/2026: hoàn thiện reference report trước parity spike

Nền `9237018`. Người dùng yêu cầu tiếp tục chỗ dừng, dùng subagent mô hình cao kiểm tra/cải thiện phần đã làm và làm rõ mục đích plan. Kiểm tra ban đầu thấy P3-A design đã đóng, P3-B chưa có results; P1/P2 có regression tooling nhưng còn declared/effective constraint collision khi nối report.

Ưu tiên prerequisite P4-A: report offline có version riêng, tách declared/effective constraints, giữ references/reasons/limitations và bindings về immutable input; dùng làm oracle cho S1 cross-runtime parity. Sau audit D-21, report mới dùng P2 v2, giữ v1 để replay lịch sử. Python chỉ là reference tooling hiện có, không chốt runtime/stack đích. Không mutate frozen handoff/P1 v2/P2 corpus hoặc nâng verification để hợp schema. Output riêng không tự là P1 report/persistence: collision export v2 vẫn fail-closed, không report_ready/completed. Runtime integration cần versioned contract/schema/graph tests tiếp theo.

Đổi thứ tự vì cần oracle không mất semantics trước so parity và có thể hoàn thành bằng tooling hiện có, không cần DB/engine/native shell. Giữ P3-B mở và kiểm từng boundary bằng spike actual; không dùng unit tests để đóng DB/container/native/provider gate. Plan thêm mục đích người dùng, trạng thái thực, phụ thuộc/acceptance theo slice và phân biệt reference/prototype/product/package. Review độc lập mô hình cao và kết quả thực chạy lưu tại record phiên, không ghi trước verdict. Chưa pilot, account/API/project thật, commit/push hoặc public publish.

## D-19 — 05/11/2026: kiến trúc P3-A và review sau mỗi step

Nền `337ab82`. Người dùng yêu cầu tiếp như cũ và sau mỗi step dùng subagent kiểm tra lại. Áp dụng cho các step tiếp theo: independent review, sửa findings, kiểm lại trước commit/push; không chỉ tự review rồi gọi độc lập.

Thiết kế P3-A đặt pure core/projector, trusted assessment acceptance, modular control service và worker/container boundary; API HTTPS JSON/SSE, auth/service identities, transactional metadata/outbox + immutable blobs. Không chấp nhận accepted/authorized từ model/client. Local connector chỉ enable khi enforce được project outbound policy; event chưa resolve common occurrence/exact revision không tạo run phỏng đoán.

Tách P3-B spike/chốt stack để không giả đo tối ưu hoặc runtime khả thi: Node/PostgreSQL/Tauri/rootless Linux là candidates, chưa chốt/benchmark; P3 vẫn partial. Không đổi P1/P2/fixture/evidence; chưa model/account/container/pilot/publish. Review scope/findings/results được lưu P3-REVIEW, handoff ghi việc tiếp.

## D-18 — 05/11/2026: P2 rules và conditional assessment offline

Nền `2463cc0`. Tiếp plan thiết kế trước: thêm rules v1, assessment sidecar schema, coverage obligations/comparison contexts có nguồn, eligibility và precedence, constraint review, finding/action transition predicates. Không đổi P1 v2 hoặc fixture/evidence cũ. Python chỉ reference tooling, chưa chốt stack sản phẩm.

55 decision scenarios và 20 lifecycle cases kiểm logic trên supplied facts; accepted/integrity/authorization không phải trust thực đã được xác minh. Không lấy record-only để cấp behavior gate; humanDecision luôn pending. P3 phải thiết kế trusted assessment boundary và mapping assessment sang P1 report, auth/proof/audit cùng server/worker/desktop. Không model/API/container/pilot hoặc publish.

## D-17 — 05/11/2026: sửa audit P1 bằng contract v2

Người dùng yêu cầu sửa sáu nhóm finding sau review GPT-6 Astra high. Version hóa thành 2.0.0 vì thêm task identity/task-scoped source-diff, decisive/context evidence và rerun lineage; active validator từ chối v1, giữ nguyên schema/JSON v1. Khép source/evidence revision contradiction cho conclusive status, assessment provenance, exact-run progress, unique accepted event→run, assignee done và duplicate cycle; thêm report_ready exactly-one ID sau vòng review tiếp.

9 positive bundles, 58 negative scenarios, CLI và legacy rejection pass. Subagent high-model replay độc lập và rà docs/code lần cuối, xác nhận có thể đóng gate sửa P1 trong phạm vi offline contract/self-consistency. Trace tại P1-REVIEW-FIXES. Không claim P2 sufficiency hoặc runtime enforcement đã xong. Tiếp P2 bằng v2, không dùng v1 chưa vá làm nền.

## D-16 — 05/11/2026: P1 contract v1 và kiểm specimen offline

Nền `e87e15b`. Chọn JSON Schema Draft 2020-12 cho resource shapes, không chốt product runtime. DATA-CONTRACT mô tả handoff/evidence/project/config, fixed-role permission matrix, idempotency/event identity, commands/progress, run lifecycle và worker fencing. Schema/3 valid bundles/39 negative mutation scenarios được kiểm bằng jsonschema 4.26.0 và CLI; tool P1 chỉ shape/reference/self-consistency, không là QA engine/security enforcement.

Tách run completed khỏi verification complete và approval. Khi có source conflict thì unverified; stale evidence được giữ context nhưng không cite như verified candidate. Worker-result match attempt/token/version được kiểm theo snapshot, chưa có atomic claim/expiry/auth code. Runner cancel chỉ run của mình, Owner/Admin theo quyền project; initiator phải do server gắn. Examples chứa dummy references/budget/timestamp, không là execution hay permission thật. P2 tiếp bảng sufficiency/status; P3/P4 mới bindings/transport/enforcement.

## D-15 — 05/11/2026: chốt topology, execution và identity

Người dùng chọn self-host worker/server trên máy/server của mình/team, cấu hình quyền repo/data scope/secrets theo project trên server, chạy khi desktop đóng. Bản đầu multi-user với tài khoản nội bộ admin quản lý, thêm SSO sau; fixed roles System Admin/Project Owner/Runner/Viewer. Tests trong container project/run theo config môi trường project; GitHub polling+webhook cùng có ở bản đầu. Lựa chọn mới thay local-only/no-server-RBAC trước đó; không tự thành SaaS do sản phẩm vận hành.

P1/P3 phải có server/UI/worker identity/permissions, job lifecycle, container boundary, data/secret policy và adapters. Chưa chọn stack/API/SDK versions, chưa triển khai dịch vụ hay gọi credentials thật. PRODUCT-DECISIONS lưu lựa chọn thống nhất; tiếp contract thay vì tiếp hỏi lại các lựa chọn đã trả lời.

## D-14 — 05/11/2026: ghi yêu cầu nền từ câu hỏi sản phẩm

Lưu lựa chọn tại PRODUCT-DECISIONS: hai intake, hai chế độ runtime/project, phạm vi QA/can thiệp read-check-report-only, GitHub trigger bàn giao/PR chờ review, data scope project, requirement conflict chờ owner, OpenAI/Anthropic adapter riêng. Desktop theo dõi worker/server chạy cả khi đóng app; topology/data-secrets còn chờ trả lời. Thay các giới hạn chỉ host model/local process cũ, chưa chọn công nghệ hoặc triển khai. Không suy lựa chọn chức năng thành quyền dùng account/key/project thật.

## D-13 — 05/11/2026: thêm desktop dashboard Windows dùng chung core

Người dùng muốn plugin hoặc desktop dashboard, desktop càng tốt; chọn Windows trước và mở rộng macOS/Linux sau. Scope thêm desktop client/bridge, application command/event interface và local run/history; không thêm bộ rules riêng. Agent target vẫn chưa chọn.

Tra tài liệu chính thức Tauri/Electron/SQLite để ghi shortlist/tradeoff tại TECHNOLOGY-DIRECTION, chưa chốt stack hoặc claim tối ưu. P1/P3 bổ sung IPC/capability/run-state/storage/agent connector; P4 core trước rồi desktop/headless flow; P5 checks/benchmark có budget; P6 Windows installer/adapter target đã chọn. Không dựng UI demo tách core, không pilot/publish hoặc giả định app tự có model khi chưa có connector.

## D-12 — 05/11/2026: mục tiêu plugin tự động cho agent, chưa chọn nền tảng

Người dùng muốn framework có thể publish thành plugin cho các agent tự thực hiện QA; chọn chốt kiến trúc dùng chung trước, chưa chọn target. Tạo P0 FRAMEWORK-SCOPE: agent là consumer/caller, core/workflow/adapter tách biệt, checks theo quyền host, inference có nguồn và human decision riêng. Không còn coi người điền Markdown là luồng sản phẩm chính.

Plan thêm P6 packaging sau khi chọn target; P1/P2/P3 cần capability, reasoning và execution interfaces. Chưa chọn SDK/runtime/transport/distribution, không tự tuyên bố hỗ trợ Codex/Claude/MCP hoặc publish package. Giữ hướng chưa pilot và bảo toàn as-is/fixture/evidence cũ. Tiếp P1 DATA-CONTRACT cho handoff/evidence/report và host capabilities.

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
