# S6-A results — encrypted storage/recovery subset; S4 prerequisite inventory

11/11/2026. Baseline master **e61be7e** + S2-C working tree đã DONE/chưa commit. **S6-A synthetic storage subset DONE sau R4 10 groups PASS và final independent CLEAN WT-S6A-R4.** [Protocol](S6-A-PROTOCOL.md), [implementation/setup](../spikes/s6/README.md), [review](S6-A-REVIEW.md). S4 actual execution **NOT RUN**; full S6/P3-B/P4-B vẫn partial.

## Actual prerequisites và selected scope

Git root/HEAD/branch/status xác nhận đúng checkout và giữ toàn S2-C uncommitted output. Python3.14.8 chạy thật. Windows `Get-Command docker,podman,nerdctl,wsl`: chỉ WSL; actual WSL Ubuntu24.04 `command -v`7 tools docker/podman/nerdctl/runc/crun/rootlesskit/slirp4netns + common docker/podman paths không có output executable. `id -u`1000, kernel6.18.40.1-microsoft-standard-WSL2. Latest R4 còn chạy `engine_inventory` capture exit0 và hai observations này. Discovery giới hạn Windows PATH/WSL PATH/common paths, không chứng minh không có software ở mọi nơi. Chưa executable/daemon/image/capability probe sẵn cho S4; resource/network/collector/cleanup checks NOT RUN/unknown, không host fallback/engine global install/mock gate.

Để tiếp phần độc lập, chọn S6-A **private operator storage/library spike**, chưa user auth/session/secret broker. `argon2` không có ở initial Python inventory; global cryptography50.0.2 có nhưng không dùng làm pin/fallback. Đã install **chỉ `.cache/s6/deps`** bằng official PyPI wheel hashes trong [lock](../spikes/s6/requirements-win-py314.lock): cryptography50.0.2/cffi2.1.1/pycparser3.12. Python3.14.8/Windows10 build19045 là actual host, không vendor deployment support matrix. Read [AEAD docs](https://cryptography.io/en/50.0.0/hazmat/primitives/aead/)/[installation](https://cryptography.io/en/latest/installation/) và [key management](https://cheatsheetseries.owasp.org/cheatsheets/Key_Management_Cheat_Sheet.html) trước dùng; không tự viết cipher.

Preflight kiểm local metadata/origins trước import, loaded package/binary paths/versions, Python/platform;5 real subprocess tests thiếu/sai/incomplete/global-loaded bị từ chối mà không import global crypto. Actual pinned local pass. `spikes/s2/local.py preflight/start` reuse disposable PostgreSQL18.6 exact marker/driver/integrity; mỗi run namespace s6_<uuid>, keyring dummy mới; no real DB/account/key/API/global service.

## Runs/commands thực

`py -3 -B spikes/s6/run_s6.py docs/s6-results/2026-11-11-r<N>.json` ghi evidence mới, source/input before-after hashes, crypto/DB prerequisites, actual S4 discovery, fixed result codes/booleans/counters. Không echo canary/plaintext/DEK/master keys trong evidence.

| Run | Actual / scope |
|---|---|
| [R1](s6-results/2026-11-11-r1.json) | PASS10 groups/12.350s trên initial snapshot đã sửa nonce-history/preflight; O01 chưa captured CLI, K02 chưa đủ envelopeVersion/DB swaps, chưa provider snapshot probe; không DONE từ run này |
| [R2](s6-results/2026-11-11-r2.json) | PASS10 groups/18.864s, thêm actual captured subprocess CLI errors và DB cross-scope swaps; chưa README/final key-provider snapshot fix |
| [R3](s6-results/2026-11-11-r3.json) | PASS10 groups/18.443s,42 source/input hashes; chưa S6A-RV-05 changing-provider fix/probe |
| **[R4 latest](s6-results/2026-11-11-r4.json)** | **PASS10 groups/17.771s**,42 source/input hashes before=after, key provider snapshots actual registered bytes once per operation |

Versions/check counts là engineering fixture evidence, không production readiness/performance hoặc auth result. Không sửa historical hashes/rows để giả source mới đã được chạy trong run cũ. Root full `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: **45 methods PASS/37.048s**, wrapper37.984s; shared core source không đổi sau check này. S6 prerequisite suite **5 methods PASS/0.775s**; actual new S6 behavior được kiểm riêng trong R4, không cộng group count vào unittest methods.

## Expected/actual latest R4

| ID | Actual observation |
|---|---|
| K01 | Local version/path/binary checks READY; maintained AESGCM256 round-trip correct |
| K02 | Changed wrapped DEK/data ciphertext/nonces/key-id/scope/version/kind reject; unsupported envelopeVersion string/empty/int/None reject.4 DB swaps (payload/data nonce hoặc wrapped key) từ khác project/ref và cùng project/khác ref bị normal private-open reject; injected tamper transactions rollback original envelope |
| K03 | Missing/wrong master key fail closed bằng fixed code, không fallback plaintext |
| D01 | Actual stored secret opens đúng dummy canary; scan DB rows không có raw plaintext/selected DEK/master-key bytes. Bool/float policy anchor versions/epochs reject; DB chỉ ciphertext/wrapper/key ID/tag/nonce/ref/metadata |
| D02 |2 independent processes tranh cùng expected version/epoch: đúng1 update accepted/1 rejected, old anchor không đọc normal path, prior ciphertext giữ nguyên |
| D03 | Rewrap giữ payload/data nonce, đổi wrapper/revision; injected content rollback giữ wrapper/audit, nonce reservation vẫn burned. A→B→A forced reused nonce bị reject, physical-key alias reject. Selected row mở chỉ với KEK mới. Changing provider test write đọc key1 lần, rewrap old/new mỗi key1 lần; exact registered bytes dùng mã hóa |
| D04 | Revoke tăng epoch/disable, original/current-shaped anchors đều không mở, DB stop/start không revive; nonce registry cũng giữ qua restart |
| Q01 | Encrypted secret-tainted raw log;4 roles ×5 routes =20 fixed E_RESTRICTED, fake redacted/authorized labels không thay authority. No sanitizer/allow path hoặc full RBAC claim |
| R01 | Actual schema pg_dump/restore vào generated marked DB, ciphertext metadata fingerprints khớp, archive không chứa raw canary/key tokens; child process nhận external dummy key file mở đúng dữ liệu. Wrong key child fail E_KEY_ID; restored write/rewrap deny, newer independently held policy anchor reject old restored head |
| O01 |6 real CLI subprocesses valid/missing/wrong/tamper/unsupported/invalid-mode có exit0 hoặc2 đúng, stderr0, fixed JSON/boolean/code. Raw/base64/hex scan các canaries trong stdout/stderr/audit/evidence không thấy material; captured parent harness stdout/stderr0. No plaintext match data/key material được emit |

Nonce registry là append-only theo một fresh vault namespace/keyring. Reservation commit riêng **trước encryption**, độc lập rollback content; key-tag binding từ immutable bytes snapshot bảo đảm registry và AEAD dùng cùng key. Không có writable restored clones chia sẻ keyring; global/cross-vault coordination và stale-backup latest-ledger reconciliation chưa implemented. Pure library seal helpers không được gọi persistent global allocator. Selected rewrap success không chứng minh đã retire KEK khỏi mọi retained version/project.

## Limits và bước tiếp

S6-A là private operator/library/DB boundary. Không authenticated client/server API, Argon2 login, session/refresh/reset, admin bootstrap/RBAC, trusted service broker injection/live membership/policy revoke, TLS/OS credential store, actual container/output collector hoặc sanitization pipeline. Low-level operator có master keys vẫn decrypt retained ciphertext; revoke không xóa bytes đã lộ hoặc cryptographically destroy historical keys.

Dummy key backup là plain test-only file ngoài DB archive trong ignored `.cache/s6`, **không secured OS keystore/production backup practice**. Restored Vault read-only cho tới future trusted nonce-ledger/key-rollover recovery protocol; latest policy anchors phải có nguồn tin độc lập bên ngoài older archive. Mất anchors/keystore hoặc rollback control metadata chưa được giải quyết. No power-loss/secure-memory/key-zeroization/full disaster recovery proof. Cache/marked restore DBs retained để inspect; stop cluster trước handoff.

S4 actual gate NOT RUN. Recovery nhỏ nhất: cung cấp approved runnable rootless engine + pinned disposable image và capability/network/resource/collector primitives, chạy actual matrix; không dùng discovery current làm proof mọi host absent. Phần tiếp khả thi: **S6-B internal identity/session/RBAC subset** với maintained Argon2 và disposable accounts/tokens, chốt protocol/threat/failure matrix trước implementation; full S4/S6/P3-B/P4-B không đóng từ S6-A. Giữ S2-C working tree và frozen inputs; không tự commit/push/platform/pilot/publish hoặc gọi credential/API/project thật.
