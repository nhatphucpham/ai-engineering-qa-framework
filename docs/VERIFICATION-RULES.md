# P2 — Quy tắc kiểm chứng, finding và action

Semantics nền ngày 05/11/2026, cập nhật 10/11/2026 từ `9237018`. Current assessment `2.0.0` / rules `p2-rules-2.0.0`, dùng [contract P1 v2](DATA-CONTRACT.md). [Audit và regression v2](P2-V2-REVIEW.md) ghi hai lỗi đã tìm: source reasoning tự gán integration level và mixed violation/conflict mất reason. V1 giữ semantics/corpus lịch sử để replay, có known limitations; không dùng làm oracle corrected report. Đây là **semantics và reference evaluator offline**, không có server, model, container, authentication, execution attestation hoặc workflow production. Ví dụ chỉ synthetic.

## 1. Rule nhận gì và không thể tự chứng minh gì?

Reference evaluator nhận bundle P1 v2 và assessment sidecar theo [schema v2](../schemas/qa-assessment-v2.schema.json). [Schema v1](../schemas/qa-assessment-v1.schema.json) chỉ phục vụ replay explicit v1, không silent upgrade. Bundle giữ requirement/source/evidence/revision. Sidecar giữ coverage plan, risk/context, mappings và judgment đã được cung cấp. Không lấy verdict trong report cũ làm đầu vào quyết định; report cũ nếu có chỉ được P1 kiểm cấu trúc.

Rule xác định được logic từ các dữ liệu đó. Rule **không** tự đọc code rồi chứng minh semantic correctness, xác thực người chạy, kiểm source hash thật hoặc biết judgment của model đúng. Sidecar không được coi là API công khai cho model tự gắn `accepted` rồi lấy status verified.

Trong sản phẩm đích, trusted assessment boundary phải được P3/P4 hiện thực: authenticated workflow nhận candidate reasoning → resolve source/locator/expected context, integrity/attribution/scope → chấp nhận hoặc giữ candidate/disputed theo policy. Việc chấp nhận có thể là bước tự động đủ căn cứ trong project policy, không bắt người dùng duyệt từng mapping; vẫn phải lưu source/assessor/policy version và giới hạn. Accepted không tự có nghĩa độc lập với implementer hoặc được con người adjudicate.

Trong reference tests, mọi judgment/integrity/authorization là input do tác giả soạn, **không phải phép kiểm trust đã chạy**. Kiểm truth và đầy đủ phép suy luận của domain cần đánh giá riêng; không dùng test oracle để tuyên bố framework đã tự QA được.

## 2. Các khái niệm

| Khái niệm | Ý nghĩa |
|---|---|
| Criterion/AC | Expected behavior có nguồn và trạng thái clarification; mandatory quyết định gap có chặn tổng thể không |
| Obligation | Một phần của expected behavior cần được account, ví dụ quản lý được phép và nhân viên bị từ chối |
| Comparison context | Điều kiện/input/role/env liên quan có mô tả và source locator; key không phải test ID hoặc cách gộp tùy tiện |
| Coverage plan | Obligation + required comparison keys + required evidence levels + allowed provenance, scope và trạng thái accepted/draft |
| Evidence review | Input judgment về integrity, attribution và scope; thiếu/unknown/mismatch không được tự nâng thành accepted |
| Binding | Evidence → AC/obligation/comparison context, quan hệ supports/violates/inconclusive, judgment và rationale |
| Decisive evidence | Bằng chứng đủ eligibility cho một kết luận trong scope, không phải mọi log được cung cấp |
| Context evidence | Evidence cũ, chưa accepted hoặc không đủ kết luận nhưng cần hiển thị để giải thích gap |

Sidecar có project/handoff/candidate, projectConfigVersion/dataPolicyVersion, assessorRef và policySourceArtifactId; phải khớp bundle snapshot. Mỗi AC có đúng một plan; không bỏ AC khó hoặc bịa source. Source/locator phải thuộc project/task hoặc shared artifact hợp lệ; không dò tùy ý toàn project để gắn evidence task khác.

Required contexts có nguồn, không được model đặt một key khác để né contradictory evidence. Counterexample mới có thể nằm ngoài required positive contexts, nhưng vẫn phải đăng ký context có mô tả/source và có binding accepted phù hợp expected behavior. Core không thể xác minh nội dung mô tả đó đúng chỉ bằng việc ID tồn tại.

## 3. Eligibility của evidence

Input invalid về schema/reference/version/project/task → `processingStatus=input_error`, không phát ra verified/failed AC. Contract error không là defect behavior. Assessment schema thiếu/ID trùng/mapping sai cũng là input error; evidence hợp lệ nhưng thiếu trust/scope là gap, không phải malformed input.

Một binding chỉ có thể góp phần kết luận khi:

1. Requirement/project/handoff/candidate và source references hợp lệ theo P1/P2.
2. Binding judgment `accepted`; candidate/disputed giữ làm context, không tự nâng lên confirmed defect.
3. Evidence đúng candidate; old evidence/source vẫn giữ context nhưng không verify/fail candidate mới.
4. Evidence review có integrity matched, attribution accepted, scope accepted. Các giá trị này do trusted assessment cung cấp; không thay execution attestation.
5. Provenance được coverage plan cho phép và đúng mode ở mục 4.
6. Outcome/relationship nhất quán: pass → supports, fail → violates; inconclusive hoặc mismatch chưa đủ kết luận.

`error/skipped/blocked/not_run/unknown` không xác nhận behavior đúng hoặc sai. Chúng giữ nguyên outcome và lý do để tạo action phù hợp. Unit pass không tự thay integration/QC nếu plan yêu cầu mức khác.

Scope review phải đối chiếu actual assertion/source với expected behavior, context và environment. Tên test, số test hoặc mapping tự khai báo không đủ. Một test có thể cover nhiều obligation nếu có assertions thực và mapping được account; nhiều test cùng một issue không tăng số defect.

## 4. Provenance, mode và risk

| Mode | Evidence có thể kết luận | Cách trình bày |
|---|---|---|
| execution_review | Execution/source_reasoning đủ eligibility và được plan cho phép | `candidate_scoped_assessment`; không hứa toàn hệ thống hoặc independent review |
| record_review | Có thể thêm reported/authored_mock nếu plan cho phép và judgments accepted | `record_only`; verified/failed chỉ về record trong bài tập, không là behavior đã thực chạy |

Không được tự chuyển sang record_review để làm green gate thật; mode/policy phải do project/workflow được ủy quyền chọn. Execution-shaped specimen trong test vẫn là dữ liệu tác giả soạn, không biến thành actual execution bởi nhãn provenance.

Risk có tier/state/rationale và policy source; unknown/candidate không tự mặc định low. Positive verification chờ coverage/risk plan accepted. Tuy nhiên, counterexample đã đủ căn cứ đối với requirement rõ vẫn cho failed dù full coverage plan chưa hoàn thiện; không cần trì hoãn nhận diện lỗi để chạy hết checks.

Không đặt quy tắc phổ quát “high luôn integration” hoặc “low chỉ unit”. Required levels/contexts/provenance phải xuất phát từ expected behavior, impact, reversibility, môi trường và project policy có nguồn. Nếu chưa xác định được phù hợp risk thì plan draft, phần verification chưa đủ. Một scope source-only chỉ được verified trong scope đó nếu plan chấp nhận, không nâng thành API/UI/system test.

## 5. Thứ tự quyết định criterion

| Ưu tiên | Điều kiện | Kết luận |
|---|---|---|
| 1 | Requirement conflict/ambiguous | unverified; hỏi owner, tiếp AC độc lập, không tự chọn nguồn thắng |
| 2 | N/A được yêu cầu, quyết định owner accepted/đúng scope có actor/source/revision, không có evidence trái cần giải quyết | not_applicable trong scope |
| 2a | N/A thiếu/pending/stale hoặc N/A accepted nhưng mâu thuẫn với evidence đủ căn cứ | unverified; yêu cầu clarification về applicability |
| 2b | N/A bị owner từ chối bằng quyết định hợp lệ | Tiếp kiểm như applicable, không bỏ AC |
| 3 | Có accepted current violation, không bị phản bác trong cùng comparison context | failed; không đợi full positive coverage |
| 4 | Supports và violates đủ eligibility trái nhau về **cùng** obligation/context | unverified phần đó; điều tra nguồn/env/assertion, không chọn theo số phiếu |
| 5 | Positive coverage/risk plan còn draft/unknown | unverified, kể cả các test đang pass |
| 6 | Thiếu support cho obligation/context bắt buộc hoặc thiếu evidence level | unverified; nêu chính xác check/nguồn cần thêm |
| 7 | Tất cả declared obligations/contexts và required levels được support, plan accepted | verified trong declared scope, limitations giữ riêng |

Một pass trong tình huống A không phủ định counterexample ở tình huống B. Nếu cùng AC có conflict một context và violation rõ ở context khác, status vẫn failed, đồng thời ghi open coverage/conflict. Không dùng “có một test pass” hoặc “đa số pass” để che fail.

`requiredLevels` áp dụng cho từng required context của obligation. Không đếm 10 unit test thành một integration test. Source reasoning có thể chứng minh lỗi mà không cần assertion fail; để verify positive bằng source reasoning, plan phải chấp nhận source_review và coverage đủ, không thay required integration bằng một nhận xét source.

V2 thực thi quy tắc này bằng effective level `source_review` cho provenance `source_reasoning`, kể cả metadata tự gán level `integration`/`unit`. Áp dụng cho cả positive coverage và open-check accounting, không loại bỏ source counterexample hợp lệ. Conflict reason được giữ độc lập với status precedence, nên violation rõ + conflict cùng AC vẫn failed/open và có cả hai reason.

## 6. Coverage chưa đủ và tổng thể

Reference output có:

- `verification`: failed nếu có AC failed; nếu không, incomplete khi có mandatory AC unverified hoặc mandatory constraint pending; còn lại complete trong scope.
- `hasUnverifiedMandatory`: đúng với ý nghĩa P1 — có AC mandatory ở trạng thái unverified.
- `hasOpenMandatoryCoverage`: còn context/level chưa được kiểm hoặc conflict/coverage-plan chưa được chốt trong mandatory AC; có thể true ngay cả khi status AC failed.
- Criterion `hasOpenCoverage`, reasonCodes, decisive/context references và scopeDescription.
- `humanDecision=pending` luôn tách riêng; no automatic approval.

Known failure không cần hết coverage để thành failed. Test fail đã chạy có thể account một required context nhưng không support positive pass; source-only counterexample với required integration chưa chạy cho failed đồng thời open coverage. Một AC có nhiều phần rõ/mơ hồ nên được intake tách thành subcriteria có nguồn; nếu chưa tách thì ghi cả các gap trong rationale/limitations, không lấy một phần pass che phần chưa biết.

Mandatory constraint (ví dụ P-05 review domain/security) không tự satisfied chỉ từ claim trạng thái. Reference semantics cần constraint-review accepted với actor/source/candidate phù hợp. Source phải trùng source của constraint được khai; metadata không thay authority check. Pending hoặc missing/stale/candidate review giữ constraint pending. Optional constraint pending không chặn verification, vẫn hiển thị.

Behavior pass + mandatory review pending → incomplete. Verification complete + human decision pending vẫn có thể xảy ra nếu review đó không phải constraint bắt buộc trong scope. Không auto-merge khi complete.

Reference result là **P2 assessment output**, không phải P1 report wire object. P3/P4 phải map status/ref/scope/limitations vào report v2 và giữ structured assessment artifact riêng; `hasOpenMandatoryCoverage` phải được giữ ở assessment và diễn giải trong criterion/report limitations, không âm thầm bỏ mất hoặc nhét field mới vào object strict. Nếu cần field machine-readable mới trong report, phải version contract, không sửa nghĩa v2 ngầm.

## 7. Finding: tạo, phân loại, adjudication và dedup

| Tình huống | Finding phù hợp | Không kết luận |
|---|---|---|
| Accepted current counterexample against clear requirement | Defect có rationale, source/reproduction, impact và scope | Không từ test import/error suy defect |
| Requirement mơ hồ/mâu thuẫn | Ambiguity + câu hỏi owner | Không tự đặt expected behavior hoặc ưu tiên nguồn |
| Thiếu/stale/blocked/coverage thiếu | Verification gap + check/permission/source cần bổ sung | Không mặc định app sai hoặc reviewer bỏ sót |
| Evidence/quy trình cần lưu ý, chưa đủ kết luận behavior | Process observation | Không đếm thêm defect cùng nguyên nhân |
| Đủ evidence, không có issue | Không cần finding | Không tạo finding giả để “có output” |

Model/agent suggestion bắt đầu candidate; chỉ được confirmed khi basis accepted có refs/rationale, phù hợp expected behavior/candidate, bằng người hoặc workflow có quyền trong scope. Source reasoning hợp lệ có thể là basis, không bắt buộc check fail. Không gọi confirmed trong mock là độc lập/human adjudicated. Rejected/disputed/duplicate/pending có rationale riêng; pending không là false positive.

Dedup theo behavior/nguyên nhân/scope có nguồn, không theo số test hoặc độ giống câu chữ. DuplicateOf dẫn canonical finding trong cùng report, không cycle/dangling; chain hợp lệ kết thúc ở gốc. Chỉ group khi có basis accepted; nếu chưa rõ cùng nguyên nhân thì giữ candidates và nêu nghi ngờ duplicate, không ép giảm count. Không gộp lỗi khác revision/cause chỉ vì cùng AC.

Lifecycle thiết kế: candidate/pending → confirmed/rejected/duplicate/disputed; disputed → confirmed/rejected/duplicate khi có basis mới. Confirmed/rejected/duplicate muốn đổi verdict phải mở disputed với lý do rồi adjudicate lại, giữ lịch sử; không silent overwrite. Verdict, severity, risk và release decision là các khái niệm khác nhau.

Thống kê dùng unique canonical issue và khai rõ declared/adjudicated/self-check/independent. Validity chỉ confirmed/(confirmed+rejected) trên unique defect candidates có verdict phù hợp; denominator 0 là N/A. Không là recall hoặc efficacy. Reference evaluator hiện không sinh/đếm findings tự động; P1 giữ graph, P2 cung cấp quy tắc/transition predicates, P3/P4 mới điều phối và lưu verdict.

## 8. Action và điều kiện hoàn thành

Action xuất phát từ finding/gap, có việc cụ thể, vai trò xử lý, assignee hoặc unknown, depends-on, và `doneWhen` kiểm được. Không yêu cầu người dùng tự suy “làm gì tiếp” từ một bảng test.

Trình tự: proposed → assigned → in_progress → done; proposed/assigned/in_progress có thể blocked, blocked trở lại assigned/in_progress sau khi reason giải quyết; done có thể reopen thành assigned với rationale/proof mới và giữ lịch sử. Không cho proposed nhảy thẳng done để che việc chưa giao/chưa thực hiện.

Assigned/in_progress/done cần assignee. Done còn cần accepted completion basis, proof references và done predicate thật sự đạt. Claim “đã sửa” hoặc đã cấp tài khoản không thay QC rerun/evidence khi doneWhen yêu cầu; completion proof/version/scope phải phù hợp. Action done không tự làm AC verified hoặc cấp approval; phải re-evaluate evidence và constraint trên candidate hiện tại.

N/A, finding adjudication, action completion và risk acceptance phải do actor/workflow có thẩm quyền theo project/domain scope. Không suy role Runner được duyệt mọi domain judgment. Quyền nội bộ thực tế thuộc P3/P4, không lấy bool `authorized` của model/client làm authority.

`validate_transition` chỉ là predicate tham khảo trên **trusted context facts đã cung cấp** (authorized/basisRefs/basisState/donePredicateMet/assignee). Nó kiểm shape, transition và presence/logic; chưa resolve proof refs, principal hoặc authorize ai. Để áp transition thực phải qua auth, ref/version/canonical graph và basis resolution trước, append audit event sau. Không dùng helper này làm endpoint công khai.

## 9. Ranh giới code và judgment

| Code/reference rule làm được | Agent/domain/workflow phải cung cấp và có thể sai |
|---|---|
| Shape/ref/scope/revision, eligibility flags, deterministic status precedence, coverage declared contexts/levels | Expected behavior đầy đủ, obligation decomposition, assertion relevance, comparability contexts, risk/coverage plan đúng |
| Chặn record-only trong execution review, loại blocked/error khỏi positive/negative behavior proof | Integrity/attribution/scope thật sự, execution attestation, source proof đúng |
| Nhận conflict, N/A/constraint metadata requirements, transition predicates | Owner applicability, authority, adjudication, doneWhen satisfaction |

P3 phải thiết kế nơi trusted context hình thành/được kiểm, nơi secrets/permission/lease được enforce, và audit trail. Chưa có thành phần đó thì output chỉ là conditional assessment, không “tự động chứng minh mọi requirement”. Đây không phải lý do hỏi người dùng duyệt mọi bước routine, mà là yêu cầu tách raw inference với state được hệ thống chấp nhận.

## 10. Scenarios, công cụ và kết quả

[Bộ tình huống v1](../examples/rules/v1/README.md) gồm 55 decision scenarios và 20 lifecycle cases, giữ replay lịch sử. [V2](../examples/rules/v2/README.md) và [tests v2](../tools/test_rules_v2.py) kiểm corrected semantics, legacy compatibility, version mismatch và no-mutation. [Reference evaluator](../tools/evaluate_rules.py) dispatch theo assessment version; không silent upgrade. Dependency dev dùng lại `tools/requirements-contracts.txt`, không chốt product language/stack.

```text
py -3 -X utf8 -B tools/test_rules.py -v
py -3 -X utf8 -B tools/test_rules_v2.py -v
py -3 -X utf8 -B tools/evaluate_rules.py examples/rules/v1/base-bundle.json examples/rules/v2/base-assessment.json
```

CLI: exit 0 evaluated + verification complete; exit 1 evaluated nhưng failed/incomplete; exit 2 input_error, không có status QA. Reference result và reason codes hiển thị rõ để không nhầm exit 1 là process crash. Không network/model/container/test project hoặc ghi đè input/report.

Evaluator và report CLI dùng chung strict JSON intake tại `tools/json_input.py`: duplicate members, NaN/Infinity hoặc deep recursion bị từ chối thành input_error, không traceback/raw-value diagnostics. Valid v1 replay vẫn giữ semantics; JSON mơ hồ/lỗi không được coi là historical compatibility cần giữ.

Bốn unittest methods v1 (`tools/test_rules.py`) dùng subtests: decision table, lifecycle, repeatable/no-mutation và CLI semantics. V2 và report/shared-parser tests có methods riêng, không gộp vào con số bốn này. Tests đã pass cho requirement conflict/independent AC, coverage thiếu, same-context conflict vs different-context counterexample, source proof, record-only, stale/trust gaps, N/A accepted/rejected/contradicted, P-05 và lifecycle. Không tính số case thành effectiveness hoặc số lỗi app đã phát hiện.

## 11. Gate P2 và bước tiếp

P2 có precedence/sufficiency theo scope, mode/provenance/risk, mandatory constraint, finding/action lifecycle và reference scenarios kiểm được; v2 sửa hai lỗi audit, v1 chỉ replay lịch sử. P1 v2/schema/specimens được giữ nguyên, không thay identity hay field P1 ngầm. Không claim domain truth hoặc runtime readiness từ independent code review/reference tests.

Prerequisite [reference report P4-A](OFFLINE-REPORT.md) và [S1 parity](S1-RESULTS.md) đã hoàn tất trên workload synthetic. Việc tiếp theo là versioned runtime report/constraint integration và module pure core Python theo [ADR-004](adr/004-core-baseline-after-s1.md)/[plan hiện hành](IMPLEMENTATION-PLAN.md). Trusted acceptance, runtime enforcement và các stack boundaries khác vẫn cần implementation/spike riêng; không pilot/E3/public publish.
