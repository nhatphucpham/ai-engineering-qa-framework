# P2 rules v2 — corrected reference semantics

Assessment `2.0.0`, rules `p2-rules-2.0.0`. [Base assessment](base-assessment.json) dùng cùng [P1 bundle synthetic](../v1/base-bundle.json); migration đổi version fields, không validate/accept trust hoặc domain judgment. Không execution/model thật.

```text
py -3 -B tools/evaluate_rules.py examples/rules/v1/base-bundle.json examples/rules/v2/base-assessment.json
py -3 -B tools/test_rules_v2.py -v
```

V2 tính provenance source_reasoning ở effective level source_review cho positive/open coverage, không cho nhãn integration thay execution. Source counterexample có nguồn vẫn được giữ. Violation rõ + evidence conflict cùng AC giữ failed/open và cả hai reason.

V1 schema/corpus vẫn nguyên để replay lịch sử, có hai known limitations tại [review](../../../docs/P2-V2-REVIEW.md). Evaluator dispatch explicit theo version; mismatched/unknown versions bị từ chối. Tests v2 reuse 55 scenarios trên copies được nâng version có chủ đích, không sửa corpus cũ. Report mới chỉ nhận v2. Đây vẫn là conditional assessment, chưa là trust hoặc product runtime.
