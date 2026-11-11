# P4-A — Staged publication/replay package v1

Ngày 10/11/2026. Tiếp [internal report/core slice](P4-A-RUNTIME-REPORT.md) đã DONE. Baseline Git vẫn `d8bf175`, cộng working tree WT-P4A-R2 đã review; giữ toàn bộ thay đổi trước, chưa commit/push. Slice này formalize typed internal envelope + manifest cho publication/replay, không chọn DB/server hoặc tự mở ordinary outbound export.

## Mục đích, outputs và acceptance trước implementation

Người nhận report cần phát lại kết luận từ đúng frozen inputs mà không lấy live branch hoặc mất raw/effective constraint semantics. Adapter persistence tương lai cần một graph candidate nhất quán, có report/run/event refs và manifest để kiểm trước transaction.

Outputs: `qa_core/publication.py`, application functions, strict `qa-publication-package-v1.schema.json`, stdout harness `tools/package_runtime_report.py`, ba goldens mới, regression, review record và current plan/handoff.

Acceptance:

- Gói tự chứa bundle P1 v2, assessment P2 v2 và prepared report/completion v1 nguyên nghĩa; preserve raw inputs/digests, requirement/evidence/provenance/mapping, declared/effective constraints và humanDecision pending. Không sửa schema/corpus/fixtures/goldens cũ hoặc rerun S1.
- Manifest v1 có đúng ba slots bundle/assessment/prepared, canonical JSON SHA256 + UTF-8 byte length và media type; missing/extra/duplicate/altered slot/payload bị reject.
- Graph v1 candidate có completedRun, reportReference và reportReady, derived từ đúng run snapshot/proposal; release lease, successor version/sequence chính xác, one report ID. Complete/incomplete/failed verification đều giữ riêng khỏi completed processing intent.
- Validator kiểm strict shape và rederive toàn package từ embedded inputs, **so caller-held input digests và expected run/report IDs**. Không chỉ tin manifest hash của chính gói; consistent rewrite cũng bị chặn khi anchors giữ nguyên.
- Whole-input scope ghi đúng mọi project/task có trong bundle; không gắn asset nhiều project thành target-project-only export. Package restricted internal replay, outbound authorization chưa evaluated, không include artifact file bytes.
- Detached/deterministic, CLI stdout-only và safe errors; full regression pass + reviewer high-model clean trước DONE slice. Không claim persistence, live authorization/lease/trust hoặc transaction/outbox đã enforce.

## Contract và API

`packageVersion=1.0.0`, `kind=internal_publication_candidate`, `publicationState=staged`. Strict schema root/lồng nhau tham chiếu local registry của P1/P2/offline/runtime/prepared schemas; không fetch network.

`payloads` chứa toàn bundle/assessment/prepared parsed JSON. `manifest` dùng cùng `sha256-python-json-v1` đã ghi tại [OFFLINE-REPORT](OFFLINE-REPORT.md): sorted keys, compact separators, Unicode UTF-8, finite JSON. Byte length là độ dài **canonical representation**, không bytes file input, ZIP member hoặc source artifact; whitespace/key order của file input không giữ nguyên, arrays và `1`/`1.0` vẫn ảnh hưởng digest. Không JCS, signature, authenticated judgment hoặc source-content attestation.

`target` là project/task/handoff/revision/config/policy/run/report được đánh giá. `containedScopes` là toàn project/task inventory của raw bundle; bundle nhiều project/task vẫn giữ nguyên để raw digest không đổi. `handling` cố định whole_bundle/restricted_internal_replay/outboundAuthorization=not_evaluated/artifactBytesIncluded=false. Đây là metadata yêu cầu xử lý, **không có enforcement access control trong core**. Package có thể chứa mô tả requirement, rationale, provenance và metadata project khác; không đưa nó qua ordinary QA read/export hoặc model outbound chỉ vì target có quyền. Không có raw artifact/log bytes được đọc/gom vào gói. Text fields vẫn là supplied data, không là secret scan/redaction proof.

`graph.completedRunCandidate` là bản sao pre-completion run + mutation từ proposal; `reportReference` bind exact run/report/digest; `reportReadyCandidate` giữ project/run/sequence/next version và đúng một report ID. Không đặt event ID, occurredAt, worker identity mới hoặc durability receipt. Đây không phải P1 v2 bundle: report nội bộ mới không nằm trong `bundle.reports`; frozen bundle vẫn là pre-completion snapshot. Không đưa candidate graph vào legacy validator rồi mutate raw input/AC để làm xanh.

```python
from qa_core.application import stage_report_package, check_report_package
from qa_core.reports import digest

package = stage_report_package(bundle, assessment, run_id="run", report_id="runtime-report")
errors = check_report_package(package,
    expected_bundle_sha256=digest(bundle),
    expected_assessment_sha256=digest(assessment),
    run_id="run", report_id="runtime-report")
```

Caller giữ anchors từ frozen inputs độc lập với package nhận được. Hai digests + IDs là required context; tự đọc digest từ cùng package chỉ còn self-consistency, không bảo vệ substitution. Nếu attacker thay cả anchors được caller tin thì validator không xác thực được nguồn/tác giả hoặc truth. Caller-held anchors chưa có authenticated store trong repo. `stage_report_package` raise AssessmentError khi invalid; check trả safe diagnostics. Không mutate inputs; output detached.

## Harness và evidence

Python 3.14.8 đã xác nhận, dependencies pin hiện có; chưa là support/deployment matrix. Từ repo root:

```text
py -3 -B tools/package_runtime_report.py examples/reports/runtime-v1/constraint-collision/bundle.json examples/reports/runtime-v1/constraint-collision/assessment.json --run-id run --report-id runtime-report
py -3 -B tools/package_runtime_report.py examples/reports/runtime-v1/constraint-collision/bundle.json examples/reports/runtime-v1/constraint-collision/assessment.json --run-id run --report-id runtime-report --check examples/reports/publication-v1/constraint-collision.json
py -3 -B -m unittest discover -s tools -p 'test_*.py' -v
```

Generate exit 0 cho complete, 1 cho incomplete/failed, không phát event hoặc ghi file. Check exit 0 với package đúng, kể cả incomplete/failed; invalid JSON/package/context exit 2 với diagnostics cố định, không echo path/raw fields/traceback. Check CLI dùng hai file input caller chỉ định làm anchors, không tin embedded digests. File bên ngoài cũng phải do caller chọn đúng; CLI không authenticates file owner.

[Goldens mới](../examples/reports/publication-v1/README.md) có complete, constraint collision, failed + pending. Tests kiểm 55 scenario inputs (45 evaluable/10 expected input errors), exact graph, Unicode canonical byte lengths, whole-bundle nhiều project/task, consistent rewrite với old anchors, tamper/rehashed payload/missing-extra-duplicate, exact run/numeric successor/detachment, CLI và strict parser. [Review](P4-A-PUBLICATION-REVIEW.md) lưu actual results/verdict, không suy từ count thành product readiness.

## Phần còn mở

Slice này chỉ tạo/kiểm **staged internal publication package**, chưa persisted/readable report, actual completed run, report_ready/outbox event hoặc ordinary user export. Chưa trust acceptance, auth/RBAC/live revoke, lease expiry, concurrent CAS/idempotency/uniqueness, blob integrity từ bytes, atomic transaction/restart/recovery hoặc egress filtering.

Tiếp S2/runtime-storage decision prerequisites và P4-B transaction adapter: stage bytes nội bộ, verify digest/length/scope, authenticated/live policy+lease/CAS recheck, commit report ref + completed + outbox cùng transaction, sau commit mới expose/replay; failure không publish partial graph. Đường read/export cần scoped manifest riêng với source lineage/taint và live policy, không dùng toàn raw replay package như allowlisted QA artifact. Legacy P1 v2 exporter vẫn unsupported. P4-A tổng thể partial; S2–S6/P4-B–E/P5/P6 còn mở. Chưa chọn platform/distribution hoặc gọi hệ thống/API/project thật.
