# P2 rules v1 — synthetic assessment scenarios

Mọi evidence, execution-shaped record, actor, accepted judgment, authorization/basis facts là **do tác giả soạn**. Không có test/model/container thật hoặc authority được xác thực. [Rules và boundary](../../../docs/VERIFICATION-RULES.md), [assessment schema](../../../schemas/qa-assessment-v1.schema.json).

- `base-bundle.json`: bundle P1 v2, candidate/requirement/evidence làm input; không có report kết luận sẵn để evaluator dùng như đáp án.
- `base-assessment.json`: trusted-assessment **specimen**, risk/coverage plan, sourced comparison contexts, evidence reviews và bindings. Không phải raw model output được phép tự gắn accepted trong sản phẩm.
- `scenarios.json`: 55 biến thể với expected status/reason/flags hoặc input-error code; test áp trên deep copies của hai file gốc.
- `lifecycle-cases.json`: 20 finding/action transition cases; bool authorization/completion chỉ là supplied facts để kiểm predicate, không authorize hoặc kiểm chứng proof thật.

Từ root repo:

```text
py -3 -X utf8 -B tools/test_rules.py -v
py -3 -X utf8 -B tools/evaluate_rules.py examples/rules/v1/base-bundle.json examples/rules/v1/base-assessment.json
```

Cần dev dependency ở `tools/requirements-contracts.txt`. Chạy CLI chỉ đọc JSON, không chạy check/source từ bundle. Exit 0 complete, 1 evaluated nhưng incomplete/failed, 2 input_error. Đọc cả processingStatus/verification/statusScope, không suy “chạy xong” là approval.

Các scenario là design regression biết trước outcome, không phải holdout, real pilot hoặc benchmark model. P3/P4 phải implement trusted judgment intake, auth/ref/proof resolution và runtime enforcement trước khi dùng kết quả như state vận hành.
