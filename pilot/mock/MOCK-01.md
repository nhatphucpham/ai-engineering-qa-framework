# Walkthrough MOCK-01 — Đủ evidence

Loại dữ liệu: **synthetic/mock**, case thiết kế đã biết đáp án, không phải blind evaluation hoặc human adjudication. Người chuẩn bị: trợ lý thực hiện walkthrough. Reviewer/owner quyết định thật: unknown; human decision: pending. Effort thực tế và cost: unknown.

Nguồn phiên bản: commit nền `063d25f0577d7bcbbba534073bc5b8dcc3cd8976`; snapshot `mock-01-head` là nhãn toy. Requirement [mock-req-01-v1](../../examples/mock/01-complete/requirements.md). Liên hệ [pilot brief](../../docs/PILOT-BRIEF.md).

## Mục tiêu và risk

Tính phí 5 nếu total < 100 và 0 nếu total >= 100, input là số nguyên không âm. [Diff](../../examples/mock/01-complete/change.diff) đổi `>` thành `>=` từ [before](../../examples/mock/01-complete/before.py) sang [after](../../examples/mock/01-complete/after.py). Risk low trong bài tập hàm cô lập: tác động chỉ tới kết quả trả về, phạm vi hẹp, sửa/revert dễ. Không suy ra risk checkout hoặc tiền tệ thật. Checks: hai nhánh và đúng biên 100; probe bổ sung phía trên biên.

## Trạng thái từ input ban đầu

Đây là tái dựng trước probe sau khi đã biết đáp án. [CI input](../../examples/mock/01-complete/evidence.mock.json) khai báo baseline pass tại `mock-01-head`, nhưng không phải execution log thật. Mapping được đối chiếu assertion và source, không coi khai báo pass tự nó là đủ.

| AC | Expected behavior / nguồn | Evidence tại head | Trạng thái ban đầu | Gap / action |
|---|---|---|---|---|
| AC-01 | Requirement v1: total < 100 → 5 | [baseline](../../examples/mock/01-complete/test_baseline.py) `test_below_threshold`: `shipping(20)=5`; source trả 5 ở nhánh <100 | verified trong toy, sau đối chiếu source/assertion; execution local xác nhận bên dưới | Không có gap đã xác định |
| AC-02 | Requirement v1: total >= 100 → 0, bao gồm 100 | Baseline `test_exact_threshold`: `shipping(100)=0`; [source](../../examples/mock/01-complete/after.py) dùng `>=100` | verified trong toy với giới hạn test ví dụ và source | Không tạo finding vì ít test; probe trên biên là bổ sung đã thiết kế |

## Sau probe và cách lặp lại

Từ root repo:

```sh
python3 -B examples/mock/run.py
```

Quan sát ngày 03/11/2026 trên file ở commit nền: baseline 2 tests, 0 failures, 0 errors, 0 skipped; [probe](../../examples/mock/01-complete/expected/test_probe.py) `test_above_threshold` kiểm tra `shipping(101)=0`: 1 test, 0 failures/errors/skipped. Diff khớp snapshots. Runner toàn bộ exit 0; các failure ở MOCK-02/04 là dự kiến, không thuộc MOCK-01.

| AC | Sau probe | Thay đổi so với input |
|---|---|---|
| AC-01 | verified trong scope toy | Baseline được chạy lại local, không có claim behavior mới |
| AC-02 | verified trong scope toy | Có thêm execution tại 101; không thay đổi next action |

Đối chiếu [đáp án có sẵn](../../examples/mock/01-complete/expected/quality-record.md): phù hợp. Không tuyên bố tự tìm ra kết luận mới. Các input/source/expected không bị sửa.

## Finding, hành động và giới hạn

Finding: không có trong phạm vi đã khai báo; không tạo defect cho input ngoài scope. Verification: **complete trong phạm vi toy**, không chứng minh toàn bộ đầu vào hay tích hợp checkout. Tests dùng điểm ví dụ, có thêm source reasoning; không phải kiểm chứng hình thức.

Hành động đề xuất: reviewer tiếp tục quy trình review thông thường; không yêu cầu thêm QA layer nếu chỉ lặp thông tin đã có. Reviewer thật đã biết gì hoặc có thay đổi quyết định không: unknown. Human decision vẫn pending, không có approval merge/release. Owner bước review thật: chưa được xác nhận. Giá trị gia tăng, overhead và effectiveness: unknown.
