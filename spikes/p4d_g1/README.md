# P4D-G1 trusted offline ingress 1.0.0

Read [protocol](../../docs/P4D-G1-PROTOCOL.md) and [results](../../docs/P4D-G1-RESULTS.md).
This is a synthetic conformance port calling unchanged `runtime_candidate.Application.dispatch`.
It has no public HTTP receiver, provider authenticator, GitHub revision resolver, unattended
host connector or model-provider implementation. Trusted fixture pairings are never provider proof.

With retained, verified Python 3.14.8/PostgreSQL prerequisites and the marker-bound DB STOPPED:

```text
py -3 -B -m spikes.p4d_g1.run_conformance g1-<new-exclusive-batch>.json
```

Root alone owns DB start/stop. No WSL/container/QA/model execution. New schema/state is retained
under ignored `.cache/p4d_g1/`; credentials stay private. The final injected precommit failure
intentionally leaves this disposable schema authority-unresolved. Do not repair or reuse it as
healthy state. Its existing DB/service is stopped after the campaign.

`receive` atomically records the local page/cursor and pending bindings; `drain` explicitly calls
intake/start in separate authorized, idempotent API transactions. Cursor commit does not imply a
run exists. Source-only fixture registration creates new synthetic snapshot/run identities;
it does not fetch a Git commit or import prior QA/reasoning results. No automatic drain/retry or
reconciliation of unresolved receipts. Full P4-D remains OPEN, count 7/12.
