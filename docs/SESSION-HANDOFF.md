# Bàn giao phiên — mới nhất ở đầu

## Commit local theo yêu cầu người dùng — 11/11/2026

Đã tạo implementation commit **`e56ed7db579830f0252968215a1c2bdbae791e47`**: `feat: add shared QA core and staged report publication`, đủ 45 files đã review. Git blob manifest 33 implementation paths là `34222735b29d8450e93742cced92dc7a66536566526c5acf014d5ea0b99c2878`; working-file manifest lịch sử vẫn `325c39...`. Đã kiểm 22 files khác byte chỉ do CRLF→LF; normalized contents của toàn bộ 33 files giống nhau. Commit tài liệu bổ sung chỉ ghi nhận snapshot/normalization, không đổi implementation. Chưa push.

User yêu cầu commit toàn output đã review trong session. Commit chứa entry này lưu shared Python core, runtime/prepared report, staged publication/replay package, schemas/goldens/tests và docs/plan bàn giao. Baseline trước commit là master `d8bf175`; đọc Git log/status thực để lấy hash snapshot mới và mọi thay đổi còn lại. Brief [NEXT-SESSION](NEXT-SESSION.md) đã đổi từ trạng thái uncommitted sang cách nhận diện commit snapshot; các entries chưa commit bên dưới là lịch sử tại lúc ghi. Không suy remote đã nhận snapshot: user chỉ yêu cầu commit local, chưa push.

## Chuẩn bị chuyển session — 11/11/2026, master `d8bf175` + working tree P4-A

Theo yêu cầu bàn giao tiến độ/việc tiếp/cách làm một session, viết lại [NEXT-SESSION](NEXT-SESSION.md) và thêm [SESSION-PLAN](SESSION-PLAN.md). Brief cũ trước extraction đã thay; lịch sử giữ ở entries bên dưới. **Bàn giao DONE sau clean review HS-R1**, không có finding mới; links/fences/whitespace/diff PASS, implementation manifest 33 paths không đổi. [SESSION-TRANSFER-REVIEW](SESSION-TRANSFER-REVIEW.md) lưu verdict/evidence; không dùng DONE docs đóng implementation gate.

Hai slice core/runtime và staged publication/replay DONE, latest WT-PUB-R2 CLEAN/45 methods pass; full P4-A partial. Code P4-A vẫn có tracked/untracked changes chưa commit/push; session mới giữ checkout hoặc chuyển đủ snapshot, không chỉ checkout HEAD. Đề xuất phiên tiếp: S2-A prerequisite inventory + actual disposable DB transaction/queue spike nếu READY; NOT READY thì preparation độc lập với DB checks NOT RUN. Chưa thực thi S2-A, chọn production DB/runtime, cài toolchain hoặc tạo chat. Plan giữ high-model review → fix → checks → re-review đến clean, stable IDs và DONE đúng scope.

## Re-review P4-A theo yêu cầu người dùng — 11/11/2026

**WT-PUB-R2 CLEAN**, reviewer mới độc lập GPT-6 Astra high kiểm lại core/runtime/publication/replay từ source/schema/acceptance, không dựa vào verdict trước. P4A-RV-01..06 giữ CLOSED, không có finding mới/tái xuất hiện; **DONE tái xác nhận cho hai slice**, full P4-A vẫn partial. Root chạy mới 45 methods pass (37.113s), reviewer chạy mới 45 methods pass (36.320s), thêm 638 deletion probes đều reject; root thêm 15 deep-JSON probes đều reject. Implementation manifest 33 paths khớp bản trước, AST legacy/frozen tracked artifacts/Markdown links/diff-check pass. Không sửa code/schema/tests/goldens, không rerun S1 hoặc regenerate evidence. [Review record](P4-A-PUBLICATION-REVIEW.md) lưu R2/verdict/giới hạn; còn storage/transaction/outbox, live auth/lease/trust và scoped read/export. Giữ working tree, chưa commit/push.

## P4-A staged publication/replay — 10/11/2026, nền `d8bf175` + WT-P4A-R2

**Slice DONE, clean review WT-PUB-R1 xác nhận 11/11/2026**. Theo yêu cầu tiếp các bước, thêm internal publication package v1 tự chứa raw bundle/assessment/prepared, canonical digest/byte-length manifest, whole-input scopes và completed-run/report/report_ready candidate graph. Anchored replay validator dùng input digests/expected IDs caller giữ độc lập; không chỉ tin manifest của gói. Application interface/harness stdout-only, ba goldens mới và regression có tamper/coherent rewrite/mixed project scopes. Xem [scope/cách chạy](P4-A-PUBLICATION.md), [checks/review](P4-A-PUBLICATION-REVIEW.md).

Giữ toàn thay đổi trước chưa commit; không sửa schema/corpus/fixtures/evidence/goldens cũ hoặc rerun S1. Full regression **45 methods pass, 33.469s**; AST compatibility, tracked frozen artifacts, Markdown links và diff whitespace pass. Reviewer độc lập xác nhận CLEAN, không có finding mới; P4A-RV-01..06 giữ CLOSED. Independent full suite 45 methods pass 33.562s (khởi chạy trước quota, nhận completion khi resume; không rerun full suite ngày 11/11), thêm 235 mutation probes bị reject. Full P4-A partial: staged package không persisted report, actual completed/report_ready/outbox hoặc authorized user export. Tiếp S2/storage-runtime decision prerequisites, transactional publication và scoped read/export policy. Chưa model/API/project thật, auth/lease enforcement, platform/distribution hoặc commit/push.

## P4-A internal report/core slice — 10/11/2026, nền `d8bf175`

**Slice DONE sau clean review WT-P4A-R2**, full P4-A partial. Tách Python shared `qa_core` khỏi CLI, giữ v1/v2/offline semantics; thêm versioned internal report + pure completion proposal bind exact run/stateVersion/attempt/raw-input digests, giữ declared/effective constraints và human decision pending. Goldens mới complete/collision/failed-pending, regression corpus và graph/lifecycle/tamper/CLI. Mục đích/acceptance/cách chạy tại [P4-A-RUNTIME-REPORT](P4-A-RUNTIME-REPORT.md), checks/findings/verdict tại [review](P4-A-RUNTIME-REVIEW.md).

Vòng review 1 phát hiện sáu lỗi P4A-RV-01..06; đã sửa trên WT-P4A-R2, reviewer độc lập xác nhận đóng cả sáu, không có finding mới/tái xuất hiện. Full regression mới **38 methods pass** (tác giả 26.018s, reviewer 24.986s); targeted 11 methods pass. Extraction giữ nguyên AST mọi non-CLI function/class; tracked schemas/corpus/fixtures/evidence/protocol cũ không đổi, links/diff whitespace pass. S1 source inventory được cập nhật để guard core vừa tách, không rerun S1 hoặc đổi official evidence. Không gọi account/API/project thật, chưa commit/push. Full P4-A partial: publication/export/storage contract, actual persisted report+completed+outbox, live auth/lease/trust còn mở. Legacy P1 v2 exporter unsupported; proposal không là P1 v2 bundle. Tiếp publication/export contract và integration prerequisites.

## Chuyển session — 10/11/2026, baseline `d35ae6b`

Người dùng yêu cầu mang tiến độ các phase và cách làm sang session mới để tiếp tục. **S1 đã DONE và đã commit/push** tại `d35ae6b337d1450f911d388adce2ee1bd0e3efd8` trên master; trạng thái “chưa commit/push” ở entry lịch sử bên dưới là tại thời điểm trước commit đó, không trạng thái hiện hành.

Đọc [NEXT-SESSION](NEXT-SESSION.md) để khởi động: file cần đọc, trạng thái P0–P6, decisions/giới hạn, mục tiêu P4-A và quy trình reviewer mô hình cao → sửa → kiểm chứng → re-review đến clean → DONE trong scope. **Tiếp P4-A versioned runtime report/constraint integration và module core Python**, không chạy lại S1 hoặc chọn lại stack toàn hệ thống. Chưa triển khai phần P4-A mới trong session bàn giao này.

**Bản bàn giao DONE:** Astra high review hai vòng, NS-RV-01 (mandatory/optional constraint và failed precedence) cùng NS-RV-02 (tracked source so với ignored runtime/dependencies) đã đóng; quyền Git chỉ trong scope đã được giao/cấp. Links/code fences của hai tài liệu và diff whitespace pass, không cần rerun code tests cho thay đổi chỉ tài liệu.

## S1 cross-runtime parity — 10/11/2026, nền `c4149bd`

Đã triển khai `spikes/s1` native TypeScript candidate (P1/P2 v1/v2/lifecycle/report + strict lossless JSON boundary), local pinned Node 26.13.0/TypeScript7.0.2/Ajv8.20.0 và `tools/run_s1.py`/oracle worker. Candidate không gọi Python hoặc đọc expected answers. `.cache/s1`/build/dependencies được ignore, không đổi runtime global hoặc fixture/reference cũ.

[Official evidence](s1-results/2026-11-10-r1.json) **PASS 356/356 + 28/28 CLI, 0 skip**, ba engine trials/runtime; hashes trước/sau 58 source/fixture files khớp. Reviewer Astra high tự rehash 58 files và chạy 26 methods pass (20.603s); root full suite 26 methods pass (19.554s). **Output S1 DONE**: [S1 review](S1-REVIEW.md) đóng S1-RV-01..09, final clean xác nhận đủ 28 payload files theo manifest và không có finding mới. Sau reset chỉ kiểm hash/docs rồi ghi trạng thái hành chính; không sửa code/evidence hoặc giả đã chạy lại benchmark/tests.

[Results](S1-RESULTS.md) ghi versions/measurements/limits; [ADR-004](adr/004-core-baseline-after-s1.md) chọn Python làm baseline pure shared core/report, TS giữ conformance spike. Node nhanh hơn trong workload này nhưng không có service SLA buộc migration, Python giữ semantics sẵn có và tránh second production rules engine/compat layer. Không chọn server/worker/DB/desktop shell từ S1.

**Việc kế tiếp: P4-A versioned runtime report/constraint integration + tách module core Python**. Legacy P1 exporter vẫn projection_unsupported, không report_ready/completed của server. S2–S6/P3-B tổng thể vẫn mở; chưa server/auth/worker/container/adapters/desktop installer, pilot hoặc model/API project thật. Chưa commit/push output S1 ở thời điểm ghi entry này.

## Review lặp bắt buộc — 10/11/2026, nền `9237018`

Yêu cầu mới: luôn chỉ định ít nhất một reviewer độc lập mô hình cao; đưa output hiện tại vào review độ chính xác/tính thực dụng và reasoning cải thiện; sửa → kiểm chứng → re-review bản mới đến vòng sạch rồi mark DONE. Đã ghi vào AGENTS.md, [REVIEW-WORKFLOW](REVIEW-WORKFLOW.md) và plan. Reviewer hiện tại Astra high, root sửa, stable finding ledger tại [OUTPUT-REVIEW-LOOP](OUTPUT-REVIEW-LOOP.md).

Mở lại review output phiên trước; reviewer tìm RV-01 JSON parser CLI không nhất quán, RV-02 action routing/doneWhen sai loại gap, RV-03 current docs stale. Vòng 2 đóng RV-01/RV-03 nhưng giữ RV-02 vì multiple blockers bị priority branches che mất. Đã refactor independent reason groups/dedup và thêm regression simultaneous check/conflict/plan, cùng các nhánh mismatch/NA/risk; root suite **24 methods pass (14.201s)**. Goldens và valid legacy replay giữ nguyên.

**Output hiện tại: DONE sau vòng 3.** Astra high đối chiếu đủ 31 file của snapshot `offline-review-r3-2026-11-10`, tự chạy **24 methods pass (13.910s)**, đóng RV-02 và giữ RV-01/RV-03 đã đóng; không còn finding mở hoặc finding mới được tìm trong scope. Root đối chiếu lại sau reset: manifest/payload hashes và file inventory vẫn khớp; chỉ ghi nhận verdict/DONE hành chính, không thay code hoặc manifest và không giả đã rerun suite. Scope DONE là P2 v2/reference report/current docs/review workflow; P3-B/S1 chưa chạy và full runtime chưa hoàn tất. Tiếp S1 cross-runtime parity theo plan. Không commit/push/pilot/API thật.

## P4-A prerequisite và plan — 10/11/2026, nền `9237018`

Mục tiêu phiên: tiếp tục sau P3-A, kiểm phần đã làm bằng subagent mô hình cao, hoàn thiện bước nối report offline và làm rõ mục đích plan. Checkout `master` sạch khi bắt đầu. P3-B chưa có spike results; không tự chốt stack hoặc gọi design là runtime.

Đã kiểm baseline bằng `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: 8 methods pass, gồm 9 valid/58 negative P1, 55 decision/20 lifecycle P2 cùng checks CLI/repeatability. Python 3.14.8 chạy được; Node 26.12.1 hiện có, không là product pins. Không chạy fixture runners ghi execution.

Plan được hợp nhất theo mục đích sản phẩm → phạm vi bản đầu → trạng thái/acceptance P0–P6 → dependencies/việc kế tiếp → verification/review. README, TARGET, ADR-003 và D-20 đồng bộ lý do ưu tiên reference report oracle trước S1; Python vẫn reference tooling. Full bản đầu vẫn gồm self-host multi-user/worker/container, hai intake/providers/ingress và Windows client, không hạ scope thành core đơn lẻ.

Hoàn tất reference slice: `tools/evaluate_rules.py` dispatch strict v1/v2; schema/assessment v2 sửa source_reasoning tự gán integration coverage và mixed violation/conflict mất reason. V1 giữ replay lịch sử, không làm oracle corrected flow. `tools/project_report.py`, schema report v1 và tests/goldens mới tạo report từ v2, giữ declared/effective constraints, stages/risk/bindings/source/provenance, proposed actions và input digests; `--check` recompute phát hiện tamper. [Hướng dẫn chạy](OFFLINE-REPORT.md), [P2 audit/fix](P2-V2-REVIEW.md), [review phiên](P4-A-REFERENCE-REVIEW.md) ghi contract/CLI/digest/giới hạn.

Ba subagents high-model tham gia: Astra audit rules và độc lập review report (7 tests pass 5.884s); Terra review patch v2/report sau fixes (không tự chạy); Astra plan reviewer cuối đã đọc plan, hướng dẫn OFFLINE-REPORT và handoff, không blocker sau sửa nit trạng thái P3-B. Reviewer này không đối chiếu độc lập toàn PRODUCT-DECISIONS/skill hoặc tự chạy tests. Root viết code sau tool ghi subagent bị treo/hủy. Đã xử lý các findings: stages/binding/risk trace, pending-declaration action, duplicate/recursion parser và serialized 1/1.0 tamper.

Kiểm cuối: full suite **20 methods pass (10.171s)** sau duplicate-valid-report regression; P1/P2 legacy corpus và v2/report checks cùng pass. Links/fences ở 12 docs pass, diff whitespace pass; đối chiếu nền xác nhận fixture/evidence/protocol/schema/corpus lịch sử giữ nguyên. Không chạy fixture runners ghi execution, model/API, DB/container/native-shell hoặc benchmark.

Trạng thái: P2 v2 và prerequisite P4-A reference report completed trong scope offline. **P3-B chưa chạy; P4 mới hoàn tất prerequisite report offline của P4-A.** Tiếp **S1 cross-runtime parity** trên v1 legacy + v2 corrected/report oracle, ghi numeric serialization/precision/version behavior, runtime/dependencies và số đo thực rồi quyết định core stack theo ADR-003. Full runtime report/persistence còn cần versioned contract/schema/graph/lifecycle integration; legacy exporter vẫn projection_unsupported, không report_ready/completed. DB/engine/secrets/GitHub/native spikes và plugin target còn mở. Chưa commit/push, pilot/E3/account/API thật/public publish.

## P3-A — kiến trúc đích đã review, 05/11/2026, nền `337ab82`

Người dùng yêu cầu sau mỗi step dùng subagent kiểm tra lại; đã ghi thành quy trình trong IMPLEMENTATION-PLAN/D-19, áp dụng cho các bước tiếp theo. Step này thêm TARGET-ARCHITECTURE, ADR-001/002 accepted design, ADR-003 proposed stack/spikes và P3-REVIEW traceability. Không triển khai server/plugin/desktop hoặc chọn stack như đã benchmark.

GPT-6 Astra high review độc lập, tìm bốn nhóm: P1 declared vs P2 effective constraint collision; hostile output collection; log taint/secret đọc hoặc export; cùng GitHub occurrence/two SHA. Đã sửa design/cases và gửi re-review; kết luận đóng P3-A design, P3 overall vẫn partial. Review không thay runtime tests/security certification.

Kiểm tra thực: relative links/code fences/whitespace diff pass; replay collision in-memory xác nhận P2 incomplete nhưng P1 E_REPORT_SUMMARY, còn complete được P1 nhận nhưng trái P2. Không sửa code/schema/examples/evidence/protocol cũ (diff đối chiếu nền sạch ở các vùng đó). Không chạy model/API/DB/container/native shell hoặc benchmark; Node/npm sẵn, Rust/Docker chưa tìm thấy qua PATH.

Tiếp P3-B theo ADR-003: bounded spikes/core parity, DB queue/concurrency, Windows shell comparison, executor/network/output controls, GitHub occurrence/revision reconciliation, secret/identity backend. Kết quả chưa có phải giữ unknown; không cài toàn máy ngầm hoặc giả số đo. P4-A còn prerequisite versioned report/constraint contract trước full projection: hiện phải projection_unsupported + no report/completed ở collision, không mutate frozen handoff/P2 status. Chưa pilot/E3/public publish; agent host chưa chọn.

## P2 rules v1 — 05/11/2026, nền `2463cc0`

Đã thêm VERIFICATION-RULES, qa-assessment-v1 schema, examples/rules/v1 và evaluate_rules/test_rules. Reference evaluator phân biệt coverage thiếu, counterexample/conflict theo context, stale/trust gaps, N/A, risk/plan, mandatory constraint và approval; lifecycle helper kiểm supplied context facts, không authorize hoặc resolve proof thật.

Kiểm tra: 55 decision scenarios + 20 lifecycle cases qua 4 methods (kèm CLI/repeatability/no-mutation) pass; P1 regression cũng pass. Chỉ test dev tooling, không chạy model/API/container hoặc QA project. P1 contract/specimens và mọi fixture/evidence/frozen protocol giữ nguyên. Không có review độc lập model cao cho P2 trong phiên này.

Tiếp P3 TARGET-ARCHITECTURE và ADR: trusted assessment intake/acceptance, report projection, server/auth/project, queue/worker/container, GitHub ingress, provider/agent adapters, storage/event/audit và desktop. Chưa chọn stack, target agent, pilot hoặc public publish.

## P1 audit fixed — contract v2, nền `872c498`, 05/11/2026

Sau yêu cầu sửa, v2 thêm stable tasks/taskRef, scoped source/diff, source-evidence revision check, decisive/context evidence, execution provenance guard, exact report-run progress, event initial-run uniqueness/manual rerun lineage, done assignee và duplicate cycle. Schema/JSON v1 giữ nguyên; archive doc/readme ghi rõ legacy, active validator chỉ nhận2.0.0. P1-REVIEW-FIXES trace sáu finding và review độc lập.

Tests: 9 valid bundles/58 negative scenarios, 4 methods với subtests/CLI/legacy rejection đều pass. GPT-6 Astra high đã kiểm bản sửa hai vòng, bổ sung report_ready exactly-one và kết luận đóng targeted P1 correction gate. Không thay fixtures/evidence/frozen protocols hoặc triển khai runtime. Tiếp P2 VERIFICATION-RULES.md với v2; gate chỉ contract offline, chưa domain sufficiency/security/runtime/readiness.

## P1 contract v1 — 05/11/2026, nền `e87e15b`

Đã tạo DATA-CONTRACT.md, schemas/qa-contract-v1.schema.json, 3 valid bundles + 39 negative mutation scenarios tại examples/contracts/v1 và tools/validate_contracts.py/test_contracts.py. Dev dependency jsonschema 4.26.0 đã có trên máy, không phải product stack. Tests kiểm schema/reference/version/project/lease/report và CLI; không chạy test app/container/model/network hoặc thay fixture/evidence cũ.

P1 v1 bao quát resource/ownership/permissions/start-cancel/progress/worker-result/lifecycle; admin/auth/query wire transport và atomic enforcement chưa có code, thuộc P3/P4. Run completed có thể report incomplete; approval pending riêng. Budget/key/image/actor trong examples là specimen. Tiếp **P2 VERIFICATION-RULES.md**, không xây desktop/server từ schema rồi coi đã đủ runtime hoặc pilot-ready.

## Chốt yêu cầu qua câu hỏi — 05/11/2026, nền `303b85a`

PRODUCT-DECISIONS ghi toàn bộ lựa chọn: hai intake chung pipeline; agent local/API theo project, OpenAI/Anthropic adapter riêng; read-check-report/đề xuất, không sửa code/test; QA requirement/nghiệp vụ/code review/unit-integration; manual + bàn giao Dev/QC/PR chờ review, GitHub; outbound scope theo project; conflict AC hỏi owner, phần độc lập tiếp tục. Local trước/team sau ban đầu được mở rộng bởi worker/server xử lý khi desktop đóng, UI theo dõi.

Đã chốt worker self-host, project config/repo/data/secret store trên server, multi-user với auth nội bộ admin quản lý/SSO sau, fixed roles Admin/Owner/Runner/Viewer, container project/run và GitHub polling+webhook. P1/P3 cần project config, source/runtime/provider/event/capability/data policy và run lifecycle UI-worker. Không thêm implementation/API calls/pilot trong lượt hỏi đáp.

## Desktop + plugin — 05/11/2026, nền `e40d4e3`

Người dùng muốn desktop dashboard càng tốt, tối ưu kỹ thuật; chọn Windows trước, mở rộng macOS/Linux sau. Scope/plan/skill cập nhật hai client dùng chung core/application interface. TECHNOLOGY-DIRECTION có sơ đồ định hướng, UI flows, performance/concurrency/cache/permission principles và shortlist Tauri/Electron/SQLite dựa docs chính thức. Chưa chốt stack hoặc implementation; không có desktop/plugin chạy được.

Tiếp P1 contract cho handoff/evidence/report và commands/events/capabilities/run-state/storage references dùng chung agent/UI; sau đó P2/P3. Desktop thiếu agent connector thì không tự có reasoning. Không tự chọn host/transport, không analytics cloud/platform, không pilot/E3/public publish. As-is/fixture/evidence frozen giữ nguyên.

## Mục tiêu plugin — 05/11/2026, nền `edce89f`

Người dùng muốn framework publish được thành plugin cho agents thực hiện tự động; đã chọn kiến trúc dùng chung trước, chưa chọn nền tảng. P0 `docs/FRAMEWORK-SCOPE.md` có actors/decision, core/shared workflow/adapter, input-output, automation/permission/termination và packaging goal. Plan mở P0–P6, README/skill đồng bộ. Không sửa as-is hoặc coi thành phần đích đã tồn tại; chưa chọn host/SDK/transport/language/distribution.

Tiếp P1 DATA-CONTRACT gồm handoff/evidence/report và host capabilities/check execution. P2 rules/inference, P3 target architecture/ADR, P4 harness offline, P5 technical checks, P6 adapter/package khi đã chọn target. Chưa pilot/E3, chưa public publish/cài môi trường thật. Core không cần backend model API; host agent reasoning không bị cấm, nhưng không thay code/rules/contracts.

## Plan mới — 05/11/2026, nền `5e5d340`

Người dùng xác nhận thiết kế framework/năng lực tối thiểu trước, chưa pilot. `docs/IMPLEMENTATION-PLAN.md` là source kế hoạch hiện hành P0–P5; plan S0–S5 lưu nguyên file lịch sử, proposal pilot có banner superseded. Repo skill/README đã đồng bộ. Không thay core/template/fixture/execution/protocol frozen hoặc gắn readiness từ feedback.

Bước tiếp **P0: docs/FRAMEWORK-SCOPE.md** cho QC → Reviewer/TL: use case/actors/decision/input-output/non-goals/năng lực tối thiểu. Sau P0 mới contract/rules, target architecture/ADR rồi implement một luồng offline. Các output còn dự kiến chưa được tạo, P0–P5 chưa hoàn tất. Không mở E3/pilot hoặc tự chọn stack trước contract/architecture.

## Audit kiến trúc hiện tại — 05/11/2026, nền `c95086f`

Người dùng yêu cầu kiến trúc đầy đủ/chi tiết và subagent model cao kiểm sai sót; chưa đồng ý thử vận hành. Đã tạo `docs/CURRENT-ARCHITECTURE.md` cùng sơ đồ tổng thể PNG, mô tả phương pháp thủ công, sáu runner, evidence, workflow E1/E2 và phần chưa có. Subagent GPT-6 Astra high đọc độc lập và review draft; đã sửa các cạnh/thứ tự gây nhầm tự động hóa, constraint review bắt buộc và trạng thái snapshot. Audit tĩnh, không thay code/fixture/protocol frozen hoặc chạy pilot.

Hướng tiếp theo là thảo luận contract/trách nhiệm/kiến trúc đích dựa trên bản as-is; không tự coi file deliverable/test fixture pass là readiness hoặc tiếp tục đề xuất pilot khi người dùng chưa chấp nhận mức độ hoàn thiện.

## Tổng kết E2 và proposal — 05/11/2026

Sau hồ sơ tại `486ff6c`, người dùng phản hồi “đã ổn”. Lưu tại observations; kết thúc E2 với phản hồi chấp nhận chung, chưa xác nhận benefit tăng thêm/decision change/effort/G1 đầy đủ. Đã cập nhật results và tạo MANAGEMENT-PROPOSAL: giữ prototype thủ công, thử tiếp giới hạn có điều kiện owner/budget, chưa rollout/automation. Budget đề xuất vòng sau chưa đo/chưa được duyệt.

Các deliverable tài liệu cuối vòng đã có. Bước tiếp là người dùng xem tổng kết/proposal và chọn tiếp tục có giới hạn/đổi/dừng; không mặc định tạo thêm case hoặc chạy pilot thật. Code, evidence và protocol frozen giữ nguyên.

## E2-01 — nhận baseline, chuẩn bị hồ sơ bổ sung ngày 05/11/2026

Người dùng đề xuất quản lý tài khoản cấp user cho QC và Frontend sửa UI-17 trước bước tiếp. Đã lưu nguyên văn ở `pilot/e2-01-observations.md`; thời gian/nguồn cụ thể chưa cung cấp. Hồ sơ `pilot/e2-01-review.md` dùng core/template frozen, chỉ tổng hợp record cũ và làm rõ phụ thuộc/retest/current revision. Không thêm execution/fix/evidence, không nâng severity UI-17 hoặc tự ghi approval.

Bước tiếp: gửi hồ sơ lấy quyết định sau, điều mới/đã biết, nguồn và phút đọc. Nếu hồ sơ chỉ lặp lại điều đã biết thì ghi đúng; không kéo dài thêm case. Sau đó cập nhật results/proposal theo plan. Input/protocol E2 giữ nguyên.

## E2-01 — 05/11/2026

Người dùng chọn QC → Reviewer/TL. Đã chuẩn bị protocol E2 và input xuất CSV, tự chứa vị trí/quyết định, self-test/QC, revision/môi trường, issue low và blocked. Tất cả record là authored synthetic, không có execution/app/QC thật. E1/core/template frozen không đổi. Input thông báo tiếp tục budget 10 phút gần nhất và cho phép điều chỉnh trước lượt; phút thực đọc unknown.

Bước tiếp: gửi input và lấy nhận định trước/nguồn/action/điều kiện xong bằng câu hỏi tự do, rồi mới tạo hồ sơ phân tích. Ghi protocol commit giới thiệu E2 khi lưu phản hồi. Không biến số pass giả lập thành bằng chứng thực thi; không gợi ý quyết định trước baseline.

## Kết thúc E1-01 — thiếu bối cảnh bàn giao

Người dùng hỏi self-test/QC và nhận xét input chỉ có feature/unit test. Đã đồng ý ghi nhận E1 chưa đánh giá được mục tiêu và thiết kế lại lượt mới. `pilot/results.md` lưu phản hồi/giới hạn; register đổi trạng thái kết thúc, không thu tiếp baseline như chưa có vấn đề. Phút thực đọc unknown; không kết luận hết thời gian hoặc G1 fail. Code/evidence/protocol E1 không đổi.

Bước tiếp là chốt điểm bàn giao/quyết định cho E2 trước khi viết case: developer → QC để nhận kiểm thử hay QC → Reviewer/TL để quyết định tiếp. Đây là lựa chọn mô phỏng, không tự áp quy trình thật; trạng thái self-test/QC và provenance phải rõ. Không tự giả lập QC approval thật, không yêu cầu người dùng tiếp tục tìm lỗi code trong E1.

## E1-01 — hỗ trợ định hướng sau input `081b455`

Phản hồi đầu của người dùng yêu cầu nêu tình trạng/vị trí hiện tại, chưa là nhận định behavior/action. Đã giữ nguyên INPUT và thêm ORIENTATION.md riêng: bối cảnh bàn giao, hai check đã chạy, phần chưa chốt và bước đang làm. Register lưu nguyên phản hồi và đánh dấu hỗ trợ; core/template/protocol frozen cùng code/evidence không đổi. Phút đọc chưa được cung cấp, không suy từ thời gian chat. Bước tiếp: lấy nhận định/action ban đầu cùng phút thực đọc; chưa gửi hồ sơ phân tích hoặc đáp án.

## E1-01 — nền `183b477`

Người dùng chọn tự đọc/review với 10 phút tổng trước/sau hồ sơ. Case mới `examples/evaluation/e1-seat-cancellation` có requirement/base/head/diff, 2 baseline pass và input đọc ban đầu. Chưa gửi hồ sơ phân tích, chưa có phản hồi baseline. Task register ghi protocol/freeze/timebox và exposure đã biết; không ghi thời gian người dùng bằng thời gian trôi qua trong chat.

Bước tiếp: nhận nhận định/action/nguồn/phút đọc thực tế trước hồ sơ qua câu hỏi tự do. Sau đó mới chuẩn bị hồ sơ bằng core/template frozen và gửi để lấy nhận định sau trong thời gian còn lại. Không gợi ý đáp án hoặc sửa head trước khi lưu baseline; không ghi kết quả G1/E1 khi chưa có phản hồi.

## Chuẩn bị E1 — nền `8c03ad5`

Đã chốt core/template tại full commit nền, manifest `pilot/e1-freeze.json` ghi blob/hash nội dung Git. Protocol tại `docs/EVALUATION-PROTOCOL.md`; task register và adjudication log tách walkthrough/feedback/self-check cũ khỏi đánh giá E1 chưa bắt đầu. Budget 20 phút là đề xuất chưa được duyệt; case/người đọc mới chưa chọn. Không thay code/fixture/evidence hoặc khai kết quả E1.

Bước tiếp: chốt người đọc/timebox và đăng ký một case mới trước lượt E1; nếu thiếu điều kiện, vẫn viết `pilot/results.md` và `docs/MANAGEMENT-PROPOSAL.md` nêu đúng giới hạn. Không tạo mock vô hạn, không tự nâng feedback dễ hiểu thành G1 đầy đủ.

## MOCK-07 — nền `b7d84de`

Theo hướng tiếp tục đã thống nhất, thêm case giảm giá để dùng lại bố cục được người dùng phản hồi tốt. Có requirement synthetic, head/fixed, 2 baseline/2 probe, runner riêng và hồ sơ `pilot/mock/MOCK-07-review.md`. Hai lỗi riêng: bỏ đúng ngưỡng 100.000 và giảm nhầm phí giao hàng. Head 2 pass/2 fail; fixed 4 pass; không errors/skipped, runner exit 0. Giữ nguyên các case/manifest/evidence cũ. Không coi case mới là holdout hoặc đánh giá độc lập. Bước tiếp: người dùng đọc hồ sơ mới và phản hồi hai lỗi/cách sửa có dễ phân biệt không; không hỏi lại độ dễ hiểu của MOCK-06 v2 đã được xác nhận.

## Phản hồi v2 — nền `fd3b8df`

Người dùng xác nhận “hồ sơ v2 hợp lý, khá dễ hiểu”. Đã ghi tại REVIEWER-CHECK; giữ cách trình bày hiện tại, không lặp lại yêu cầu xác nhận dễ hiểu. Đây là phản hồi tích cực trong walkthrough có hỗ trợ; chưa đo khả năng truy evidence độc lập, effort hoặc effectiveness, không coi G1 đầy đủ hoặc approval đã đạt. Bước tiếp: áp dụng bố cục cho một case synthetic nhỏ khác theo implementation plan, ghi phạm vi/tiêu chí trước khi làm. Code/evidence giữ nguyên.

## V2 — nền `1064b2f`

Người dùng đã chọn toàn dấu cách nghĩa tất cả, bỏ dấu cách hai đầu khi tìm category. Requirement `mock-req-06-v2`, snapshot `mock-06-fixed-v2` nằm trong `examples/remediation/06-filter-pagination-v2`; service chỉ strip ASCII space. Có 4 test mới qua service/API/UI và reuse 9 cũ. Runner local exit 0: v2 13 pass; fixed-v1 9 pass/4 fail đúng thiết kế; không errors/skipped. Evidence mới có hashes; fixture/requirement/evidence cũ không đổi.

Hồ sơ `pilot/mock/MOCK-06-v2.md` giải thích behavior và kết quả, verification complete trong scope v2; không phải approval hoặc xác nhận usefulness. Bước tiếp là người dùng phản hồi cách giải thích mới. G1 chưa xác nhận; không tiếp tục hỏi whitespace cho v1 như một blocker hiện hành vì đã được chốt tại v2.

## Cập nhật mới nhất — nền `dbf1582`

Theo phản hồi tự diễn giải, đã tách hai lỗi trong hồ sơ sau sửa và thêm mong muốn/lý do/thực tế/cách sửa/kết quả ngay tại chỗ. Lý do reset lấy từ catalog mẫu; quy tắc từ AC-02. Lỗi cache có cách sửa riêng, không được gộp với reset. Template áp dụng cùng cách trình bày; phản hồi ghi tại REVIEWER-CHECK, quyết định D-04. Chỉ sửa Markdown, không chạy lại/ghi đè evidence. Bước tiếp: người dùng đọc phần mới; chưa xác nhận G1 hoặc chốt whitespace.

## Lượt trước

Commit nền phiên mới nhất: `17e8e4f`. Phạm vi: ghi phản hồi người dùng có gợi ý và chỉnh cách đọc kết quả/thứ tự hành động; không thay code, fixture hoặc execution evidence.

Phản hồi: người dùng chọn đúng trạng thái nhưng truy evidence còn khó, chưa rõ action; lý do là chưa quen đọc test và cần thứ tự việc/điều kiện xong. Đã lưu tại `docs/REVIEWER-CHECK.md`, thêm diễn giải và bảng hành động vào hồ sơ, cập nhật template và D-03. Câu hỏi có đáp án gợi ý, chưa đủ chứng minh đọc độc lập. Requirement whitespace giữ pending.

Evidence runtime của vòng trước vẫn tại thư mục remediation: head có 6 pass và 1+2 failure cố ý; fixed 9 pass, không errors/skipped. Phiên chỉ sửa Markdown nên kiểm tra liên kết, diff và đối chiếu semantics; không chạy lại hoặc ghi đè evidence.

G1/usability/effectiveness và human decision chưa được xác nhận. Effort/budget unknown. Bước tiếp: cho người dùng tự diễn giải một kết quả và bước tiếp theo sau khi đọc bản mới; ghi đúng hỗ trợ đã cung cấp. Không tự chuyển sang generic verifier hoặc pilot dữ liệu thật.
