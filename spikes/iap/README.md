# IAP-A synthetic queued-command composition

[Protocol](../../docs/IAP-A-PROTOCOL.md) defines selected acceptance before code. [Results/review](../../docs/IAP-A-RESULTS.md) records actual runs and open gates. Fresh S6-B identity namespace + versioned application tables, unchanged S6-B identity source and shared transaction mutex; no migration or old S2 namespace fusion. Trusted host/DB fixture, no HTTP/UI/service/worker/secret broker/runtime-stack decision.

From repo root with existing pinned local S2/S6-B prerequisites:

```text
py -3 -B spikes/s6b/preflight_b.py
py -3 -B spikes/s2/local.py preflight
py -3 -B spikes/s2/local.py start
py -3 -B spikes/iap/run_iap.py docs/iap-results/<new-id>.json
py -3 -B spikes/s2/local.py stop
```

Only marker-bound disposable cluster, no DSN/environment credential discovery. Check DB stopped before start: harness restarts the local DB in Q08, so never run with another fixture using it. Runner refuses existing evidence path, preserves ERROR records, writes safe fixed status summary; local `.cache/s6/iap-a/last-error.txt` holds private diagnostics. Inspect cause before new filename/retry. No global install or real accounts/keys/API.

`Application.dispatch` accepts exact version/fields for grant/configure/revoke/start/cancel/receipt; client authority fields/helper method names/fault callbacks cannot route. `_ApplicationStore` setup/SQL/hooks are trusted local fixtures, not a Python introspection sandbox. All commands and S6-B identity changes share the held identity control mutex; final DB-clock session/grant checks roll back tentative graph on expiry. Idempotency tuple excludes payload digest; digest comparison includes command parameters, excludes rotating access/grant references. Replays reauthorize live before returning historical receipt. Singleton serialization has no throughput/SLA claim.

Queued-only state has no claim/dispatch/assignment/IO ports. Cancel is terminal only because work cannot start in this model; not proof of authenticated worker cleanup. Delegation rows are metadata only. Policy updates bump epoch/config version and invalidate old grants; live S6-B membership checked under mutex, no general membership epoch/anti-rollback implementation. Candidate/input digests are synthetic selectors, no artifact authority claim. Core verification/report schemas/rules and frozen fixtures unchanged.

Actual selected groups cover transactional command graphs, two-process ordered key/policy collisions with observed DB lock waits, live role/epoch/scope, expiry rollback, deferred commit FK failure, receipt replay after DB restart and safe metadata scans. Transport response loss is simulated dropping a result after actual commit, not a network crash. Full IAP24/S4/S6/P3-B/P4-B/readiness remain open; selected-only DONE requires latest independent CLEAN + checks.
