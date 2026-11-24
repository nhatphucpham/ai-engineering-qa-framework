# Process loss, explicit retry and claim delivery

The serial integration harness calls `runtime_candidate.process_cases.run_cases(ctx)` before its checkpoint cases. The caller owns the isolated PostgreSQL instance and supplies `workspace`, `certificate`, `private_key`, `forbidden` and `checks`. Every group gets a new disposable schema, blob directory and loopback TLS listener through the lifecycle fixture. Each completed group adds a record to `ctx['checks']`. The output uses the API version from `common.VERSION`.

All inputs in these groups are labeled imported. A collector records historical fixture metadata and a separate assessor submits the historical candidate through its enrolled service route. No group executes a new check or invokes a reasoning service.

## Publication

I18aÃ¢â‚¬â€œe send a single authorized submit to an additional API process. Its operator-supplied observer selects one interruption point. The parent requires both loss of the actual TLS response and process exit 72 with a matching observation over a private pipe. Normal queries and explicit retries use the surviving listener with a fresh application and database connection.

| Group | Interruption | Verification after loss |
|---|---|---|
| I18a | The process writes and flushes exactly half of the private package into the staging file, then exits. | The new private fragment matches the corresponding expected bytes. No complete private object or published report reference exists. |
| I18b | Both immutable objects are durable, before SQL publication. | Exact private/view bytes exist but the run remains analyzing with zero report rows and zero report-ready events. |
| I18c | Report insert, state change and outbox insert are in the uncommitted transaction. | Its rollback preserves the original state, sequence and empty publication graph. |
| I18d | Publication has committed, before response. | One completed run, one report and one new report-ready event are visible. |
| I18e | The new external authority nonce is durable, before SQL commit. | Ordinary reads and submit retries return `E_UNRESOLVED`. The private operator method checks the retained transaction and cluster identity. Only PostgreSQLÃ¢â‚¬â„¢s aborted status permits recovery. Repeating the operator call yields the same durable intent receipt. |

Every I18 group verifies the explicit retry and its duplicate, the exact resulting report view, one report reference and exactly one new report-ready event. In I18e a second negative check obtains a known committed transition from the same isolated case. A transaction models its earlier SQL nonce, calls the private recovery method and forcibly rolls back. Recovery must refuse. Inside the rollback-only SQL transaction, the same operator recovery method also receives an in-memory fixture copy of the journal with only its transaction ID replaced by an unrelated genuinely aborted transaction ID from the same database. It must refuse before any write. The external head and on-disk journal retain their original values. The prior committed SQL nonce and external head/journal bytes and existing recovery receipts must remain intact.

## Claim and cancellation

| Group | Observable result required |
|---|---|
| I19a | Lose the committed claim response by exiting the API process. Ordinary claim retry is stale. The wrong scheduler, service audience, target worker or original version cannot recover a grant. Two independent TLS clients then recover behind the observed database mutex. Both deliveries retain the assignment and attempt, rotate the lease and advance the fence. The superseded lease cannot admit work. |
| I19bÃ¢â‚¬â€œc | Queue admit then recovery, and recovery then admit, with both clients observed waiting behind the held database lock. An admitted effect blocks grant rotation. When rotation wins, the previous lease cannot admit. Cancellation of an admitted effect uses the independent imported cleanup record. Terminal claim recovery returns safe run metadata. |
| I19d | Three rotations exhaust the delivery budget. A fourth rotation fails. Attempt, event count and unadmitted effect state remain consistent. |
| I19e | Wait beyond the lease using a delay derived from PostgreSQLÃ¢â‚¬â„¢s clock. Recovery terminalizes the unadmitted claim with one failed event and no effect. Repeated recovery returns the same terminal metadata. |
| I20aÃ¢â‚¬â€œb | Queue claim and cancel against the same starting version in both orders. Only the first command succeeds. A subsequent cancel with the current version closes the winning claim before an effect can be admitted. |

I21 queues two final submit requests for the same accepted assessment. The graph must expose one report, one event and the same receipt to both clients. I22 queues grant revocation ahead of final publication. No output package, view object, report row or ready event may appear, and an independent valid cancel grant closes the imported run. I23 queues two different scheduler credentials, each naming its own enrolled worker, for the same starting version. The successful claim gets one assignment and one event. The losing scheduler cannot recover it, and its worker cannot use the successful grant to admit an effect.

I24 starts a separate API process before a five-second run budget begins. After independent assessment acceptance, that process receives the final submit and pauses just after writing its external authority witness. A separate PostgreSQL connection confirms the deadline is still in the future, then confirms that it has passed before allowing the handler to proceed. The submit must return `E_STALE`. The authorized graph stays unpublished and ordinary reads return `E_UNRESOLVED` until the operator confirms the transaction aborted and repairs the witness. An explicit late submit must still be stale.

Fault selection, database inspection and recovery are private test/operator actions. No command-line argument contains a session, service credential or lease token. The partial staging file is retained inside the disposable case directory as evidence. These checks cover API-process loss with the database and filesystem still present. Host power loss, raw-container execution and whole-supervisor recovery require independent evidence. Use the actual campaign result for pass/fail status.
