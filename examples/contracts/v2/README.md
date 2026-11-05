# P1 contract v2 — specimen sau audit

Mọi giá trị là authored synthetic; không có account/key/image/container/test thật được dùng. [Contract hiện hành](../../../docs/DATA-CONTRACT.md), [schema v2](../../../schemas/qa-contract-v2.schema.json), [các finding đã sửa](../../../docs/P1-REVIEW-FIXES.md).

V2 không tương thích v1: thêm tasks/taskRef, source/diff refs, artifact task scope, contextEvidenceIds và rerunOfRunId. Schema/specimen v1 giữ lịch sử; active validator chỉ nhận `contractVersion=2.0.0`, không nâng cấp ngầm v1.

| Specimen hợp lệ | Điều kiểm tra |
|---|---|
| valid-handoff.json | Handoff/API mode, unit mock pass/QC blocked; processing completed nhưng verification incomplete |
| valid-repo-conflict.json | Repo/local agent, requirement conflict unverified |
| valid-worker-claim.json | Worker token/attempt/version đúng snapshot |
| valid-multi-task.json | Hai task cùng candidate; một task có hai handoff; source/diff/evidence không lẫn task |
| valid-manual-rerun.json | Chạy lại chủ động có lineage, không dùng lại event; report_ready đúng run/report |
| valid-execution-shape.json | Có provenance execution với refs/time đúng cấu trúc, không tự chứng minh test thật hoặc đủ AC |
| valid-stale-context.json | Evidence và artifact cũ khớp revision, giữ làm context, không kết luận candidate mới từ đó |
| valid-duplicate-chain.json | Duplicate chain kết thúc tại finding gốc, được chấp nhận |
| valid-assigned-action.json | Action done có assignee; không tự chuyển verification thành complete |

`invalid-scenarios.json` chứa 58 mutation scenarios; mỗi case có expectedCode và optional base file. Bốn test methods chạy các subtest và CLI, không phải chỉ có bốn tình huống.

Từ root repo, cần dependency tại `tools/requirements-contracts.txt`:

```text
py -3 -X utf8 -B tools/test_contracts.py -v
py -3 -X utf8 -B tools/validate_contracts.py examples/contracts/v2/valid-multi-task.json
```

Exit 0 chỉ xác nhận shape/reference/self-consistency. Auth thực, wall-clock lease expiry, atomic idempotency/persistence, execution attestation và sufficiency domain chưa được triển khai. Không dùng các file này làm bằng chứng framework production-ready.
