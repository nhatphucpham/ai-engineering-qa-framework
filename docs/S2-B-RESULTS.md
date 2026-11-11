# S2-B results — lease/recovery/cleanup persistence subset

11/11/2026. Baseline `master d73dce3d30a2ee9041b6633ce0fbfdcf78528332` + S2-A working tree đã DONE/chưa commit. **S2-B subset DONE sau R4 DB10 groups PASS và final independent CLEAN WT-S2B-R4.** [Protocol](S2-B-PROTOCOL.md), [harness](../spikes/s2b/README.md), [review](S2-B-REVIEW.md). Không đóng full S2/P3-B/P4-A/P4-B hoặc promote production stack.

## Prerequisites và commands thực

`git rev-parse --show-toplevel`, HEAD, branch/status xác nhận cùng checkout master d73dce3; giữ mọi changes S2-A. `py -3 --version`: Python3.14.8. `py -3 -B spikes/s2/local.py preflight`: toolchainReady true, PostgreSQL18.6 archive/extracted integrity, psycopg/psycopg-binary3.3.8/tzdata2026.6 exact metadata + loaded local paths/binary implementation khớp pin. Không download/update toolchain hoặc dùng DB/account thật trong S2-B. Sources/integrity limits giữ ở [S2-A setup](../spikes/s2/README.md).

Đã `py -3 -B spikes/s2/local.py start` cluster synthetic retained `.cache/s2/cluster`, loopback/marker-bound database `s2_synthetic`. Mỗi runB tạo schema mới với `model_identity=s2b-1.0.0`, load S2-A schema rồi additive alterations **trong namespace mới**, không migrate bất kỳ schema/evidence S2-A. Actual environment: Windows10 build19045 x64/Python3.14.8/PostgreSQL18.6/psycopg3.3.8; fsync/synchronous_commit/full_page_writes on. Không global install/service/real credential/API.

Commands experiment: `py -3 -B spikes/s2b/run_b.py docs/s2b-results/2026-11-11-r<N>.json`. Evidence JSON giữ code/input hashes, runtime/pins/command/DB state/process/backend IDs/timing/faults; destination mới, không overwrite historical run.

| Execution | Actual result / scope |
|---|---|
| [R1](s2b-results/2026-11-11-r1.json) | ERROR SyntaxError/1.026s sau B01/B02: dư dấu `)` ở COALESCE cleanup deadline. Đọc traceback, sửa cú pháp; giữ evidence, B03–B10 chưa chạy |
| [R2](s2b-results/2026-11-11-r2.json) | PASS10 groups/22.957s trên snapshot sửa integer/expiry/deadline findings; chưa có đủ stop-vs-renew/reconcile/revoke-reclaim races theo finding RV04, không DONE acceptance từ run này |
| [R3](s2b-results/2026-11-11-r3.json) | PASS10 groups/29.506s; thêm actual races cho cả cancel/revoke vs renew/reconcile/reclaim. Source/input before=after; chưa ordered opposite schedules mới của R4 |
| **[R4 latest](s2b-results/2026-11-11-r4.json)** | **PASS10 groups/32.140s**, thêm forced opposite schedules cho cả cancel/revoke,37 code/input hashes before=after; final snapshot cho review |

Không có performance/SLA target trong subset này. Durations là workload local, không tổng engineering effort. Reruns do fix/coverage thật, không chạy lại S1 benchmark hoặc sửa expected cho xanh. Reviewer giữ stable findings S2B-RV-01..04; xem ledger/final verdict.

## Expected và actual assertions của latest harness

| ID | Phép kiểm và expected observation |
|---|---|
| B01 | DB-server-time renewal extends hoặc giữ expiry, không đổi stateVersion/attempt/fence/raw attempt bundle/anchors/current receipt. Completion vẫn lưu atomic graph và canonical bytea round-trip |
| B02 | Stale version/attempt/fence + expired renew/receipt/complete reject. Test-only delay hook thực sự được gọi giữa current check và write, chờ DB clock hết hạn rồi conditional UPDATE/INSERT reject; graph unchanged, report insert rollback |
| B03 | Expiry tạo recovering + durable cleanup request/open incident + increased version/fence. Wrong request/run/attempt/token, bool/float fields/args, boolean observation và replay reject. Exact synthetic ack mới queued, previous canonical bytes/digests còn nguyên |
| B05 | Hai processes/bốn independent connections: trước ack cả4 empty; sau ack đúng1 accepted attempt2/3 empty, mọi backend tham gia. Không actual worker execution proof |
| B04 | Old claim/receipt/package không tái dùng ở attempt2. Receipt mới required, hai receipt/attempt-input histories còn nguyên, đúng1 report/outbox và round-trip với current independent anchors |
| B06 | Ordered stop-first/complete-first và actual two-process complete-vs-stop cho cả cancel/revoke. Stop đi cancelling/fenced/no report; chỉ exact cleanup ack mới cancelled. Terminal repeated stop reject/immutable |
| B07 | Early timeout reject; deadline thật qua → failed cleanup_unconfirmed/open incident. Late ack chỉ close sidecar incident, run columns unchanged. Ack sau deadline dù sweeper chưa chạy không thể queued/cancelled. Ack-vs-timeout independent-connection race vẫn failed |
| B08 | Attempt2 hết lease/cleanup ack → failed attempts_exhausted; không attempt3 |
| B09 | DB immediate stop trong lúc child có uncommitted recovery writes, terminate child/restart. Committed request survives; uncommitted state/requests absent; WAL recovery log; restarted reconcile idempotent; no claim before exact cleanup, then attempt2 |
| B10 | Active/expired renewal-vs-reconcile; cả cancel/revoke vs renew, expiry reconciliation và reclaim. Stale stop CAS rejected; one explicit refreshed-version retry được ghi khi cần. Ordered recovery-first/reclaim-first/renew-first cases kiểm nhánh scheduler có thể chưa quan sát |

B01–B10 đều actual PASS trong completed R4, không gộp chúng với methods unittest. Cleanup observations/`policy_ok` là synthetic supplied facts được kiểm DB scope/CAS/shape, **không authenticated live revoke hoặc observed container cleanup**. Recovered/failed/cancelled không tự cấp domain/human approval.

Checks bổ sung đã chạy: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: **45 methods PASS/34.940s** (wrapper wall35.653s). S2-A preflight suite: **6 methods PASS/0.051s**. AST parse S2-B Python PASS; rehash toàn33 paths S2-A R5 khớp current working files. Frozen schemas/core/corpus/fixtures/goldens/S1 artifacts không đổi; không regenerate evidence cũ.

## Gaps và việc tiếp

DONE chỉ khi latest evidence/checks và high-model final review CLEAN. Đây là DB persistence subset; acknowledgements mô hình không xác thực worker/supervisor, không quan sát engine/container stop/volumes/egress. Per-run revoke không thay auth/membership/policy epochs hoặc real account revocation. Không có worker/scheduler/control/API production, capacity/fairness, backup/restore/external immutable blobs/orphan recovery hoặc ordinary authorized read/export. Heartbeat thay live expiry column; frozen initial lease timestamp trong canonical attempt input là historical binding, không quyền hiện tại.

Tiếp ưu tiên S2-C capacity/fairness và metadata backup/restore trên disposable DB, chốt protocol/subset trước sửa; full worker cleanup/live revoke cần S4/S6 và gate riêng. Sau đủ relevant evidence mới chốt storage/runtime ADR và P4-B adapter. Không suy production DB/control-worker/platform/distribution, commit/push/pilot/publish hoặc account/API thật từ DB checks.
