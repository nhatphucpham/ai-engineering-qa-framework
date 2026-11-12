# S4-A preparation / private collector subset

[Protocol](../../docs/S4-A-PROTOCOL.md), [results/review](../../docs/S4-A-RESULTS.md). Actual engine execution/resource/network/hard-time/cleanup controls **NOT RUN**; launch gate deliberately blocked. Current Windows/WSL discovery is scoped observation, not proof that software is absent everywhere. No global install, host workload fallback or production stack selection.

Windows discovery and independent preflight tests:

```text
py -3 -B spikes/s4/preflight.py
py -3 -B -m unittest discover -s spikes/s4 -p 'test_*.py' -v
```

Preflight Windows exit2 means blocked engine readiness, not failure of the inventory itself. Internal `--linux` returns inventory success exit0 with launchGate still BLOCKED. Executables/claimed booleans alone cannot enable launch; no accepting adapter/control proof implemented.

Run collector harness in WSL native Linux (repo path converted with `wslpath -u`), using caller-held baseline hash from Windows Git:

```text
wsl -d Ubuntu-24.04 -- python3 -B /mnt/e/phucpn-workspace/git/ai-engineering-qa-framework/spikes/s4/run_collector.py docs/s4-results/<new-id>.json <baseline-sha40>
```

Use a new evidence path. Harness creates only its own temporary synthetic files on Linux filesystem and cleans them up; no actual repo/code/log/key inputs. Windows direct collector is unsupported/fail-closed. Source/manifest identity is working bytes, not attestation; evidence compares input hashes before/after. Linux version/environment recorded at run, no global dependency install.

Private collector requires host-held root directory FD + independent inode/device anchor and synthetic scope. Directory components are opened relative to FDs with no-follow; leaf uses O_PATH and fstat type/link/size before read of pinned `/proc/self/fd` handle. Raw bytes remain private memory-only restricted output. `qa_content` always denies every role/channel, including fake sanitized/authorized claims. No Vault/broker/sanitizer/authenticated worker integration or ordinary export/read allow route.

Stat fingerprints reject observed mutations, not universal atomic snapshots. Deadlines are cooperative checks around IO; no hard stalled-filesystem syscall cancellation or process/worker cleanup guarantee. Fork/time guard in special-file tests belongs to harness only. Do not claim full S4 or connect this helper to actual worker release until engine/resource/network/cleanup and trusted collector/quarantine/auth integration have evidence. Preserve old source/protocol/fixtures/evidence and actual ERROR records; diagnose ignored `.cache/s6/s4-a/collector-last-error.txt` before new filename/retry.
