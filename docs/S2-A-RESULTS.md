# S2-A results — disposable PostgreSQL transaction subset

Ngày 11/11/2026, baseline `master d73dce3d30a2ee9041b6633ce0fbfdcf78528332` sạch lúc bắt đầu; output mới chưa commit/push. **S2-A subset DONE sau independent CLEAN WT-S2A-R5 và required checks PASS**, không đóng full S2/P3-B/P4-A/P4-B. [Protocol v1](S2-A-PROTOCOL.md), [harness/setup](../spikes/s2/README.md), [review ledger](S2-A-REVIEW.md).

## Prerequisites và môi trường thực

Read-only discovery: `Get-Command py,python,psql,postgres,pg_ctl,docker,podman,wsl` thấy Python launchers và WSL; PostgreSQL/Docker/Podman không trong PATH. Các thư mục cài đặt PostgreSQL/Docker phổ biến và project cache không có candidate DB. `wsl --list --quiet` thấy Ubuntu-24.04; discovery bên trong distro không thấy postgres/pg_ctl/docker/podman. Không suy phần mềm vắng ở mọi nơi; không dò/kết nối DB/service công việc, không lấy env connection string.

Đã tự hoàn thành portable setup trong quyền local: archive từ [EDB official binaries](https://www.enterprisedb.com/download-postgresql-binaries), link Windows 18.6 `fileid=1260609` (384,620,317 bytes), SHA256 `e2246ba91d22345bc3d017586c09ede52d9df180b1eeb480f050445f1cad84e2`. Pin đo qua official HTTPS, không publisher-signed checksum; Authenticode `postgres.exe`: NotSigned. Rehash archive + đối chiếu extracted bin/lib/share trước execute trong preflight. [PostgreSQL support policy](https://www.postgresql.org/support/versioning/) xác nhận major 18 supported tại lúc kiểm; không suy binary publisher attestation hoặc production choice.

Actual: Windows 10 build 19045 x64, Python 3.14.8, PostgreSQL 18.6 (MSVC 19.44), psycopg/psycopg-binary 3.3.8, tzdata 2026.6, jsonschema 4.26.0/referencing 0.37.0 có sẵn. Driver wheels từ PyPI, hashes pin trong lock; install chỉ `.cache/s2/deps`, không global. Preflight kiểm metadata + loaded versions/path + binary implementation, exact Python/platform, archive/extracted integrity. Cluster mới `.cache/s2/cluster`, loopback port 51180, DB/user `s2_synthetic`/`s2synthetic`, random identity marker, trust chỉ dummy local data. `fsync`, `synchronous_commit`, `full_page_writes` đều on; isolation read committed. Không tạo service hoặc sửa PATH. Cache và DB retained để inspect, stop trước bàn giao.

Setup ban đầu bị Windows inherited-pipe stall sau `pg_ctl start`; sửa subprocess stdout/stderr sang temporary file, tránh pipe còn mở ở server child. PID data-path dùng slash khác Windows path; sửa so resolved paths. Kiểm own marker/status rồi `initialize-database` hoàn tất DB mới, không reset hoặc đụng service khác. Các lỗi setup không được gọi DB PASS; chỉ sau actual smoke + full experiment mới READY.

## Actual commands và evidence

Setup commands/pins ở [README](../spikes/s2/README.md). Đã chạy `py -3 -B spikes/s2/local.py preflight` và `setup`/`initialize-database` như trên. Mỗi experiment dùng schema mới, evidence destination mới; source/input hashes trước/sau nằm trong evidence.

| Run / command suffix `py -3 -B spikes/s2/run.py ...` | Actual | Phạm vi và nguyên nhân thay đổi |
|---|---|---|
| [R1](s2-results/2026-11-11-r1.json) | PASS, 25.882s / 13 check groups | Initial workload; chưa có commit FK failure, expiry-during-validation hoặc DB stop khi transaction còn mở |
| [R2](s2-results/2026-11-11-r2.json) | ERROR `CheckViolation`, 7.505s | Probe duplicate run tự tạo `completed`/null report, CHECK chặn trước unique. Giữ failure; sửa probe thành queued/null để isolate PK, không nới expected hoặc DB constraints. Checks sau điểm lỗi chưa chạy |
| [R3](s2-results/2026-11-11-r3.json) | PASS, 21.003s / 14 groups | Server-clock lease/final expiry recheck, deferred FK commit failure, constraint-specific duplicate probes; DB stop sau rollback child |
| [R4](s2-results/2026-11-11-r4.json) | PASS, 21.934s / 14 groups | Thêm expiry-during-validation, DB stop với transaction mở, recovery log và pending outbox replay sau restart |
| **[R5 latest](s2-results/2026-11-11-r5.json)** | **PASS, 22.872s / 14 groups** | Snapshot sửa S2A-RV-01: driver/tzdata pin và fail-closed preflight; 33 source/input hashes before=after |

R5 command chính xác: `py -3 -B spikes/s2/run.py docs/s2-results/2026-11-11-r5.json`. Source manifest hash mỗi file dùng bytes working tree (không Git blob); frozen payload canonical hashes tách riêng. R1–R4 giữ historical bytes/snapshots; R5 là evidence hiện hành. Execution durations là workload local, không tổng engineering effort; review không nằm trong timebox DB experiment. Không rerun S1 benchmark hoặc frozen case runners.

## Expected/actual theo failure matrix

| Checks | Actual R5 |
|---|---|
| C01 | 100/100 distinct jobs completed; 2 child processes nhận 50 jobs/process; 4 backend connections nhận 25 jobs/connection. Barrier + observed overlap. Mỗi job đúng 1 claim/receipt/report/outbox, version 3→4→5, attempt 0→1/fence 3→4 |
| C02 | Exact unique constraint names cho occurrence, run PK, report PK/run, outbox PK/run; mọi reject giữ graph không đổi |
| F01 | Wrong version/attempt/token và expired lease reject. Server clock đi qua expiry trong real DB với injected validator delay cũng reject; delay không mock DB |
| F02 | Cleanup-unresolved hoặc policy-denied chặn claim và completion. Chỉ DB predicates, authenticated policy/revoke và real cleanup **NOT RUN** |
| F03 | Tamper graph và coherent bundle rewrite với old independent anchors đều reject trong transaction; no graph mutation |
| T01/T03 | Observer connection không thấy report/completed/outbox trước commit; explicit rollback và deferred `report_ref` FK failure tại commit đều giữ original graph |
| T02 | Hai completions, completion vs synthetic cancel: đúng một terminal winner, no partial graph, terminal repeat reject. Full cancellation lifecycle **NOT RUN** |
| K01/K02/K03 | Actual kill trước commit / sau commit trước ack / sau synthetic receipt: fresh connection thấy rollback đầy đủ / committed graph đầy đủ / receipt-only. Retry complete hoặc reject terminal đúng; round-trip bytes/digests giữ nguyên |
| K04 | Kill publisher trước delivery, sau delivery trước ack, sau ack. Sink ghi hai lần cùng stable event ID; ack ngăn send tiếp. Không exactly-once claim |
| R01 | `pg_ctl immediate stop` lúc child giữ transaction mở, rồi terminate child/restart. WAL recovery log có automatic recovery/redo. Committed graph/bytes + ack tồn tại; uncommitted graph vắng; pending event được publish/ack sau restart |
| SEM01 | Real DB round-trip ba cases complete/incomplete/failed, giữ raw payload/mapping/provenance, declared/effective constraints/human decision và canonical bytea + independent anchors |

Claim latency R5 median **34.526ms**, p95 nearest-rank **46.837ms**; queue age median **3882.097ms**, max **6552.125ms**. Harness cố ý giữ row lock 15ms để tạo overlap; R5 chạy cùng regression trên máy này. Đây không throughput/SLA hoặc benchmark so DB/runtime, không performance verdict.

Checks bổ sung thực chạy: `py -3 -B -m unittest discover -s spikes/s2 -p 'test_*.py' -v`: **6 methods PASS, 0.066s**. Full `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: **45 methods PASS, 36.754s** (wrapper wall 37.533s). Tests độc lập preflight không thay DB evidence. Core/schemas/corpus/fixtures/goldens/S1 artifacts giữ nguyên so baseline; links/fences/whitespace và snapshot rehash được ghi tại review record sau kiểm.

## Gaps và bước tiếp

S2-A chỉ candidate DB model: persisted canonical package trong DB bytea, atomic metadata graph và outbox subset. Không external immutable blob adapter/orphan sweeper/backup-restore/power-loss guarantee; không production application ports/API/RBAC, trusted semantic acceptance, worker enrollment/lease renewal/reclaim, live revoke, complete cancellation/cleanup/fairness hoặc scoped ordinary read/export. Terminal cancel trong spike là CAS competitor, không implement lifecycle đích. Whole raw package restricted internal replay; legacy exporter vẫn `projection_unsupported`.

Ưu tiên tiếp: protocol S2-B lease expiry/reclaim với unresolved cleanup, cancel/revoke races và restart reconciliation dùng DB synthetic này; kiểm fairness và backup/restore riêng. Chốt DB/control-worker composition ADR sau đủ evidence, rồi P4-B adapter. S3–S6 có prerequisites riêng và chưa chạy. Không dùng S2-A PASS đóng full S2/P3-B/P4-A hoặc chọn production stack. Chưa account/API/project thật, pilot/platform/distribution/publication hoặc quyền commit/push mới.
