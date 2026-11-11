# Bàn giao session mới — sau P4-A core/runtime và publication/replay

Ngày 11/11/2026. **Bản bàn giao DONE sau clean review HS-R1** tại [SESSION-TRANSFER-REVIEW](SESSION-TRANSFER-REVIEW.md). Đây là brief hiện hành thay brief 10/11 trước extraction; lịch sử giữ ở [SESSION-HANDOFF](SESSION-HANDOFF.md). Không cần toàn bộ lịch sử chat.

## 1. Checkout phải giữ nguyên

- Repo: `E:\phucpn-workspace\git\ai-engineering-qa-framework`.
- Baseline lúc soạn brief: `master`, HEAD **`d8bf1757228f31a8fd0e00f49baeda96741857aa`**. S1 implementation baseline trước đó là `d35ae6b337d1450f911d388adce2ee1bd0e3efd8`; đây không phải yêu cầu quay về các hash cũ.
- **User sau đó đã yêu cầu commit local. Commit chứa cập nhật này là snapshot bàn giao P4-A + docs**: gồm `qa_core/`, schemas runtime/prepared/publication, `examples/reports/runtime-v1/`, `publication-v1/`, tools và docs/review records. Xác định commit thực bằng Git log/status; không dùng riêng baseline `d8bf175` để khôi phục code mới. Chưa có yêu cầu push hoặc xác nhận remote đã có snapshot này.
- Session mới ưu tiên chính checkout này. Kiểm Git root/branch/HEAD/status thật và giữ mọi thay đổi phát sinh sau commit; không reset/clean/stash. Nếu chuyển checkout/máy, phải mang đúng commit snapshot và mọi tracked/untracked changes còn lại, rồi kiểm nội dung trước làm. Không assume remote đã cập nhật.
- Quyền commit local vừa cấp chỉ cho output hiện tại; không tự suy quyền commit/push cho các phase sau, tạo chat, merge/approve/deploy/publish hoặc pilot. Session mới chỉ bắt đầu implementation sau khi nhận yêu cầu tiếp tục.

## 2. Đọc để bắt đầu

1. `AGENTS.md`, `.agents/skills/qa-framework-development/SKILL.md`, [REVIEW-WORKFLOW](REVIEW-WORKFLOW.md).
2. Brief này, [SESSION-PLAN](SESSION-PLAN.md), phần đầu [SESSION-HANDOFF](SESSION-HANDOFF.md), [IMPLEMENTATION-PLAN](IMPLEMENTATION-PLAN.md), [DECISION-LOG](DECISION-LOG.md).
3. [P4-A-RUNTIME-REPORT](P4-A-RUNTIME-REPORT.md), [runtime review](P4-A-RUNTIME-REVIEW.md), [P4-A-PUBLICATION](P4-A-PUBLICATION.md), [publication review](P4-A-PUBLICATION-REVIEW.md).
4. [CORE-FRAMEWORK](CORE-FRAMEWORK.md), [PRODUCT-DECISIONS](PRODUCT-DECISIONS.md), [TARGET-ARCHITECTURE](TARGET-ARCHITECTURE.md) §5–6 và live policy/worker boundaries; [ADR-001](adr/001-boundaries-and-persistence.md), [ADR-002](adr/002-transport-identity-and-execution.md), [ADR-003](adr/003-stack-and-spikes.md), [ADR-004](adr/004-core-baseline-after-s1.md).
5. Chỉ đọc source/test/contracts liên quan slice chọn: [DATA-CONTRACT](DATA-CONTRACT.md), [VERIFICATION-RULES](VERIFICATION-RULES.md), [OFFLINE-REPORT](OFFLINE-REPORT.md), `qa_core/`, schemas và harness/tests. S1 evidence chỉ đọc khi cần, không mặc định rebenchmark.

## 3. Đã có gì, DONE ở đâu?

| Mốc | Hiện trạng | Không suy rộng thành |
|---|---|---|
| P0/P1/P2 | Scope; P1 v2 validator; P2 v2 evaluator, v1 replay; synthetic corpus | Authenticated judgments, domain truth hoặc runtime enforcement |
| P3-A | Architecture/ports/transport đã review | Các dịch vụ trong sơ đồ đã chạy |
| S1 | DONE: 356/356 structured cases + 28/28 CLI, ba trials/runtime; S1-RV-01..09 đóng | S2–S6, P3-B tổng thể hoặc chọn toàn stack |
| P4-A core/runtime slice | **DONE**: shared Python core, wrappers CLI; report/prepared v1, exact-run binding và pure completion proposal | Persisted report, actual completed run hoặc emitted report_ready |
| P4-A publication/replay slice | **DONE**: staged self-contained package v1, manifest, whole-input scopes, graph candidate và anchored replay validator | Durable publication, ordinary user export hoặc live read/outbound permission |
| P4-A tổng thể | **PARTIAL**: còn storage/transaction/outbox, scoped read/export, live auth/lease/trust và full lifecycle integration | Không lấy DONE của hai slice đóng toàn phase |
| P4-B–E, P5/P6 | Chưa implementation/gate hoàn chỉnh | Chưa có server/worker/desktop/adapters/installer production |

Python chỉ được chọn cho **pure shared core/report baseline** theo ADR-004. TS/Node `spikes/s1` là conformance spike, không second production rules engine. Control/worker runtime, DB, shell, agent host/distribution chưa chốt. PostgreSQL là candidate S2, không phải production DB đã chọn.

## 4. Output và evidence hiện tại

- Core: `qa_core/{contracts,rules,reports,runtime,publication,application}.py`; tools cũ giữ compatibility wrappers.
- Runtime: schemas `qa-runtime-report-v1`/`qa-prepared-report-v1`; `tools/prepare_runtime_report.py`, `test_runtime_reports.py`; goldens `examples/reports/runtime-v1/`.
- Package: schema `qa-publication-package-v1`; `tools/package_runtime_report.py`, `test_publication.py`; goldens `examples/reports/publication-v1/`.
- Latest re-review **WT-PUB-R2 CLEAN**, reviewer mới GPT-6 Astra high. Root chạy mới **45 methods pass / 37.113s**; reviewer chạy mới **45 methods pass / 36.320s**, thêm **638 deletion probes** đều reject. P4A-RV-01..06 giữ CLOSED; chưa có PUB-RV finding. Review records lưu lịch sử các vòng; không cộng probe thành unittest methods.
- Manifest **33 implementation/schema/test/golden paths** trước commit: `325c39c933a448434c842c297917e27232c5714f3176b83fd2f96980755fa478`. Inventory lịch sử: sorted union Git diff names + untracked names tại lúc review, lọc prefixes `qa_core/`, `tools/`, `schemas/`, `examples/`; dòng path + ASCII space + SHA256(file bytes), join LF không trailing LF, SHA256 UTF-8 toàn chuỗi. Sau commit cây sạch sẽ không còn inventory đó trong Git diff; dùng danh sách paths của snapshot/commit nếu kiểm lại, không hash danh sách rỗng để so. Đây không là hash toàn repo/trust proof; xem review records cho snapshot trước administrative doc updates.

## 5. Việc cần làm tiếp

**Ưu tiên đề xuất: S2-A — prerequisite inventory rồi transaction publication/queue spike trên DB synthetic riêng.** [SESSION-PLAN](SESSION-PLAN.md) là plan một session có nhánh khi môi trường chưa sẵn. Không làm lại extraction/package hoặc thêm envelope thuần chỉ để tăng output.

Cần evidence thật cho candidate storage: exact run/version/attempt, chống duplicate claim/occurrence/report, report ref + completed + outbox atomic, crash/restart, no publish-before-commit. S2-A là subset, chưa full S2: cancel/revoke/cleanup/fairness và các boundary ADR-003 vẫn phải kiểm riêng. Mock/unit/predicate không đóng DB gate. Production control/worker composition quyết định riêng sau evidence.

Nếu actual disposable DB chưa sẵn, không dùng DB/account thật hoặc SQLite/in-memory mock để gọi S2 PASS. Hoàn thành protocol/harness/preflight phần độc lập, ghi DB checks NOT RUN/unknown và bước khôi phục cụ thể. Routine trong slice tiếp được giao thì tự làm; thiếu input/authority bắt buộc mới hỏi cụ thể, vẫn tiếp phần độc lập.

## 6. Semantics và giới hạn phải bảo toàn

- Mandatory declared satisfied nhưng missing/stale/unaccepted review → effective pending → incomplete khi không có failed khác. Optional pending đơn thuần không chặn; failed giữ precedence và các gap vẫn hiện. Raw pending không tự hết nhờ review.
- Giữ raw handoff/AC/assessment, revision/provenance/mapping, humanDecision riêng. Không mutate inputs, hạ AC thành unverified giả hoặc nâng P2 complete để né P1 v2. New contracts/output phải version rõ; bảo toàn schema/corpus/fixture lỗi/evidence/protocol frozen.
- Legacy P1 v2 exporter vẫn `projection_unsupported`; runtime graph/package không là P1 v2 bundle. Persist/ref/read/event chỉ claim khi boundary thật implemented và verified.
- Package chứa **whole raw bundle**, có thể có project/task khác target; restricted internal replay metadata không phải ACL. So expected input digests/IDs caller giữ độc lập, không lấy anchors từ package. Không tự đưa gói qua ordinary QA read/export/model outbound.
- Snapshot scope ∩ live policy khi có runtime; chưa auth/lease/container/egress thì không nói đã enforce. Không gọi key/account/API/project thật, pilot/public publish, tự chọn platform/distribution/shell hoặc cài global.

## 7. Cách làm một session

Theo [SESSION-PLAN](SESSION-PLAN.md): Git/brief → chốt slice và acceptance trước sửa → implementation + failure/regression checks → reviewer độc lập high-model → fix/recheck/re-review đến clean → DONE đúng scope và bàn giao. Không đặt trần vòng review, không lấy suite xanh thay verdict, giữ stable finding IDs và reopen lỗi cũ nếu regression.

Regression hiện hành: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`. 45 methods là kết quả hiện tại, không quota vĩnh viễn. Docs-only bàn giao kiểm links/fences/consistency/diff và manifest, không cần rerun suite/S1 khi code không đổi. Không chạy runners ghi đè evidence gốc.
