# M50 worker acceptance

This Windows and WSL campaign exercises the synthetic API 1.1 worker and collector against the pinned disposable PostgreSQL cluster. The controlled interruption profile owns a fixed three-process container and consumes no QA inputs. The normal `vf1-fixed-1.0.0` profile uses the fixed QA executor with issuer-held source pins. See the [worker protocol](../../docs/M50-WORKER-CONTROLLER-PROTOCOL.md).

From the repository root, the operator runs one campaign at a time with the retained Python 3.14.8, WSL and pinned local dependencies. Start with the disposable database stopped and choose a new evidence name for each invocation.

```powershell
py -3.14 -B -m spikes.m50_worker.run m50-worker-20261123-r1.json
```

The runner checks local dependencies and the database's initial status before starting it. It writes one exclusive JSON file in `docs/m50-worker-results/`. Each case uses its own schema and private application state under `.cache/s6/m50-worker/<evidence-stem>/`. Normal QA staging uses the retained private VF1 staging root. Keep the private diagnostics for review alongside the corresponding evidence. The runner closes its test units and loopback listeners, then stops the owned database and checks `pg_ctl` status 3. An unexpected error stops the matrix and leaves later cases pending. Before starting a new campaign, check that the exact units from the failed case are absent and the database is stopped. Use a new evidence name for the next invocation.

| Cases | Acceptance evidence |
| --- | --- |
| UI exit and user cancellation | A spawned coordinator receives the scheduler's assignment and owns the original unit. An independent Linux observer sees the live exact container after the separate UI process exits. Cancel returns `stopping` and the separately enrolled collector can terminalize only the held cleanup pair. |
| Revocation, lease expiry, run-budget expiry, whole-supervisor loss | The coordinator detects TLS authority loss or a real unit exit. PostgreSQL records expiry timestamps and the application advances the fence before a new unit attaches the original context. |
| Before create and after start before identity | A consumed journal exists without durable container identity. Cleanup proves empty enumeration before creation and exact removal of the independently observed container after start. |
| Newer server head and unknown external head | Explicit operator fixture mutations deny application cleanup before unit I/O. Separate exact local safety teardown leaves the application graph unresolved. |
| Lost cleanup acknowledgement | The external proof is retained after the callback aborts the acknowledgement. Retry hits the old journal pin, and a valid collector cannot submit the exact pair without the held observation. |
| Coordinator restart | The initial Windows coordinator is terminated after the live resource and its context are committed. A different process receives only the fixture locator and run scope. It rebuilds from the database, verifies the original unit identity, and recovers through a new unit. The original Windows relay is observed exited through its retained process handle. |
| Normal QA cancellation and collected-work expiry | The normal executor is interrupted at its real pre-check release barrier, then recovers and supplies the cleanup-only pair. A separate run finishes real QA, obtains independent collector acceptance, and expires before assessment using that exact accepted cleanup proof. |
| Collected work with missing cleanup proof | After real QA and independent collector acceptance, an operator fixture substitutes a missing raw proof reference and preserves the original proof bytes. Real lease expiry leaves the run unresolved with an open incident and no assessment or report. |

The JSON records source hashes before and after, process and resource identities, denial outcomes, database state and outbox events. Test credentials travel over private pipes and verified loopback TLS. Evidence and diagnostics are scanned for their raw, Base64 and hexadecimal forms. The fresh native QA assessment, publication and populated checkpoint restore use the separate fresh candidate campaign. Full P4-C requires independent review of the matching evidence from both campaigns.
