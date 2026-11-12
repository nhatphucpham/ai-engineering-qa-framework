# S2-C protocol v1 — capacity/fairness and metadata restore subset

11/11/2026. User yêu cầu commit/push rồi tiếp tục: S2-A/S2-B đã commit **e61be7e0e5d64432871cc891b0061db80da189ea**, push origin/master và `ls-remote` xác nhận exact hash, checkout sạch trước S2-C. Pre-push docs finding S2AB-RV-01 CLOSED sau independent CLEAN. Reviewer S2-C độc lập GPT-6.1 Terra high `/root/s2_final_review`, được chỉ định trước implementation.

Purpose: kiểm scheduler admission theo project/global trong cùng claim transaction; project backlog lớn không chiếm hết các lượt đủ điều kiện; metadata backup/restore giữ exact report/input/outbox graph. Outputs mới `spikes/s2c/`, protocol/results/review, `docs/s2c-results/<new-id>.json`, current plan/handoff/decisions. Fresh namespace model s2c-1.0.0 extends unchanged S2-B; không migrate S2-A/B hoặc sửa frozen core/schema/fixture/evidence. P3-B/S2 subset, không production stack decision.

## Acceptance/invariants trước implementation

- Reuse marker-bound portable PostgreSQL18.6 + pinned local driver; actual preflight READY trước start. No DSN/env credentials/work DB/global installation. Mỗi run source namespace mới; restore **database mới** tên generated/marker-bound riêng trong cùng disposable cluster, không overwrite source/đích tồn tại. Dump/sinks/cache ở ignored `.cache/s2`.
- Atomic admission locks singleton scheduler row (DB contention point explicit), then selects eligible project/run, claims exact attempt/version/fence, records monotonically ordered admission turn cùng transaction. Actual workload hai OS processes/bốn DB connections trên100 jobs synthetic skew90/5/5 across3 projects. DB serializes critical section, không giả single-process là concurrency evidence.
- Global cap3/project caps2/1/1 là fixture bounds, không product defaults. Mỗi admission giữ total/project occupancy <= cap; full/denied/cleanup-unresolved projects không head-of-line block project khác. Bad/bool/float/nonpositive limit hoặc giảm cap dưới occupancy reject atomically.
- Occupancy gồm checking (kể cả expired), recovering/cancelling và **failed với cleanup request còn pending**. Lease expiry/terminal timeout không tự giải phóng slot; exact synthetic cleanup ack mới giải phóng. Completion releases metadata slot; actual process/container quiescence vẫn S4 prerequisite, không physical concurrency claim.
- Fairness dùng least-recently-served eligible project (round-robin turns), tie project ID; cùng project FIFO theo queued_at/id. Ghi eligible set/last-served at each admission, counts/queue age, assert không bỏ qua project continuously eligible quá N-1 intervening admissions; deterministic ordered probe bảo đảm cả3 projects đều eligible và đúng vòng. Không suy throughput, time SLA hoặc fairness under arbitrary stalled workers từ fixture.
- Fairness evidence dùng untargeted scheduler. `specific` là fixture-only request giới hạn project để isolate capacity/fault probes, không public production scheduler API; không lấy targeted turns làm fairness evidence. Targeted request vẫn không được vượt FIFO head của project. Locked head khiến project tạm ineligible, chọn project khác thay vì nhảy job sau. Đây là scope của admission model, không thay production API contract.
- Preserve actual package canonical bytea/length/digests, independent caller anchors, attempt history, declared/effective constraints/mapping/provenance/humanDecision; đúng1 report/outbox per accepted run. Scoped project IDs trong synthetic raw bundle/assessment phải match scheduler metadata; không relabel whole replay package thành ordinary export.
- Backup dùng trusted locally generated schema-only-scope custom archive (`pg_dump -Fc --schema ... --no-owner --no-privileges`), source có child đang giữ uncommitted completion graph. Restore (`pg_restore --single-transaction --exit-on-error`) vào DB synthetic mới/empty namespace. So all table fingerprints từ consistent read snapshot + exact canonical bytes/anchors/report refs/sequence/acked state; no uncommitted graph. Test truncated archive failure leaves no partial schema. Không restore archive ngoài harness.
- Restore outbox replay giữ stable IDs; acked event không gửi lại, pending event gửi/ack và retry trước-ack có thể duplicate. Source graph không đổi do restore/replay; restore tự nó không gửi events. DB-only metadata restore không đóng external blob/secret-key/roles/cluster/PITR/power-loss/production backup gate.

## Failure matrix

| ID | Probe | Expected |
|---|---|---|
| C01 | 2 processes/4 connections,100 jobs,3 projects | No duplicate claims/reports; all backlogs drain, all connections participate, capacity logs <= bounds |
| C02 | Global/project saturation + bad/reduced config | No over-admission; other project can progress; invalid config leaves state unchanged |
| C03 | Expired/recovering/cancelling/failed-pending cleanup occupies slots | No slot leak on expiry/timeout; ack frees; blocked project does not starve others |
| C04 | Deterministic round-robin + concurrent eligibility logs | Eligible least-served project chosen; bounded continuously-eligible skip count; actual queue ages recorded |
| C05 | Admission failure/rollback before commit | No claim/turn/log/attempt subset published; retry once fresh works |
| R01 | pg_dump while uncommitted completion transaction open | Consistent committed graph snapshot; source unchanged after child kill |
| R02 | Truncated archive + single-transaction restore | Nonzero failure, no partial namespace/graph; valid archive still intact |
| R03 | Valid restore into fresh DB | All table fingerprint hashes/rows, canonical packages/anchors/refs/outbox/attempt history match source snapshot |
| R04 | Replay pending/acked outbox after restore | Stable IDs/ack behavior, no auto-send on restore, source unchanged |

Actual DB/tool failures kept ERROR/NOT RUN, source fixes use new evidence filename. Required full regression + actual selected groups + high-model review loop clean before DONE; stable S2C-RV IDs and re-open old regressions. Timebox DB60 phút sau READY (ADR-003), không cắt review loop hoặc bỏ findings để DONE. Không tự commit/push S2-C trong lần tiếp này: quyền user vừa dùng cho output S2-A/B đã hoàn thành; handoff S2-C reviewable trước quyền Git tiếp.

Primary docs checked11/11: [pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html), [pg_restore](https://www.postgresql.org/docs/18/app-pgrestore.html), [transaction isolation](https://www.postgresql.org/docs/18/transaction-iso.html). Chỉ local metadata restore của model, không blanket backup recommendation. Full S2/P3-B/P4-A/P4-B/S4/S6 còn mở; no live auth, actual worker cleanup, real key/account/API/project, pilot/platform/distribution/publication.
