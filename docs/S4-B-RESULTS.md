# S4-B authorized setup / actual rootless container controls — results and review

12/11/2026, baseline **0d1c4539cd65fdbf38b931dbcf2d39debb1756e7 + uncommitted S4-A DONE**. User explicitly requested **“cấp quyền hoặc tìm cách run thử”**. Status **DONE — independent CLEAN**, selected S4-B scope only. Reviewer GPT-6.1 Terra high `/root/identity_contract_review` independent read-only từ đầu, stable S4B-RV IDs; fix/check/re-review đến CLEAN. [Protocol](S4-B-PROTOCOL.md) written before setup mutation/code; [source/README](../spikes/s4b/README.md). No commit/push/production-stack choice/real accounts or API/project QA.

## Authorization / setup / footprint

User request mới authorizes system setup needed for experiment, overrides prior no-system-change default narrowly; historical S4-A inventory/NOT RUN giữ nguyên. Actual WSL systemd255 PID1, root via owner WSL command UID0 available, ordinary user phucpn UID1000. Transient `qa-s4-*` service with User/Group=phucpn, Delegate=yes, DelegateSubgroup=supervisor, MemoryMax512M, TasksMax256 gives writable exact child cgroup with cpu/memory/pids. Root only installs packages/creates transient service, workload/Podman/helper remain rootless UID1000. No WSL restart/boot change/linger/global cgroup chown or user service deployment.

[Setup/provenance/post-run evidence](s4b-results/2026-11-12-setup-r1.json):20 new Ubuntu signed-archive packages including deps, **0 upgrades**. Explicit tool versions Podman4.9.3+ds1-1ubuntu0.2, crun1.14.1-1, uidmap1:4.13+dfsg1-4ubuntu3.2, slirp4netns1.2.1-1build2, fuse-overlayfs1.13-1, busybox-static1:1.36.1-6ubuntu3.1. APT no-install-recommends/no-upgrade, no external repo/key/registry login; package verification for busybox exit0. Full APT plan/install logs retained ignored `.cache/s6/s4-b`, only safe package metadata committed candidate.

Package install auto-enabled root Podman service/socket/timers. Verified exact unit files belong newly installed Podman package, then disable/stop those units; restart service had failed status after stop, reset only that owned unit. Final root podman service/socket/auto-update timer/restart inactive and disabled; no retained root daemon. No default root/user engine context used by harness; no prune/autoremove or deletion of unrelated data.

Engine builds local synthetic rootfs from signed busybox-static binary, pins binary+tar+image hashes, runs exact image ID with pull=never. Private marked `/tmp/qa-s4-engine-*` storage/runroot/config/empty authfile/task child home, never real user registry credentials/default engine storage/socket. Retained marked image/cache and installed packages for reuse, not automatic uninstall. Rollback only recorded newly installed packages after checking they are still unused; no dependency autoremove. No automatic recursive deletion of computed paths.

## Actual runs / scoped evidence

| Evidence | Actual result | Snapshot limits |
|---|---|---|
| Delegate probe |UID1000 in transient supervisor, parent writable, cpu/memory/pids controllers created in owned child, exit0|Permission proof only, before engine tests |
| Initial smoke |ERROR image ID representation comparison before container launch; no owned containers|Import returned `sha256:` prefix while inspect ID lacked prefix; equal normalized64-hex identity fix, no weakening hash invariant; ignored log preserved |
| Smoke2 |Actual rootless container ran, exact owned container removed, exit0|Private image/storage and cgroup observed, no full controls claim |
| [Actual R1](s4b-results/2026-11-12-r1.json) |6 groups PASS18.926s|Before stronger network parser + finite PID pressure; retained historical snapshot, not final coverage |
| **[Actual R2 latest](s4b-results/2026-11-12-r2.json)** |**6 groups PASS17.524s,6 inputs before=after/current match**|Exact interface/route/status/namespace assertions + finite PID probe, controlled sink scope precise |
| [Post-run setup evidence](s4b-results/2026-11-12-setup-r1.json) |All5 task transient units LoadState not-found and cgroup paths absent; root package units inactive/disabled|No persistent scope/privileged workload, marked caches retained |

Actual command pattern: WSL owner/root `systemd-run --unit=qa-s4-b-rN --wait --pipe --collect --property=User=phucpn --property=Group=phucpn --property=Delegate=yes --property=DelegateSubgroup=supervisor --property=MemoryMax=512M --property=TasksMax=256 /usr/bin/python3 <repo>/spikes/s4b/run_engine.py docs/s4b-results/<new-id>.json <caller-held-HEAD>`. Exact argv and stdout/stderr saved `.cache/s6/s4-b/command-rN.json`, engine-rN logs. Root systemd launches user process, not rootful Podman. No arbitrary artifact/model shell or host test fallback; synthetic commands only.

Fresh Windows core45 PASS35.518s; S4-A preflight4 PASS0.010s; new network-parser4 PASS0.001s, no failures/errors/skips. Commands unittest discover tools/spikes/s4/spikes/s4b with test_*.py. S4-A default discovery remains conservative BLOCKED because that preparation API has no accepting control adapter, while S4-B is a separately authorized transient context with actual proof. No silent flip of historical/generic readiness.

| Group | Latest actual observations | Limits |
|---|---|---|
| E01 |Rootless host UID1000; inner UID1000; CapEff zero/NoNewPrivs1; inspect not privileged/readonly; pinned image; runtime cgroup under transient delegated parent|No deployed worker enrollment/authentication |
| E02 |Rootfs and input writes fail; only exact private input/output bind mounts; actual mounted output read by unchanged S4-A private collector and ordinaryRelease DENIED|No sanitized export, encrypted quarantine or authenticated bridge |
| E03 |Separate successful link/IPv4/IPv6 route commands; exact interfaces `[lo]`, no default form; netns differs from host. Actual request to synthetic host127.0.0.1 listener fails and sink accepts0 connections|One controlled sink + namespace topology, not every possible egress/exfiltration scenario |
| E04 |Cgroup memory.max67108864,pids.max32,cpu.max50000/100000 verified **before pressure**. CPU nr_throttled+12/throttled_usec+596282; pids.max events+1; capped32MiB memory OOM kill+1|Fixture observations, no production perf/SLA; no uncapped host stress |
| E05 |3 container processes observed; stop grace1sec, actual stop1.104s; container not running/Pid0; original PID+start-time identities not live; cgroup empty/removed|No authenticated application cancel/revoke race, no full worker failure recovery |
| E06 |Repeated fresh container/exact pinned image; all4 owned IDs removed, private context ps all empty; transient service/cgroup absent after completion|Engine restart/crash recovery NOT RUN; retained marked image cache/packages |

Image identity is actual locally imported configuration digest; deterministic rootfs tar/binary hash separately recorded. No registry image tag/credential assumed trusted. Engine flags alone are not enforcement proof: selected CPU/PID/OOM/network/read-only/process events above were observed. Actual shell strings are fixed harness fixture code, not product permission to execute arbitrary commands.

## Current finding ledger

**S4B-RV-01/02 CLOSED by independent reviewer**, current selected output DONE. Reviewer found issues before official latest snapshot; no self closure, preserve R1 historical data.

| ID | Expected / actual / impact | Fix / actual verification / closure |
|---|---|---|
| S4B-RV-01 / P2 |R1 network assertion only excluded eth0/default-via and combined command status, not exact loopback/no-default proof|R2 separate statuses and parsed exact interface list; reject default/dev/IPv4/IPv6 forms, assert netns differs.4 meaningful negative/positive parser tests. Explicit one-sink scope, not every-egress claim. Reviewer confirmed CLOSED on exact R2 source/evidence and parser regressions |
| S4B-RV-02 / P2 |PID pressure sleep20/wait with6sec exec deadline could timeout unpredictably before event observation despite actual R1 pass|R2 finite2sec children +10sec bounded exec, actual pids.events max delta still required, no PASS on timeout; stop/remove verified. Reviewer confirmed CLOSED on finite workload, fail-on-timeout and actual event/cleanup evidence |

Root source-preservation/manifests/checks and independent verdict append after actual observations. Substantive change after CLEAN requires re-review; only administrative status/verdict update afterward. No gate closure from count alone.

## Remaining gates

S4-B selected actual engine-control subset DONE after CLEAN/checks; not full S4/P3-B/P4-B/P5 readiness. Authenticated IAP-B→worker release/lease/cancel/revoke/cleanup, orphan/crash/network partition/recovery, broker/secret-use/taint/collector quarantine/sanitized ordinary export/OS keys/end-to-end still open. S4-A observed-stable/cooperative timeout limits remain; this harness doesn't turn those into universal hard syscall/snapshot guarantees. Next versioned authenticated release/cleanup integration protocol and actual failure evidence before production executor.

Primary setup/flag references: [Ubuntu package](https://packages.ubuntu.com/noble-updates/amd64/podman), [Podman4.9.3 run](https://docs.podman.io/en/v4.9.3/markdown/podman-run.1.html), installed systemd255 delegation/transient unit documentation plus actual delegate probe. Sources justify API choices, not blanket security claims.

## Preservation / final snapshot sent for review

Actual check `py -3 -B .cache/s6/s4-b/check_output.py official-r1`: PASS, 358 prior paths byte-identical and 5 current-doc original suffixes byte-identical (363 baseline paths total), 216 local links resolve, Python AST/UTF-8/fences/whitespace/scope/credential-pattern checks pass, `git diff --check` exit0. Latest R2 six source inputs exactly match both recorded before/after hashes. Fresh tests: core45 + preflight4 + network-parser4 PASS. These checks supplement independent semantic review.

The first output scan found two task-generated `.pyc` files from WSL imports and stopped before producing a check result. Verified exact paths absent from baseline and inside the two spike cache directories, removed only those files and their now-empty directories; rerun above PASS. No source/evidence changes, no recursive cleanup.

Reviewed body manifest SHA256 **1440375f2dd0c58ce2211938bea892ae9dfcf74d11deeebe3a9b9e178154052d**: 13 paths below, sorted `path + ASCII space + raw-byte SHA256`, joined LF with no trailing LF. This results record is excluded to avoid a self-hash; its separate revision digest is supplied to reviewer. Administrative verdict/status update will keep this reviewed manifest historical and record a fresh post-status check, never relabel altered bytes as reviewed.

| Path | SHA256 |
|---|---|
| `docs/DECISION-LOG.md` | `04391e99ce4be42306afb44c215cca9804c326c98de74202a73631eb1f9ff839` |
| `docs/IMPLEMENTATION-PLAN.md` | `220934df1b653f638a5402686c241a5c26522ad0d75a77dcd989f94246017027` |
| `docs/NEXT-SESSION.md` | `5d1d5841e45f06f8185b74397cfb622896d7acb018b5fecba627166ac7b734d0` |
| `docs/S4-B-PROTOCOL.md` | `7a40a08d9fd11745aa3d1b0ccb5d803c2eaba1e1b84102835e65dbcad7a5d728` |
| `docs/SESSION-HANDOFF.md` | `7399bdbbce361d2092eab3f4865b4ae7b978f3644e91a27413c7ae90987d9445` |
| `docs/SESSION-PLAN.md` | `d27aaf07b97f12c58a4bbb5c8ecd604428d04032151898a4896e1e7bb95a079c` |
| `docs/s4b-results/2026-11-12-r1.json` | `34aac5c9ab1ca615f1bd0c4c7b72ebec34b9de9c43294d20e5f0aac412ad3c64` |
| `docs/s4b-results/2026-11-12-r2.json` | `fee6efb979bef8ea480b4b8429f323e2d15b31947efe3e0be00e8057846acee3` |
| `docs/s4b-results/2026-11-12-setup-r1.json` | `a5f5f3cf32958ee36a1976f5eb713cba6042a3812457a3eadb2dfb883cb68d05` |
| `spikes/s4b/README.md` | `62e720b93fcc1a3d230fda5005f085d7ecc9bc970d0f56c0cb7bd188ed6c99e2` |
| `spikes/s4b/engine.py` | `9c493db4f40d5885acfd2cb0ab881dd44df02d17c520c352d2c25fd5eaf42e10` |
| `spikes/s4b/run_engine.py` | `3c411d42e8274297fd27456f45caafe018ccd746b0265626206bf5ce7bae0856` |
| `spikes/s4b/test_network.py` | `78979fd09a7203899566549671c70b96a5366d6beb77291193b3dca3e31e2b97` |

## Independent final verdict / administrative close

Independent read-only GPT-6.1 Terra high `/root/identity_contract_review` returned **CLEAN** for exact R2 and body manifest `1440375f2dd0c58ce2211938bea892ae9dfcf74d11deeebe3a9b9e178154052d`, reviewed results-record SHA256 `b657fe955d1d1dd03c4d42577c121bbb583888f894aa8e907fd4936d2d213a68` (before this administrative status/verdict addition). S4B-RV-01 CLOSED after exact topology/status/netns/sink and negative-route tests; S4B-RV-02 CLOSED after finite PID workload, timeout failure semantics and actual cap-event requirement. No remaining or new finding in selected synthetic engine-control scope. Reviewer independent `reviewer-r2` checker PASS:358 unchanged old paths,5 preserved suffixes,216 local links,6 actual groups/6 source hashes match,core45/preflight4/parser4,diff0.

**DONE applies only to S4-B selected actual container controls**. Required checks PASS and reviewer CLEAN; full product/worker gates above remain OPEN. Subsequent edits are only this verdict/finding closure and corresponding current-doc status; reviewed manifest remains historical. Fresh final checker captures post-status body hashes separately. No commit or push performed in this request.
