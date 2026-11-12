# S4-B v1 — authorized rootless engine setup and actual control subset

12/11/2026. User mới yêu cầu **“cấp quyền hoặc tìm cách run thử”**: cho phép setup/cấp quyền hệ thống cần thiết cho synthetic experiment, thay giới hạn mặc định không thay hệ thống ở S4-A trong phạm vi cụ thể này. Baseline master0d1c453 + uncommitted S4-A DONE giữ nguyên. Reviewer GPT-6.1 Terra high `/root/identity_contract_review` read-only từ đầu, stable S4B-RV IDs. Protocol chốt trước setup mutation/code thử; không commit/push/production-stack choice hoặc real accounts/keys/API/projects.

## Setup plan / scope / rollback

Actual read-only: WSL Ubuntu-24.04 systemd PID1; root UID0 có thể dùng qua `wsl -u root` trong quyền user vừa giao; user workload UID1000. Mount cgroup2 rw/nsdelegate nhưng current `/non-systemd` không writable; user@1000 has Delegate=yes but inactive giữa WSL commands. Không yêu cầu password hoặc enable global lingering/đổi WSL boot config.

1. Snapshot package versions trước setup và current source/nonignored hashes. Chỉ cài maintained Ubuntu archive packages cần experiment (Podman/crun/uidmap/slirp4netns/fuse-overlayfs) bằng APT signature verification, exact selected versions recorded; không upgrade toàn distro/daemon root hoặc thêm external repo/signing key. Record new dependencies và no arbitrary autoremove. Package install là system change được user mới cho phép, không production stack decision.
2. Prefer root-created **transient systemd service** `qa-s4-*`, `User=phucpn`, `Delegate=yes`, `DelegateSubgroup=supervisor`; workload/helper/engine rootless UID1000. Delegate chỉ cgroup của service, không chown toàn cgroup tree hoặc cấp quyền global. If supported, private container parent dưới delegated unit; no internal-process/controller bypass. No restart WSL hoặc dừng unrelated jobs.
3. Dedicated rootless Podman storage/runroot/config/authfile trong marked Linux temp/cache directory của experiment, không default user engine storage/context/credentials. Ưu tiên synthetic local rootfs từ signed Ubuntu `busybox-static` package: pin binary/tar/image digests before checks, tránh registry credentials/network không cần thiết. Nếu cần public registry chỉ anonymous tooling; subsequent run `--pull=never`, image ID exact. No registry login, no host sockets/keys/home/repo mount rộng. Lý do refinement trước image execution: local signed-package fixture đáp ứng workload test mà không tải image ngoài.
4. Containers label/name unique `qa-s4-*`; nonroot inside and rootless host, read-only root, caps dropped/no-new-privileges, network none, finite memory/CPU/PID, only narrowly scoped temporary output/input fixtures when needed. Fixed synthetic commands, không shell từ artifact/model/client. Authority IAP-B không tự attach vào executor; standalone actual controls first.
5. Cleanup only exact task-owned container IDs/names/label + transient cgroup/unit/storage marker. Retain diagnostic metadata if cleanup cannot verify, do not claim stopped. End inspect all owned resources, units/cgroup emptiness, no unrelated cleanup or prune. Leave distro packages installed with recorded versions for next run; rollback commands list only newly installed packages, never automatic dependency removal. No persistent privilege/cgroup/boot/linger change intended; transient service collected after run.

Outputs `spikes/s4b/` setup/actual harness/README and fresh `docs/s4b-results/` evidence, results/review, current plan/decision/handoff. Cache binary/image/raw diagnostics ignored under existing cache patterns or marked Linux private directory. Preserve S4-A protocols/evidence/source exactly; no rewriting NOT RUN history as prior actual engine proof.

## Selected actual acceptance before execution

| ID | Probe | Required actual observation |
|---|---|---|
| E01 |Setup/rootless/pinned image/namespace |Versions/provenance; host engine UID1000/rootless, inner UID nonzero; image pinned; inspect namespace/cgroup and no privileged/socket/broad mount |
| E02 |Readonly/no-new-privileges/capabilities/input containment |Actual rootfs write denied, no privilege escalation/caps, no sensitive host mounts; bounded safe outputs |
| E03 |Network none/controlled local sink |Actual namespace contains loopback only/no default route and container attempt cannot reach host synthetic listener; no provider/GitHub/model calls |
| E04 |Memory/CPU/PID controls |Actual cgroup files match configured values; bounded synthetic pressure or events prove selected enforcement, distinguish configuration-only CPU rate from measured throttling; no uncapped fork/memory bomb |
| E05 |Cancel/timeout/descendants cleanup |Actual long-running synthetic container stopped/killed, inspect stopped state/PIDs and cgroup no live processes; cleanup time measured. Any unknown → pending incident/NOT PASS, no bool metadata cleanup substitute |
| E06 |Repeat/restart/owned-resource cleanup |Repeat fresh container no stale ownership/outputs, only owned IDs removed; temp service/cgroup and containers verified quiescent; image/storage provenance retained or scoped cleanup recorded |

Selected engine control subset only. Actual output collector from S4-A may be exercised on narrow mount if feasible but no automatic trusted execution/assessment/secret-safe sanitized export claim; authenticated server/worker/IAP-B/cancel-revoke race/broker/OS keys/full recovery/end-to-end remain open. If setup fails, preserve ERROR/NOT RUN with exact cause and smallest restore step; don't lower expected or switch to rootful workload/host checks to call PASS.

DoneWhen: selected actual probes with version/source/command/expected-actual evidence PASS, source preservation/core relevant checks, latest high-model CLEAN/no old/recurrent/new findings. Scope DONE not full S4/P3-B/P4-B/readiness. External docs guide APIs only; use actual cgroup/network/process evidence, not flags/inspect alone for runtime enforcement.

Primary references: [Ubuntu Podman package](https://packages.ubuntu.com/noble-updates/amd64/podman), [Podman4.9.3 run flags](https://docs.podman.io/en/v4.9.3/markdown/podman-run.1.html), systemd installed man pages for delegation/transient unit behavior. Verify supported properties/version on actual host before use.
