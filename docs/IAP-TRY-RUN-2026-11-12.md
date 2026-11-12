# Chạy thử local synthetic — 12/11/2026

Status **DONE cho hồ sơ chạy thử subset sau independent CLEAN TRY-R1 và required checks PASS**. User yêu cầu “Hãy run thử” sau IAP contract docs DONE. Scope chạy thử **implementation hiện có**: S6-B identity/session/RBAC và core/report regression; không triển khai hoặc chạy IAP24 integration chưa có code. Baseline master `ef6d3c162ff68fab568d19c8eac9c50892d304c2`, toàn uncommitted docs từ phiên trước giữ nguyên.

## Mục tiêu, acceptance và reviewer

Trước chạy đã đọc S6-B README/protocol/harness, S2 local marker/preflight/start/stop; Python3.14.8 xác nhận. Acceptance lượt chạy: prerequisites READY từ actual pins/paths/integrity; new synthetic schema/evidence path; S6-B nhóm I01–I09 PASS và hashes before=after/current match; core45 PASS không errors/skipped; DB stop xác nhận; source/old evidence/docs giữ nguyên; independent high-model review latest output CLEAN. DONE chỉ hồ sơ chạy thử subset, không runtime integration/readiness.

Reviewer độc lập GPT-6.1 Terra high `/root/identity_contract_review` chỉ định từ đầu, read-only. IDs mới IAP-TRY-RV-01… ổn định qua fix/re-review; IAP-RV-01…04 của contract vẫn CLOSED. Không dùng số vòng hoặc suite xanh thay CLEAN. Scope output: record này, [new S6-B evidence](s6b-results/2026-11-12-try-r1.json), current prepended entries NEXT/SESSION-PLAN/SESSION-HANDOFF. Record self ngoài body manifest; source/contract/old records không sửa.

## Actual commands và kết quả

| Command | Actual result |
|---|---|
| `py -3 --version` | Python3.14.8 |
| `py -3 -B spikes/s6b/preflight_b.py` | READY; argon2-cffi25.1.0/bindings26.1.0/cffi2.1.1/pycparser3.12, local loaded paths |
| `py -3 -B spikes/s2/local.py preflight` | toolchainReady=true; archive/extractedIntegrity=true, PostgreSQL18.6; local psycopg/binary3.3.8/tzdata2026.6 |
| Marker-bound `pg_ctl status` qua `local.read_config(False)` | Initial exit3: stopped, không restart DB đang dùng |
| `py -3 -B spikes/s2/local.py start` | exit0 STARTED |
| `py -3 -B spikes/s6b/run_b.py docs/s6b-results/2026-11-12-try-r1.json` | exit0;9 groups PASS; elapsed14.939131s (harness experiment timer, không gồm inventory) |
| `py -3 -B spikes/s2/local.py stop` | exit0 STOPPED trong finally |
| Marker-bound `pg_ctl status` sau stop | exit3: stopped |
| `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v` | exit0;45 tests/33.866s; OK, không errors/failures/skipped |

Core regression và S6-B chạy trong hai processes độc lập; core chỉ offline, không truy DB. S6-B harness có actual DB restart giữa I05, hai-process refresh/last-admin races, expiry bằng DB clock và fresh schema; không gọi service/credential thật. Không sửa test hoặc expected để đạt PASS.

| S6-B group | Actual |
|---|---|
| I01 | PASS |
| I02 | PASS |
| I03 | PASS |
| I04 | PASS |
| I05 | PASS |
| I06 | PASS |
| I07 | PASS |
| I08 | PASS |
| I09 | PASS |

Coverage hiện có: I01 Argon2id/salts/parameter verify; I02 bootstrap/forced password change/throttle/whitelist; I03 token kind/rotation/logout/DB expiry; I04 concurrent refresh/reuse revokes winner pair; I05 reset/change/disable qua restart; I06 fixed-role/cross-project/client claims/last-admin race; I07 snapshot promotion/live downgrade/remove/project disable và queued-resource ownership; I08 expiry trước final write rollback; I09 safe diagnostics/canary raw/base64/hex scans. Action names read/source/export trong S6-B chỉ authorize probes, **không content delivery**. Harness outcomes không chứng minh timing indistinguishability hoặc production settings.

Evidence là actual local synthetic execution mới, không bản sao PASS ngày11/11.31 input raw hashes before=after và rehash current đều match. Evidence file raw SHA256 `566531dafbed4e68591054c946f47977f89986d1a87fa2e4e3013974009d183e`. Core transcript local `.cache/s6/iap-try-2026-11-12/core.stderr.txt` SHA256 `d925a0b0cd494036b33ecdb9e9ead2eb22ef47cf2b40998b5792903c238d58f9`; command/result/count/time được lưu ở record này, transcript/cache chỉ retained local, không portable dependency. Không đưa dummy passwords/tokens/hashes/keys vào committed evidence.

## Preservation và giới hạn

Baseline ngay trước run328 tracked/untracked nonignored paths, raw SHA256 manifest tại ignored local cache. Sau cả hai runs **328/328 unchanged**; không mutate fixture/evidence cũ hoặc các docs đã review. Sau khi ghi bàn giao mới, chỉ3 current docs có prepend mới, giữ original bytes làm suffix;325 paths còn lại phải nguyên vẹn. New evidence dùng path chưa tồn tại, fresh schema, không overwrite historical ERROR/PASS.

Không có HTTP/UI/server mới để mở, worker/service enrollment, common transaction-aware live-policy/application integration, ordinary scoped read/export, broker/sink/taint/collector/OS key custody. **IAP-A01…A24 vẫn NOT RUN integration**, dù S6-B cũ kiểm một số behavior tương tự. S4 actual controls NOT RUN; full S4/S6/P3-B/P4-B và full product readiness chưa đạt, full P4-A partial. Không rerun S1/DB workloads S2/S6-A, không chọn production stack, không real account/key/API/project, no pilot/publish/commit/push.

## Current finding ledger và doneWhen

Current sau independent TRY-R1: **CLEAN, không IAP-TRY-RV findings trong scope**, required checks PASS. Trạng thái lịch sử trước official R1 là chưa có findings/chờ snapshot-checks; trạng thái chuẩn bị đó không tự là CLEAN. Sau findings phải sửa→check→re-review đến CLEAN theo [workflow](REVIEW-WORKFLOW.md); chỉ bổ sung verdict/status hành chính khi đủ điều kiện. Manifest/docs checks sẽ ghi actual bên dưới. Bước tiếp nếu phát triển: bounded IAP integration harness mới theo [protocol §10](IDENTITY-APPLICATION-PROTOCOL.md), schema/scope/selected acceptance trước code; không dùng lượt chạy thử subset này thay implementation còn thiếu.


## Root actual output checks — TRY-R1

`py -3 -B .cache/s6/iap-try-2026-11-12/check_output.py r1` **PASS**:325 baseline paths unchanged,3 original current-doc suffixes exact,82 local Markdown targets tồn tại/fences/newlines/whitespace PASS,31 S6-B inputs before=after/current hash match,9 groups PASS, core transcript45/33.866s OK, git diff check exit0 và không unexpected new nonignored files. Giữ existing uncommitted source/docs; no git action.

Four-body raw SHA256 manifest (record self excluded): sorted `path + ASCII space + raw SHA256`, joined LF no trailing LF, SHA256 UTF-8 = `3aeff9514bb3a1528049b79b58dc08cd2e9131d21fe25dc0cc11d813b1f1dc3b`.

| Path | Raw SHA256 |
|---|---|
| `docs/NEXT-SESSION.md` | `27cfff37b7a4022e368ce55472bb32d251582263e3865d65bee20f14e79a95c0` |
| `docs/SESSION-HANDOFF.md` | `2f677b14b1ba923c2aa2c1947d9bfb9e10c1dc1830352eab6d7d42385aba4067` |
| `docs/SESSION-PLAN.md` | `59338ad1f4570e7e171f89fc2318b24e9eecf341f97919b15bc059897201778f` |
| `docs/s6b-results/2026-11-12-try-r1.json` | `566531dafbed4e68591054c946f47977f89986d1a87fa2e4e3013974009d183e` |

Reviewer nhận exact4 body files + record sau append này; execution logs/DB-step receipts và baseline ở ignored `.cache/s6/iap-try-2026-11-12`,31 input source hashes trong new committed-candidate evidence. Current protocol/old review records unchanged. Chờ official review; chưa DONE.


## Final independent verdict — TRY-R1 CLEAN

12/11/2026. Reviewer GPT-6.1 Terra high `/root/identity_contract_review` đã đọc exact record SHA256 `8580567dce0aa7a3ce5d6105a9acf001d5561bc20d4711d12d4902e3cf78bbcf`,4-body manifest `3aeff9514bb3a1528049b79b58dc08cd2e9131d21fe25dc0cc11d813b1f1dc3b`, evidence/current entries và actual logs/receipts. Xác nhận **CLEAN**, không finding mới trong scope. Independent `py -3 -B .cache/s6/iap-try-2026-11-12/check_output.py reviewer-r1` PASS325 preserved paths/3 suffixes/82 links/31 inputs/9 groups/45 tests/diff0.

**DONE chỉ output chạy thử implementation hiện có và hồ sơ**. Sau verdict chỉ cập nhật status/ledger/verdict hành chính ở record và3 current-doc prefixes; historical reviewed hashes không bị sửa, không claim là post-status hashes. IAP24 integration vẫn NOT RUN; full S4/S6/P3-B/P4-B/readiness chưa đạt. No new runtime/source/code change, real accounts/keys/API hoặc commit/push. S6-B evidence JSON/source/old docs suffixes giữ nguyên; DB đã stopped.


Final post-status check `py -3 -B .cache/s6/iap-try-2026-11-12/check_output.py final` PASS cùng325 preserved paths/3 suffixes/82 links/31 inputs/9 groups/45 tests/diff0; administrative body manifest `92fcf7425d6ae3ecddb42930d386d94a61e0362da7ceb12fdf4d7cf693f5d2b8`. Evidence JSON raw SHA vẫn `566531dafbed4e68591054c946f47977f89986d1a87fa2e4e3013974009d183e`. Không thêm runtime rerun sau verdict.
