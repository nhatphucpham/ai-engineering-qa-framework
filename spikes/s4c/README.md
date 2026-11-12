# S4-C live local worker admission / observed cleanup

[Protocol](../../docs/S4-C-PROTOCOL.md), [results](../../docs/S4-C-RESULTS.md). Compose existing synthetic IAP-B authority with rootless S4-B engine over an owned local helper pipe. No new packages, remote worker enrollment/TLS, production executor, arbitrary commands or application terminal state.

```text
py -3 -B spikes/s6b/preflight_b.py
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py start
py -3 -B spikes/s4c/run_s4c.py docs/s4c-results/<fresh-id>.json
py -3 -B spikes/s2/local.py stop
```

Require retained pinned Windows disposable S2/S6-B setup and approved Ubuntu-24.04 Podman/crun/busybox/systemd delegation from S4-B. Runner refuses unready pins or unknown cluster marker; no external DSN/credentials. Only start an observed stopped synthetic DB; stop it after every run. Fresh filename, preserve ERROR evidence and inspect `.cache/s6/s4-c/<id>-error.log` before new execution.

Runner starts a fresh `qa-s4-c-*` transient unit using owner WSL root only to set User=phucpn/Group=phucpn/DelegateSubgroup=supervisor, 512M/256 tasks/120s ceiling. Helper/Podman/workload UID1000 rootless, private marked engine storage/config/authfile; no service credentials leave Windows controller. Fixed3-process fixture, exact pinned local image, unchanged S4-B isolation flags. Helper stdin/stdout is trusted owned process channel, not a public wire protocol. Registry generation and exact job IDs prevent unrelated cleanup. Only controller-owned observations can mark cleaned; client cleanup/authorized fields denied.

Common identity DB mutex orders live assignment check + one-use consumption against revoke. Consumption commits before IO: effect may be in flight if revoke commits afterward. Never replay consumption after error; unresolved job blocks new prepare even after IAP-B metadata retirement. Explicit supervision performs live check then stops observed resources on denial; no continuous polling or bounded revoke latency claim. `cleaned` records resource observations only, not app cancelled/completed/report_ready. Crash/lost-helper reconciliation, public active cancel, retry, broker/sanitizer/export remain open.

Helper exits clean up only owned containers; runner closes unit and verifies unit/cgroup absent. Engine caches/images and preinstalled tools retained for diagnostics, no prune/uninstall/global boot/linger changes. No automatic deletion of computed paths or unrelated data.
