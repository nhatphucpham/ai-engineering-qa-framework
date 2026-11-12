# IAP-B service / delegation / attempt authority — results and review

12/11/2026. Status **DONE service/delegation/assignment authority metadata subset sau independent CLEAN R3 và required checks PASS**. Baseline master **e8b47a18925dc1c64d817e1facd27dc83250f69c + uncommitted IAP-A R5 DONE**; no Git action. User yêu cầu tiếp theo plan. [Protocol](IAP-B-PROTOCOL.md) chốt scope/acceptance trước code; [source/README](../spikes/iapb/README.md) chỉ synthetic local host/DB. Reviewer độc lập GPT-6.1 Terra high `/root/identity_contract_review` read-only từ đầu, stable IAPB-RV IDs qua fix/re-review.

## Output, composition và acceptance

New `spikes/iapb/authority.py/schema.sql/run_iapb.py/README.md`, versioned protocol, R1–R3 evidence, IAP-A regression evidence mới, record này và5 current docs. Fresh namespace reuse unchanged S6-B/IAP-A source/tables; thêm service credentials và authority metadata, không migrate old schema. Common held identity mutex bao gồm auth/account/role/policy/grant/service/assignment writes; credential/grant/delegation/assignment deadlines rechecked bằng final DB-clock conditional checkpoint.

DoneWhen: actual B01–B08 selected authority behavior PASS với negative/ordered concurrency/rollback/observer evidence; old path hashes/source preservation; core45/prereq11 và IAP-A composition regression PASS; latest reviewer CLEAN/no open findings. DONE chỉ authority metadata subset, không full IAP24/engine/network/worker/secret broker hoặc product gates. No real accounts/keys/API/project/global install/production stack/commit/push.

## Actual executions và snapshots

| Evidence | Actual outcome | Scope/limits tại snapshot |
|---|---|---|
| [B R1](iapb-results/2026-11-12-r1.json) |8 groups PASS14.393s,41 inputs before=after|Initial coverage; thiếu ordered check/revoke và tentative renewal expiry so với acceptance, không claim final completion |
| [B R2](iapb-results/2026-11-12-r2.json) |8 groups PASS20.485s,41 inputs before=after|Bổ sung RV01/RV02 actual probes |
| **[B R3 latest](iapb-results/2026-11-12-r3.json)** |**8 groups PASS18.069s,41 inputs before=after/current match**|Thêm explicit live denial trên check/renew/assign, queued cancel fence, active/expired reservation không tự reassignment, rotated credential vẫn deny sau restart |
| [IAP-A regression](iap-results/2026-11-12-after-iapb-r1.json) |8 groups PASS18.968s,36 inputs before=after/current match|Unchanged IAP-A source/fixtures, fresh independent namespace; không rewrite old R1–R5 |

Commands actual: `py -3 --version` → Python3.14.8; S6-B preflight READY local Argon2id pins/loaded paths; S2 preflight toolchainReady/archive/extracted integrity true PostgreSQL18.6 + local psycopg/binary3.3.8. Marker-bound initial pg_ctl status3 STOPPED verified trước start, không dùng DB/service/DSN thật. `py -3 -B spikes/s2/local.py start`; `py -3 -B spikes/iapb/run_iapb.py docs/iapb-results/<new-id>.json` each exit0. B1→B2 dùng own cluster liên tiếp; sau B2 chạy IAP-A regression sequentially rồi stop; B3 start→run→stop. Harness B08/Q08 actual stop/start disposable DB; không chạy DB fixtures song song.

Core command `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v` →45 PASS33.613s, no failure/error/skip. S6-B prerequisites5 PASS0.720s; S2-common6 PASS0.040s. Core/prereq suites chạy offline process riêng trong lúc B1; authority model không thay sau đó, chỉ harness probes được bổ sung cho R2/R3 nên targeted reruns thích hợp. Logs retained ignored `.cache/s6/iap-b/{core.log,s6b-prerequisites.log,s2-prerequisites.log,checks.json}`; commands/counts/durations ghi ở record, không yêu cầu cache portable.

| Group | Latest actual selected evidence | Chưa chứng minh |
|---|---|---|
| B01 |Live Admin-only enrollment; opaque service token namespace; user-vs-service/kind/audience, extra authority/helper/hook/version denials; service cannot user-start|No network enrollment/TLS/OS key custody |
| B02 |Actual logout/DB user access expiry: interactive denied, service checks same persisted delegation succeed. Credential reset+relogin fences old run delegation|No actual background process/check execution |
| B03 |Wrong project/run/worker/assignment/attempt/fence; rotate old credential denied/new credential cannot revive old assignment epoch; revoke cannot auto-rotate/enable; expired credential denies|No full IAM/membership/restore anti-rollback provider |
| B04 |Role downgrade/remove, project disable, grant revoke and policy narrowing block; relevant check/renew/assign denials; new policy/grant cannot rebind old run. Queued user cancel fences metadata check|No actual worker stop/cleanup, no general member epoch history |
| B05 |Actual two processes/connections, DB lock wait observed; one assignment winner; assign↔revoke and check↔revoke each forced both orderings; audit/graph counts independent observer|No exactly-once workload or external IO/release cutover |
| B06 |Renew same attempt/fence extends deadline; active/expired head cannot silently reassign; retirement+next attempt monotonic; stale assignment cannot check/renew. Tentative assignment expiry rolls back all; tentative renewal observed extended then old-deadline expiry restores original expiry/audit via independent observer|`retiredMetadata` không cleanup acknowledgement; no retry authority for real workload |
| B07 |Actual deferred FK fault via facade fixed E_DEPENDENCY; trusted observer confirms23503; no partial head/assignment/audit, then valid retry. Actual audit+denial-audit outage fail closed|No deployed multi-service failure/recovery proof |
| B08 |Actual DB restart keeps current authority, retired fence/rotated and revoked tokens denied; raw/base64/hex dummy credential/hash scan on metadata/parent capture/evidence|No container collector, secret taint or raw content release pipeline |

Service credentials256 random bits, digest only stored in b_credentials; raw credentials returned only in authorized create/rotate response and kept in harness memory for comparison, never emitted. Issuer Admin session is not worker identity. Policy/config/snapshot digest selectors remain IAP-A synthetic selectors, not trusted artifact attestation; delegation rows resolved from authoritative DB graph, no client authority bool. Membership state is live under mutex but no general monotonic membership history/restore authority; do not infer more.

## Current finding ledger

**IAPB-RV-01/02 CLOSED** theo independent CLEAN R3, không finding cũ/tái xuất hiện/mới chưa xử lý trong scope; required checks PASS, DONE chỉ metadata authority subset. Reviewer identified both coverage gaps during early source review, before official latest snapshot; root preserves historical R1.

| ID | Expected / actual / impact | Root fix, actual check và closure condition |
|---|---|---|
| IAPB-RV-01 / P2 |B05 promised revoke-vs-check two orderings, initial harness only assign races; claim not covered by initial PASS|R2/R3 actual2process check-first→accepted+revoke, revoke-first→check denied; observed DB lock wait and scoped check audit counts, later check denied in both. Reviewer R3 verified CLOSED, no regression |
| IAPB-RV-02 / P2 |B06 promised tentative renewal expiry rollback; initial only assignment expiry|R2/R3 observe tentative renewed expiry greater than old, wait DB old deadline, checkpoint denies; independent observer sees original expiry and unchanged audit; current expired check denied. Reviewer R3 verified CLOSED, no regression |

Required preservation/docs/hash checks and reviewer verdict append below; no self-closing findings or DONE until latest CLEAN. Stable IDs across rounds, new/recurrent findings must be fixed and re-reviewed. Administrative status/verdict after CLEAN allowed; substantive changes need re-review.

## Gaps / next

Assignment is **authority reservation metadata only**. No engine/worker process can launch through these ports. Metadata retirement and queued cancel do not stop actual processes or satisfy cleanup; do not integrate them as executable claim/retry protocol. Scheduler revoke may leave pending reservation requiring future operator/cleanup flow; no auto-enable/restore claim. Full IAP24/S2/S4/S6/P3-B/P4-A/P4-B–E/P5/P6/readiness remain open. No network auth/service enrollment deployment, release permits/sink/broker/secret injection, content/export/source streams, collector/taint/OS keys or actual cleanup.

Next refresh actual S4 prerequisites and specify real worker release/cleanup integration before attaching this authorizer to execution. Prior S4 discovery from11/11 is not today's host inventory; missing engine → NOT RUN, no mock PASS/host fallback/global install. Output IAP-A/IAP-B/current docs remain uncommitted/unpushed; keep all old fixtures/source/protocol/evidence, no worktree change/reset/clean/stash.


## Root actual snapshot checks — IAPB-R3 / official review1

`py -3 -B .cache/s6/iap-b/check_output.py official-r1` **PASS**:337 original nonignored paths byte-exact +5 current-doc original suffixes exact (342 protected total),185 local links/fences/newlines/whitespace/credential-pattern/Python AST checks; B3 eight groups/41 before=after/current hashes and IAP-A regression8/36 match; core45/prereq11 logs; final marker-bound pg_ctl status3 STOPPED; git diff check0. Before docs prepend all342 paths byte-exact. No source/protocol/evidence/fixture from IAP-A/older slices changed, including uncommitted source/evidence; only5 current docs prepend.

Fourteen-body raw working-byte manifest excludes this self-record: SHA256 UTF-8 of sorted `path + ASCII space + SHA256(raw bytes)`, join LF **no trailing LF** = `6f55e1e00918045b7faf8f250322bc436ffd946af37d71612cc81a9f79d09e01`.

| Body path | Raw SHA256 |
|---|---|
| `docs/DECISION-LOG.md` | `a9953ac833024000694e1811eae8062b8f17d2fdd5e4b2480f325e4912a7ca1e` |
| `docs/IAP-B-PROTOCOL.md` | `28534c096f638941e083ba70fcb3c5674a808e3cc248614dfc11ad7c0cebe94c` |
| `docs/IMPLEMENTATION-PLAN.md` | `b4c928e9612438b0db71f1a64324a9207839fa107cf370cf27cd842d313f7947` |
| `docs/NEXT-SESSION.md` | `7450fcd6fa0216c824a83bc878eb79b262122e454e6e5686900a9402ddd41849` |
| `docs/SESSION-HANDOFF.md` | `bb4cf0ee19a706756a17ae7267593f4fe319d1223bd49164bd8fa80ce2348dd8` |
| `docs/SESSION-PLAN.md` | `78fb12d1dd247121662f2c5146e5c0c5eb29f027dc7f974705dfbde9cdb6df05` |
| `docs/iap-results/2026-11-12-after-iapb-r1.json` | `d33bdf0a28e52efb00c85e007ddd96b3de754f9d8813f2e78ed9d970be6663d7` |
| `docs/iapb-results/2026-11-12-r1.json` | `30e2f2d8f258796db8510c361661ead3fb82c29712673fb5f115d7e57b2eb03f` |
| `docs/iapb-results/2026-11-12-r2.json` | `e3f716c5ac22a7fb54eeb71ccbf71bd21a8b69c7954de7d56287eb756a2a7c09` |
| `docs/iapb-results/2026-11-12-r3.json` | `bf33016af9a42aa92e1d4ca64b29670899f5351811ce7a577cf13c1e385b82c7` |
| `spikes/iapb/README.md` | `379dcb41f49e886a733333364e3867bbfe2df1b6ee30db5c608368ff4032e335` |
| `spikes/iapb/authority.py` | `1c4b413b781f949ccca52f710f2d21c3fec6170c7f7240bff57c77bc66627fab` |
| `spikes/iapb/run_iapb.py` | `7081e7a81e06b03d5fca7dd3725e15dd0c95fd25c95bee940d25df8be9ac4a65` |
| `spikes/iapb/schema.sql` | `31ca352095bf403507ef6e191da5dbadc6a6bf12387797f2acd5aef97ed8d1c3` |


Reviewer receives exact14 body files + self-record + stable ledger/actual evidence/limits. Actual execution logs/checker/baseline retained ignored `.cache/s6/iap-b`, source/input41 paths in B3 JSON and36 in A regression JSON make current source identity independently checkable. Historical R1/R2 input hashes do not claim current harness bytes; preserve all, no rewrite for EOL or source changes. Await latest independent re-review, do not self-close01/02 or mark DONE.


## Final independent verdict — IAPB-R3 CLEAN

12/11/2026. GPT-6.1 Terra high `/root/identity_contract_review` xác nhận **CLEAN** trên exact14-body manifest `6f55e1e00918045b7faf8f250322bc436ffd946af37d71612cc81a9f79d09e01` và self-record SHA256 `1f4f8dfafe4567d60ed1374af886e820f3a9e9d991c2c14ad520954685ec464d`. Verified IAPB-RV-01/02 CLOSED, không regression/new findings trong selected scope. Independent `py -3 -B .cache/s6/iap-b/check_output.py reviewer-r3` PASS337 old paths/5 suffixes/185 links, B8/41 inputs and A regression8/36, core45/prereq11, DB status3/diff0.

**DONE chỉ service/delegation/assignment reservation authority metadata synthetic subset**. Không actual worker execution/cleanup/broker/network authentication hoặc full IAP/product readiness. Sau verdict chỉ status/ledger/verdict hành chính trong self-record và5 current-doc prefixes; raw protocol/source/schema/README/evidence snapshots và historical manifests giữ nguyên, không claim post-admin bytes là reviewed hashes. IAP-A và IAP-B output vẫn uncommitted/unpushed; no new Git action, real accounts/keys/API hoặc production-stack choice.


Final administrative check `py -3 -B .cache/s6/iap-b/check_output.py final` **PASS**337 unchanged baseline paths/5 exact old-doc suffixes/185 links; B8/41 inputs, A regression8/36, core45/prereq11, stopped DB/status3,diff0. Post-status14-body manifest `4c06114923a7a067c7460cac32e912a3e991e7f8b0ba1885fcd73e180b78ba28`; separate from historical independently reviewed manifest, không sửa old hash claims. Source/protocol/schema/README/R1–R3 và new A regression evidence nguyên vẹn. No additional runtime execution or Git action sau verdict.
