# Source scope and private report recovery cases

The synthetic M50 integration campaign exercises these cases over loopback TLS and PostgreSQL. The operator controls fixture registration and inspects persisted state.

| Case | Setup and expected behavior |
| --- | --- |
| I25a | A `repo_task` snapshot contains eight required safe source IDs. The live config and the snapshot both carry config version 2 and policy version 2. The config omits `artifact-1`. Intake returns `E_DENIED` with zero intake, run, receipt, event, execution, assessment and report rows. |
| I25b | The same omission denies a `handoff` intake with the same empty persisted graph. |
| I26 | The config includes all eight required safe sources. Two restricted origins, two canaries and one optional safe auxiliary source are registered and omitted from the allowlist. The synthetic imported candidate reaches publication through separate scheduler, worker, collector and assessor credentials. TLS returns the completed report with links scoped to allowed sources and exactly one report-ready event. |
| I17 | The operator holds the original private package reference and bytes alongside the original issuer anchors before cutover. After the real PostgreSQL restart, the operator reads the restored private package through the target application and compares the reference and bytes, replays the package with the issuer anchors, and checks the target binding. TLS checks cover the ordinary report view and outbox. |

Each I25 case then uses operator fixture SQL in its isolated schema to install a legacy intake with its receipt, followed by a legacy queued run with its start receipt and initial event. The public intake replay, start, start replay and claim all return `E_DENIED`. The denied calls leave the rows and counts unchanged. The queued run acquires zero attempts, assignments or effects. These rows represent preexisting state for defense in depth.

The cases use the historical HC1 snapshot as imported input. The I17 backup and activation require an online authority source at cutover. Private package bytes stay in operator memory during verification.
