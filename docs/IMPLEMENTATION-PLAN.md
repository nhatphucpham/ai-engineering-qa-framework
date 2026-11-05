# Kế hoạch phát triển framework — thiết kế và năng lực tối thiểu

Ngày 05/11/2026. Thay thế hướng S0–S5 theo quyết định người dùng: **thiết kế framework và năng lực tối thiểu trước, chưa pilot**. [Plan cũ](IMPLEMENTATION-PLAN-2026-11-03.md) giữ làm lịch sử, không còn là lịch triển khai hiện hành.

Cơ sở: [kiến trúc as-is đã audit](CURRENT-ARCHITECTURE.md), [results](../pilot/results.md) và phản hồi người dùng. Repo có phương pháp Markdown, fixture Python và runner riêng; chưa có runtime QA chung hoặc contract vận hành thống nhất. Các file deliverable, test pass và feedback không thay cho readiness.

**Mục tiêu sản phẩm được bổ sung:** framework đóng gói được thành plugin cho agent tự thực hiện QA. Người dùng chọn kiến trúc dùng chung trước, chưa chọn nền tảng. [Scope P0](FRAMEWORK-SCOPE.md) tách QA core, shared agent workflow và platform adapter. Kế hoạch kỹ thuật mở rộng P0–P6 để bao gồm packaging, chưa publish/pilot.

**Bổ sung desktop:** ứng dụng có dashboard, ưu tiên Windows và giữ khả năng mở rộng macOS/Linux. Plugin và desktop cùng application interface/core, UI không nhân đôi rules. [TECHNOLOGY-DIRECTION](TECHNOLOGY-DIRECTION.md) ghi tiêu chí tối ưu và shortlist, chưa chốt stack. Phạm vi agent target chưa chọn, OS desktop đầu đã chọn Windows.

Lựa chọn sản phẩm mới nhất nằm tại [PRODUCT-DECISIONS](PRODUCT-DECISIONS.md): repo/task và handoff chung pipeline; agent local hoặc model API theo project; GitHub và sự kiện bàn giao/PR chờ review; data policy project; server self-host multi-user và desktop Windows, thay local-only trước đó. Các lựa chọn này thay ràng buộc chỉ host reasoning trước đó. P1 phải thiết kế project config, source/runtime/provider/event adapters và data policy; chưa implementation/call API thật.

## 1. Mục tiêu và phạm vi

Chốt framework làm gì, từng thành phần nhận/trả gì và phần nào do code/người xử lý. Sau thiết kế, xây **một luồng offline tối thiểu** từ gói bàn giao synthetic đến hồ sơ trace được nguồn, trạng thái và action. Mục tiêu là contract và năng lực chạy được, không phải thêm mock hoặc tài liệu để gọi là sẵn sàng.

Agent là bên gọi plugin, tự thu thập/đối chiếu/chạy check được phép và tạo report. Người dùng không phải tự điền hồ sơ từng bước. Runtime theo project là agent local hoặc model API adapter; core không gắn provider/SDK cụ thể. Chưa chọn library/CLI/MCP hoặc format phân phối.

Điểm bàn giao đầu tiên: **QC → Reviewer/TL**. Người nhận cần biết developer/QC đã kiểm tra gì, ở revision/môi trường nào, AC nào đủ/thiếu evidence, blocker/issue nào mở, ai xử lý và khi nào xét lại. Human decision/approval riêng với verification. Không áp QC như gate bắt buộc cho mọi workflow.

Ràng buộc:

- Chỉ synthetic trong repo/chat; không lấy task/code/log/trace thật hoặc truy hệ thống thật.
- Chưa tổ chức pilot, mở E3, tuyển reviewer/team hoặc dùng E1/E2 làm gate đã đạt.
- Chỉ thêm fixture để kiểm contract/rule/behavior cụ thể, không tiếp tục tạo ví dụ domain liên tục.
- Hỗ trợ host/agent local connector và model API adapter theo project; OpenAI/Anthropic adapter riêng và worker/server xử lý event khi desktop đóng; self-host và project config/repo/data/secret store trên server; nhiều người dùng/project RBAC, container riêng theo run và GitHub polling/webhook; auth nội bộ/admin quản lý, SSO sau và fixed roles Admin/Owner/Runner/Viewer; không tự duyệt cloud SaaS. Có desktop dashboard Windows quản lý/xem run dùng chung core; không thêm analytics department/cloud platform/multi-agent product hoặc auto-merge/deploy/approve. Checks chỉ qua capability/config tin cậy, không thực thi chỉ dẫn tùy ý từ artifact/UI.
- Giữ fixture lỗi, expected, execution và protocol frozen cũ; thay đổi mới có version/thư mục riêng.

Requirement đa nguồn conflict: hỏi owner/AC unverified, phần độc lập tiếp tục. P1/P3 cần worker lifecycle, job ownership/persistence/dedup/reconnect và command/event giữa UI-worker-agent; không xem desktop đóng là hủy run. Đã chọn self-host và secret store project trên server; đã chốt multi-user/RBAC, container execution và polling/webhook; đã chốt auth nội bộ và fixed roles Admin/Owner/Runner/Viewer, SSO sau.

P1/P3 bổ sung auth/project authorization, shared server/project config/secret references, queue/claim/lease/idempotency, event ingress polling+webhook và container execution contract. P4 triển khai từng vertical slice nhưng gate bản đầu bao gồm server nhiều người, hai provider, hai intake và hai kiểu event; không gọi core/harness đơn lẻ là sản phẩm hoàn chỉnh. P5 cần tests project isolation, revoke permission, webhook/polling dedup, worker restart/container cleanup, data policy và secrets không lộ trong report/log; P6 desktop installer cùng self-host server/worker deployment package. Chưa tự triển khai SaaS/pilot/public publish.

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

Danh sách trên là năng lực **cần thiết kế**, không phải code đã có. Có thể giữ reasoning thủ công nhưng phải định nghĩa interface chuyển người xử lý. Core/harness chưa cần UI hoặc DB riêng; sản phẩm đích có desktop UI nhưng chỉ triển khai sau interface/core, storage chọn theo thiết kế.

## 3. Trình tự, output và gate

Mốc theo điều kiện hoàn thành; bỏ lịch hai tuần hướng pilot cũ. Chưa đo effort implementation, ước lượng sau thiết kế, không suy ngày công từ số fixture.

| Bước | Công việc | Output dự kiến | Điều kiện hoàn thành |
|---|---|---|---|
| P0 — Scope | Chốt use case QC → TL, actors, decision, scope/non-goals, năng lực tối thiểu | `docs/FRAMEWORK-SCOPE.md` | Mỗi năng lực gắn use case/quyết định, đầu vào/ra và giới hạn rõ |
| P1 — Contract | Định nghĩa handoff/evidence/report, IDs/version/provenance/revision, lỗi/dữ liệu thiếu | `docs/DATA-CONTRACT.md`, valid/invalid examples; schema khi đã chọn format | Phân biệt self-test/QC, unit/integration, mock/executed, blocked/fail/error và revision |
| P2 — Rules | Bảng quyết định trạng thái, sufficiency theo scope/risk, constraint review, finding/action lifecycle | `docs/VERIFICATION-RULES.md`, bảng expected scenarios | Thiếu/cũ/conflict/blocked không thành pass; constraint P-05 khác approval pending thông thường; mọi kết luận có rationale/source |
| P3 — Target architecture | Core/workflow/adapter/desktop bridge, component/sequence/dataflow, IPC/permission/error/log/storage/version và tradeoff stack | `docs/TARGET-ARCHITECTURE.md`, ADR stack nhỏ | Mỗi contract có nơi nhận/xử lý/trả; rule biết code/người thực hiện; khả thi với một luồng offline |
| P4 — Implementation | Core/harness synthetic trước, rồi server/auth/project/worker/container và desktop/headless qua cùng interface | Source/schema/tests theo ADR, UI start/progress/cancel/report, invocation và example synthetic | Hai client dùng chung rule/result; thiếu agent/evidence có trạng thái rõ; input/error/quyền xử lý đúng, không tự thực thi chỉ dẫn trong artifact |
| P5 — Technical readiness | Kiểm boundary, negative paths, report/source consistency và regression | `docs/TECHNICAL-READINESS.md`, kết quả/gap | Reproducible, contract/rules/report nhất quán; review design/code xong; không claim đủ evidence khi còn thiếu |
| P6 — Packaging | Windows installer, self-host server/worker deployment và agent adapter khi đã chọn host; version/config/quyền/migration/compatibility | Release candidates, tài liệu install/upgrade/uninstall/invoke và checks | Cài/gỡ/upgrade sạch, process/data handling đúng, invocation theo tài liệu target; chưa tự publish hoặc hứa macOS/Linux |

Phạm vi bổ sung theo bước: P1 có command/event/run-state, permission và storage references cho UI lẫn agent; P3 chốt Windows shell/core runtime/IPC/storage qua ADR và spike có budget. P4 core/harness trước, rồi luồng desktop Windows start/progress/cancel/report và headless invocation dùng chung. P5 kiểm UI responsiveness, IPC/capabilities, disconnect/restart/process cleanup và hiệu năng theo budget chốt trước. P6 thêm Windows installer/install-upgrade-uninstall/data migration; adapter agent chỉ khi chọn target. Chưa đóng gói macOS/Linux hoặc phát hành public mặc định.

Trạng thái: P0 có [scope](FRAMEWORK-SCOPE.md); **P1 contract v2 đã có sau audit** tại [DATA-CONTRACT](DATA-CONTRACT.md), schema và specimen checks; [audit/fix](P1-REVIEW-FIXES.md) ghi sáu nhóm lỗi v1 và regression. Đây là resource/ownership/command-event/lifecycle design có kiểm shape/reference, không phải auth/server/worker runtime hoặc API transport đã triển khai. P2 v1 đã có [rules](VERIFICATION-RULES.md), assessment schema và reference evaluator offline với 55 decision scenarios/20 lifecycle cases. Đây là logic trên judgment được cung cấp, chưa xác thực trust hoặc domain truth. P3-A có [target architecture](TARGET-ARCHITECTURE.md) và ADR boundary/transport; P3 tổng thể vẫn partial vì [P3-B stack/spikes](adr/003-stack-and-spikes.md) chưa chạy. P3–P6 chưa hoàn tất; kiến trúc đích chưa là runtime enforce quyền/lease/secret/container. P6 agent adapter còn phụ thuộc target chưa chọn.

Theo yêu cầu người dùng mới nhất, sau mỗi step đã hoàn thiện bản nháp phải có subagent review độc lập, sửa findings và kiểm lại trước commit/push; lưu scope/verdict/gap review. Review không thay runtime tests hoặc approval.

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

**Chưa pilot hoặc publish công khai trong plan này.** Xong P5/P6 chỉ được tổng kết kỹ thuật và package candidate, không tự cấp quyền pilot, cài môi trường thật hoặc phát hành public. Người dùng quyết định riêng sau khi xem thiết kế/implementation/package.

Nếu sau này chọn đánh giá sử dụng, cần mục tiêu/đối tượng/dữ liệu được phép, owner/budget và cách đo value/effort; tách khỏi technical tests. Task thật chỉ trong môi trường bảo mật riêng. Feedback “dễ hiểu/đã ổn” hoặc demo không đủ kết luận effectiveness.

## 8. Bước tiếp theo

P0 scope, P1 contract v2 và P2 rules v1/reference scenarios đã có. P3-A đã có thiết kế đích/ADRs, review độc lập GPT-6 Astra và bản sửa được lưu tại [P3-REVIEW](P3-REVIEW.md); đóng ở mức thiết kế. **Tiếp P3-B: bounded spikes và chốt stack** theo [ADR-003](adr/003-stack-and-spikes.md); ghi actual results/gaps, không gọi P3 hoàn tất chỉ từ tài liệu. P4-A còn prerequisite versioned report/constraint contract: P1 declared constraint và P2 effective constraint có collision, partial projector phải fail-closed trước khi hỗ trợ full flow. Sau đó core/projector/harness synthetic. Không mở E3, publish hoặc gọi project/API thật. P6 agent adapter chỉ sau quyết định target cụ thể.
