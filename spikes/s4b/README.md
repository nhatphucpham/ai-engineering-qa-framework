# S4-B actual rootless container experiment

[Protocol](../../docs/S4-B-PROTOCOL.md), [results/review](../../docs/S4-B-RESULTS.md). User explicitly authorized granting/setup needed to run. Ubuntu WSL packages Podman4.9.3/crun1.14.1/uidmap/slirp4netns/fuse-overlayfs + busybox-static installed from signed archive with exact versions recorded; no distro-wide upgrade. Newly package-enabled root Podman service/socket/timers disabled again. No persistent WSL boot/linger/cgroup permission change.

Root is used only to install dependencies and create a transient `qa-s4-*` systemd service. Workload, engine and helper run as UID1000, rootless. Transient service uses User=phucpn, Group=phucpn, Delegate=yes, DelegateSubgroup=supervisor, MemoryMax=512M, TasksMax=256; the helper enables cpu/memory/pids only below that owned unit. `systemd-run --wait --pipe --collect` removes the transient unit after completion.

Harness invocation from the authorized root WSL setup channel (convert repository path using forward slashes + wslpath):

```text
systemd-run --unit=qa-s4-<unique> --wait --pipe --collect --property=User=phucpn --property=Group=phucpn --property=Delegate=yes --property=DelegateSubgroup=supervisor --property=MemoryMax=512M --property=TasksMax=256 /usr/bin/python3 <repo>/spikes/s4b/run_engine.py docs/s4b-results/<new-id>.json <baseline-sha40>
```

Fresh evidence filename required. Engine storage/config/authfile/runtime are private marked `/tmp/qa-s4-engine-*` trees, never default user/root storage or registry credentials. Local rootfs from signed Ubuntu busybox-static has binary/tar/image hashes; run exact pinned image ID with pull=never, no registry login. Fixed fixture commands only; not a public shell or application executor API.

Containers are nonroot UID1000 with read-only root, no effective capabilities/no-new-privileges, network none, finite memory/CPU/PID, narrow fixture binds and private tmpfs. Pressure tests execute only after actual cgroup limits verified. Only owned exact container IDs are stopped/removed, never prune/default context or unrelated units. Cache/image metadata retained under its marker for diagnostics; do not recursively delete a computed path without marker/scope/ownership checks.

Expected actual probes E01–E06 cover selected runtime controls, private output collector roundtrip, controlled local network denial, CPU throttling/PID max/OOM events and descendant stop/cgroup emptiness. No authenticated server/IAP-B integration, full cancel/revoke race, broker/secret injection, sanitized export, hostile-repo proof or production stack decision. S4-A historical NOT RUN observations remain unchanged. Package rollback is explicit only newly installed named packages (recorded), no autoremove, and should not remove tools now used by other work. No automatic uninstall at handoff.
