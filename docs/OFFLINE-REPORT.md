# Reference report offline v1

Ngày 10/11/2026, nền `9237018`. Đây là prerequisite P4-A và oracle cho P3-B/S1, không phải production core/server hoặc P1 wire report. [Projector](../tools/project_report.py) nhận bundle P1 `2.0.0` và assessment `2.0.0` / rules `p2-rules-2.0.0`; reportVersion riêng `1.0.0`. V1 assessment bị từ chối, không tự nâng version hoặc judgment. Chỉ synthetic, không network/model/project test execution.

## Mục đích và luồng

Reviewer đọc được kết quả trong scope, requirement/coverage/evidence ở revision nào, constraint nào chưa đủ review và việc cần xử lý. Luồng chạy thật của tooling: validate P1/P2 → evaluate rules v2 → lấy metadata nguồn → tạo report và proposed actions → kiểm schema. Human decision luôn pending, actions chưa có assignee và chưa hoàn tất. Role là routing suggestion, không phải quyền hoặc người thật đã nhận việc.

```text
py -3 -B tools/project_report.py examples/rules/v1/base-bundle.json examples/rules/v2/base-assessment.json
py -3 -B tools/project_report.py examples/reports/v1/constraint-collision/bundle.json examples/reports/v1/constraint-collision/assessment.json
py -3 -B tools/project_report.py examples/reports/v1/constraint-collision/bundle.json examples/reports/v1/constraint-collision/assessment.json --check examples/reports/v1/constraint-collision/report.json
py -3 -B -m unittest discover -s tools -p 'test_*.py' -v
```

Cài dependency dev theo `tools/requirements-contracts.txt` khi môi trường chưa có; Python 3.10+ và jsonschema pin trong file đó. Đây không là quyết định runtime sản phẩm. CLI đọc các file được chỉ định, xuất stdout, không ghi input/report/evidence. Muốn lưu output mới, caller chọn đường dẫn snapshot mới và ghi provenance; không redirect lên input hoặc evidence cũ.

| Lệnh | Exit / processingStatus | Ý nghĩa |
|---|---|---|
| Generate | 0 / reference_report | Reference verification complete trong scope, không approval |
| Generate | 1 / reference_report | Đánh giá hợp lệ nhưng incomplete hoặc failed, không phải process crash |
| Generate hoặc check | 2 / input_error | Input/report/version/derivation không hợp lệ; không có QA verdict mới |
| `--check` hợp lệ | 0 / report_validated | Report đúng schema và khớp derivation từ hai input, kể cả report incomplete |

## Contract report

[Schema strict](../schemas/qa-offline-report-v1.schema.json) khóa cả object lồng nhau; extra field/major lạ không được chấp nhận. Report gồm:

- `scope` và `inputBindings`: project/task/handoff/candidate/requirement, config/policy versions, assessor/policy source và digest hai input.
- `assessment`: output P2 v2, verification, statusScope, criterion status/reasons, decisive/context evidence, open coverage, effective constraints và humanDecision pending.
- `criterionSources`, `assessmentContext`, `evidenceSources`, `artifacts`: requirement claims/locators, coverage plan/risk, bindings evidence→obligation/context/relation/judgment/rationale, evidence provenance/review và metadata artifact. Metadata không thay nội dung source hoặc attestation.
- `handoffContext`: decision moment/request, actors, self-test/QC stages, risk rationale, known issues, source/diff references. Unknown/not_performed không tự thành provided.
- `constraintSources`: raw declaration và review nguyên bản hoặc null. P2 effective state nằm riêng ở assessment; không sửa declaration satisfied thành pending để né P1.
- `actions`: proposed work cho failed/unverified/open coverage hoặc pending constraint; role, assignee null và doneWhen. Requirement ambiguity/conflict chuyển owner; blocked/error/skipped/not-run chuyển check-owner; binding mismatch/missing evidence chuyển QA; pending risk/plan chuyển coverage-policy-owner. Chỉ đề xuất điều tra conflict khi reason có EVIDENCE_CONFLICT. N/A thiếu decision có thể bổ sung trên cùng candidate, không ép đổi requirement khi behavior không đổi. Declaration pending cần authorized resolution/new handoff snapshot cùng current accepted review; thêm review đơn thuần không làm declaration hết pending.
- `legacyProjection`: luôn projection_unsupported vì chưa triển khai P1 exporter; thêm P1_V2_CONSTRAINT_COLLISION khi summary P1 từ declared state khác P2 effective state. Không có P1 report/report_ready/completed được tạo.

`create_report` không mutate input và trả bản sao detached. `validate_report(report, bundle, assessment)` kiểm shape rồi tính lại output từ input/rules, so digest serialization của toàn report; không chỉ tin hash do report cung cấp. Vì vậy sửa status/reason/refs/mapping hoặc số `1` thành `1.0` đều bị phát hiện. Một attacker thay cả hai inputs và tính lại report vẫn chỉ có một bộ supplied judgments khác; validator không xác thực tác giả hoặc truth.

Các blocker độc lập có proposal riêng theo criterion/reason class, không dùng priority branch để che check gap khi plan pending hoặc ngược lại. Chẳng hạn blocked + pending plan có cả check-owner và coverage-policy-owner; conflict + blocked giữ cả hai việc. Không nhân bản proposal cùng reason class. Remaining-coverage là fallback khi chưa có targeted reason; xử lý action xong vẫn phải re-evaluate assessment, không tự nâng criterion verified.

## Digest và parser

Algorithm `sha256-python-json-v1`: Python `json.dumps(sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)`, UTF-8, SHA-256. Không có timestamp/random ID nên cùng parsed inputs/rules cho cùng output. Key order/whitespace trong file không ảnh hưởng; thứ tự arrays và representation `1`/`1.0` có ảnh hưởng. Đây **không phải RFC 8785/JCS**, không normalize Unicode, không cam kết numeric/digest parity giữa Python và JavaScript. S1 cần kiểm Unicode/large integers/numeric precision và chốt serialization contract trước runtime port.

Report và evaluator CLI dùng chung `tools/json_input.py`, từ chối NaN/Infinity và duplicate JSON members ở mọi cấp; lỗi đọc/parse/recursion xuất diagnostics cố định, không echo raw values/path hoặc traceback. Các input v1 hợp lệ vẫn replay cùng semantics, không bảo toàn cách chấp nhận JSON mơ hồ/lỗi trước đây. Đây là parser/tooling behavior, không DoS protection/quota hoặc runtime security boundary.

## Kết quả và phần chưa khép

[Goldens](../examples/reports/v1/README.md) có complete và constraint collision incomplete, từ supplied synthetic specimens. [Regression](../tools/test_reports.py) kiểm 55 decision inputs (45 evaluable, 10 expected input errors), source trace, missing/stale/current review, raw pending + accepted review, record-only scope, tamper, detachment, CLI và malformed JSON. [Review record](P4-A-REFERENCE-REVIEW.md) lưu actual commands/results và findings/fixes.

[S1 cross-runtime](S1-RESULTS.md) đã PASS trên corpus/discriminators được ghi; [ADR-004](adr/004-core-baseline-after-s1.md) chọn Python pure-core baseline. P1 wire/persistence/lifecycle collision chưa được sửa bằng envelope này. Việc kế tiếp là runtime report/constraint contract tích hợp; DB/queue/auth/acceptance/worker/container, provider/GitHub, Windows shell/installer và plugin target vẫn là các gate trong [plan](IMPLEMENTATION-PLAN.md). Không có quyền pilot/publish từ test pass.
