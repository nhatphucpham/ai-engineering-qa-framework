# Review loop — output hiện tại

Ngày 10/11/2026. **Trạng thái: DONE — final clean tại vòng 3.** Không còn finding mở trong scope đã review. Áp dụng [quy trình bắt buộc](REVIEW-WORKFLOW.md) cho output phiên phát triển từ nền `9237018a9ce5b0dd28d26984e1db5182adad0b2c` và yêu cầu review lặp mới của người dùng.

Reviewer được chỉ định xuyên suốt: **GPT-6 Astra high, architecture_review**, độc lập, read-only. Root sửa code/docs/tests. Scope: P2 v2, shared JSON intake, offline report/schema/goldens, plan/current docs, AGENTS và review policy. Không nghiệm thu runtime stack/server/worker/desktop/pilot. Working tree chưa commit; reviewer đọc file trực tiếp, không chỉ nhận bản tóm tắt.

## Vòng 1 — đưa output đang có vào review

Input: output 25 files từ phiên trước (P2 v2/report/plan), 20 test methods pass. Reviewer tự chạy full suite: **20 methods pass, 10.191s**, nhưng vẫn tìm thấy các lỗi dưới đây. Test xanh chưa đóng review.

| ID / mức độ | Vấn đề và suy luận ảnh hưởng | Fix / kiểm chứng bản mới | Trạng thái |
|---|---|---|---|
| RV-01 / high | Evaluator CLI dùng JSON last-wins và không catch deep recursion, khác report CLI; cùng bytes có thể cho complete ở một cửa vào và input_error ở cửa kia | Dùng chung tools/json_input.py; reject duplicate/nonfinite, catch recursion. Tests hai CLI với leading wrong/last valid members, NaN, deep JSON, no secret sentinel/traceback; giữ valid v1 replay | CLOSED tại vòng 2 bởi reviewer |
| RV-02 / medium | Action bịa conflict khi chỉ thiếu integration coverage; blocked lại giao domain-owner/gợi ý clarification. Hướng dẫn sai khiến người nhận xử lý nhầm việc | Sau vòng 2 đổi priority branches thành independent reason groups, thêm regression simultaneous blockers và dedup per criterion/reason class | CLOSED tại vòng 3 bởi reviewer |
| RV-03 / low | Current docs còn next-step/version/reviewer-scope cũ; người tiếp tục có thể quay lại bước đã xong hoặc hiểu nhầm review đã làm | S1 là next trong VERIFICATION-RULES, qualify bốn methods chỉ v1, TARGET dùng current rules v2, handoff nêu đúng ba docs plan reviewer đã đọc | CLOSED tại vòng 2 bởi reviewer |

Trong lúc sửa RV-02, reviewer kiểm draft mới và phát hiện cùng nhóm routing vẫn sai ở OUTCOME_RELATION_MISMATCH, fail + pending risk và N/A thiếu actor. Giữ **RV-02** và bổ sung regression, không tạo IDs mới hoặc coi bản sửa đầu là đã đóng. Wrong binding cần QA đối chiếu evidence; pending risk cần coverage-policy-owner; N/A decision có thể bổ sung trên cùng candidate, chỉ version requirement khi expected behavior thực sự đổi.

## Bản mới gửi vòng 2

Đã thêm policy vào AGENTS.md/IMPLEMENTATION-PLAN và REVIEW-WORKFLOW, không sửa skill hoặc fixture frozen. Root chạy **23 methods pass, 13.977s** sau code/tests fixes. New tests: 2 shared-parser methods và 1 action-routing method với nhiều cases phân biệt expected behavior. Goldens complete/constraint-collision cũ vẫn validate, không regenerate/overwrite để làm xanh tests.

Snapshot input vòng 2 được lưu tại [review-r2-2026-11-10.json](reviews/review-r2-2026-11-10.json): SHA-256 raw bytes của từng file thay đổi/mới ở thời điểm gửi reviewer, ngoài chính manifest để tránh tự tham chiếu. Snapshot là input trước ghi nhận verdict/DONE hành chính; không giả rằng hash của record trước đóng review là hash sau bổ sung verdict.

Reviewer cần re-read bản mới, xác nhận từng RV-01..03 đã hết, kiểm lỗi tái xuất hiện và lỗi mới về accuracy/practicality/policy consistency. Chưa có final verdict trong record ở thời điểm ghi đoạn này. Kết quả vòng tiếp theo được cập nhật sau khi thực hiện.

## Vòng 2 — vẫn chưa DONE

Reviewer kiểm snapshot vòng 2 và tự chạy **23 methods pass, 14.200s**. RV-01/RV-03 đóng; RV-02 giữ mở vì simultaneous blockers bị priority routing che mất: blocked + pending plan chỉ có check-owner; conflict + pending plan thiếu coverage-policy-owner. Cùng nhóm nguyên nhân nên giữ RV-02, không tạo finding mới hoặc đếm lặp như lỗi khác. Review policy không có finding mới.

## Bản mới gửi vòng 3

Refactor action generation: verification status tạo defect proposal; từng nhóm reason độc lập tạo clarification/applicability/conflict/check/plan/evidence-review proposal, tối đa một proposal mỗi criterion/reason class. Fallback remaining-coverage chỉ dùng khi không có targeted reason giải thích gap. Không hứa một action đủ giải toàn criterion; sau xử lý phải re-evaluate. Verified/N/A hoặc failed đã account coverage không tạo việc cho context phụ không chặn kết luận.

Regression thêm blocked+plan, failed conflict+plan, conflict+blocked+plan và policy-only: đủ các owners, conflict đúng điều kiện và policy action không lặp. Root chạy **24 methods pass, 14.201s**. Hai goldens giữ nguyên và validate; không sửa expected cũ để chấp nhận lỗi mới.

Snapshot input vòng 3: [review-r3-2026-11-10.json](reviews/review-r3-2026-11-10.json), giữ nguyên manifest vòng 2 làm lịch sử. Reviewer đã final re-review và xác nhận đủ điều kiện DONE.

## Vòng 3 — FINAL CLEAN / DONE

GPT-6 Astra high đọc lại code/tests/docs/policy và goldens của `offline-review-r3-2026-11-10`, đối chiếu đủ **31 file** theo sizes/SHA-256. Manifest SHA-256: `1c1f08b60d2243e078dc297faaa381bd6752d99961046b0a4ff0e3f81230418f`. Reviewer chạy độc lập `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: **24 methods pass, 13.910s**.

Final verdict: RV-01/RV-03 vẫn đóng; RV-02 đã đóng vì proposals theo actual reasons giữ đủ concurrent check/QA/plan ownership và không trùng policy-only action. Các fix P2/report trước đó còn nguyên; không phát hiện finding mới trong scope, open IDs = ∅. Đánh dấu output **DONE** theo clean verdict này, không dựa riêng vào test pass.

Sau reset, root kiểm lại manifest SHA, sizes/SHA của cả 31 file và inventory working tree: khớp, không payload drift. Không chạy lại suite khi code không đổi; kết quả root 24/14.201s và reviewer 24/13.910s là các lần đã thực chạy trước reset. Phần đóng review chỉ cập nhật verdict/trạng thái hành chính tại record này và SESSION-HANDOFF, theo ngoại lệ ghi nhận trong REVIEW-WORKFLOW. Không sửa/ghi đè manifest input hoặc code đã review để giả hash của bản sau đóng bằng bản trước đóng.

DONE chỉ bao phủ synthetic P2 v2, report tham chiếu offline, current plan/docs và persistent review workflow. S1 cross-runtime parity, P1 runtime integration và readiness sản phẩm vẫn chưa đạt/chưa triển khai. Bước tiếp theo là S1 theo IMPLEMENTATION-PLAN; chưa commit/push/pilot/publish.
