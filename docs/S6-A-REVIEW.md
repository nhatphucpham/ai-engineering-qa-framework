# S6-A independent review and S4 prerequisite inventory

11/11/2026. Baseline master e61be7e + S2-C working tree DONE/chưa commit giữ nguyên. **S6-A synthetic storage subset DONE sau final independent CLEAN WT-S6A-R4 và required checks PASS.** Reviewer GPT-6.1 Terra high `/root/s2_final_review` read-only chỉ định trước code. Scope [protocol](S6-A-PROTOCOL.md), `spikes/s6/` pinned library/preflight/envelope/vault/diagnostic CLI/harness, [results](S6-A-RESULTS.md), new evidence/S4 readonly inventory/current plan/handoff. No full S4/S6/P3-B/P4-B/production auth/keystore/broker gate. Prior S2 findings giữ CLOSED.

## Stable ledger

| ID | Severity/state | Expected/actual + impact | Fix/check |
|---|---|---|---|
| S6A-RV-01 | P1/CLOSED WT-S6A-R4 | UNIQUE current wrapper không giữ pair key/nonce đã dùng sau rewrap/rollback; AEAD lifetime safety claim thiếu | Append-only history + independently committed reservation trước crypto, key identity tag/alias guard; forced A→B→A collision reject, rollback burns reservation, restart preserves; restore readonly và cross-vault limitation rõ |
| S6A-RV-02 | P2/CLOSED WT-S6A-R4 | Preflight import envelope/crypto trước readiness, missing deps có thể global fallback/crash | Split paths/errors, local metadata/origin checks trước import, loaded paths/versions/binary guard;5 real-process tests missing/mismatch/incomplete/no global load, outside-loaded rejection, valid local positive |
| S6A-RV-03 | P2/CLOSED WT-S6A-R4 | O01 claim captured CLI/log scan nhưng initial harness chưa capture stdout/stderr/error modes | Actual6 subprocess modes fixed outputs/statuses, parent capture, raw/base64/hex scans canaries/audit/evidence; R4 O01 PASS |
| S6A-RV-04 | P2/CLOSED WT-S6A-R4 | K02 thiếu unsupported envelopeVersion và DB cross-project/ref swap vectors | Mutate version shapes +4 actual DB payload/wrapper swaps, normal private-open rejects fixedcode và transaction rollback unchanged; R4 K02 PASS |
| S6A-RV-05 | P2/CLOSED WT-S6A-R4 | Registry và AEAD đọc mutable provider2 lần có thể ghi fingerprintA nhưng mã hóaB | Pin exact immutable key bytes once/reservation+crypto, read/open key-tag check, rewrap pins old/new; ChangingKeys second-read returns wrong key nhưng calls1each + correct decrypt; R4 D03 PASS |

Gói gửi review trước verdict (lịch sử): R1/R2/R3 PASS chỉ đúng historical workload, không dùng thay latest fixes/coverage. R4 actual10 groups PASS17.771s,42 code/input hashes before=after; preflight5 PASS0.775s; core regression45 PASS37.048s, không đổi shared source sau đó. Final links/fences/syntax/protected hash/DB-stop checks và exact snapshot đã PASS khi gửi review. Yêu cầu reviewer kiểm latest files, cả5 IDs/regression/new findings, crypto/key lifecycle boundaries, source/evidence match/scope/gaps đã hoàn tất theo verdict bên dưới; không dừng theo số vòng.

DONE chỉ riêng subset sau required checks + final high-model clean; S4 actual execution/resource/network/collector/cleanup vẫn NOT RUN, full S6 identity/broker/OS keystore/RBAC còn mở. S2-C chưa commit/push vẫn bảo toàn; chưa quyền Git/pilot/publication mới.

## Final verdict — WT-S6A-R4

11/11/2026, GPT-6.1 Terra high `/root/s2_final_review` xác nhận **CLEAN**, S6A-RV-01..05 CLOSED, không finding mới/tái xuất hiện trong scope. Đã đọc protocol/schema/source/harness/results/current docs; kiểm append-only burned nonce/key identity/restore read-only limits, pre-import path checks,5 actual process prerequisite cases,6 captured diagnostic CLI cases/canary scans, envelopeVersion+4 DB cross-scope swaps, immutable key snapshot+ChangingKeys probes. **S6-A synthetic storage subset DONE**; S4 actual vẫn NOT RUN và full S6/P3-B/P4-B/OS-keystore/auth/session/broker/worker chưa đóng.

Reviewer rehash độc lập38 files của [snapshot](s6-results/review-snapshot-r1.json), manifest `60406b2058e64ea7f5ea49f44ab8e9c0718ed6e1cf5db32897e8d1a48e12de54`;42 S6 R4 inputs before=after=current, S2-C42/S2-B37/S2-A33 inputs đều khớp. Algorithm sorted path + ASCII space + SHA256(file bytes), join LF không trailing LF, SHA256 UTF-8 chuỗi; snapshot tự nó không nằm inventory. `git diff --check` PASS. R4 actual10 groups PASS;45 regression/5 prerequisite methods là root actual, **reviewer không rerun DB/full suite** trong vòng này.

Root links/fences/syntax/protected artifacts/hash/cache exclusion PASS; DB `local.py stop` thành công và `pg_ctl status` no server running(expected exit3). Dummy-key files/archives chỉ ignored cache, không tracked/evidence raw material. Sau verdict chỉ cập nhật ledger/trạng thái hành chính; source/protocol/README/evidence R1–R4/42 input hashes giữ nguyên. Manifest38-file lịch sử không sửa để giả là hash docs hậu verdict. S2-C/S6-A output mới chưa commit/push, baseline e61be7e không đổi.
