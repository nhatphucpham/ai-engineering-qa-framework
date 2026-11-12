# Bàn giao hiện hành — sau S6-B identity/session/RBAC execution

Ngày12/11/2026. User yêu cầu **commit và push** toàn output S2-C/S6-A/S6-B đã review. Commit chứa cập nhật này là snapshot mới trên master/nền e61be7e; [pre-push record](S2C-S6-PUSH-REVIEW.md) ghi scope/checks, kiểm Git log/status/remote cho hash và kết quả push thực tế. S6-B R4 PASS9/final CLEAN WT-S6B-R4-D2, S6-A/S2-A/B/C subsets DONE; S4 actual executor/controls NOT RUN. Các trạng thái chưa commit ngày11/11 là lịch sử.

## 1. Checkout phải giữ nguyên

- Repo: `E:\phucpn-workspace\git\ai-engineering-qa-framework`, ưu tiên checkout hiện tại, không worktree khác/reset/clean/stash. Kiểm Git root/branch/HEAD/status thật và giữ mọi thay đổi phát sinh.
- Tại lúc chuẩn bị commit12/11, HEAD và remote master cùng **e61be7e0e5d64432871cc891b0061db80da189ea** chứa P4-A và S2-A/B. Commit chứa brief này bổ sung S2-C/S6-A/S6-B; xem Git log/status/remote, không assume nền cũ vẫn là latest. Entries “chưa commit/push” trong [handoff](SESSION-HANDOFF.md)/slice review records ngày11/11 là lịch sử.
- Snapshot bàn giao mới gồm toàn S2-C/S6-A/S6-B source/protocol/results/review/evidence, cache ignore và current docs. Nếu chuyển checkout/máy phải mang đủ snapshot và mọi thay đổi còn lại. User đã cấp quyền commit/push cho output hiện tại; không tự suy quyền Git/pilot/publish cho slice sau.
- S6-B tạo schema id_<uuid>/model s6b-1.0.0 mới, local hash-pinned Argon2id, opaque token hashes và explicit request facade. `_Store` là trusted maintenance, không route helper/bootstrap/SQL; không Python sandbox/HTTP auth/service-worker/broker integration. R4 source phải khớp31 input hashes; fixture TTL/rate/Argon samples không product defaults. Refresh concurrent reuse revoke cả newly returned pair, cần login lại.
- S6-A tạo namespace s6a-1.0.0 mới, hash-pinned crypto trong ignored `.cache/s6/deps`, dummy key files ngoài DB archive cũng chỉ test-only trong cache; không secured OS keystore. Restored Vault chỉ recovery-read-only. Giữ toàn S2-C/old source/protocol/evidence; không đưa private operator helpers thành QA API.
- S2-C tạo model s2c-1.0.0 trên namespace mới, không migrate S2-A/B. Portable toolchain/cluster/dumps/restore DB identity/sinks retained trong ignored `.cache/s2`, không có trong Git. DB stop trước handoff; dùng [setup](../spikes/s2/README.md) hoặc `local.py start` trên cache đúng marker khi tiếp. Không dùng DB/service/account thật hoặc env DSN.
- Historical working-file hashes khác Git blob hashes nếu normalize CRLF/LF; không sửa historical evidence để giả là hash checkout mới. Pre-commit37 paths được kiểm working/index normalized content equal,11 newline-only differences; actual latest evidence42 inputs giữ byte identity trong run.

## 2. Đọc để bắt đầu

1. `AGENTS.md`, `.agents/skills/qa-framework-development/SKILL.md`, [REVIEW-WORKFLOW](REVIEW-WORKFLOW.md).
2. Brief này, [SESSION-PLAN](SESSION-PLAN.md), phần đầu [SESSION-HANDOFF](SESSION-HANDOFF.md), [IMPLEMENTATION-PLAN](IMPLEMENTATION-PLAN.md), [DECISION-LOG](DECISION-LOG.md), [S6-B protocol](S6-B-PROTOCOL.md), [results](S6-B-RESULTS.md), [review](S6-B-REVIEW.md), [harness](../spikes/s6b/README.md); [S6-A](S6-A-RESULTS.md), [S2-C](S2-C-RESULTS.md), [S2-B](S2-B-RESULTS.md) và [S2-A results](S2-A-RESULTS.md)/[setup](../spikes/s2/README.md) chỉ đối chiếu phần reuse.
3. [P4-A-RUNTIME-REPORT](P4-A-RUNTIME-REPORT.md), [runtime review](P4-A-RUNTIME-REVIEW.md), [P4-A-PUBLICATION](P4-A-PUBLICATION.md), [publication review](P4-A-PUBLICATION-REVIEW.md).
4. [CORE-FRAMEWORK](CORE-FRAMEWORK.md), [PRODUCT-DECISIONS](PRODUCT-DECISIONS.md), [TARGET-ARCHITECTURE](TARGET-ARCHITECTURE.md) §5–6 và live policy/worker boundaries; [ADR-001](adr/001-boundaries-and-persistence.md), [ADR-002](adr/002-transport-identity-and-execution.md), [ADR-003](adr/003-stack-and-spikes.md), [ADR-004](adr/004-core-baseline-after-s1.md).
5. Chỉ đọc source/test/contracts liên quan slice chọn: [DATA-CONTRACT](DATA-CONTRACT.md), [VERIFICATION-RULES](VERIFICATION-RULES.md), [OFFLINE-REPORT](OFFLINE-REPORT.md), `qa_core/`, schemas và harness/tests. S1 evidence chỉ đọc khi cần, không mặc định rebenchmark.

## 3. Đã có gì, DONE ở đâu?

| Mốc | Hiện trạng | Không suy rộng thành |
|---|---|---|
| P0/P1/P2 | Scope; P1 v2 validator; P2 v2 evaluator, v1 replay; synthetic corpus | Authenticated judgments, domain truth hoặc runtime enforcement |
| P3-A | Architecture/ports/transport đã review | Các dịch vụ trong sơ đồ đã chạy |
| S1 | DONE: 356/356 structured cases + 28/28 CLI, ba trials/runtime; S1-RV-01..09 đóng | S2–S6, P3-B tổng thể hoặc chọn toàn stack |
| S2-A subset | Actual PostgreSQL18.6 DB14 groups PASS, 100 jobs/2 processes/4 connections, commit/rollback/crash/restart/outbox; DONE sau final CLEAN | Full S2, production DB/runtime choice, auth/worker/blob/export readiness |
| S2-B subset | Actual DB10 groups PASS: renewal/expiry/fencing, exact synthetic cleanup/reclaim, cancel/revoke persistence races, DB restart; DONE sau final CLEAN | Authenticated live revoke, actual worker/container cleanup hoặc full S2 |
| S2-C subset | DONE sau DB9 groups PASS + final CLEAN: atomic capacity, eligible RR/FIFO, metadata-only restore/replay | Production scheduler/SLA, worker/auth/physical capacity hoặc blob/key/deployment recovery |
| S4 inventory | Current Windows/WSL chưa runnable engine; actual execution/controls NOT RUN | Không mock/host fallback để đóng gate |
| S6-A subset | DONE sau10 groups PASS/final CLEAN, private storage/AEAD/key registry/rotation/revoke/recovery và closed raw-content denial | Internal identity/session/RBAC/broker/OS secure keys hoặc full S6 |
| S6-B subset | DONE sau R4 actual9 groups PASS/final CLEAN; dummy identity/session/reset/refresh/RBAC/grants/queued resources | HTTP/deployed auth, service-worker/broker binding, actual worker lifecycle hoặc full S6 |
| P4-A core/runtime slice | **DONE**: shared Python core, wrappers CLI; report/prepared v1, exact-run binding và pure completion proposal | Persisted report, actual completed run hoặc emitted report_ready |
| P4-A publication/replay slice | **DONE**: staged self-contained package v1, manifest, whole-input scopes, graph candidate và anchored replay validator | Durable publication, ordinary user export hoặc live read/outbound permission |
| P4-A tổng thể | **PARTIAL**: còn storage/transaction/outbox, scoped read/export, live auth/lease/trust và full lifecycle integration | Không lấy DONE của hai slice đóng toàn phase |
| P4-B–E, P5/P6 | Chưa implementation/gate hoàn chỉnh | Chưa có server/worker/desktop/adapters/installer production |

Python chỉ được chọn cho **pure shared core/report baseline** theo ADR-004. TS/Node `spikes/s1` là conformance spike, không second production rules engine. Control/worker runtime, DB, shell, agent host/distribution chưa chốt. PostgreSQL là candidate S2, không phải production DB đã chọn.

## 4. Output và evidence

S6-B latest [R4](s6b-results/2026-11-11-r4.json):9 groups PASS13.260s,31 inputs before=after;5 actual-process prerequisite methods PASS0.893s/core45 PASS34.430s. S6B-RV-01..05 reviewer-confirmed CLOSED/final CLEAN WT-S6B-R4-D2, subset DONE. R1 preserved historical PASS trước complete stored-account/dummy-hash CLI scans. S2-C/S6-A source/protocol/evidence giữ nguyên.

S6-A latest [R4](s6-results/2026-11-11-r4.json):10 groups PASS17.771s,42 S6 input hashes before=after;5 actual-process preflight methods PASS0.775s/core45 PASS37.048s. S6A-RV-01..05 được reviewer xác nhận CLOSED, final CLEAN. Crypto pins50.0.2/cffi2.1.1/pycparser3.12 verified local; actual S4 inventory trong evidence, NOT RUN control gates. S2-C source/protocol/evidence giữ nguyên.

S2-C latest [R4](s2c-results/2026-11-11-r4.json):9 groups PASS38.708s,42 hashes before=after,100-job/4-connection capacity + eligible RR/FIFO,13-table/100-package exact restore và outbox replay. Root full45 PASS34.619s/preflight6 PASS0.059s. RV01/RV02 được reviewer xác nhận CLOSED, final CLEAN; tại thời điểm R4 ngày11/11, S2-C chưa commit/push. S2-A/B source/protocol/evidence/core/frozen artifacts giữ nguyên.

S2-B latest [R4](s2b-results/2026-11-11-r4.json):10 groups PASS/32.140s,37 source/input hashes before=after; regression45 PASS34.940s/preflight6 PASS0.051s. Findings S2B-RV-01..04 được independent reviewer xác nhận CLOSED, final CLEAN. S2-A toàn33 R5 input/code hashes vẫn khớp; không chạy lại S1 hoặc rewrite evidence frozen. R1 S2-B SyntaxError được bảo toàn, R2/R3 snapshots lịch sử; latest R4 có đủ races và forced opposite cases.

S2-A latest [R5](s2-results/2026-11-11-r5.json): 14 DB groups PASS/22.872s; 33 source/input hashes khớp before/after; preflight 6 methods PASS/0.066s; full regression 45 methods PASS/36.754s. R1–R4 giữ historical snapshots; R2 ERROR đã giải thích và sửa đúng probe. Review ledger giữ S2A-RV-01 (driver/tzdata pin/path), đã được independent reviewer xác nhận CLOSED/final CLEAN. Không thay P4-A goldens/core/schemas/fixtures. Các evidence P4-A bên dưới giữ lịch sử theo scope cũ.

- Core: `qa_core/{contracts,rules,reports,runtime,publication,application}.py`; tools cũ giữ compatibility wrappers.
- Runtime: schemas `qa-runtime-report-v1`/`qa-prepared-report-v1`; `tools/prepare_runtime_report.py`, `test_runtime_reports.py`; goldens `examples/reports/runtime-v1/`.
- Package: schema `qa-publication-package-v1`; `tools/package_runtime_report.py`, `test_publication.py`; goldens `examples/reports/publication-v1/`.
- Latest re-review **WT-PUB-R2 CLEAN**, reviewer mới GPT-6 Astra high. Root chạy mới **45 methods pass / 37.113s**; reviewer chạy mới **45 methods pass / 36.320s**, thêm **638 deletion probes** đều reject. P4A-RV-01..06 giữ CLOSED; chưa có PUB-RV finding. Review records lưu lịch sử các vòng; không cộng probe thành unittest methods.
- Manifest **33 implementation/schema/test/golden paths** trước commit: `325c39c933a448434c842c297917e27232c5714f3176b83fd2f96980755fa478`. Inventory lịch sử: sorted union Git diff names + untracked names tại lúc review, lọc prefixes `qa_core/`, `tools/`, `schemas/`, `examples/`; dòng path + ASCII space + SHA256(file bytes), join LF không trailing LF, SHA256 UTF-8 toàn chuỗi. Sau commit cây sạch sẽ không còn inventory đó trong Git diff; dùng danh sách paths của snapshot/commit nếu kiểm lại, không hash danh sách rỗng để so. Đây không là hash toàn repo/trust proof; xem review records cho snapshot trước administrative doc updates.
- **Manifest Git blob của cùng 33 paths** trong commit `e56ed7d`: `34222735b29d8450e93742cced92dc7a66536566526c5acf014d5ea0b99c2878`. Lấy paths từ diff-tree commit đó, lọc bốn prefixes trên; dùng bytes `git show e56ed7d:<path>` và cùng thuật toán manifest. Khác hash pre-commit vì Git chuẩn hoá CRLF thành LF ở 22 files; đã đối chiếu từng file, sau chuẩn hoá xuống dòng nội dung hoàn toàn khớp. Không sửa hash lịch sử để giả là cùng byte representation. Khi kiểm checkout mới, phân biệt working-file bytes với Git blob bytes.

## 5. Việc cần làm tiếp

**Ưu tiên tiếp: identity→application/live-policy/broker integration contract và acceptance/failure protocol**, theo [SESSION-PLAN](SESSION-PLAN.md). S6-B facade chưa nối S6-A private vault/S2 worker/core publication. Chốt user vs service/worker actor, policy/epoch/snapshot authority, deny/revoke/error semantics trước implementation; không tự route trusted helpers thành network API. Không real account/key/API hoặc production transport/runtime decision; không rerun S1/S2/S6-A mặc định nếu source không đổi.

S4 execution vẫn NOT RUN: cần approved runnable rootless engine + pinned image và thực đo network/resource/output collector/cleanup controls. Không dùng discovered absence làm proof mọi host absent, cũng không mock controls hoặc cài global. Full S6/P3-B/P4-B/C còn deployed auth/service-worker/broker/key custody/live-policy integration; source/old-input preservation và high-model review loop giữ nguyên. Không chốt production DB/runtime/platform hoặc tự commit/push phase mới.

Nếu actual disposable DB chưa sẵn, không dùng DB/account thật hoặc SQLite/in-memory mock để gọi S2 PASS. Hoàn thành protocol/harness/preflight phần độc lập, ghi DB checks NOT RUN/unknown và bước khôi phục cụ thể. Routine trong slice tiếp được giao thì tự làm; thiếu input/authority bắt buộc mới hỏi cụ thể, vẫn tiếp phần độc lập.

## 6. Semantics và giới hạn phải bảo toàn

- Mandatory declared satisfied nhưng missing/stale/unaccepted review → effective pending → incomplete khi không có failed khác. Optional pending đơn thuần không chặn; failed giữ precedence và các gap vẫn hiện. Raw pending không tự hết nhờ review.
- Giữ raw handoff/AC/assessment, revision/provenance/mapping, humanDecision riêng. Không mutate inputs, hạ AC thành unverified giả hoặc nâng P2 complete để né P1 v2. New contracts/output phải version rõ; bảo toàn schema/corpus/fixture lỗi/evidence/protocol frozen.
- Legacy P1 v2 exporter vẫn `projection_unsupported`; runtime graph/package không là P1 v2 bundle. Persist/ref/read/event chỉ claim khi boundary thật implemented và verified.
- Package chứa **whole raw bundle**, có thể có project/task khác target; restricted internal replay metadata không phải ACL. So expected input digests/IDs caller giữ độc lập, không lấy anchors từ package. Không tự đưa gói qua ordinary QA read/export/model outbound.
- Snapshot scope ∩ live policy khi có runtime; chưa auth/lease/container/egress thì không nói đã enforce. Không gọi key/account/API/project thật, pilot/public publish, tự chọn platform/distribution/shell hoặc cài global.

## 7. Cách làm một session

Theo [SESSION-PLAN](SESSION-PLAN.md): Git/brief → chốt slice và acceptance trước sửa → implementation + failure/regression checks → reviewer độc lập high-model → fix/recheck/re-review đến clean → DONE đúng scope và bàn giao. Không đặt trần vòng review, không lấy suite xanh thay verdict, giữ stable finding IDs và reopen lỗi cũ nếu regression. Routine phần độc lập tiếp tục trong quyền; quyền commit/push12/11 chỉ áp output hiện tại, phase sau cần yêu cầu phù hợp.

Regression hiện hành: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`. 45 methods là kết quả hiện tại, không quota vĩnh viễn. Docs-only bàn giao kiểm links/fences/consistency/diff và manifest, không cần rerun suite/S1 khi code không đổi. Không chạy runners ghi đè evidence gốc.
