# P1 contract specimens — không phải execution

**LỊCH SỬ tại commit `872c498`, còn các lỗ hổng đã được audit.** [V2](../v2/README.md) là bản đang dùng. Schema và JSON v1 không sửa; lệnh validator v1 bên dưới chỉ áp dụng khi checkout commit lịch sử. Active validator hiện trả `E_CONTRACT_VERSION` cho v1.

Mọi ID, principal, model, credential/image/network reference, timestamp và budget trong JSON là dữ liệu tác giả soạn. Không có account/key/image/container hoặc test thật được dùng. [Contract](../../../docs/DATA-CONTRACT.md) mô tả ownership và giới hạn; [schema](../../../schemas/qa-contract-v1.schema.json) chứa shapes.

- `valid-handoff.json`: handoff bundle, API mode, unit pass record/QC blocked, run completed nhưng verification incomplete.
- `valid-repo-conflict.json`: intake repo/task, local agent mode, nguồn requirement mâu thuẫn; giữ criterion unverified.
- `valid-worker-claim.json`: snapshot run checking có lease/token và worker-result/progress đúng snapshot. Không có worker thật.
- `invalid-scenarios.json`: các phép thay đổi có ID/expected error trên valid-handoff, dùng để tái hiện malformed/reference/version/lease/report errors. Đây là mutation manifest để giữ bộ lỗi nhỏ/dễ đối chiếu, không phải JSON gửi vào server.

Chạy từ root repo:

```text
py -3 -X utf8 -B tools/test_contracts.py -v
py -3 -X utf8 -B tools/validate_contracts.py examples/contracts/v1/valid-handoff.json
```

Cần dependency tại `tools/requirements-contracts.txt`. JSON Schema không kiểm được secret tồn tại, permission, execution thật, sufficiency domain hoặc container an toàn. Checker P1 chỉ thêm đối chiếu references/snapshot/self-consistency; không thay P2 rules hoặc P4 runtime.
