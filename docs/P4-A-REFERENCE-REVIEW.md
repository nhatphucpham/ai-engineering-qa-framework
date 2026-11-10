# P4-A prerequisite — review reference report

Review phiên trước dưới đây được giữ làm lịch sử. Theo yêu cầu review lặp bổ sung, output đã mở lại review; trạng thái mới nhất và RV-01..03 nằm tại [OUTPUT-REVIEW-LOOP](OUTPUT-REVIEW-LOOP.md), không lấy verdict cũ thay review bản mới.

Ngày 10/11/2026, nền `9237018a9ce5b0dd28d26984e1db5182adad0b2c`. Scope: kiểm tra phần P1/P2 đã làm, reference report/harness offline và plan. Không phải review production runtime hoặc đóng P3-B/P4 overall.

## Phân công độc lập

| Reviewer | Scope | Trạng thái |
|---|---|---|
| GPT-6 Astra, high — architecture_review | Audit P2, plan/boundaries và independent review report/schema/tests | Tìm hai lỗi rules; review report sau sửa PASS, tự chạy 7 tests pass 5.884s |
| GPT-6.1 Terra, high — implementation_audit | Audit P1/P2, independent review patch P2 v2 và report integrity | PASS targeted offline slice sau fixes; đọc code/tests, không tự chạy suite |
| GPT-6 Astra, high — plan_review | Plan 6 phần, hướng dẫn OFFLINE-REPORT và handoff hiện hành | Final docs review không blocker sau đồng bộ v2; nit P3-B chưa chạy khác partial đã sửa. Không đối chiếu độc lập toàn PRODUCT-DECISIONS/skill, không tự chạy suite |

Root thực hiện code/schema/tests/docs. Lệnh ghi của subagents bị treo rồi hủy, không có thay đổi được xác nhận từ họ; root tiếp quản để hoàn thành. Các nhận xét/vận hành review read-only độc lập ở bảng trên không bị gọi là implementation do subagent. Architecture phát hiện/đề xuất fix P2; Terra review patch đó. Report do root viết và được cả hai review.

## Kiểm tra thực trước thay đổi code

Python `3.14.8` chạy được qua `py -3`; Node `v26.12.1` hiện có, không là product pins. Checkout `master` sạch khi bắt đầu, commit nền ở trên.

```text
py -3 -B -m unittest discover -s tools -p 'test_*.py' -v
```

Kết quả: 8 unittest methods pass (3.572s); subtests gồm 9 valid P1 bundles, 58 negative contract scenarios, 55 decision scenarios và 20 lifecycle cases, cùng CLI/legacy/repeatability/no-mutation. Đây là kiểm dev tooling, không execution project/container/model.

## Findings tái hiện trước sửa

| Finding | Reviewer / severity | Replay thực của root | Hướng sửa |
|---|---|---|---|
| Source reasoning tự gán integration level thỏa required integration | GPT-6 Astra / P1 | P1 validation không lỗi, P2 v1 trả verified/complete khi đổi cả requiredLevels/evidence.level sang integration, giữ provenance source_reasoning và không execution | V2 effective level source_review cho positive/open coverage; regression bảo toàn source counterexample |
| Có violation rõ và comparable conflict nhưng mất conflict reason | GPT-6 Astra / P2 | P2 v1 trả failed + hasOpenCoverage=true, reasonCodes chỉ CURRENT_BEHAVIOR_VIOLATION | V2 giữ EVIDENCE_CONFLICT độc lập status precedence |

Replay: dùng `test_rules.scenario_inputs` với `source-proof-with-accepted-scope` và `comparable-evidence-conflict`, sửa bản sao trong memory, gọi validate/evaluate; không thay fixture/evidence. D-21 ghi versioning; report mới dùng v2, không lấy v1 có known limitations làm oracle corrected flow.

## Findings report, fixes và re-review

| Finding | Sửa | Regression / xác nhận |
|---|---|---|
| Report thiếu self-test/QC stages, risk và evidence→obligation/context/judgment mapping | Thêm strict handoffContext và assessmentContext, source metadata đầy đủ, detached copies | Stage provided/unknown, mapping/risk/claim assertions và input binding changes; Astra/Terra re-review xác nhận |
| doneWhen chỉ yêu cầu review dù declaration vẫn pending | Nhánh pending yêu cầu authorized resolution/new handoff snapshot cùng accepted current review | Raw pending + accepted review vẫn incomplete, action nêu snapshot mới; hai reviewer xác nhận |
| CLI duplicate JSON keys last-wins và recursion có thể làm output mơ hồ/traceback | Reject duplicate members/nonfinite, catch recursion, diagnostics cố định | Invalid duplicate và duplicate chèn vào report hợp lệ (last value đúng), deep JSON, NaN, malformed/null, stderr rỗng |
| Python equality coi 1 bằng 1.0, trái exact serialized derivation | So digest của canonical reference serialization cho toàn report | Tamper 1→1.0, status/reason/mapping/digest/version/extra/nonfinite bị reject; Terra re-review xác nhận |

Final independent verdict: **PASS cho targeted synthetic offline reference slice**. Astra tự chạy 7 report methods sau khi goldens sẵn; Terra review code/tests bản sửa, không tự chạy. Sau nit duplicate-test của Astra, root thêm duplicate vào report hợp lệ rồi chạy toàn suite lần cuối. Không có blocker còn mở trong scope đã rà; không bảo đảm mọi lỗi đã được tìm.

## Kết quả cuối phiên

`py -3 -B -m unittest discover -s tools -p 'test_*.py' -v` → **20 methods pass, 10.171s**, sau toàn bộ code/tests fixes. Gồm P1 9 valid/58 negative, P2 v1 55 decisions/20 lifecycle, v2 replay corpus + regression, report 55 inputs (45 evaluable/10 expected errors), 2 goldens và CLI/tamper/traceability/no-mutation. Method/subtest counts không phải số independent domain tests hoặc product readiness.

`git diff --check` pass. Kiểm 25 file thay đổi/mới, relative links/code fences trên 12 tài liệu pass (95 links), không trailing whitespace ở file mới. Check CLI trên golden constraint-collision incomplete trả report_validated/valid=true, exit 0, đúng khác biệt validation với verification. `git diff --exit-code 9237018 --` các vùng fixture/mock/remediation/contracts/rules-v1/templates/pilot, schemas P1/v1-assessment, validator và tests cũ, CORE-FRAMEWORK pass: dữ liệu lịch sử không đổi. New goldens có folder riêng, không execution evidence mới của app.

## Gate còn mở

Versioned reference report không tự trở thành P1 v2 report đã persist hoặc server event. P1 declared/P2 effective constraint collision vẫn chặn legacy projection; không mutate handoff/AC/P2 status để né validator. S1 cross-runtime, DB/queue, engine/policy, GitHub authenticated correlation, secrets/identity và native shell chưa được reference tests chứng minh.

Reference prerequisite đã hoàn tất trong scope trên. Việc kế tiếp là S1 cross-runtime parity theo oracle v2/report, rồi chốt boundary stack bằng actual spike results và versioned runtime report integration. Không commit/push hoặc publish trong phiên này.
