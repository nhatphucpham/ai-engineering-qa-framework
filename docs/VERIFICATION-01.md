# Kiểm tra lại S0/S1 — 03/11/2026

Phiên bản kiểm tra: `5c65446a7a7f1d66c22a6e8f7314855c39bb2d4d`. Đã xác nhận `refs/heads/master` trên origin trỏ đúng commit này. Các kiểm tra code đều dùng synthetic, không có network/model call của ứng dụng; truy cập remote chỉ để đọc Git ref.

## Kết quả

Không thấy lỗi ngoài các bug fixture đã thiết kế trong phạm vi kiểm tra. Các kết luận behavior trong [MOCK-01](../pilot/mock/MOCK-01.md), [MOCK-02](../pilot/mock/MOCK-02.md) và [MOCK-06](../pilot/mock/MOCK-06-review.md) khớp source/assertion và kết quả execution.

| Kiểm tra | Quan sát |
|---|---|
| Runner MOCK-01–05 | Exit 0; mọi count và diff khớp manifest, hai probe failure ở 02/04 đúng thiết kế |
| Runner MOCK-06 chạy lại trong bản sao tạm | Exit 0; 6 nhóm execution, tổng 18 lượt test, cùng test IDs/counts/errors/skipped như evidence đã commit |
| Baseline head MOCK-06 | 6 pass; chưa cover chuyển category qua cache hoặc reset từ page khác 1 |
| Historical check | Base pass; head fail vì giữ page=3 |
| Hai probe | Base cả hai pass; head cả hai fail ở đúng test IDs |
| Hash execution đã commit | Tất cả SHA-256 khớp file hiện tại; không ghi đè execution gốc khi verify |
| Bốn cách chạy baseline/historical theo README | Base cả hai exit 0; head baseline exit 0, historical exit 1 |
| Controls trong bản sao tạm | Skip baseline làm runner exit 1; sửa cache ngoài thiết kế làm runner exit 1 vì diff và kết quả probe không khớp |
| Kiểm tra syntax và liên kết | Python của MOCK-06 hợp lệ; 101 relative links trong phạm vi tài liệu đã đọc đều tồn tại trước khi bổ sung biên bản này |
| Bảo toàn dữ liệu mẫu cũ | Không có diff so với `063d25f` trong source/tests/expected của MOCK-01–05, runner cũ, manifest và template |

## Đối chiếu trực tiếp behavior

Ngoài runner, đã so service và API với phép lọc/slice theo catalog ở 5 category (`books`, `tools`, `Books`, chuỗi rỗng, `missing`), 4 page size (1, 2, 3, 10) và 5 page (1, 2, 3, 4, 10). Mỗi category dùng API instance riêng. 200 phép so sánh tại base và 200 tại head đều khớp cho phạm vi category cố định. Đây là kiểm tra bổ sung có giới hạn, không chứng minh mọi input.

Sau đó quan sát riêng hai sequence:

- Cùng API instance, books/page=1/size=2 rồi tools/page=1/size=2: base trả T1/T2, total=2; head trả B1/B2, total=6. Xác nhận F-06-02 và phân biệt với lỗi UI.
- View bắt đầu books/page=3, chọn tools với API mới: base về page=1 và T1/T2; head giữ page=3, items rỗng, total=2. Xác nhận F-06-01. Historical và probe reset vẫn là cùng một defect.

Whitespace chưa có expected behavior được owner xác nhận nên vẫn unverified; không dùng kết quả thực thi để tự gán thành defect. Không thấy mâu thuẫn giữa bảng trạng thái cuối và requirement/scope đã khai báo: AC-01/04 verified trong scope, AC-02/03 failed, AC-05 chưa kiểm chứng đầy đủ.

## Chỉnh tài liệu sau kiểm tra

Đã sửa hướng dẫn bắt đầu lệnh trong [README MOCK-06](../examples/mock/06-filter-pagination/README.md) thành từ root repo rồi chuyển vào thư mục case; làm rõ mốc commit/push trong [bản đọc nhanh](SESSION-01-EXPLAINED.md) và provenance của [hồ sơ MOCK-06](../pilot/mock/MOCK-06-review.md). Không sửa code, test, requirement, diff, đáp án hoặc execution gốc. Các chỉnh tài liệu/biên bản của lượt verification này chưa được commit/push tại thời điểm viết.

## Giới hạn

Đây là kiểm tra lại fixture và độ nhất quán hồ sơ bởi cùng trợ lý đã tạo case, không phải reviewer độc lập. Runner so outcome/count/test IDs; không tự đánh giá Markdown, phân loại finding hoặc bảo đảm mọi assertion fail vì đúng nguyên nhân. Traceback và source đã được đọc để đối chiếu các failure hiện tại. Chưa xác nhận G1 với người thật, usefulness, effort, ROI hay khả năng tìm defect mới. UI/API là mô phỏng trong process; không có kiểm tra browser/HTTP/deployment thật.
