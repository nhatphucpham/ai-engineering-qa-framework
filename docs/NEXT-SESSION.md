# Yêu cầu Git và bước tiếp — 12/11/2026

User yêu cầu **“Commit, push và tiếp tục”** cho toàn output bàn giao HS2, IAP contract và lần chạy thử hiện có đã CLEAN. [Pre-push record](IAP-PUSH-REVIEW.md) kiểm exact snapshot trước Git action; kiểm Git log/remote và handoff mới nhất sau action để biết commit/push thực, không coi intent này là bằng chứng đã push. Những câu chưa commit/push/không có quyền Git trong phần dưới là lịch sử trước yêu cầu mới.

Sau push sẽ tiếp **IAP-A queued-command subset**: common transaction-aware user identity/live policy/start/cancel/idempotency trên fresh synthetic namespace, protocol/selected acceptance trước code. Không broker/service-worker/engine/production stack hoặc gọi account/key/API thật; không dùng subset DONE đóng full S4/S6/P3-B/P4-B. Giữ source/protocol/evidence/fixture cũ; output phát triển sau push để review riêng, chưa tự push tiếp.

# Cập nhật chạy thử — 12/11/2026

Theo yêu cầu “Hãy run thử”, đã chạy **implementation hiện có** với dữ liệu synthetic: S6-B identity/session/RBAC9 groups PASS14.939s và core/report45 tests PASS33.866s. Prerequisites local pins READY; fresh schema/new evidence,31 inputs before=after/current hashes match, DB đã stop/status exit3,328 original nonignored paths không đổi ngay sau run. [Kết quả/evidence/review](IAP-TRY-RUN-2026-11-12.md) **DONE cho hồ sơ chạy thử subset sau independent CLEAN TRY-R1 và required checks PASS**; reviewer Terra high xác nhận không finding trong scope.

Chưa có implementation để chạy24 IAP integration cases: tất cả vẫn NOT RUN integration; lượt chạy này không thêm HTTP/UI/worker/broker/runtime hoặc đóng full S4/S6/P3-B/P4-B. Không source/old protocol/evidence/fixture thay đổi; nội dung docs cũ giữ nguyên phía dưới. No real account/key/API, production stack, commit/push. Việc tiếp vẫn bounded integration harness theo IAP §10 sau scope/schema/selected acceptance mới, không tự triển khai trong lượt chạy thử.

# Hiện hành — identity/application contract, 12/11/2026

Session tiếp nhận đúng checkout master `ef6d3c162ff68fab568d19c8eac9c50892d304c2`, đủ bốn tài liệu bàn giao chưa commit. Nội dung bàn giao HS2-R1 bên dưới giữ nguyên như lịch sử; entry này là tiến độ mới, không sửa verdict/evidence của HS2.

Đã soạn [IAP-1.0.0](IDENTITY-APPLICATION-PROTOCOL.md): trust/authority/operation matrix, port→source, session vs background delegation, snapshot ceilings vs live epochs, atomic mutation/release ordering, private Vault vs scoped broker và24 acceptance/failure obligations. Đây là **design/docs slice, integration NOT RUN**; trạng thái **DONE docs slice sau independent CLEAN WT-IAP-R2/R2a và docs checks PASS**, xem [record](IDENTITY-APPLICATION-REVIEW.md). Không có API/worker/broker implementation mới, không gọi account/key/API thật, không commit/push.

Đọc protocol và record mới cùng AGENTS/skill/REVIEW-WORKFLOW, SESSION-PLAN/current handoff/decision D-32; sources S6-B/S6-A/S2-B/C và pure core giữ nguyên. Mọi tài liệu hiện tại mới/cũ chưa commit phải giữ trên checkout này; `.cache/s6/identity-application-2026-11-12` chỉ local check/baseline cache, không portable runtime evidence. Không reset/clean/stash/chuyển worktree.

Việc tiếp sau CLEAN: bounded synthetic transaction-aware UserIdentity/LivePolicy/RunCommand harness trong namespace mới, chọn schema/acceptance trước code theo protocol §10; prerequisite và quyền runtime scope mới phải được chốt, không suy docs DONE thành quyền tự tích hợp toàn runtime. Chưa chọn production stack; chưa authenticated broker/service/actual cleanup. Full S4/S6/P3-B/P4-B và toàn readiness giữ mở, S4 actual NOT RUN. Không rerun S1/S2/S6 mặc định; giữ old evidence/frozen fixtures và latest working-byte/Git-EOL limits ở bàn giao cũ.

# Bàn giao session mới — 12/11/2026

Đọc file này trước khi tiếp tục. **Code/evidence đã commit và push** tại master **`ef6d3c162ff68fab568d19c8eac9c50892d304c2`** (`feat: add capacity, encrypted storage and identity spikes`,57 files). HEAD/origin/master/remote master đã được kiểm cùng hash; cây sạch ngay sau push. [Pre-push review](S2C-S6-PUSH-REVIEW.md) lưu hai vòng CLEAN; đây là record trước action, kết quả Git thực ghi tại [handoff](SESSION-HANDOFF.md).

**Bàn giao này là thay đổi tài liệu mới sau commit trên, chưa commit/push.** Giữ bốn file `docs/NEXT-SESSION.md`, `docs/SESSION-PLAN.md`, `docs/SESSION-HANDOFF.md`, `docs/SESSION-TRANSFER-2026-11-12-REVIEW.md`. Session mới trên cùng checkout thấy đủ; nếu chuyển máy/checkout phải mang cả bốn file cùng commit ef6d3c1, không chỉ kéo remote. Review bàn giao theo [record](SESSION-TRANSFER-2026-11-12-REVIEW.md); **bàn giao DONE sau independent CLEAN HS2-R1**.

## Checkout và dữ liệu phải giữ

- Repo `E:\phucpn-workspace\git\ai-engineering-qa-framework`, PowerShell/Windows; ưu tiên checkout hiện tại. Kiểm root/branch/HEAD/status thật, giữ thay đổi mới; không reset/clean/stash hoặc tạo worktree khác mặc định.
- Commit ef6d3c1 chứa S2-C/S6-A/S6-B và mọi source/protocol/results/review/evidence tương ứng. Các câu chưa commit/push/no Git authority trong records ngày11/11 là lịch sử. Yêu cầu commit/push trước đã hoàn tất; docs bàn giao/phase mới chưa được yêu cầu commit/push.
- `.cache/s2`, `.cache/s6`, `.cache/s6b` chỉ retained/ignored trên máy hiện tại, không nằm trong Git. Portable PostgreSQL18.6/driver, pinned crypto/Argon2 deps, dumps và dummy credential/key fixtures không tự có trên máy mới. DB đã dừng; kiểm marker/preflight và dùng [S2 setup](../spikes/s2/README.md) trước start; không nhận DSN/service thật. Không cài global hoặc chép key/password fixture vào Git.
- Evidence hashes là **working bytes tại lần chạy**. Git chuẩn hóa CRLF→LF ở17/57 files của commit mới; đã đối chiếu toàn57 normalized contents khớp. [Pre-push record](S2C-S6-PUSH-REVIEW.md) có manifests56 body paths loại self-record. Checkout mới có thể khác raw hash do EOL: phân biệt Git blobs/working bytes, không sửa historical hashes hoặc gọi raw mismatch là PASS.

## Trạng thái và evidence

| Phần | Đã xong trong scope | Còn mở |
|---|---|---|
| P0/P1/P2/P3-A | Scope/contracts/rules/reference reports/architecture; shared Python core/report baseline | Không là deployed system/trusted domain judgment |
| P4-A core/runtime + publication/replay slices | DONE sau review; pure reports và staged anchored package | Full P4-A partial; durable integration, ordinary scoped read/export/live auth còn mở |
| S1 | PASS356 cases +28 CLI,3 trials/runtime; Python chỉ chọn cho pure core | Chưa chọn control/worker/desktop/plugin runtime hoặc production DB |
| S2-A/B/C subsets | DONE/CLEAN; PostgreSQL transaction/outbox, lease/recovery predicates, capacity/fairness/metadata restore | Auth/worker/container cleanup/blob/key/runtime composition; không full S2 |
| S6-A | DONE/CLEAN; private encrypted storage/nonce/key lifecycle/recovery/raw-content denial | Chưa authenticated broker/OS key custody |
| S6-B | DONE/CLEAN; dummy Argon2id accounts/sessions/reset/refresh/RBAC/grants/queued resources | Chưa network auth/service-worker/broker/core integration |
| S4 | Discovery ngày11/11 chưa tìm runnable engine trong phạm vi đã kiểm; actual controls **NOT RUN** | Cần runnable rootless engine/pinned image/network/resource/collector/cleanup; không suy mọi host đều thiếu |
| P3-B/full S6/P4-B–E/P5/P6 | Chưa đóng full gates | Chưa server/worker/dashboard/installer production, chưa pilot/publish |

Latest evidence: [S2-C R4](s2c-results/2026-11-11-r4.json)9 groups PASS38.708s/42 inputs; [S6-A R4](s6-results/2026-11-11-r4.json)10 groups PASS17.771s/42 inputs; [S6-B R4](s6b-results/2026-11-11-r4.json)9 groups PASS13.260s/31 inputs. Mỗi run inputsBefore=inputsAfter; root/reviewer đã rehash current source trước push, old S2-A33/S2-B37 inputs cũng khớp. Historical ERROR/older PASS snapshots giữ nguyên, không thay latest coverage.

Checks thực chạy trước push12/11: core45 PASS33.658s; prerequisite S6-A5 PASS1.054s/S6-B5 PASS0.869s/S2-common6 PASS0.087s. Hai vòng reviewer Terra high CLEAN, prior S2C-RV-01..02/S6A-RV-01..05/S6B-RV-01..05 CLOSED. Không rerun DB workloads cho docs-only/Git action; không cộng counts thành AC readiness. Bàn giao hiện tại chỉ kiểm docs/Git/hash, không tạo execution evidence mới.

## Việc tiếp — một slice cụ thể

Ưu tiên **identity→application/live-policy/broker integration contract và acceptance/failure protocol**, theo [SESSION-PLAN](SESSION-PLAN.md). Đây là việc dự kiến, **chưa triển khai**: nối semantics S6-B user/session/grant với application operations, S2 durable mutations và S6-A private storage mà không để client/worker tự khai authority. Chưa route trusted `_Store`/Vault helpers ra API hoặc tự chọn production runtime/transport. Không lặp DONE slices hoặc rerun S1/S2/S6 mặc định.

Mở phiên: đọc `AGENTS.md`, `.agents/skills/qa-framework-development/SKILL.md`, [review workflow](REVIEW-WORKFLOW.md), brief này/[session plan](SESSION-PLAN.md), [implementation plan](IMPLEMENTATION-PLAN.md), phần mới nhất [decision log](DECISION-LOG.md)/[handoff](SESSION-HANDOFF.md). Sau đó đọc [product decisions](PRODUCT-DECISIONS.md), [core semantics](CORE-FRAMEWORK.md), [target architecture](TARGET-ARCHITECTURE.md), [ADR-002](adr/002-transport-identity-and-execution.md), [ADR-003](adr/003-stack-and-spikes.md) và S6-A/B/S2-C protocol/README/source liên quan. Plans/candidates không là code có sẵn.

## Cách làm và giới hạn

Chốt purpose/scope/outputs/doneWhen/failure matrix trước sửa; chỉ định ít nhất một reviewer độc lập model cao từ đầu. Review→fix→actual checks phù hợp→re-review đến CLEAN, stable finding IDs, không đặt trần vòng. DONE chỉ subset được kiểm, không thay human approval hay tự cấp quyền Git/publish. Thiếu prerequisite thì phần phụ thuộc NOT RUN, phần độc lập vẫn tiếp tục.

Giữ synthetic/frozen core/schema/corpus/fixture lỗi/protocol/evidence; không thật account/key/API/project, pilot hoặc global install. Raw/effective constraints, provenance/revision/input anchors và humanDecision giữ tách biệt. Legacy P1v2 projection vẫn unsupported; report/package không tự là persisted completion/read/export permission. Whole-input package có thể chứa scope khác target; không gửi qua ordinary QA/model outbound. S6-A helper là private operator; S6-B facade tin host/DB, không Python sandbox/HTTP deployment. Concurrent refresh reuse revoke cả pair vừa trả, cần reauthenticate; TTL/rate/Argon timings không production defaults.
