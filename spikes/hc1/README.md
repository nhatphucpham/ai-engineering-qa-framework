# HC1 — versioned host orchestration experiment

[Protocol](../../docs/HC1-PROTOCOL.md), [results/review](../../docs/HC1-RESULTS.md). This is a trusted-local synthetic P4-D/P4-A slice. It reuses the unchanged VF1 fixed rootless executor, bridge/core and narrow viewer template. It does not select a production host SDK/platform or implement an unattended connector. Python 3.10+ and the already provisioned Ubuntu-24.04 Python/Podman/crun/systemd delegation are required; no installation or network download. Use an unused batch ID.

```powershell
py -3 -B spikes/hc1/orchestrator.py collect <fresh-batch>
py -3 -B spikes/hc1/orchestrator.py offer <fresh-batch> --label a
# No configured connector: waiting_connector, no report or inference.
py -3 -B spikes/hc1/orchestrator.py offer <fresh-batch> --label a --agent-task <native-task-id>
# Retain dispatchDigest in the trusted caller, separate from model output.
# Invoke the actual fresh-context host agent with only the returned offer.
# It includes responseContract.schema and responseContract.instructions (no answer/golden).
# Agent echoes offered runId/jobId/jobDigest in its native vf1-host-response-1.0.0 proposal.
py -3 -B spikes/hc1/orchestrator.py complete <fresh-batch> --label a --ticket <held-dispatchDigest> --response <native-response.json>
```

PowerShell can capture and parse the machine offer directly; stdout JSON uses ASCII escapes so Windows console/pipe encodings preserve all Unicode after decoding. On-disk canonical bytes remain UTF-8.

```powershell
$qaOffer = (py -3 -B spikes/hc1/orchestrator.py offer <batch> --label a --agent-task <native-task-id>) | ConvertFrom-Json
$qaHeldTicket = $qaOffer.dispatchDigest
# Keep $qaHeldTicket in the trusted caller; pass $qaOffer to the native host integration.
```

Repeat offer/invocation/completion for B with its own offer, native task and ticket. Native invocation, response saving and completion are still mediated by the session tools. Completion automatically validates execution/source bindings and the proposal, calls core, and publishes `accepted/{view.json,viewer-data.json,dashboard.html,receipt.json,...}` together. Open that standalone `dashboard.html` directly; no separate derive/build command or status editing. Internal bundle/assessment/prepared files stay outside the narrow viewer's embedded data. The result is a synthetic internal proposal, lifecycle `analyzing`, human decision `pending`; `view_ready` is HC1 presentation state, never production `report_ready`/completed or authorization to export content.

Caller supplies transport metadata from actual launch configuration. Agent task/model strings are engineering provenance, not authentication or token/cost attestation. The native model cannot change caller-held anchors by echoing replacements. The completion entry point constructs the HC1 envelope from the caller ticket and the unchanged native proposal; both outer ticket and inner run/job/request bindings must match. Do not feed full private execution, old responses, reports or expected conclusions to an actual assessor.

The offer embeds a complete wrapper schema with nested definitions from [P2 v2](../../schemas/qa-assessment-v2.schema.json) and the copyable [host instructions](HOST-INSTRUCTIONS.md). Their canonical digest is bound in dispatch; contract drift rejects completion. No source-code reverse engineering or old proposal is required. The nested assessment schema alone is not the native VF1 wrapper. `receipt` validates by deterministic reconstruction from held execution/request, the archived native proposal and the current compatible producer `hc1-orchestrator-1.0.1`; metadata or refreshed self-hashes cannot promote human approval. Prior experimental producer receipts are historical, not silently upgraded or reported as current replay PASS.

One relational rule goes beyond JSON shape: the reused VF1/P1 bridge includes only observations referenced by bindings in its handoff. Include evidenceReviews only for observations actually used by bindings, each ID once. Reviewing an offered but unbound observation produces `E_ASSESSMENT_REFERENCE`; preserve that rejected native proposal and ask the same assessor to correct the proposal within the attempt's deadline. Do not invent a binding merely to make an unused review pass. The final live run exercised this rejection/correction path; the embedded schema is a shape contract and does not guarantee semantic acceptance.

`drive(folder, transport, connector)` is a platform-neutral callable seam. With no connector, it waits. With a trusted callable, it reserves a fresh dispatch once, calls it, then auto-publishes core/view. Existing dispatch, disconnect or ambiguous invocation never auto-retries; a missing invocation marker is not permission to invoke again. Repository tests use authored historical replay callables for transport conformance only. They do not prove native model integration. A real unattended adapter still needs target selection, cancellation/budget/process supervision, policy/auth and native integration evidence.

```powershell
py -3 -B spikes/hc1/orchestrator.py status <batch> --label a --ticket <held-dispatchDigest>
py -3 -B spikes/hc1/orchestrator.py cancel <batch> --label a --ticket <held-dispatchDigest>
py -3 -B -m unittest discover -s spikes/hc1 -p 'test_*.py'
py -3 -B -m unittest discover -s spikes/vf1 -p 'test_*.py'
py -3 -B -m unittest discover -s tools -p 'test_*.py'
```

Deadline is checked at admission and before publication; CLI uses a one-hour cap. Cancellation fences completion but does not claim to terminate an already running native model/callable. Same valid completion after publication returns the exact receipt even after deadline; conflicting bytes or damaged accepted files reject. Invalid proposals are archived under `submissions/` and may be corrected within the same attempt/deadline without rerunning checks or silently discarding their history. No automatic model retry/budget expansion. Concurrent mutation rejects via `.mutation-lock`; abandoned locks after process death require explicit investigation. Atomic directory rename avoids partial accepted output during ordinary failures; this is not power-loss durability or S4-F supervisor recovery. Collection is exclusive and never resumes/overwrites; after any executor error, inspect exact diagnostics and owned resources before another fresh batch.

The standalone browser checker uses the existing bundled Playwright/Chrome, fresh contexts and no personal profile: `node spikes/hc1/browser_check.cjs <batch-path> <fresh-output-path>`. It checks each generated run at390/1280px and light/dark, status text against its derived view, retained keyboard focus/source disclosure, own-run provenance, B coverage gap visibility, overflow, errors and zero network. These checks cover the generated synthetic viewer, not a native Windows client or product usability.

Full S4-F/authenticated worker/broker/secret/ordinary content-export/GitHub-live/native desktop/P5/P6 gates remain OPEN. MOCK-06 bugs and historical v1/v2 evidence remain untouched. No real account/API/key/project, pilot, package/publish or new Git action follows from this slice.
