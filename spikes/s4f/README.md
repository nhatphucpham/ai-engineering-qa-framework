# Whole-supervisor cleanup-only recovery experiment

This versioned synthetic experiment runs on the retained Windows PostgreSQL fixture and Ubuntu24.04 rootless Podman4.9.3/crun/systemd environment. It installs nothing and uses no real account/provider/API. Read [protocol](../../docs/S4-F-PROTOCOL.md) and [actual results](../../docs/S4-F-RESULTS.md) first. Only one operator may run shared DB/WSL effects; no concurrent campaign or existing live marked database is accepted.

From the repository root, choose an unused evidence name:

```powershell
py -3 -B spikes/s4f/run_s4f.py docs/s4f-results/<unused-name>.json
```

The runner requires the marker-bound database STOPPED before starting, uses a fresh identity schema and private engine per case, and verifies the database stopped afterward. Output and private diagnostics are exclusive. On error inspect the exact retained context, incident and known unit identities before another effect; a missing or failed listing never means clean. Do not replace old evidence or edit fixture bugs.

F01 kills the entire original delegated unit after full resource identity; F02 kills before create; F03a uses an independent live observer before full identity durability; F03b actually creates but does not start a container. A replacement is a genuinely new process/unit attaching the exact original marker/inodes/boot/image/context and independently pinned journal. It never initializes a fresh empty store. The preserved failed execution is separate from observed resource cleanup and server acknowledgement.

Whole-unit loss also kills the rootless namespace helper. The new context pins its PID/start and exact regular runtime files. Current-head and engine locks fence a bounded repair of only the proven stale pause PID file and runtime alive sentinel, with durable intent and unchanged UID/GID maps. No migrate/reset/prune or recursive deletion is used. Unknown resources, changed pins or interrupted repair remain incidents. A complete successful original-store listing and full labels/command/mount/image/process ownership are still required before exact container removal.

F04 checks wrong context/journal/binding/epoch/process identity, live old writers, altered runtime anchors, listing failure/truncation, an inactive unknown fault container, newer authority, cleanup/reassignment ordering and lost acknowledgement. Only the separately pinned inactive injected object is removed by its fault test; it never acknowledges cleanup of the original resource. F05 monitors actual original-process loss or service revocation on a separate database connection, then replaces the supervisor for cleanup only. F05 covers this local authority monitor; the candidate TLS worker/collector/native-assessment/application pipeline requires its separate integration evidence.

The source pins include actual helper/authority/identity/engine modules and protocol. The runner retains original/new PIDs and start times, full immutable container IDs, cgroups, context/journal pins and final unit absence. Assertion-level unit checks cannot replace these actual effects. Current source and required extra negatives still need final independent high-model review; do not mark this output or a full P4-C milestone DONE from a passing batch alone.
