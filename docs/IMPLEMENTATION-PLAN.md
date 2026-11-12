# Kế hoạch phát triển QA framework

Cập nhật 12/11/2026: user yêu cầu commit/push S2-C/S6-A/S6-B trên nền `e61be7e` đã push S2-A/B; [hồ sơ trước push](S2C-S6-PUSH-REVIEW.md) ghi snapshot/checks. Kiểm Git log/status/remote cho hash thực tế, không dùng nền cũ để bỏ output mới. Đây là plan P0–P6 hiện hành, thay [plan pilot cũ](IMPLEMENTATION-PLAN-2026-11-03.md). [PRODUCT-DECISIONS](PRODUCT-DECISIONS.md) ghi yêu cầu đã chốt; [DECISION-LOG](DECISION-LOG.md) ghi lý do thay đổi. Chỉ synthetic trong repo, chưa pilot/publish.

## 1. Mục đích và kết quả người dùng cần

Giúp Reviewer/Tech Lead khi nhận bàn giao biết **requirement nào có evidence phù hợp, phần nào còn thiếu hoặc mâu thuẫn, ai cần xử lý và điều kiện nào cho phép xét lại**. Kết luận phải truy về requirement, source/check/evidence và đúng candidate revision. Verification và quyết định phê duyệt của con người luôn tách riêng.

Luồng đích: nhận repo/task hoặc handoff Dev/QC → đóng băng candidate/config/policy → thu thập nguồn → agent phân tích requirement và đề xuất checks → thực hiện checks được phép → đánh giá evidence → report/action → Reviewer/TL quyết định. Requirement conflict chờ owner ở phần liên quan; phần độc lập tiếp tục. Người dùng không phải điền từng bảng hoặc duyệt lại thao tác routine đã ủy quyền.

Điểm bàn giao đầu là QC → Reviewer/TL, không áp QC làm gate bắt buộc mọi workflow. Report cần nêu self-test/QC đã làm gì, ở revision/môi trường nào, giới hạn của kết luận, action/role/assignee hoặc unknown và doneWhen. Không lấy số test pass làm kết quả sản phẩm.

## 2. Phạm vi bản đầu đã chốt

| Nhu cầu | Kết quả cần có | Ranh giới |
|---|---|---|
| Hai đầu vào | Repo/task và gói bàn giao Dev/QC cùng chuẩn hóa về task/handoff/candidate | Không có hai bộ rules |
| QA tự thực hiện | Requirement/nghiệp vụ, code review và unit/integration evidence; đọc, chạy checks, report, đề xuất | Không tự sửa code/test, approve, merge hoặc deploy; chưa audit UI/e2e/security/performance chuyên sâu như năng lực sản phẩm |
| Reasoning theo project | Local-agent connector hoặc OpenAI/Anthropic qua adapter riêng | Thiếu connector/model thì báo gap; inference không tự thành execution hoặc trusted judgment |
| Kích hoạt | Manual, bàn giao Dev/QC, PR chờ review; GitHub polling và webhook | Dedup theo occurrence và exact revision; unresolved không tự tạo run phỏng đoán |
| Triển khai/quyền | Server/worker self-host nhiều người, auth nội bộ admin quản lý; fixed roles Admin/Owner/Runner/Viewer | Desktop đóng worker vẫn chạy; SSO sau; không SaaS do sản phẩm vận hành |
| Dữ liệu/thực thi | Repo/data scope và secret references trên server; container riêng project/run, trusted check config và budgets | Live permission/policy recheck trước side effect; không host fallback hoặc lệnh tùy ý từ artifact/model/UI |
| Hai client | Windows dashboard và headless/plugin cùng API/core/results | Chưa chọn agent host; macOS/Linux là hướng mở rộng, chưa là release target |

Hai intake, hai provider, local connector, hai kiểu ingress, multi-user/RBAC, worker/container và Windows client đều thuộc bản đầu. Có thể triển khai từng slice; core/harness đơn lẻ hoặc UI demo chưa là sản phẩm hoàn chỉnh.

Repo/chat chỉ dùng synthetic: không lấy task/code/log/key thật, gọi account/API thật để chạy QA hoặc mở E3/pilot. Giữ fixture lỗi, expected outcome, execution và protocol frozen; remediation có snapshot/version riêng. Không tiếp tục thêm ví dụ domain nếu không kiểm contract/rule/failure mode cụ thể.

## 3. Hiện có gì và mỗi mốc cần hoàn thành gì?

| Mốc | Mục đích và đầu ra | Hiện trạng / điều kiện hoàn thành |
|---|---|---|
| P0 — Scope | [FRAMEWORK-SCOPE](FRAMEWORK-SCOPE.md): users, decision, inputs/outputs, non-goals | Có thiết kế scope; mỗi năng lực gắn use case. Giá trị sử dụng thực tế chưa đo |
| P1 — Contract | [DATA-CONTRACT](DATA-CONTRACT.md), schema và valid/invalid specimens: identity/revision/provenance, commands/events/run/report | V2 có validator, 9 valid bundles/58 negative scenarios và [audit/fix](P1-REVIEW-FIXES.md). Gate offline shape/reference, chưa auth/lease/trust/atomic enforcement |
| P2 — Rules | [VERIFICATION-RULES](VERIFICATION-RULES.md), assessment schema/evaluator: coverage, conflict/N/A, constraints, finding/action lifecycle | [V2 sửa hai lỗi audit](P2-V2-REVIEW.md), chạy 55-case corpus và regression mới; v1/20 lifecycle cases giữ replay lịch sử. Đã review patch; chưa tự hiểu domain hoặc xác thực trust |
| P3-A — Architecture | [TARGET-ARCHITECTURE](TARGET-ARCHITECTURE.md), ADR-001/002: component/ports, dataflow, quyền/error/storage/transport | Design đã [review độc lập](P3-REVIEW.md); contract có owner và boundaries rõ. Chưa chứng minh stack khả thi |
| P3-B — Stack/spikes | [ADR-003](adr/003-stack-and-spikes.md): parity, queue/storage, shell, executor/policy, GitHub correlation, secrets/identity | S1/S2-A/B/C subsets DONE; push e61be7e chứa S2-A/B. [S6-A storage](S6-A-RESULTS.md)DONE trong subset sau10 groups PASS/[review CLEAN](S6-A-REVIEW.md); S4 prerequisites chưa READY/execution NOT RUN. [S6-B identity](S6-B-RESULTS.md) DONE trong subset sau actual9 groups PASS/final CLEAN; full S2/S6 và deployed auth/worker/OS-key management còn mở; S3/S5 chưa chạy, P3-B chưa đóng |
| P4-A — Shared core/report | Versioned report, projector và synthetic offline harness; đóng module pure core theo baseline đã chọn | Prerequisite offline/S1 đã có. [Internal report/core slice](P4-A-RUNTIME-REPORT.md) DONE trong scope sau review R2: Python module, versioned report + completion proposal, exact-run graph/predicate. [Publication/replay package](P4-A-PUBLICATION.md) staged DONE trong scope sau clean review ngày 11/11; production storage/transaction, scoped read/export và full lifecycle integration còn mở |
| P4-B — Control service | Auth/project/config, hai intake, API, DB/blob/outbox, immutable snapshots | Chưa triển khai. Gate: RBAC/revoke/isolation, atomic commands/claim/idempotency, restart/restore theo runtime đã chọn |
| P4-C — Worker/acceptance | Enrollment/lease, container checks, policy/budgets/cleanup, trusted assessment pipeline | Chưa triển khai. Gate: stale worker fenced, cancel chỉ sau cleanup, raw inference không tự cấp authority, không host fallback |
| P4-D — Adapters | GitHub polling/webhook, OpenAI/Anthropic, local connector ports | Chưa triển khai. Gate: offline conformance trước; occurrence/revision resolve hoặc explicit gap; authenticated/network readiness kiểm riêng trong môi trường được phép |
| P4-E — Windows client | Dashboard start/progress/cancel/report/source/export qua cùng API | Chưa triển khai. Gate: đóng app run vẫn tiếp tục, reconnect/replay đúng; desktop/headless cùng kết quả, UI bridge không có executor quyền riêng |
| P5 — Technical readiness | `docs/TECHNICAL-READINESS.md`: failure boundaries, recovery, performance và end-to-end evidence | Chưa có/đóng gate. Kiểm project isolation/revoke, queue races, container/output/network, secrets, report consistency và UI responsiveness theo targets đã ghi |
| P6 — Packaging | Windows installer + self-host server/worker deployment; plugin adapter khi target được chọn | Chưa có package. Gate: install/upgrade/uninstall/migration/compatibility và tài liệu tái lập; chưa tự publish/pilot |

Các số scenario chỉ mô tả coverage tooling, không là pass rate AC, effectiveness/ROI hoặc readiness sản phẩm. Python đã chọn làm pure-core baseline sau S1, tooling hiện tại vẫn chưa production runtime. Node control/worker, PostgreSQL, Tauri/Linux OCI vẫn là candidates theo boundary. Chưa chọn library/CLI/MCP, SDK hoặc distribution agent. HTTPS JSON/SSE là thiết kế ADR-002, chưa có server.

## 4. Việc kế tiếp và thứ tự phụ thuộc

Điểm dừng nền `9237018`: P3-A design xong, P3-B chưa chạy. Trước khi so parity toàn luồng, còn collision P1/P2: handoff khai constraint satisfied nhưng thiếu current accepted review thì P2 incomplete, còn P1 v2 tính summary từ khai báo gốc. Không sửa handoff, AC hoặc nâng P2 complete để né lỗi.

Phiên 10/11 ưu tiên prerequisite **P4-A reference report contract/harness**, giữ P1 v2 và P2 v1 để replay lịch sử. Audit độc lập phát hiện source reasoning tự gán integration level có thể false verified, và mixed violation/conflict mất conflict reason; thêm assessment/rules v2 explicit để sửa, report mới chỉ nhận v2. Lý do ưu tiên: cần oracle giữ effective constraint và semantics đã sửa để S1 so cross-runtime; phần này không cần DB, engine hoặc native toolchain. Đây là đổi thứ tự kỹ thuật, không quyết định Python thành product stack hoặc bỏ P3-B. Legacy P1 v2 export gặp collision vẫn phải `projection_unsupported`, không publish report/report_ready/completed.

| Thứ tự | Việc cụ thể | Điều kiện xong | Phụ thuộc/gap |
|---|---|---|---|
| 1 — xong reference slice | Rules v2 và versioned reference report, bindings về bundle/assessment, declared/effective constraints, nguồn/reason và việc cần xử lý | Đã kiểm legacy/v2 corpus, false-green/mixed-conflict, collision/tamper/CLI/no-mutation; [review và actual checks](P4-A-REFERENCE-REVIEW.md) | Output riêng không tự thành P1 wire report hoặc authenticated judgment |
| 2 — S1 workload PASS | Native TS/Node parity so Python reference, pinned runtime/deps và actual metrics | [Evidence](s1-results/2026-11-10-r1.json): 356/356 + 28/28 CLI, 3 trials/runtime, no mutation; review/final output status tại [S1-REVIEW](S1-REVIEW.md) | Chọn Python pure-core baseline; không chọn toàn stack hoặc claim universal JSON parity |
| **3 — P4-A đang triển khai** | [Internal report/core slice](P4-A-RUNTIME-REPORT.md): Python module + versioned report/completion proposal DONE trong scope sau review R2; [publication/replay package](P4-A-PUBLICATION.md) staged DONE trong scope sau clean review ngày 11/11; tiếp storage/transaction, scoped read/export và full lifecycle integration | Slice có schema/validator/pure graph predicate và goldens; full gate cần durable refs, atomic completed/report_ready và integration evidence | Internal proposal không là P1 v2 bundle hoặc persisted report; legacy exporter vẫn unsupported, không âm thầm thay v2 |
| 4 | S2 metadata/S6-A subsets DONE; [S6-B](S6-B-RESULTS.md) identity/session/RBAC subset DONE sau actual9 groups PASS/final CLEAN; tiếp identity→application/live-policy/broker composition protocol + S4 prerequisites rồi P4-B/C | Full gates cần authenticated service/worker/broker, actual cleanup/network/collector, trusted OS keys/restore và runtime integration | In-process identity/library model không là deployed auth/key store; S4 NOT RUN không được mock thành pass |
| 5 | S5 + P4-D: event reconciliation, provider/local connector conformance | Common occurrence/exact revision hoặc explicit gap; adapters không bypass policy | Recorded fixtures không chứng minh auth/rate limit/history availability thật |
| 6 | S3 + P4-E, rồi P5/P6: native shell, desktop flow, readiness/package | Release-build comparison, cùng kết quả headless/desktop, cài/upgrade/gỡ kiểm được | Plugin host chưa chọn chỉ chặn platform package, không chặn core/API |

Các spike độc lập có thể làm khi prerequisite sẵn; không ép một thứ tự cứng cho toàn stack. Mỗi spike theo timebox/targets ADR-003, xuất actual/unknown và bước khôi phục nhỏ nhất; không benchmark giả, đổi ngưỡng sau chạy hoặc retry vô hạn. P4-A reference không đóng P3-B/P4 overall. Effort implementation ước lượng sau spike/design, không suy ngày công từ số fixture.

## 5. Kiểm chứng phải bảo toàn qua mọi slice

- Claim → requirement/version + source/check/evidence + candidate revision; tách decisive/context evidence và authored mock/execution/source reasoning. Hash nhận dạng nội dung, không chứng nhận actor/trust.
- Thiếu mapping/coverage, cũ revision, conflict, ambiguity, error/skipped/blocked có trạng thái và action rõ; không suy suite xanh thành mọi AC verified hoặc input error thành defect behavior.
- Constraint review bắt buộc khác approval pending; failed vẫn hiển thị phần mandatory chưa kiểm đủ. N/A, finding adjudication và domain decision cần basis/authority phù hợp.
- Input malformed, duplicate/ref lỗi, major lạ, path ngoài scope hoặc chỉ dẫn trong artifact không tự thành executable command. Diagnostics không lộ raw secret-like input. Shape đúng không thay runtime containment/policy enforcement.
- Cùng input/rule version cho kết quả quyết định tương đương; rerun không ghi đè evidence. Permission/account/policy/secret revoke được kiểm trước side effect; snapshot không giữ quyền đã thu hồi.
- Finding dedup theo behavior/cause; action có role, assignee hoặc unknown, doneWhen và completion proof phù hợp. Human decision pending khi chưa có quyết định thật; action done không tự nâng AC/approval.

Checks chọn theo failure mode và vùng đổi: docs-only kiểm links/consistency/diff; code đổi kiểm behavior/regression liên quan. DB/engine/native/adapter readiness cần boundary thực, unit/schema tests không thay được. Không sửa fixture lỗi/expected để làm suite xanh. [CORE-FRAMEWORK](CORE-FRAMEWORK.md) giữ semantics nền, [CURRENT-ARCHITECTURE](CURRENT-ARCHITECTURE.md) là audit as-is tại ngày ghi nhận.

## 6. Review, bàn giao và giới hạn quyết định

Mọi output luôn có ít nhất một agent review độc lập mô hình cao. Áp dụng [vòng review bắt buộc](REVIEW-WORKFLOW.md): đưa bản hiện tại vào review độ chính xác/tính thực dụng, ghi reasoning và stable finding IDs, sửa → kiểm chứng → gửi bản mới re-review; lặp tới vòng sạch, không còn lỗi cũ/tái xuất hiện/mới trong scope rồi mới mark DONE. Lưu scope/snapshot/verdict/checks, không ghi trước verdict hoặc dừng theo số vòng tùy ý. Review không thay execution tests hoặc human approval. Review/sửa thường lệ trong scope đã giao không cần hỏi duyệt lại; thiếu domain decision thì hỏi cụ thể và tiếp tục phần độc lập.

Mỗi phiên cập nhật [SESSION-HANDOFF](SESSION-HANDOFF.md): commit nền, mục tiêu, outputs, commands/results thực chạy, review/fixes, giới hạn và bước tiếp nhỏ nhất. Không coi kiến trúc đích là code đã có hoặc sửa audit lịch sử thành current runtime. E1/E2/feedback/proposal/H1–H5 cũ chỉ là lịch sử/tham khảo, không gate đầu tư thiết kế hiện hành.

Xong P5/P6 chỉ cho phép tổng kết kỹ thuật và package candidate. Pilot, cài môi trường thật hoặc public publish cần yêu cầu riêng; không tự suy quyền từ test xanh. Effort/cost/usefulness chưa đo là unknown. Không yêu cầu pilot benefit trước khi thực hiện năng lực tối thiểu đã được giao.
