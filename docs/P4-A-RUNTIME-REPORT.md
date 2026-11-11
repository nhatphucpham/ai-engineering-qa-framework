# P4-A — Internal report và pure completion proposal v1

Tiến độ tiếp theo: [publication/replay package v1](P4-A-PUBLICATION.md) bổ sung typed internal envelope/manifest và graph candidate, DONE trong scope sau clean review ngày 11/11. Các giới hạn runtime/persistence bên dưới vẫn áp dụng; scoped user read/export và transaction chưa được triển khai. Nội dung slice runtime-v1 bên dưới giữ phạm vi đã review.

Ngày 10/11/2026, baseline `d8bf175`. Đây là slice kiểm được của P4-A theo yêu cầu tiếp tục từ session trước. Chỉ synthetic, supplied judgments; P4-A tổng thể và full runtime integration còn mở.

## Mục đích, outputs và acceptance đã chọn trước sửa

Reviewer/TL cần giữ kết luận P2, declared/effective constraints và nguồn khi gắn report vào một run. Client tương lai cần cùng một Python application interface thay vì tự triển khai rules. Slice này tách code dùng chung và formalize **internal proposal contract**, chưa thay P1 v2 wire format.

Outputs: package source `qa_core/`, compatibility CLIs cũ, schemas `qa-runtime-report-v1` / `qa-prepared-report-v1`, harness `tools/prepare_runtime_report.py`, goldens mới `examples/reports/runtime-v1`, regression và review record.

Acceptance:

- Giữ nguyên bundle P1 v2, assessment/rules v2, offline report v1, schemas/corpus/fixtures/evidence/protocol cũ. Không đổi expected cũ hoặc rerun S1 benchmark.
- Mandatory constraint declared satisfied nhưng missing/stale/unaccepted review → effective pending → incomplete khi AC đã verified và không có failed khác. Optional pending đơn thuần không chặn; failed giữ precedence, pending gaps/actions vẫn hiện. Raw pending + accepted review vẫn pending.
- Giữ requirement/source/evidence/obligation/context/rationale/revision/provenance, policy/assessor và humanDecision pending. Input không mutate; output detached, deterministic.
- Expected run/report identities do caller cung cấp; report bind exact project/handoff/candidate/config/policy/stateVersion/attempt và digest toàn pre-completion run. Validation tính lại từ inputs, không chỉ tin hash.
- Chỉ analyzing/checking chưa có report/ref/report_ready cho target run được đề xuất complete, kể cả verification incomplete/failed. Proposal bind report digest, CAS version, attempt, terminal lease release và đúng một report ID trong event proposal. Sequence tăng theo exact run.
- Corpus/goldens cũ và checks mới pass; independent reviewer clean trước DONE trong scope.

## Interface và contract

Từ repo root, Python 3.14.8 đã kiểm trong phiên này; đây chưa là support matrix hoặc package distribution. Dependencies pin hiện có tại `tools/requirements-contracts.txt` (jsonschema kéo theo referencing). Không thêm server, SDK, DB, network hoặc subprocess executor vào core.

```python
from qa_core.application import prepare_report, check_prepared_report

prepared = prepare_report(bundle, assessment, run_id="run", report_id="runtime-report")
errors = check_prepared_report(prepared, bundle, assessment,
                               run_id="run", report_id="runtime-report")
```

`prepare_report` nhận parsed finite JSON và hai expected IDs, trả dict detached gồm `report` và `completion`; invalid input raise `AssessmentError`. `check_prepared_report` trả diagnostics; schema checks đi trước exact derivation. Caller dùng strict parser tại ingress; pure API không phục hồi duplicate members đã bị parser ngoài làm mất.

`qa_core/contracts.py`, `rules.py`, `reports.py` là implementation duy nhất của validators/evaluator/projector Python đã có. `tools/validate_contracts.py`, `evaluate_rules.py`, `project_report.py` giữ CLI và compatibility imports. Extraction giữ nguyên semantics v1 replay/v2; assets đọc từ `schemas/` cạnh package trong checkout. Chưa là wheel hoặc distribution CLI/library/MCP đã chọn.

`runtimeReportVersion=1.0.0` có identity, `runBinding`, digest run và `content` theo **nguyên contract offline report 1.0.0**. `constraintSources[].declaration/review` giữ raw state/review; `assessment.constraints[]` là effective state. Content giữ digest **toàn raw bundle/assessment**, bao gồm run/progress; thay đổi input khác run cũng invalidates proposal. Đây là conservative whole-input binding, không incremental cache.

`completionVersion=1.0.0` có expected run version/attempt/digest, report digest, run mutation và `eventProposal`. Schema prepared strict ở mọi object; reference schema qua URN trong local registry. Consumer cần cả ba schema prepared/runtime/offline; không fetch network. Digest vẫn `sha256-python-json-v1` theo [OFFLINE-REPORT](OFFLINE-REPORT.md), không JCS hoặc trust proof.

Caller cấp report ID mới; core chỉ kiểm syntax và collision với reports trong snapshot. Uniqueness toàn store, concurrent idempotency/serialization thuộc persistence tương lai. Cùng inputs/IDs cho cùng JSON; không tự timestamp/UUID hoặc emit event.

New report ID/ref chỉ gồm ASCII letter đầu, theo sau letters/digits/`._-`, tối đa 96 ký tự; final LF bị từ chối bằng schema riêng cho new report identity. Legacy run/project/handoff IDs vẫn theo semantics P1 v2, không âm thầm siết corpus cũ. Integral floats được JSON Schema coi là integer: proposal chuyển version/sequence sang Python int trước khi tính successor, giữ raw representation trong input/run digests. Nếu successor vượt giới hạn JSON encoder hiện hành thì prepare fail-closed với input diagnostic, không trả object không serialize được và không đổi giới hạn toàn máy.

## Harness và checks

```text
py -3 -B tools/prepare_runtime_report.py examples/reports/runtime-v1/constraint-collision/bundle.json examples/reports/runtime-v1/constraint-collision/assessment.json --run-id run --report-id runtime-report
py -3 -B tools/prepare_runtime_report.py examples/reports/runtime-v1/constraint-collision/bundle.json examples/reports/runtime-v1/constraint-collision/assessment.json --run-id run --report-id runtime-report --check examples/reports/runtime-v1/constraint-collision/prepared.json
py -3 -B -m unittest discover -s tools -p 'test_*.py' -v
```

Generate exit 0 khi verification complete, 1 khi incomplete/failed; cả hai là proposal hợp lệ. `--check` exit 0 với proposal đúng kể cả incomplete/failed, exit 2 khi invalid. Read/parse/derivation error exit 2 với safe diagnostic, không echo path/raw input/traceback. Harness stdout-only, không ghi input/evidence hoặc chạy project checks.

Goldens mới có complete, mandatory constraint collision, failed + mandatory pending. Regression có 55 scenario inputs (45 evaluable/10 input errors), missing/stale/current/optional/raw pending constraint, tamper, run scope/revision/version/attempt/lease-token change, exact-run sequence/report refs, lifecycle rejection, detachment, CLI và strict parser. Regression cũ bảo vệ v1/v2/offline semantics, không là S1 trials mới. [Review record](P4-A-RUNTIME-REVIEW.md) ghi actual checks/verdict.

Sau extraction, `tools/run_s1.py:source_hashes` bao gồm `qa_core/` để future conformance run vẫn guard/hash implementation thật, không chỉ wrappers. Inventory regression kiểm source coverage; không rerun S1 trials hoặc sửa official evidence lịch sử trong slice này. P1 compatibility import/module CLI cũng có regression ngoài `tools/` discovery path.

## Giới hạn và bước tiếp

Đây là **report derivation + pure graph/lifecycle predicate**, chưa tạo persisted report, actual completed run hoặc report_ready event. `runMutation` không được đưa vào P1 v2 bundle: report ID thuộc contract nội bộ mới, không có P1 v2 report tương ứng. Offline content vẫn ghi legacy exporter `projection_unsupported`; không che collision bằng raw mutation hoặc AC unverified giả.

Trước full integration, cần versioned publication/export manifest, production run/report/event storage contract và transaction kiểm live authority/policy, lease expiry/worker identity/fencing, CAS/idempotency, durable source/report refs và outbox. Proposal không xác minh các điều kiện đó, không nhận supplied accepted judgments thành authenticated authority. Không phát report_ready trước durable publication; raw/effective provenance phải đi trọn persistence/read/export. Đây là phần mở P4-A/P4-B/C, không đóng bằng tests predicate.

Server/worker runtime, DB, desktop shell, agent host/distribution, real model/API/project và pilot chưa được chọn/chạy bởi slice. Human decision pending; không approve/merge/deploy/publish. Tiếp publication/export contract và integration prerequisites, sau đó transactional service theo runtime decision riêng.
