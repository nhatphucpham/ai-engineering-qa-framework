# Plan hiện hành — sau S6-B identity/session/RBAC execution

12/11/2026: user yêu cầu commit/push output S2-C/S6-A/S6-B đã review; [pre-push record](S2C-S6-PUSH-REVIEW.md). Commit chứa cập nhật này là snapshot bàn giao mới; kiểm Git log/status/remote thay vì áp trạng thái chưa commit của ngày11/11. Quyền Git lần này cho output hiện tại; chưa giao triển khai slice tiếp.

## Current S6-B outcome / next session

User yêu cầu “tiếp”. [S6-B protocol](S6-B-PROTOCOL.md) chốt trước code, `spikes/s6b/` thực thi actual Argon2id/dummy accounts/opaque sessions/refresh reuse/reset/epochs/fixed roles. [R4](s6b-results/2026-11-11-r4.json)9 groups PASS13.260s,31 source/input hashes before=after;5 prerequisite methods PASS0.893s/core45 PASS34.430s. [Review](S6-B-REVIEW.md) final CLEAN WT-S6B-R4-D2, synthetic subset DONE. Giữ S2-C/S6-A subsets DONE/uncommitted work/old inputs; không production auth/backend/DB/runtime choice.

Tiếp **identity→application/live-policy/broker integration contract và acceptance/failure protocol**, phân biệt user actor với service/worker identity, current policy/epoch với snapshot grant, S6-A private vault với scoped broker operation. Chưa tự chọn transport/runtime/platform hoặc route trusted helpers ra network. Thiết kế/test integration riêng trước claim actual P4-B lifecycle; no real account/key/API. S4 actual engine/rootless image/network/resource/collector/cleanup cần prerequisites riêng; thiếu vẫn NOT RUN, tiếp phần độc lập thay mock gate.

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
