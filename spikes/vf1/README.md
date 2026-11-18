# VF1 — synthetic input → execution → host reasoning → core → viewer

Selected local experiment from [protocol](../../docs/VF1-PROTOCOL.md). [Results and independent review](../../docs/VF1-RESULTS.md) identify the accepted snapshot; this directory is not a production worker/plugin/desktop server. Python 3.10+ on Windows for orchestration/core, existing Ubuntu-24.04 Python 3.12/Podman 4.9.3/crun and delegated transient systemd service for actual checks. No package installation, provider credential or external network is needed.

`linux_worker.py` verifies the eight allowlisted fixture inputs and trusted `test_worker.py` bytes, builds a pinned image from existing local Python/stdlib/shared libraries, executes the nine fixed tests as UID1000 in a readonly/no-network bounded container and privately collects outcomes. It checks actual process identity/cgroup/container cleanup. A nonzero/unresolved worker blocks the next run; investigate exact owned resources, never host-execute as fallback. Engine runtime/image caches remain in marker-owned `/tmp/qa-s4-engine-*` paths recorded in execution; no live task container or process remains after successful completion. Full host/supervisor-crash cleanup is outside this experiment.

`run_vf1.py` is the trusted session orchestrator. It freezes staged bytes under ignored `.cache/s6/vf1`, serializes A then B, checks supervisor cleanup and creates distinct IDs/requests from those staged bytes. Later source edits cannot relabel old observations. Derivation/audit recheck artifact bytes against worker input pins and reconstruct the complete offered job from execution, including exact tests/outcomes/reasons, timestamp/IDs, held anchors and ingestion mask. B executes all checks again, then withholds the API page/size observation before building the offered request. The full private execution remains auditable; it is not offered to B's reasoning agent. Eight source texts preserve exact UTF-8/CRLF byte hashes. `host-request.json` uses core canonical finite JSON bytes with no trailing newline; anchors retain its digest and execution-file hash.

The host reasoning port is **mediated by this engineering session**, not an implemented unattended connector. For each new request, root invokes a separate fresh-context host agent, supplies only that run's offered job plus schema and binding digest, then saves its actual native response/provenance. The agent derives obligations, contexts and mappings; it never writes outcome/status fields. No historical quality-record/oracle/golden is supplied. Root fixes request-format/policy errors through the same agent while keeping attempts. Do not generate responses by copying the checked-in run's mappings. Exact model selection is launch metadata; token usage/cost are unknown.

`core_bridge.py` validates offered hashes, scope, caller-held digest, IDs, revision, test/level provenance and response references, then calls unchanged `qa_core.application.prepare_report`. AC04 requires the designated API page/size integration observation in addition to the assessor's other scope obligations. A passing repeat-call or UI test cannot satisfy that runtime floor. `verified` still means the **stated assessed scope**, not exhaustive behavior or approval. Execution checks are in-process component integration, not HTTP. The stored P1 budget/repository placeholders are schema-only, not a live configured project. Report is an internal derived candidate; lifecycle stays analyzing and humanDecision pending.

`build_viewer.py` packages only narrow `view.json` objects, never the restricted internal bundle/prepared package/raw traces. Source excerpts are bounded and inserted using textContent. The viewer selects runs/criteria and inspects evidence/actions; it has no backend Start action. Current generated view: [dashboard-r3.html](../../docs/vf1-results/vf1-20261118-r1/dashboard-r3.html).

## Commands

Run from repo root, use an unused lowercase batch ID:

```powershell
py -3 -B spikes/vf1/run_vf1.py collect <fresh-batch-id>
# Host session now invokes fresh reasoning agents and saves exact per-run host-response.json.
py -3 -B spikes/vf1/run_vf1.py derive <fresh-batch-id>
py -3 -B -m unittest discover -s spikes/vf1 -p 'test_*.py'
py -3 -B -m unittest discover -s tools -p 'test_*.py'
```

Collection/result IDs never overwrite. Derivation prevalidates all records before writing; `--resume-exact` reuses existing output only if byte-identical, useful after an interrupted partial write. Different bytes or default duplicate operations reject. It cannot silently replace an accepted report. To update presentation while preserving evidence:

```powershell
py -3 -B spikes/vf1/build_viewer.py vf1-20261118-r1 dashboard-r4.html
py -3 -B spikes/vf1/verify.py vf1-20261118-r1 audit-new.json
```

The audit uses the frozen `baseline-paths.json` of the recorded experiment and original baseline Git commit; it verifies source preservation plus actual A/B outputs, cross-run rejection, revision/digest/hash/reference boundaries and authored error/skipped negatives. Authored negatives are tests of core semantics, not extra real executions. Duplicate collection/report attempts must leave all existing bytes unchanged.

`browser_check.cjs <rendered-preview> <fresh-output-dir> <source-fragment>` uses bundled Playwright and a fresh headless Chrome context. The repo records the specific local binary paths; it does not install dependencies or connect to personal browser state. Render the fragment with the installed visualization renderer first. Checks bind the fragment's script bytes and record fragment/preview/checker hashes; cover both runs/all four criteria at1024/320px, own-run provenance, source disclosure, retained focus through a keyboard-only run→criterion→source journey, visible failed+gap, overflow and page errors. Offline preview CDN attempts are logged separately from zero application network calls. Screenshot capture expands the iframe after viewport interaction checks; screenshot height does not imply a tested device viewport.

Do not use this trusted fixed synthetic experiment as an arbitrary source runner, remote authenticated service or ordinary content-export authorization. Original fixture bugs and v1/v2 records remain unchanged. Full S4-F/security/connector/native Windows/P5/P6 gates remain open; no pilot, product effectiveness or percent-readiness claim follows from these checks.

## Commit byte preservation

The authorized VF1 Git package adds exact-path `-text` attributes so canonical request bytes and all reviewed evidence survive staging/checkout when `core.autocrlf=true`. The audit permits only that scoped append to the baseline attributes; old policy bytes and original fixture/evidence remain unchanged. Historical review/handoff manifests retain their original snapshot hashes. New pre-push records explain later authorization prefixes, this audit-only extension and the expanded browser harness.

`browser_push_check.cjs <rendered-preview> <source-fragment> <fresh-output-dir>` adds390/768/1280px and light/dark verification without changing the viewer or original browser evidence. It writes12 full-content captures and18 scenario records. [Pre-push review](../../docs/VF1-PUSH-REVIEW-2026-11-18.md) records the actual checks, exact staged/checkout bytes and independent review verdicts. The Git request authorizes committing/pushing this package; it does not close the open product gates.
