# Review IAP-1.0.0 contract slice — 12/11/2026

Status **DONE — docs/design slice sau independent CLEAN WT-IAP-R2/R2a và required docs checks PASS**. Baseline master `ef6d3c162ff68fab568d19c8eac9c50892d304c2`. Reviewer độc lập GPT-6.1 Terra high `/root/identity_contract_review`, read-only, chỉ định trước sửa theo [workflow](REVIEW-WORKFLOW.md). Stable finding IDs IAP-RV-01…; giữ ID nếu reopen, không giới hạn số rounds. Không thay prior HS2/S2/S6 verdicts hoặc dùng docs DONE đóng product gate.

## Scope và acceptance

Người triển khai cần contract/acceptance nối identity→application/live-policy/broker, không code integration. Outputs review: [protocol IAP-1.0.0](IDENTITY-APPLICATION-PROTOCOL.md), current entries trong [NEXT](NEXT-SESSION.md), [plan](SESSION-PLAN.md), [handoff](SESSION-HANDOFF.md), [implementation plan](IMPLEMENTATION-PLAN.md), [D-32](DECISION-LOG.md), record này. Bốn bàn giao ban đầu còn nguyên bytes (ba current docs giữ làm suffix; record HS2 không sửa). Không source/schema/frozen protocol/corpus/fixture/evidence cũ thay đổi.

Acceptance docs: source mapping chính xác; user vs service identity, persisted ceilings vs live state/epoch và private operator Vault vs scoped broker tách rõ; start/cancel/read-report/source/export/secret-use có authority/trust/fence/deny/audit/retry boundary;24 acceptance cases có expected/observations và NOT RUN. Links/fences/diff/source-preservation checks thực PASS, latest independent CLEAN, không finding chưa xử lý thì mới DONE trong scope.

Non-goals: actual auth/worker/broker/API/DB harness mới, production stack/runtime selection, real account/key/API/project, OS key custody, pilot/publish hoặc commit/push. Full S4/S6/P3-B/P4-B và readiness còn mở; full P4-A partial. Các bằng chứng source/S2/S6 cũ dẫn tại protocol §2, không rerun hoặc coi là integration pass.

## Snapshot và actual checks — WT-IAP-R1

Chưa ghi kết quả trước khi chạy. Manifest/check evidence và reviewer verdict sẽ append bên dưới; record tự thân loại khỏi body manifest để tránh self-hash. Thay substantive content sau verdict phải mở lại review. Chỉ bổ sung status/verdict hành chính sau CLEAN theo workflow, không đổi historical manifest.

## Finding ledger

Current sau independent CLEAN WT-IAP-R2 + record R2a: **IAP-RV-01/02/03/04 CLOSED** do reviewer xác nhận; không finding mới/tái xuất hiện chưa xử lý trong scope. Output **DONE chỉ docs/design slice**, required docs checks PASS. Ledger/status này chỉ ghi nhận verdict đã nhận, không tự đóng findings thay reviewer.

Trạng thái lịch sử **trước official R1**: chưa có official findings, reviewer đang chờ exact snapshot/checks. Đây chỉ là thời điểm chuẩn bị, không là current verdict; “chưa findings” không nghĩa CLEAN.


### Root checks thực chạy — R1

`py -3 --version` → Python3.14.8. Baseline326 paths lấy bằng `git ls-files -z` cộng untracked HS2 record trước sửa, raw SHA256 lưu local; mọi path ngoài5 current docs vẫn khớp **321/321**. Năm docs current giữ toàn original bytes làm suffix **5/5**, kể cả ba docs bàn giao dirty ban đầu. HS2 record untouched. Source symbols kiểm bằng AST parse không import dependencies:25/25 symbols tồn tại trên unchanged sources, không chứng minh runtime auth.

Lần đầu `py -3 -B .cache/identity-application-2026-11-12/check_docs.py r1` **FAIL** chỉ vì thư mục scratch mới chưa ignored (`?? .cache/`); các checks nội dung pass. Đã chuyển đúng8 scratch files do phiên này tạo sang existing ignored `.cache/s6/identity-application-2026-11-12` sau xác minh source/destination nằm trong workspace và destination chưa tồn tại; không đổi ignore rule/source/evidence hoặc cache có trước. Giữ failed JSON và sửa ref scratch trong NEXT.

Lần mới `py -3 -B .cache/s6/identity-application-2026-11-12/check_docs.py r1b` **PASS**:167 local Markdown links có target, fences cân bằng/final newline,24 acceptance IDs liên tiếp,25 source symbols,321 preserved paths/5 suffixes, `git diff --check` exit0, changed paths chỉ7 docs của slice + HS2 untracked có trước. Không tests/DB/engine/network rerun, không integration evidence mới. Local checker/baseline JSON không portable prerequisite; kết quả/algorithm/hash cần thiết ghi tại đây để reviewer kiểm lại độc lập. External web links không được kiểm network trong docs scope.

Snapshot body manifest **WT-IAP-R1** (record tự thân loại khỏi hash): SHA256 UTF-8 của sorted `path + ASCII space + SHA256(raw file bytes)`, join LF **không trailing LF**. Tổng hash `73b4f928a096971cceeb718b0a9790e75f3ca69b7b8e00f3068c79e9d09aee17`.

| Body path | Raw SHA256 |
|---|---|
| `docs/DECISION-LOG.md` | `64b92a2b76962f77cf737529ba3924264ca9ab6e09e94fea612165911939e183` |
| `docs/IDENTITY-APPLICATION-PROTOCOL.md` | `c3e29fc9b4ced089ef9f05e86229c96e5f057f2777bb90f111bdbd756e58f3f2` |
| `docs/IMPLEMENTATION-PLAN.md` | `99220b8e80fe71dd06e191f5ddc5334ff1eee3372e5a4e360b26216b6162e026` |
| `docs/NEXT-SESSION.md` | `3c1d2f560c4b131e9a8fb12f60f97253622ab409633ce799caad65c02190a35f` |
| `docs/SESSION-HANDOFF.md` | `13f5ee1948fb6398440f0906aca44a70d9ea0e51090df1fda600f7ea011cc3ed` |
| `docs/SESSION-PLAN.md` | `b74b4ba2adb82492aba5f9657594a6736b17050ea161d011d76cb1c2e2637aef` |

Reviewer nhận đúng6 body files + record hiện tại, baseline ef6d3c1 + old S6/S2/core sources/results ở protocol §2, scope/acceptance/known gaps ở trên. Chờ official findings/verdict trên working bytes này; không tự mark DONE.


## R1 findings và root fixes chuẩn bị WT-IAP-R2

Reviewer kiểm6/6 raw hashes khớp snapshot R1; chưa CLEAN, chưa DONE. Ba findings mới, stable IDs giữ qua re-review:

| ID / severity | Expected vs actual / impact | Root fix và điều kiện reviewer đóng |
|---|---|---|
| IAP-RV-01 / P1 | §5.1 đưa payload digest vào key scope nhưng lại yêu cầu changed payload conflict; có thể tạo2 runs | Unique tuple chỉ principal kind/id + project + operation + client key, digest là comparison field; atomic insert-or-compare. A01 thêm2 independent concurrent processes/connections khác payload và cả hai ordering; reviewer kiểm docs/test obligation, runtime NOT RUN |
| IAP-RV-02 / P1 | A24 “no unsupported report_ready/completed” có thể cấm internal report hợp lệ chỉ vì legacy exporter unsupported | Tách legacy artifact bị chặn với internal proposal/completion mang projection_unsupported và đúng incomplete/failed/human pending. Positive/negative quan sát riêng, internal event chỉ sau durable authorized commit. Đối chiếu P4-A-RUNTIME-REPORT §§acceptance/limits, qa_core/runtime.py/reports.py; chưa runtime run |
| IAP-RV-03 / P2 | A03 gộp response loss với replay nên có thể hiểu loss đơn lẻ tự revoke family | A03 tách (a) reuse/concurrent → family revoke gồm winner pair, (b) loss sau success không reuse → family chưa tự revoke, client reauthenticate/no retry. §4.2 giải thích consistent; source S6-B refresh chỉ revoke khi used token bị reuse |

Root chỉ sửa protocol mới, không source/old evidence/old docs suffix. Re-run docs/preservation/checks và gửi full latest scope cho reviewer kiểm cả3 lỗi cũ/tái xuất hiện và lỗi mới; root fixes chưa tự đóng findings.


### Root checks thực chạy — WT-IAP-R2

`py -3 -B .cache/s6/identity-application-2026-11-12/check_docs.py r2` **PASS**:167 local links, fences/final newlines,25 AST symbols,24 IDs,321 preserved baseline paths và5 unchanged original suffixes; git diff check exit0. Bổ sung independent root scan toàn7 output docs: không trailing spaces/tabs; origin/master vẫn ef6d3c1 (không remote network action). Chỉ protocol body thay đổi sau R1, hash mới `b1e93f199f47e475814e74fbabe132a9c236c97919ec12006922a338e18c53c8`;5 body hashes khác giữ nguyên bảng R1. Body manifest R2 `8eef8ef9f96eaef7d6429247b13a98b2de4f357f0420d4e5c88e85debfcabf4d` theo cùng algorithm. Không test/DB/runtime run; chưa integration PASS, không commit/push. Gửi R2 + ledger cho independent re-review; chưa tự đóng findings/DONE.


## Re-review R2 và correction record R2a

Reviewer độc lập đã kiểm lại WT-IAP-R2, xác nhận **IAP-RV-01/02/03 CLOSED**, không tái xuất hiện. Reviewer actual `py -3 -B .cache/s6/identity-application-2026-11-12/check_docs.py reviewer-r2` **PASS** (167 links/25 symbols/24 cases/321 unchanged paths/5 suffixes/diff0), reproduced body hash `8eef8ef9f96eaef7d6429247b13a98b2de4f357f0420d4e5c88e85debfcabf4d`. Không reviewer DB/runtime run.

**IAP-RV-04 / P2**: Finding ledger vẫn ghi như hiện tại “chưa official findings” trong khi R1/R2 đã có3 findings. Impact: bàn giao có thể hiểu sai current state. Expected: label rõ lịch sử trước R1 hoặc current ledger đúng. Root sửa ledger phía trên ghi3 CLOSED theo reviewer và04 chờ xác nhận; giữ câu cũ dưới nhãn historical-before-R1. Chỉ record self đổi,6 body hashes/contract vẫn WT-IAP-R2. Gửi record R2a và checks mới cho reviewer kiểm04 + regression/new findings; chưa CLEAN/DONE.


## Final verdict — independent CLEAN WT-IAP-R2 + record R2a

12/11/2026. GPT-6.1 Terra high `/root/identity_contract_review` xác nhận **CLEAN** trên6-body manifest `8eef8ef9f96eaef7d6429247b13a98b2de4f357f0420d4e5c88e85debfcabf4d` và record R2a raw SHA256 `19b30b614098a33fbfecf6b821735ba1a1eccc92f842b43e15b5e506cbc7fb1d`. Reviewer kiểm lại01/02/03 vẫn CLOSED, xác nhận04 CLOSED, không findings mới/tái xuất hiện trong scope. Independent checker reviewer-r2 PASS như ở trên; root r2a cũng PASS cùng body hash. **DONE cho contract/docs output** theo acceptance, không readiness runtime/security/worker/broker/actual cleanup hoặc product gates.

Sau verdict chỉ cập nhật hành chính current status/ledger/verdict trong record và5 current docs: IN REVIEW→scoped DONE/CLEAN/checks PASS. Protocol WT-IAP-R2, source/evidence/fixtures và mọi original docs suffix giữ nguyên; historical hashes R1/R2/R2a không bị sửa và không claim là hashes sau admin update. 24 integration obligations vẫn **NOT RUN**. Không test/DB/engine/network execution mới, không production stack hoặc Git action; full S4/S6/P3-B/P4-B vẫn mở, full P4-A partial. Final docs/preservation/status checks bổ sung kết quả thực bên dưới.


### Final administrative checks thực chạy

`py -3 -B .cache/s6/identity-application-2026-11-12/check_docs.py final` **PASS** sau scoped status update:167 local links, fences/final newlines,25 AST source symbols,24 acceptance IDs,321/321 baseline paths unchanged,5/5 original suffixes preserved, `git diff --check` exit0. Current protocol raw hash vẫn `b1e93f199f47e475814e74fbabe132a9c236c97919ec12006922a338e18c53c8`. Final administrative body manifest `e895a56d89f8bb1c7f8f283d28905c6e3d57f5c5828709fe7ee0d9e24569789d` dùng cùng6 paths/algorithm; đây là post-verdict status snapshot, không thay reviewed R2 hash. Self-record ngoài body manifest.

Git HEAD vẫn ef6d3c1; changed scope7 docs mới/cập nhật + untracked HS2 record có trước (không sửa). No new commit/push; toàn original source/protocol/evidence và bàn giao bytes bảo toàn. Scratch/baseline/check JSON chỉ ignored local cache; mọi kết quả cần bàn giao đã ghi tại record này. Next action/authority và NOT RUN/gaps giữ theo protocol §10 và current handoff.
