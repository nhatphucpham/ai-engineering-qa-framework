# P4-D capability audit after G1

24/11/2026, clean master/origin-master baseline `f71413f547b0963c6ca0c332f7571d6ab1f7a869`, verified by Git history and local remote-tracking ref (no fetch). [G1 final review](p4d-g1-results/final-review.json) is authoritative for its bounded DONE/CLEAN; conditional PENDING text in historical summaries does not reopen that slice. This audit is source inspection and design, not fresh execution. Full P4-D OPEN, product progress **7/12 ≈58.3%**, human decision pending.

## Current capability and gaps

The table reconciles [P1](DATA-CONTRACT.md), [target architecture](TARGET-ARCHITECTURE.md), [API1.1](../runtime_candidate/API.md) and actual source. The 05/11 as-is architecture and older plan table are historical; they do not negate M50/G1 implementation.

| Capability | Evidence already available | Still missing / prerequisite |
|---|---|---|
| Shared application lifecycle | M50 control/worker [closure](m50-results/m50-20261124-final-closure.json), API1.1 dispatch: intake/start/claim/admit/collector/assessment_accept/submit; current scope and authority checks | A reasoning adapter must join these boundaries; a second report/rules path is forbidden. M50 success does not establish provider access or deployment readiness |
| GitHub webhook | G1 R4 trusted offline receipt/binding/quarantine, explicit intake/start into API | Signature authentication, integration principal, canonical occurrence↔exact event revision provider proof, live reconciliation remain OPEN |
| GitHub polling | Same G1 binding across paired authored observations, local durable page cursor and pending plans | Provider history completeness/availability, paging/rate handling and common provider identity unproved. Receipt/cursor commit is local; receive/intake/start are distinct transactions, not atomic provider occurrence→run/cursor |
| Missing or conflicting GitHub proof | S5 negatives, G1 durable unresolved/quarantine | No current HEAD/nearest timestamp or SHA-only fallback. `trusted_synthetic_pairing` cannot become `provider_verified`; S5 hypothetical pairing cannot supply provider authority |
| Local host reasoning | [HC1](HC1-PROTOCOL.md) offer/ticket/deadline/explicit cancel and one-call callable seam; M50 [fresh flow](../runtime_candidate/run_fresh.py) session-issued offer and bounded explicit submissions | No enrolled unattended host connector, isolated context/tool/outbound enforcement or authenticated task identity. Cancel fences acceptance but does not prove native task termination. A broad-workspace host is not made policy-safe by a wrapper |
| OpenAI reasoning | Architecture provider port only; no OpenAI adapter implementation or actual call proof | Independent request/response profile and malformed/refusal/incomplete/error/usage tests; policy admission, reservation and ambiguity fencing; real credentials/API readiness separately |
| Anthropic reasoning | Architecture provider port only; no Anthropic adapter implementation or actual call proof | Independent Messages-shaped fixtures/mapping and stop/error/usage tests. No proof borrowed from OpenAI or local-host tests |
| Project outbound policy | `valid_config` in [application.py](../runtime_candidate/application.py) requires `outboundProviders == []`; source registry/classification and current config/policy fences exist | No public allow-outbound configuration, model budget ledger or reasoning-send authority exists. A sidecar config/fake provider must not enable outbound behind API1.1 |
| Reasoning result acceptance | `assessment_accept` requires enrolled assessor distinct from worker/collector, exact accepted execution and source/target pins; `worker_submit` independently publishes | Schema-valid provider output is only a candidate. New attempt fencing must cover both acceptance and publication; no provider/model supplied authority/cleanup/human approval |
| Errors, budget and replay | Core/HC1/M50 have their own bounded contracts; M50 fresh flow allows up to 3 explicit submissions in its 120-second correction window | No common three-port request ledger/usage reconciliation/uncertain-send recovery. These existing correction semantics remain historical and unchanged; new RC1 proposes one submission, no automatic correction |
| Desktop, packaging, performance | P4-A/B/C closed in synthetic reference scope | P3-B/S3 Windows release comparison/stack decision, P4-E native client/app-close/reconnect, P5 integrated technical checks, P6 target-dependent packaging remain OPEN. Dev browser timing cannot replace native comparison |

## Selected independent slice

**P4D-RC1 design only:** [versioned offline reasoning conformance protocol](P4D-RC1-PROTOCOL.md) and [acceptance matrix](P4D-RC1-ACCEPTANCE.md), before code. The immediate implementation candidate is three distinct offline mappers sharing a context/attempt contract. It can progress without credentials, host target, SDK, transport or production stack. Every adapter result remains authored synthetic transport evidence. Lifecycle integration has separate acceptance gates and prerequisites; none is implied by parser fixtures.

This continues the G1 handoff priority. Improving GitHub proof would currently require a provider-backed strategy not established by supplied data; implementing more authored correlation would not close that gap. Reasoning conformance exposes a concrete missing prerequisite (`outboundProviders == []`) and can specify failure/lineage behavior independently. No percentage target is added.

## Prerequisite order and owners

1. Framework maintainer: review RC1 design and then implement offline contract/mappers with per-port tests. No actual reasoning or application integration is claimed at this stage.
2. Framework maintainer: version and independently review a reasoning authority extension before integrated admission. It needs an operator-enrolled local capability, current policy/config binding, durable send intent/reservations, cancellation/expiry fencing through assessment_accept **and** worker_submit, and release ordering. API1.1 cannot supply these by itself. A future integration-only campaign may use imported synthetic execution, explicitly labeled; fresh QA/native reasoning requires separate evidence and is not rerun here.
3. Target decision owner: select/enroll a host whose context/tool/outbound limits can be enforced. For actual APIs, configure project data/model limits and secret custody in an authorized environment. Model/endpoint/SDK pins and reliable usage/bounds must be reviewed before automatic calls; unsupported capability stays blocked. No credentials are requested in this repo.
4. Framework maintainer + target decision owner: retain GitHub proof/auth/history gates; prepare P3-B/S3 comparison under ADR-003, then P4-E Windows through the same application API → P5 → P6 when prerequisites and target decision exist. Missing tooling is NOT RUN/unknown, not permission to install or choose a winner.

The design review closes only this audit/protocol/acceptance/handoff output. It does not close any adapter implementation, native provider/host integration, GitHub proof, product milestone, human approval, usability or ROI gate.
