# Plan một session kế tiếp — S2-A prerequisite và transaction spike

Ngày 11/11/2026. **Kế hoạch chưa được thực thi**; bắt đầu khi session tiếp nhận yêu cầu tiếp tục. Đọc [NEXT-SESSION](NEXT-SESSION.md), [ADR-003](adr/003-stack-and-spikes.md) và architecture storage boundary. User có thể đổi ưu tiên; ghi lý do trong decision log. Không coi plan này là production DB/runtime decision.

## Đích phiên và outputs

Tiến từ staged package đã DONE sang **S2-A subset** kiểm chứng concurrent claim + atomic report/completed/outbox trên đúng run/version/attempt, dùng DB riêng synthetic và crash/recovery evidence. Ưu tiên candidate PostgreSQL của ADR-003. Không triển khai toàn server/auth/worker/container/UI trong một lần. Spike language/driver không tự chọn runtime control/worker; Python core vẫn source of truth report semantics.

Outputs dự kiến: `docs/S2-A-PROTOCOL.md`, `spikes/s2/` (preflight/pinned harness/setup-cleanup), `docs/S2-A-RESULTS.md`, `docs/s2-results/<run-id>.json`, `docs/S2-A-REVIEW.md`, cập nhật plan/decisions/handoff. Đây là **đường dẫn dự kiến, chưa là files/evidence có sẵn**. Ghi runtime versions, input/code hashes, actual commands, expected/actual, crash points và limits. Không regenerate goldens cũ.

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
