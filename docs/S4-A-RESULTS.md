# S4-A inventory/private collector — actual results and review

12/11/2026, baseline **0d1c4539cd65fdbf38b931dbcf2d39debb1756e7**, checkout clean đầu phiên. Status **DONE S4-A independent inventory/private collector preparation subset sau independent CLEAN R2 và required checks PASS**. User yêu cầu tiếp S4 theo plan; no commit/push trong phiên này. Reviewer độc lập GPT-6.1 Terra high `/root/identity_contract_review` read-only từ đầu, stable S4-RV IDs; fix/check/re-review đến CLEAN, không trần vòng. [Protocol](S4-A-PROTOCOL.md) chốt trước code; [README/source](../spikes/s4/README.md).

## Actual prerequisite branch

[Windows/WSL inventory R1](s4-results/2026-11-12-inventory-r1.json): Windows Python3.14.8, PATH docker/podman/nerdctl không thấy; common Docker Desktop/Podman executable paths đã kiểm không có. WSL Ubuntu-24.04 Python3.12.3 uid1000/kernel6.18.40.1 có unshare userns probe0, nhưng PATH/common runtime paths không tìm docker/podman/nerdctl/runc/crun/rootlesskit/slirp4netns/newuidmap/newgidmap. cgroup membership `/non-systemd`; root/current writable=false; kernel controllers cpuset/cpu/io/memory/hugetlb/pids/rdma được liệt kê, **delegated enforcement NOT PROVEN**. Không suy software absent mọi nơi hoặc engine impossible trên host.

Launch gate **BLOCKED**, actual engine execution/network/resource/cleanup **NOT RUN**. Preflight deliberately has no accepting launch/control adapter; executable paths hoặc forged ready flags không tự bật engine. Userns probe0 chỉ chứng minh phép namespace probe đó, không engine/image/cgroup controls. Không global install/system changes, unsafe host fallback, real credentialed engine/service context hoặc production stack choice.

Nhánh độc lập thực hiện: actual Linux filesystem collector/private FD containment and denial behavior; đây là **preparation/collector subset**, không actual container integration. Next prerequisite: approved runnable rootless engine + pinned image/disposable context + actual delegated resource/network controls, sau đó actual release/cleanup/collector/auth/quarantine pipeline probes. Chưa tự download/install engine vì current environment chưa có candidate runnable/delegated control setup trong scope; không coi metadata retirement của IAP-B là proof cleanup.

## Outputs / acceptance

New `spikes/s4/preflight.py/collector.py/run_collector.py/test_preflight.py/README.md`, protocol, inventory + collector R1/R2 evidence, record này và5 current docs. No original source/schema/protocol/fixture/evidence đổi. Collector operator-only receives FD+independent root anchor+synthetic scope, no transport auth or IAP-B binding; no content release allow path. Before/after stat checks only reject **observed changes**, not atomic snapshots on arbitrary filesystem. Deadline cooperative only, no hard blocked-syscall timeout or worker/process cleanup guarantee.

DoneWhen subset: actual selected F01–F08 PASS with filesystem/negative/budget/FD evidence; required core/preflight/preservation/docs checks PASS; independent latest CLEAN, old/recurrent/new findings resolved. Full S4/S6/P3-B/P4-A/P4-B/readiness gates stay open regardless of this subset DONE. No raw fixture values in Git/evidence/logs or ordinary APIs; temporary synthetic Linux files cleaned by fixture.

## Actual execution / evidence

| Evidence/check | Actual | Scope |
|---|---|---|
| [Inventory R1](s4-results/2026-11-12-inventory-r1.json) |Windows preflight exit2, OBSERVED Linux inventory exit0, engine BLOCKED|Discovery only, not execution PASS |
| [Collector R1](s4-results/2026-11-12-collector-r1.json) |8 groups PASS0.798s/6 input hashes before=after|Initial Linux subset, before closed-FD normalization fix |
| **[Collector R2 latest](s4-results/2026-11-12-collector-r2.json)** |**8 groups PASS0.782s/6 inputs before=after/current match**|Constructor closed-FD/fstat failure safe code/no leak; serialized shared budgets/concurrent probe added |
| Windows core regression |45 PASS33.517s, no failures/errors/skips|Unchanged core/rules/report source, independent offline process |
| Windows S4 preflight tests |4 PASS0.008s initial;4 PASS0.015s recheck after collector fix|Missing/timeout/malformed/forged-ready fail closed and actual direct Windows collector denial |

Commands: `py -3 --version`; `py -3 -B spikes/s4/preflight.py` captured stdout to fresh inventory JSON (exit2 expected BLOCKED); `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`; `py -3 -B -m unittest discover -s spikes/s4 -p 'test_*.py' -v`. Linux harness `wsl -d Ubuntu-24.04 -- python3 -B <converted-repo>/spikes/s4/run_collector.py docs/s4-results/<fresh>.json <caller-held-git-HEAD>`; exact command stored local `.cache/s6/s4-a/collector-command.json`, baseline independently from Windows Git. Linux temporary filesystem fixture native under `/tmp`, not Windows path behavior; actual Python/kernel/uid and input hashes in JSON.

Two host discovery/launch mistakes retained as history: initial PowerShell→sh inventory lost tool names through native quoting, discarded as authoritative evidence; corrected stdin script showed named tools accurately. Initial wslpath conversion using Windows backslashes failed **before collector execution**, so no fake collector ERROR/PASS claimed; using forward-slash Windows path fixed conversion, inventory R1 preserved and new collector R1 ran. `.cache/s6/s4-a` retains command/logs, no secret content; no repeated unchanged failed command.

| Group | Latest actual proof | Remaining boundary |
|---|---|---|
| F01 |Read-only actual inventory + blocked engine gate even claimed ready; Windows missing/timeout/malformed tests, Linux flags/user context observed|No engine/container/control attestation |
| F02 |Private regular/empty/nested/Unicode bytes, digest/length; detached scope; wrong inode anchor, closed FD/fstat failures fixed error and no FD leak|FD+scope is trusted operator context, not authenticated worker authority |
| F03 |10 invalid path shapes, leaf+directory symlinks denied|No host/privileged-mount compromise defense claim |
| F04 |Actual FIFO/socket/directory/hardlink and regular→FIFO swap denied; separate fork probe completes under2-second harness guard|Harness guard not product hard IO/process-cleanup proof; no actual device-node probe |
| F05 |Parent rename+external symlink swap still reads original pinned directory; pinned leaf unlink/symlink replacement observed and denied|Observed FD/metadata containment, not atomic mutable-filesystem snapshot |
| F06 |Per-file/aggregate/count cap, actual growth/same-size write denied; two concurrent calls share total budget with one accepted, one E_SIZE; failed calls no returned bytes/accounting|No executor resource limits/cgroup enforcement |
| F07 |Actual cooperative clock deadline crossing denies payload; missing-capability negative and Windows native collector fail closed|Hard stalled-filesystem timeout/descendant cleanup NOT RUN |
| F08 |4 roles×5 channels always E_RESTRICTED incl fake labels; safe repr,200 failures without FD leak; raw/base64/hex canary absence in emitted diagnostics/evidence|No sanitizer, encrypted quarantine adapter, model/source/export allow route or zeroization guarantee |

Raw bytes only in private memory/temp fixture, no JSON output/logging of bytes; no actual project data. SHA256 identifies content, not actor/auth; internal manifests not ordinary export permission. No Vault/key/broker API invoked. Memory-only `RestrictedBlob.private_bytes` explicitly trusted host helper, cannot be treated as QA route.

## Current finding ledger

**S4-RV-01 CLOSED** theo independent CLEAN R2, không finding cũ/tái xuất hiện/mới chưa xử lý trong selected scope. Required checks PASS, DONE chỉ preparation/private collector subset. Reviewer early source review found constructor error normalization gap, root fixes then actual new snapshot tested; historical R1 not rewritten.

| ID | Expected / actual / impact | Fix / actual recheck / closure |
|---|---|---|
| S4-RV-01 / P2 |Constructor os.dup/fstat on stale FD could expose raw OSError instead of fixed error; unsafe diagnostic boundary|Dup/fstat failure → fixed E_CONTEXT, cleanup any duplicate; actual closed FD + injected fstat failure preserve FD count in F02 R2; reviewer R2 verified CLOSED, no regression/new finding |

Root also serialized collect/close so concurrent private calls share budgets safely, F06 actual two-thread test. No old source changed. Snapshot hashes/docs/preservation checks and official reviewer verdict append after actual execution; no self-closing findings. Substantive changes after CLEAN require review again; administrative status/verdict alone allowed afterward.

Primary implementation references (not execution evidence): [Python FD APIs](https://docs.python.org/3.14/library/os.html), [Linux O_PATH/open](https://man7.org/linux/man-pages/man2/open.2.html), [kernel cgroup delegation](https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html). Source and actual probes bound claims to this subset; no general hostile-repo isolation/security guarantee.


## Root actual snapshot checks — S4-A R2 / official review1

`py -3 -B .cache/s6/s4-a/check_output.py official-r1` **PASS**:348 original paths byte-exact +5 current-doc original suffixes,353 baseline files protected.202 local links/fences/newlines/whitespace/AST/credential-pattern checks; latest collector F01–F08 PASS/6 source hashes before=after/current match; core45 + preflight4 logs match actual. Engine remains BLOCKED/NOT RUN. `git diff --check` exit0. No DB/model/API/engine calls or old source/protocol/evidence/fixture changes; cache ignored.

Fourteen-body raw working-byte manifest excluding this record: SHA256 UTF-8 of sorted `path + ASCII space + SHA256(raw file bytes)`, join LF **without trailing LF** = `26b92925762e52838ed357000d65120f36eb93d81c1345211871e4e5c0c9c4d1`.

| Body path | Raw SHA256 |
|---|---|
| `docs/DECISION-LOG.md` | `4f5c89e1f13a24c99fe88bd7e29a79c5c25c208b0dd076a0f9e06343af023cde` |
| `docs/IMPLEMENTATION-PLAN.md` | `6ca0d97ee6badac191e32e1b2d1e12ca9b7e6bb7d8d03169df4b74d01385347d` |
| `docs/NEXT-SESSION.md` | `2377a90ddb8bc8d94aefff6818ba32519054cebe1cc0d4a190cb638c612c4b6e` |
| `docs/S4-A-PROTOCOL.md` | `ccf9da172de3f3e33596c0fdf954b03fdeff1dc50209af2b5f54c13a593310a2` |
| `docs/SESSION-HANDOFF.md` | `8114b44d0f8687fd08c85523893cc3633ea6be49992c8af3f71a29ba195dfe6d` |
| `docs/SESSION-PLAN.md` | `e021ca5179224bea4b97f3d618cae3603d345555287ab2d827d0457ab0f00b43` |
| `docs/s4-results/2026-11-12-collector-r1.json` | `4b74985f902e97f33c388ae4c1664887e1f2b8d1bbdae74a1a432c6e32d63ae6` |
| `docs/s4-results/2026-11-12-collector-r2.json` | `b1e76450d2f8f8a19fd66edec2a0b513ebf654b6786157786d5621b52f6cac9d` |
| `docs/s4-results/2026-11-12-inventory-r1.json` | `4ba8f9a51f831aa8989c0e5e5464bc129f481204e21a7640e223d86b433d1acc` |
| `spikes/s4/README.md` | `f8cc50a91b5b8f61feb00eb95518c704616dcd7d0233f9872b507690014c37d2` |
| `spikes/s4/collector.py` | `515bf7958a979c0476ff96c223ad72649ffe53d8841f94ffbc406fcc93477f94` |
| `spikes/s4/preflight.py` | `104446c72082b68859af2d4972b8814caecdde683407e3248c33026bda057177` |
| `spikes/s4/run_collector.py` | `30b81ca2a7552d1f665c373c35580bf3a55f8cd4aaf28663074575e42e69bb5b` |
| `spikes/s4/test_preflight.py` | `bf2be99d6cb1ca337938890822067c8a579694491c60e5910c407acd3dbcbb1c` |


Independent reviewer receives exact14-body + self-record + source/evidence/finding/limits. Root logs/checker/baseline retained ignored `.cache/s6/s4-a`; input hashes and Linux runtime in collector JSON, actual scope-specific inventory JSON separate. Historical R1 refers previous collector source; do not rewrite it to current R2 or Git-normalized bytes. Await reviewer closure/CLEAN; no self-DONE.


## Final independent verdict — S4-A R2 CLEAN

12/11/2026. GPT-6.1 Terra high `/root/identity_contract_review` confirmed **CLEAN** trên exact14-body manifest `26b92925762e52838ed357000d65120f36eb93d81c1345211871e4e5c0c9c4d1` và self-record SHA256 `4e36750789e989daba7bd766e8ef889c6e61532ae011ffa5af1e6977e4208867`. S4-RV-01 CLOSED, no new/recurrent finding in selected scope; reviewed constructor normalization/FD cleanup, collect/close lock và actual concurrent budget probe. Independent `py -3 -B .cache/s6/s4-a/check_output.py reviewer-r2` PASS348 old paths/5 suffixes/202 links/8 collector groups/6 input hashes/core45/preflight4/diff0.

**DONE chỉ independent inventory/private collector preparation subset**. Engine launch vẫn BLOCKED; actual engine execution/network/resource/hard-time/worker cleanup NOT RUN, không full S4 hoặc product readiness. No authenticated bridge/encrypted quarantine/sanitizer/atomic-snapshot guarantee. Sau verdict chỉ status/ledger/verdict hành chính trong self-record và5 current-doc prefixes; raw source/protocol/README/test/evidence và historical manifests giữ nguyên. No runtime rerun/Git action/real API hoặc production-stack choice sau verdict.


Final post-verdict administrative check `py -3 -B .cache/s6/s4-a/check_output.py final` **PASS**348 old paths/5 exact suffixes/202 links,8 groups/6 source hashes/core45/preflight4,diff0; launch BLOCKED/engine NOT RUN. Administrative14-body manifest `34a331639afea6b12f7252c4cba68eb69304638f5c755fa8791249c45b8032fd`, separate from historical reviewed R2 manifest. No source/evidence/protocol behavior change, Git action or extra runtime execution sau verdict. Output mới uncommitted/unpushed; full gates giữ trạng thái mở.
