# HC1 historical specimen import

The persistence acceptance harness can load either synthetic archive from the final HC1 live-r3 review. The operator selects A or B before registering any input. Reading an archive creates no database row, executes no check and issues no assessment acceptance.

```python
from runtime_candidate.fixture_import import load_hc1

fixture = load_hc1("a", config_version=2, policy_version=2, include_canaries=True)
receipt = app.register_snapshot(fixture["project"], "snapshotA", "handoff",
                                fixture["bundle"], sources=fixture["sources"],
                                mode="imported", manifest=fixture["provenance"])
```

The caller supplies an initialized trusted application, a unique snapshot ID and an existing project configured for the chosen versions. Registration returns a new receipt. A separate authorized assessor may later submit the returned assessment candidate. Its historical criterion plans, reasoning and evidence references retain their original meaning. The original run ID, evidence IDs, revision and lease timestamps belong to the archived review. They provide no current lease, assessor authority or new execution evidence.

The loader reads the original HC1 review inventory and requires its exact SHA-256, recorded in the historical review closure. Against that inventory it verifies the original receipt, bundle, assessment, host request, execution bytes, anchors, dispatch and caller tickets. It also checks run/job identity and agreement between the receipt, held dispatch ticket and exact request/execution digests. The returned provenance records the inventory path and digest, verified subset of historical file pins, observation time, dispatch digest, every changed metadata field and the two resulting canonical digests. [HC1 review closure](../docs/hc1-results/hc1-20261118-r1/review-closure.json)

For import into configuration/policy version 2, six integer fields change in fresh parsed objects. The project config and data policy, run config and data policy, and assessment config and data policy each record their respective new version. With both parameters set to 1 the canonical bundle and assessment match their original file hashes. Differences between run A and B survive import, including the observations visible to each historical assessor.

Each source maps an archive artifact ID to a tuple of raw bytes, classification and original revision. For artifact-1 through artifact-8, UTF-8 encoding the offered text reproduces the SHA-256 in both the host request and the bundle, including the original line endings. The operator permits these fixed synthetic source files as safe_source. The full execution record and host-request package have restricted classification. Their exact archive bytes are available for trusted validation. Optional fixture-raw-canary and fixture-taint-canary are newly created dummy markers outside the report inputs. They exercise raw_secret and tainted denial respectively.

Both historical bundles reuse the same project and artifact IDs. Their execution and host-request files contain different per-run bytes. A service registering both in one project must preserve snapshot-specific source references. Candidate checks must exercise the policy in force for the resulting report and its complete lineage, including restricted inputs.

To check both version-preserving imports without a database or external dependency, run this from the repository root.

```powershell
@'
from runtime_candidate.common import digest
from runtime_candidate.fixture_import import load_hc1

for label in ("a", "b"):
    item = load_hc1(label, config_version=1, policy_version=1)
    source = item["provenance"]
    assert source["metadataChanges"] == []
    for key in ("bundle", "assessment"):
        path = source["origin"] + "/accepted/" + key + ".json"
        assert digest(item[key]) == source["originalFileDigests"][path]
    print(label, item["run_id"], len(item["sources"]), "verified")
'@ | py -3 -B -
```
