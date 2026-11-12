# Yêu cầu Git và bước tiếp — 12/11/2026

User yêu cầu **“Commit, push và tiếp tục”** cho toàn output bàn giao HS2, IAP contract và lần chạy thử hiện có đã CLEAN. [Pre-push record](IAP-PUSH-REVIEW.md) kiểm exact snapshot trước Git action; kiểm Git log/remote và handoff mới nhất sau action để biết commit/push thực, không coi intent này là bằng chứng đã push. Những câu chưa commit/push/không có quyền Git trong phần dưới là lịch sử trước yêu cầu mới.

Sau push sẽ tiếp **IAP-A queued-command subset**: common transaction-aware user identity/live policy/start/cancel/idempotency trên fresh synthetic namespace, protocol/selected acceptance trước code. Không broker/service-worker/engine/production stack hoặc gọi account/key/API thật; không dùng subset DONE đóng full S4/S6/P3-B/P4-B. Giữ source/protocol/evidence/fixture cũ; output phát triển sau push để review riêng, chưa tự push tiếp.

# Cập nhật chạy thử — 12/11/2026

Theo yêu cầu “Hãy run thử”, đã chạy **implementation hiện có** với dữ liệu synthetic: S6-B identity/session/RBAC9 groups PASS14.939s và core/report45 tests PASS33.866s. Prerequisites local pins READY; fresh schema/new evidence,31 inputs before=after/current hashes match, DB đã stop/status exit3,328 original nonignored paths không đổi ngay sau run. [Kết quả/evidence/review](IAP-TRY-RUN-2026-11-12.md) **DONE cho hồ sơ chạy thử subset sau independent CLEAN TRY-R1 và required checks PASS**; reviewer Terra high xác nhận không finding trong scope.

Chưa có implementation để chạy24 IAP integration cases: tất cả vẫn NOT RUN integration; lượt chạy này không thêm HTTP/UI/worker/broker/runtime hoặc đóng full S4/S6/P3-B/P4-B. Không source/old protocol/evidence/fixture thay đổi; nội dung docs cũ giữ nguyên phía dưới. No real account/key/API, production stack, commit/push. Việc tiếp vẫn bounded integration harness theo IAP §10 sau scope/schema/selected acceptance mới, không tự triển khai trong lượt chạy thử.

# Session hiện hành — contract IAP-1.0.0, 12/11/2026

Yêu cầu mới từ session tiếp nhận thay trạng thái “chỉ chuẩn bị bàn giao” bên dưới: thực hiện identity→application/live-policy/broker **contract và acceptance/failure protocol**, chưa runtime integration. Baseline master `ef6d3c162ff68fab568d19c8eac9c50892d304c2`; bốn docs bàn giao sau push đã có, giữ toàn nội dung cũ bằng entry mới, không reset/clean/stash/chuyển worktree.

Outputs: [protocol](IDENTITY-APPLICATION-PROTOCOL.md) IAP-1.0.0 với port/source/trust/operation matrices và24 obligations; [review record](IDENTITY-APPLICATION-REVIEW.md); current NEXT/plan/handoff/implementation plan/decision D-32. **DONE docs slice sau independent CLEAN WT-IAP-R2/R2a và required docs checks PASS**; doneWhen docs-only đã đạt: source mapping chính xác, user/service và snapshot/live/private-Vault/broker tách rõ, acceptance có expected/observations/NOT RUN, links/fences/preservation/diff checks PASS và independent Terra high CLEAN trên latest snapshot, stable IAP-RV IDs. Không dùng DONE slice đóng full product gates.

Quyết định ghép: interactive access/family lifetime không là background worker credential. RunDelegation có nguồn/epoch/ceiling riêng; logout/access expiry dừng interactive, còn reset/change/disable/admin-change hoặc project/delegation revoke fence background. Snapshot promotion không mở rộng quyền cũ. Common atomic auth/mutation và external release/revoke ordering là yêu cầu thiết kế, chưa provider/dispatcher implementation. Broker chỉ sink-bound secret-use, không raw-secret/raw-log read/export/stream/attachment/source cho bất cứ role nào.

Checks phiên này chỉ docs/source preservation; không DB/core/runtime rerun, không tạo integration PASS. Reviewer độc lập model cao chỉ định trước sửa; gửi exact snapshot + source/evidence/checks, fix→recheck→re-review đến CLEAN. Kết quả và hashes tại review record. Giữ record HS2 nguyên vẹn, source/schema/protocol/evidence cũ và fixture có lỗi không đổi; thêm current entries để phân biệt lịch sử với tiến độ mới.

Tiếp sau output này: chọn bounded synthetic common-policy/RunCommand harness theo protocol §10, namespace mới + version/schema/selected obligations trước code; không tự bắt đầu ngoài scope phiên contract. S4 actual controls NOT RUN; full S6/P3-B/P4-B còn mở. No real accounts/keys/API/projects, production stack/runtime integration, commit/push/publish.

---

Phần dưới là kế hoạch/bàn giao lịch sử, giữ nguyên bytes; “dự kiến/chưa triển khai slice” áp dụng tại thời điểm bàn giao, không phủ nhận draft contract mới ở trên.

# Plan cho session tiếp — sau push ef6d3c1

12/11/2026. Baseline master **ef6d3c162ff68fab568d19c8eac9c50892d304c2 đã push/remote verified**, gồm57 files S2-C/S6-A/S6-B. [NEXT-SESSION](NEXT-SESSION.md) là entry point; bốn docs bàn giao mới sau push chưa commit, phải giữ/chuyển đủ. Những plan thực thi bên dưới là lịch sử, không là việc cần chạy lại. User hiện yêu cầu chuẩn bị bàn giao; chưa triển khai slice mới hoặc Git action mới.

## Mục tiêu dự kiến cho một phiên

Chốt **contract và acceptance/failure protocol cho identity→application/live-policy/broker** thuộc hướng P3-B/P4-B. Giải quyết chỗ ghép giữa S6-B user/session/snapshot grants, application/core report, S2 transaction/outbox và S6-A private Vault. Đây là protocol/design slice trước integration, không claim có API/worker/broker mới.

Outputs dự kiến (chưa có tại lúc bàn giao): một protocol versioned `docs/IDENTITY-APPLICATION-PROTOCOL.md` có trust/authority/operation matrix, mapping ports→source hiện có và failure matrix; một review record mới cho slice; cập nhật current plan/decision/handoff theo kết quả. Không đổi frozen protocols hoặc migrate các spike cũ để giả đã tích hợp. Nếu phiên sau mở rộng sang harness, ghi scope/acceptance mới trước code và chỉ claim actual behavior đã chạy; không dùng prose contract đóng integration gate.

## Trình tự và điều kiện xong

1. Kiểm Git/remote/status/cache thực; đọc AGENTS/skill/review workflow và current docs. Mang đủ bốn docs chưa commit nếu đổi checkout. Chỉ định high-model reviewer read-only từ đầu, giao scope/source/evidence cùng bản cụ thể.
2. Đọc S6-B `Identity.dispatch`/trusted `_Store`, S6-A Vault/raw-content denial, S2-C/S2-B transactions và `qa_core/application.py`/runtime/publication. Liệt kê port nào có implementation, port nào chỉ thiết kế; không tạo second rules engine hoặc tự chọn production runtime/DB/transport.
3. Chốt user actor vs service/worker identity, credential/session/role/project live state vs persisted snapshot grant, trusted policy provider và thao tác nào cần atomic recheck cùng mutation. Scope project/run/content/version/attempt không suy từ client role/authorized/cleanup flag hoặc ciphertext possession.
4. Mapping tối thiểu start/cancel/read-report/source/export/secret-use: preconditions, owner component, trust input, current policy/epoch fence, deny/error, audit/outbox/rollback/retry boundary. Chỉ rõ raw-secret/raw-log direct read/export/stream/attachment luôn deny mọi role; secret-use qua scoped broker là proposed contract, chưa actual injection. Không tự approve hoặc gửi whole-input replay package ra ordinary read/export.
5. Failure matrix phải phân biệt old/expired/reset/disabled session, refresh replay, cross-project ref, role promotion không mở rộng snapshot/downgrade/revoke, thay policy giữa authorize và write, stale worker/attempt/lease, broker misuse và secret-tainted output. Mỗi case có expected, observation/evidence cần thu và NOT RUN nếu chưa harness; synthetic bool không chứng minh authenticated worker cleanup.
6. Reviewer kiểm đúng latest output: tính chính xác/thực dụng/khả năng kiểm, lỗi cũ/tái xuất hiện/mới. Fix→checks→re-review đến CLEAN, stable IDs, không số vòng tối đa. Docs checks links/fences/diff/source-reference preservation phù hợp; không rerun suite/DB chỉ vì viết plan.
7. DONE chỉ protocol/output sau CLEAN+checks, full runtime integration vẫn open. Bàn giao ghi actual/unknown/next action; không commit/push docs hoặc implementation mới khi chưa được giao.

## Nhánh prerequisite

S4 actual engine controls vẫn NOT RUN từ discovery11/11. Khi công việc cần engine, inventory lại khả năng hiện tại trước khi gọi READY, không assume hôm nay y hệt; cần runnable rootless engine/pinned image và actual network/resource/collector/cleanup evidence. Không global install/host fallback/mock PASS. Protocol độc lập tiếp tục nếu engine thiếu. Local retained PostgreSQL cluster đã stop; chỉ start marker-bound synthetic cluster khi actual DB check được chọn, theo S2 README. Máy mới cần setup/preflight pins trước; cache không ở remote.

## Verification và semantics

Source/core/schema/corpus/goldens/old protocols/evidence giữ nguyên nếu chỉ làm contract. Runtime report/completion proposal và staged replay package chưa là durable completed/outbox hoặc ordinary scoped export. Declared/effective constraints, revision/provenance/input anchors/humanDecision phải bảo toàn; legacy projection unsupported giữ nguyên. No real accounts/keys/API/projects/pilot/publish hoặc production stack/platform choice.

## S2-C đã thực thi (lịch sử)

## S2-C đã thực thi và việc tiếp

User yêu cầu commit/push rồi tiếp: S2-A/B commit e61be7e và remote master verified, checkout sạch trước S2-C. [Protocol](S2-C-PROTOCOL.md) và `spikes/s2c/` model riêng; [R4](s2c-results/2026-11-11-r4.json) DB9 groups PASS38.708s,42 hashes before=after; full45 PASS34.619s/preflight6 PASS0.059s. [Review](S2-C-REVIEW.md) final CLEAN, S2-C subset DONE. S2-C output mới chưa commit/push; giữ old code/protocol/evidence/frozen artifacts.

Ưu tiên tiếp **S4/S6 prerequisite inventory và boundary protocol** cho actual executor/policy/identity, rồi runtime composition/P4-B/C. Kiểm công cụ/khả năng hiện tại, không dùng discovery cũ để assume READY. Chốt purpose/outputs/acceptance/fault matrix trước implementation, actual disposable engine/libs/dummy identities mới đóng integration gates; thiếu prerequisite tiếp phần độc lập và ghi NOT RUN/gap/restore step. Không dùng cleanup bool hoặc metadata restore làm proof container stop/auth/revoke/blob-key recovery. S2-C không tự quyết định production DB/control-worker hoặc chọn desktop/plugin platform; không rerun S1/S2 mặc định khi source không đổi.

## Ghi nhận S2-B trước S2-C (lịch sử)

## S2-B đã thực thi và việc tiếp

11/11/2026, user yêu cầu tiếp. [Protocol](S2-B-PROTOCOL.md) chốt trước sửa; `spikes/s2b/` model riêng và [results](S2-B-RESULTS.md) R4 DB10 groups PASS/32.140s,37 source/input hashes before=after; full regression45 PASS34.940s và preflight6 PASS0.051s. [Review](S2-B-REVIEW.md) final CLEAN, S2-B subset DONE. S2-A source/evidence/33 input paths không đổi, checkout d73dce3 + toàn uncommitted outputs được giữ.

Ưu tiên sau S2-B là S2-C đã được user yêu cầu/thực thi như entry đầu file. DB-only metadata restore không đóng external blob/key recovery. S4/S6 phải kiểm authenticated revoke và actual worker/container cleanup trước full lifecycle gate; giữ NOT RUN đúng boundary, không dùng DB subsets đóng full S2/P3-B/P4-A/P4-B.

## Plan S2-A đã thực thi (giữ acceptance lịch sử)

Ngày 11/11/2026. **Đã thực thi S2-A DB subset, DONE sau clean review trong subset**: [actual results](S2-A-RESULTS.md), [review](S2-A-REVIEW.md). Nội dung bên dưới giữ acceptance/nhánh READY–NOT READY đã dùng, không còn là bước chưa bắt đầu. Đọc [NEXT-SESSION](NEXT-SESSION.md), [ADR-003](adr/003-stack-and-spikes.md). Không coi spike này là production DB/runtime decision.

## Đích phiên và outputs

Tiến từ staged package đã DONE sang **S2-A subset** kiểm chứng concurrent claim + atomic report/completed/outbox trên đúng run/version/attempt, dùng DB riêng synthetic và crash/recovery evidence. Ưu tiên candidate PostgreSQL của ADR-003. Không triển khai toàn server/auth/worker/container/UI trong một lần. Spike language/driver không tự chọn runtime control/worker; Python core vẫn source of truth report semantics.

Outputs đã tạo: `docs/S2-A-PROTOCOL.md`, `spikes/s2/` (preflight/pinned harness/setup-stop), `docs/S2-A-RESULTS.md`, `docs/s2-results/2026-11-11-r1.json` đến `r5.json`, `docs/S2-A-REVIEW.md`, cập nhật plan/decisions/handoff. Versions/input-code hashes/commands/expected-actual/faults/limits nằm trong results và evidence. Không regenerate goldens cũ.

## Trình tự

| Bước | Làm gì | Điều kiện/đầu ra |
|---|---|---|
| 1. Baseline | Kiểm root/branch/HEAD/status thật, tracked + untracked changes; đọc brief/plan/review/decisions; confirm Python executable | Giữ đủ snapshot; không reset/clean/stash |
| 2. Prerequisites | Read-only discovery DB/driver/container tools/versions và khả năng tạo disposable instance; không dump env/secrets hoặc kết nối service thật | READY hoặc NOT READY từ actual observations; không dùng observation 05/11 làm trạng thái hôm nay |
| 3. Chốt slice | Nêu purpose/outputs/acceptance, invariant/fault matrix, scope DB experiment; chỉ định reviewer độc lập high-model trước sửa | Protocol versioned; S2-A subset/gaps rõ |
| 4. Hiện thực | READY: DB harness thật; NOT READY: protocol/preflight/harness độc lập, DB checks NOT RUN | Không dùng mocks để gọi DB gate pass |
| 5. Verify | Behavior/failure/regression theo vùng; before/after DB state và package hashes; đọc nguyên nhân trước retry | Actual evidence và safe diagnostics, không đổi expected để làm xanh |
| 6. Review loop | Gửi đúng latest snapshot + scope/tests/results/gaps/ledger; fix/check/re-review lỗi cũ/tái xuất hiện/mới | Stable IDs, high-model clean + required checks pass; không tự giới hạn số vòng |
| 7. Chốt phiên | Cập nhật plan/decisions/review/handoff/NEXT-SESSION; diff/status cuối | DONE đúng output/slice; completed/partial/not-run và việc tiếp; không tự commit/push |

## READY — actual DB experiment

Chỉ dùng instance/database riêng tạo cho spike với dummy identities/data. Không reuse DB/service công việc thật hoặc tự lấy connection string/secret từ môi trường. Toolchain nếu cần thì dùng project-local/portable/disposable trong quyền có sẵn, verify official version/support/integrity và pin trước chạy; không cài global/thay cấu hình hệ thống. Thiếu quyền/khả năng thì chuyển NOT READY.

1. Adapters/harness ở `spikes/s2/`, tách core. Document DB schema/CAS/uniqueness/claim/transaction semantics và cleanup scope. Payload dùng package v1 hiện tại; round-trip phải giữ canonical bytes/digests và caller-held anchors. Không chỉ đọc normalized JSON rồi giả raw representation/hash được giữ. Blob staging/integrity/durability thật kiểm riêng; thiếu thì không claim durable publication.
2. Seed **100 synthetic jobs**, dùng **2 processes/4 independent DB connections** tranh claim theo ADR-003. Kiểm row-lock/CAS/unique constraints thật, accepted attempts/tokens/versions và no duplicate claim/report/initial occurrence run. Không serialize mọi request trong một process rồi gọi concurrency proof.
3. Thử atomic unit **report metadata ref + completed transition + report_ready outbox row** trong một transaction; validate package và current DB preconditions trong đúng boundary. Concurrent completion/cancel-state transition chỉ một terminal winner. Rollback/commit failure không expose subset. Event chỉ readable/deliverable sau commit; delivery có thể trùng, không hứa exactly-once execution/delivery.
4. Kill/restart harness trước/sau commit, result acceptance và outbox delivery/ack; query từ connection/process khác sau restart. Ghi fault points inject/observe thật, pending points không gộp pass; kiểm accepted rows, sequence/ref, immutable package integrity và retry bounded.
5. Thử stale version/attempt/token, terminal repeat, duplicate IDs và unresolved-cleanup block trong **DB model của spike**. Synthetic permission/revoke/cleanup facts chỉ kiểm persistence predicates, không chứng minh authenticated live policy hoặc worker cleanup. Cancel/revoke/cleanup chưa kiểm đủ giữ gate partial. Thu latency/queue age và môi trường thực, không suy throughput SLA từ fixture.

ADR-003 đặt execution timebox 60 phút **sau khi prerequisites sẵn**: engineering protocol, không SLA user. Hết timebox giữ actual/unknown và bước tiếp, không đổi thresholds/bỏ failures để gọi pass. Review loop không bị cắt vì hết timebox spike; có thể hoàn tất reviewed partial results, không tự đóng S2.

## NOT READY — phần độc lập vẫn làm

Ghi tool/runtime/capability thiếu cùng safe discovery commands/results; không suy absence chỉ vì không có PATH. Hoàn thiện protocol/preflight fail-closed/harness/tests độc lập nếu có thể, review đúng scope. Results ghi DB race/crash/restart **NOT RUN/unknown**; không dựng benchmark hoặc JSON evidence pass. Nếu local disposable setup trong quyền đã có khả thi, tự hoàn thiện rồi chuyển READY; chỉ hỏi khi thiếu quyền/input bắt buộc và nêu quyết định nhỏ nhất.

Có thể DONE **preparation/protocol output** sau clean review/checks, nhưng S2-A DB experiment/S2/full P4-A vẫn PARTIAL/NOT RUN. Không dùng SQLite/mock thay PostgreSQL để đóng candidate gate; phương án so phải có label/scope/evidence riêng.

## Acceptance và bàn giao

- Outputs khớp scope chốt; nguồn/snapshot/version/execution truy được, raw/effective constraints/mapping/provenance/human decision của core giữ nguyên.
- READY: invariants đã chọn có actual DB evidence/checks pass, gaps ghi riêng. NOT READY: preparation được verify/review, DB tests không claim pass và có bước khôi phục.
- Full regression khi code/shared behavior đổi: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`, thêm S2-specific tests; 45 methods hiện tại không chứng minh DB correctness. Không mặc định rerun S1 trials hoặc ghi đè fixtures/evidence/goldens.
- High-model reviewer clean trên latest output, stable IDs/reopen lỗi cũ nếu regression. Review record có commands/results/limits/verdict; không đếm rounds thay checks hoặc giữ DONE khi blocker mới xuất hiện.
- Bàn giao completed/partial/gaps/việc tiếp, diff/status và quyền còn thiếu. Không đóng P3-B/S2/P4-A/P4-B hoặc toàn sản phẩm từ một subset.

Sau phiên này tiến theo evidence: full S2 (queue/crash/cancel/revoke/cleanup/fairness/restore), runtime/storage ADR rồi P4-B transaction adapter; scoped read/export, S4/S6, S5 adapters và S3/desktop có prerequisites riêng. Không tự chọn platform/distribution, gọi account/API/project thật, pilot hoặc publish.

## Kết quả và bước tiếp sau S2-A

Actual disposable PostgreSQL18.6/psycopg3.3.8 đã READY qua portable project-local setup. Latest R5: DB14 groups PASS/22.872s, 6 preflight methods PASS, 45 regression methods PASS; output DONE sau final CLEAN trong review record. Working tree dựa d73dce3, chưa commit/push. Không dùng preparation DONE hoặc DB subset PASS đóng full S2/P4-A/P4-B.

Ưu tiên sau S2-A là **S2-B**, đã được user yêu cầu và thực thi như entry hiện hành đầu file. DB persistence subset không thay authenticated revoke hoặc worker cleanup proof; fairness/restore vẫn cần actual evidence riêng. Giữ acceptance/phân biệt READY–NOT READY bên trên như protocol session S2-A, không đọc là S2-B chưa bắt đầu.
