# P4D-G1 results — 24/11/2026

Selected offline scope status follows the independent final-review record linked below; it remains PENDING until that record confirms CLEAN/DONE. Full P4-D OPEN; product count remains **7/12 ≈ 58.3%**. Baseline master `019692b688737340790722474d36b1e264aa9937`; no commit/push, branch/worktree change or production stack decision. [Protocol](P4D-G1-PROTOCOL.md), [implementation](../spikes/p4d_g1/README.md), [new handoff](NEXT-SESSION-POST-P4D-G1.md).

## Actual checks

[R4 campaign](p4d-g1-results/g1-20261124-r4.json): **19 actual PostgreSQL/application groups PASS**, **9 unit tests PASS**, 0 unit failures/errors/skips, **75.562 seconds** including preflight/cleanup. Source pins before=after; final database observation **STOPPED**, `pg_ctl` status 3. Python 3.14.8, retained PostgreSQL18.6/psycopg3.3.8 and identity dependency pins; no packages installed. No WSL/container, QA executor or model invocation. Each fixture snapshot is newly registered source-only MOCK-06 input; the SHA-shaped candidate is authored synthetic, not a fetched Git commit or provider attestation.

| Groups | What was actually checked |
|---|---|
| C01 | Unproved webhook/timeline/current snapshot, delayed/head-advanced and incomplete-history observations remain durable unresolved; no intake/run; raw claimed proof ignored |
| C02–03 | Exact registered webhook+poll pair shares one binding and two receipts; duplicate delivery/page/drain yields one intake/run/initial event. Same SHA at another occurrence creates a distinct run |
| C04–07 | Revision and snapshot contradictions stick in quarantine, prior run retained; exact digest/proof/subject/project/actor isolation; rejected mixed pages leave authority usable |
| C08–09 | New process reopens/replays committed receive and commits start without a completion marker; explicit replay when its own run fills maxQueued=1 produces no second intake/run/event; new work denied at capacity before intake |
| C10–12 | Revoked grant, role/config/data/enabled state, revoked session and absent stream deny without new effects. C11 config changes intentionally invalidate old grants; independent data-scope paths are covered in C15 |
| C13 | After one committed intake, injected failure after run_start witness write rolls back actual run/event/start receipt. Fresh process observes retained intake only, no run/event/start receipt, and ordinary read fails E_UNRESOLVED. Incident schema retained, no automatic repair |
| C14–17 | Project-wide run uniqueness across repo streams; valid current config/grant with independent stream/snapshot scope denial; start-key/different-snapshot collisions and another owner's existing run denied before a new intake |
| C18–19 | Escaped NUL keys/values and Unicode preserve exact canonical observation bytes and digest through persistence/replay; None/empty/bool/malformed session returns E_AUTH with no ledger/intake changes |

The nine unit tests cover strict subject integers/booleans, receipt derivation, unknown versions/fields/kinds/actions, bounds and contradictory payloads, plus mocked partial-startup, close/hash failure and cleanup failure paths. They do not simulate authenticated GitHub delivery or deployed services.

[Core regression](p4d-g1-results/core-regression-20261124.json): **45 PASS**, 37.917s, 0 failures/errors/skips. [Unchanged candidate regression](p4d-g1-results/candidate-regression-20261124.json): **54 PASS**, 3.121s, 0 failures/errors/skips. The candidate record's original command label is a wrapper placeholder; [verification commands](p4d-g1-results/verification-commands.json) records its actual inline runner and the reproducible test invocation separately. The first attempted core discovery used `-t .` and failed before collecting tests because tools is not a package; the successful command omitted that option. No prior actual worker/native campaign was rerun.

## Review and preserved history

Independent reviewers: `/root/p4d_review` then `/root/p4d_review_replacement`, both GPT-6.2 Astra high. First reviewer hit a usage limit; stable findings and current files/evidence transferred rather than resetting review history. [Ledger](p4d-g1-results/review-ledger.json) tracks P4D-R001–R012; [snapshot](p4d-g1-results/snapshot-final.json) pins the exact payload, [preservation](p4d-g1-results/preservation-final.json) checks original bytes, and [final verdict](p4d-g1-results/final-review.json) is written only after independent review.

[R1](p4d-g1-results/g1-20261124-r1.json) remains ERROR: setup attempted to enable source IDs before registering source-only bytes; no acceptance group reached, DB STOPPED. Setup order fixed without changing application policy. [R2](p4d-g1-results/g1-20261124-r2.json) 13 groups/5 unit PASS, but review found incomplete acceptance and implementation gaps; it is not final evidence. [R3](p4d-g1-results/g1-20261124-r3.json) 17 groups/5 unit PASS; R4 adds opaque byte preservation, missing-session and robust cleanup fixes. Each historical record retains its original source pins and is never relabelled as evidence of the new implementation.

Raw baseline contains 754 files, including four local post-M50 handoff files. Preserve those four unchanged. Only append scoped .gitignore/.gitattributes entries and prepend new current entries to IMPLEMENTATION-PLAN/DECISION-LOG; their entire original bytes remain. No fixture, S5, HC1, M50, previous evidence or historical ERROR content changed. New private `.cache/p4d_g1/` state/dummy sessions are excluded by the exact .gitignore path, checked without printing credentials.

## Remaining gates

This is a trusted local fixture port into the unchanged application API, not an authenticated GitHub adapter. Synthetic proof registration remains explicitly `trusted_synthetic_pairing`. Missing occurrence/revision provider proof stays unresolved; never current HEAD or nearest-time fallback. Provider pagination completeness, rate/history availability, authentication, integration principal and live reconciliation remain unproved. Receipt/cursor/pending plan commit is atomic locally; intake/start occur separately and may leave an intake pending. The full provider occurrence→initial-run/provider-cursor atomicity requirement remains OPEN.

Local host connector, OpenAI and Anthropic remain separate ports with their own conformance gaps. HC1/M50 reasoning is session-mediated, not unattended. Human decision pending; no inference of readiness, approval, usefulness or ROI. Next: complete adapter prerequisites, then P3-B/S3 Tauri/Electron comparison → P4-E native Windows via the same API → P5 → P6 once prerequisites and target decisions exist.
