# S2-C results — metadata capacity/fairness and restore

11/11/2026. **S2-C subset DONE sau R4 DB9 groups PASS và final independent CLEAN WT-S2C-R4.** [Protocol](S2-C-PROTOCOL.md), [harness/setup](../spikes/s2c/README.md), [review](S2-C-REVIEW.md). Không đóng full S2/P3-B/P4-A/P4-B hoặc auth/worker/container/production backup gates.

## Baseline/Git/prerequisites

Theo user “Commit push rồi tiếp tục”, đã commit37 reviewed S2-A/S2-B files tại **e61be7e0e5d64432871cc891b0061db80da189ea**, message `feat: add PostgreSQL transaction and lease recovery spikes`, sau clean re-review [S2-PUSH-REVIEW](S2-PUSH-REVIEW.md). Stage kiểm từng working file với Git blob sau normalize CRLF/LF:11 files chỉ khác newline, không content khác. `git push origin master` đưa d8bf175→e61be7e (gồm hai commit P4-A cũ e56ed7d/d73dce3). HEAD/origin/master/`git ls-remote --heads origin master` đều e61be7e; WT sạch trước S2-C. Không amend/force/reset/merge hoặc push output S2-C mới.

S2-C reuse portable cluster marker-bound local: `py -3 -B spikes/s2/local.py preflight` READY, exact Python3.14.8/PostgreSQL18.6/psycopg+binary3.3.8/tzdata2026.6, archive/extracted/local module pins khớp; actual `pg_dump --version`/`pg_restore --version` đều18.6. Sources/integrity limitations theo [S2-A setup](../spikes/s2/README.md). Không install/download toolchain mới hoặc gọi real DB/account/API. `local.py start` chỉ cluster riêng retained, fresh namespaces cho mỗi group/run, fresh marked restore DB. Windows10 build19045 x64, fsync/synchronous_commit on.

## Actual runs/commands

Lệnh `py -3 -B spikes/s2c/run_c.py docs/s2c-results/2026-11-11-r<N>.json`; JSON ghi runtime/command/baseline, before/after input hashes, process/backend inventory, admission turns/counts/eligibility, metadata fingerprints và dump/restore/replay observations.

| Run | Actual |
|---|---|
| [R1](s2c-results/2026-11-11-r1.json) | ERROR OperationalError/18.222s sau C01/C04/C02/C03/C05 PASS. C03 restart DB khiến source bulk connection cũ bị đóng; restore checks chưa chạy. Đọc traceback, sửa close/reopen mọi live store sau restart, giữ failed evidence |
| [R2](s2c-results/2026-11-11-r2.json) | PASS9 groups/26.102s; có locked-whole-project probe/fix RV01, chưa strict locked-head FIFO RV02 |
| [R3](s2c-results/2026-11-11-r3.json) | PASS9 groups/34.229s; head-first generic probe và README; chưa targeted-tail FIFO probe/clarification của latest R4 |
| **[R4 latest](s2c-results/2026-11-11-r4.json)** | **PASS9 groups/38.708s**,42 source/input hashes before=after; strict FIFO cả targeted fixture + untargeted fairness evidence |

Historical evidence giữ nguyên source snapshots, không lấy pass cũ đóng latest acceptance. Runtime durations không engineering effort/SLA. R4 chạy đồng thời regression trên máy này, không DB/runtime benchmark comparison. Không rerun S1 hoặc frozen case runners.

## Expected/actual R4

| ID | Actual observations |
|---|---|
| C01 |100 jobs skew90/5/5,2 processes/4 independent connections, claims24/24/26/26. Đúng100 unique accepted claim/report/outbox. Every admission log <= global3/project2/1/1; max recorded total3 |
| C02 | Global/project saturation chặn claim, project khác tiến sau slot release. Bool/float/nonpositive/reduce-below-occupancy config reject và all-table state unchanged. Giữ tất cả queued rows project a bằng connection riêng → project b/c vẫn claim; giữ riêng FIFO head a còn tail unlocked cũng không cho tail vượt head |
| C03 | Expired checking/recovering/cancelling/failed-with-pending-cleanup đều chiếm slot. Normal DB stop/start không làm mất pending slot. Late scoped synthetic ack giải phóng capacity, failed run vẫn failed; no pretend cancelled/actual cleanup proof |
| C04 | Untargeted least-recently-served eligible project đúng mọi admission; max continuously-eligible skipped turns a2/b1/c2 (boundN-1=2). Ordered probe a,b,c ×3; targeted tail request bị từ chối. Fairness chỉ finite metadata model/eligible set, không SLA |
| C05 | Throw sau claim/attempt/turn/log writes nhưng trước commit; observer thấy original fingerprint, rollback toàn bộ, retry có turn1/attempt1 |
| R01 | Trusted schema-scoped pg_dump trong lúc child giữ completion graph uncommitted; child bị terminate thực. Source committed fingerprint không đổi, archive170384 bytes có SHA256 caller giữ; không uncommitted graph |
| R02 | Truncated local archive pg_restore single-transaction exit1; đích không có partial namespace. Valid archive còn nguyên; wrong caller-held hash bị reject trước restore |
| R03 | Restore vào generated/marked DB mới,13 table fingerprints bằng source repeatable-read snapshot.100 package bytea so exact bytes; replay validator dùng source-held independent bundle/assessment anchors; refs/sequence/acked/attempt history match. Existing namespace overwrite bị từ chối; uncommitted backup-open run vẫn checking/no report |
| R04 | Restore không auto-send. Acked stable event ready-a-000 bị skip; pending ready-b-000 append hai lần cùng ID khi retry trước ack, ack ngăn send tiếp. Source fingerprint sau restore/replay vẫn bằng before |

Queue age R4 median4258.775ms/p95 nearest-rank6793.700ms/max7104.850ms; deliberately synthetic workload, central DB admission lock và local CPU/IO, không throughput target. Admission counts là metadata slots, không physical container execution: actual quiescence và trusted cleanup thuộc S4. Whole raw replay packages restricted internal, không ordinary export authority.

Additional actual checks: full `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v` **45 methods PASS/34.619s**, wrapper35.386s; S2 preflight `unittest discover -s spikes/s2` **6 methods PASS/0.059s**. Static AST syntax PASS. S2-A/B source/lock/protocol/evidence và frozen core/schema/fixtures/goldens/S1 giữ nguyên; hash/link/fence/diff final checks ghi tại review sau actual verification.

## Limits/next

Single scheduler row is an explicit DB serialization point; this experiment does not show production scaling. Targeted claim restricts project only for isolated fixture checks, still respects FIFO; no targeted turn is used as global fairness evidence. Cleanup acknowledgements/per-run revoke remain synthetic supplied facts, not authenticated supervision. Successful completion releases metadata slot only; real worker/container exit/resource/network enforcement unimplemented.

Restore chỉ schema metadata của trusted local model, excludes external blobs/secret keys/roles/cluster configuration/PITR/power loss/retention/migration/cross-version compatibility. Not a production backup plan. Primary [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)/[pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html) docs đã kiểm trước code; archive ngoài harness không được restore. Retained target DBs/cache cùng disposable cluster dừng trước handoff, không auto-delete hoặc service mới.

Next: kiểm prerequisites S4 executor/policy và S6 identities/secrets với synthetic/dummy inputs, chốt actual boundary checks trước P4-B/C; full S2 cần authenticated worker/revoke/cleanup + runtime composition/integration. S2-A/B/C subsets không đóng whole stack/gate; chưa production DB/control/worker/desktop/platform decision, account/API/pilot/publish. S2-C output mới chưa commit/push.
