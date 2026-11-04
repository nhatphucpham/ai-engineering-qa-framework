# MOCK-06 v2 — Dấu cách đã có yêu cầu rõ và kiểm chứng mới

Ngày 04/11/2026. Synthetic-only, case đã biết đáp án. Commit nền `1064b2f`. Snapshot mới `mock-06-fixed-v2`, requirement `mock-req-06-v2`; đây là nhãn local, không phải Git SHA. Người chuẩn bị: trợ lý. Người dùng chọn behavior cho mock trong chat; reviewer/approval hệ thống thật vẫn pending.

## Kết quả và việc tiếp theo

**Bản v2 đạt 13/13 test: 9 test cũ và 4 test mới.** Phần dấu cách từng mơ hồ đã được người dùng chọn rõ và được kiểm chứng trên snapshot mới. Verification **complete trong scope v2 đã khai báo**, dựa trên assertions/source và execution nêu dưới; không phải cam kết mọi input đều đúng hoặc human approval.

Việc tiếp: người dùng đọc phần giải thích dưới và xác nhận có hiểu hành vi/kết quả mà không phải mở file khác không. Hoàn thành bước này khi có phản hồi thực tế về khả năng hiểu và hành động; chưa coi G1 đạt chỉ vì test xanh. Nếu phát hiện gap mới thì sửa hồ sơ/check trong version mới; chưa cần mở rộng automation.

## Thay đổi dấu cách — mong muốn, lý do, thực tế, cách sửa, kiểm tra

- **Mong muốn:** `"   "` nghĩa tất cả; `" books "` nghĩa books. Người dùng chọn hai đáp án này trong chat, được ghi tại [requirement v2](../../examples/remediation/06-filter-pagination-v2/requirements.md). Phạm vi mới là dấu cách ASCII ở hai đầu; vẫn phân biệt hoa thường, không xóa dấu cách giữa chữ.
- **Lý do:** theo lựa chọn cho ví dụ, dấu cách ở hai đầu không làm thay đổi nhóm sản phẩm cần tìm. Sau khi bỏ dấu cách mà không còn chữ, xử lý như không chọn nhóm: hiển thị tất cả. Đây là quyết định cho mock, không phải quy tắc phổ quát.
- **Thực tế trước thay đổi:** bản fixed-v1 chỉ so khớp nguyên chuỗi, nên hai input trên không trùng category nào và trả danh sách rỗng. V1 chưa chốt yêu cầu này; không gọi đó là defect hồi tố của v1.
- **Cách sửa:** [service v2](../../examples/remediation/06-filter-pagination-v2/fixed/service.py) bỏ dấu cách hai đầu trước khi lọc. API/UI dùng service này nên cùng nhận kết quả đúng. Cache vẫn phân biệt category/page/page_size; không yêu cầu các cách viết tương đương dùng chung entry. Reset trang và các thay đổi trước giữ nguyên.
- **Kết quả kiểm tra:** service với `"   "` trả total=8, trang 1 là B1/B2; `" books "` ở trang 2 trả B3/B4, total=6. API không lẫn books/tools/tất cả qua nhiều request. UI đổi từ trang 3 sang `" tools "` về trang 1, trả T1/T2, rồi chọn `"   "` trả total=8. Cả 4 test mới pass ở v2, fail trên v1. Bốn test là các kiểm tra của một clarification, không phải bốn defect riêng.

## Evidence và đối chiếu yêu cầu

Lệnh thực chạy từ root repo trên Python 3.14.8:

```text
py -3 -X utf8 -B examples/remediation/06-filter-pagination-v2/run.py
```

Exit 0. [Execution local v2](../../examples/remediation/06-filter-pagination-v2/execution.local.json) ghi hashes requirement, code, tests, worker/runner, snapshot và traceback. Mỗi nhóm chạy trong process riêng.

| Snapshot | 6 baseline | 1 historical | 2 probe cũ | 4 test dấu cách mới | Errors/skipped |
|---|---|---|---|---|---|
| fixed-v1 | 6 pass | 1 pass | 2 pass | 4 fail | 0/0 |
| fixed-v2 | 6 pass | 1 pass | 2 pass | 4 pass | 0/0 |

`pass` nghĩa kết quả khớp mong đợi trong test đã chạy. `fail` ở v1 cho thấy nó chưa đáp ứng quy tắc v2. Runner `MATCH`/exit 0 nghĩa outcome khớp thiết kế, kể cả failure đối chứng; không có nghĩa v1 đạt yêu cầu v2.

| AC v2 | Nguồn kiểm chứng trên fixed-v2 | Trạng thái và giới hạn |
|---|---|---|
| AC-01 | [Baseline.test_service_category_and_case](../../examples/mock/06-filter-pagination/tests/test_baseline.py), [Whitespace.test_service_padded_category_and_pagination](../../examples/remediation/06-filter-pagination-v2/tests/test_whitespace.py), source service | verified: category/case, dấu cách hai đầu, không xóa dấu cách giữa chữ trong input mẫu |
| AC-02 | [Historical.test_reset_from_third_page](../../examples/mock/06-filter-pagination/tests/test_historical.py), [Probe.test_reset_with_recorded_api_call](../../examples/mock/06-filter-pagination/expected/test_probe.py), Whitespace.test_ui_spaces_and_padded_category | verified: reset trước request, kể cả chọn category có dấu cách |
| AC-03 | Probe.test_cache_across_categories, Whitespace.test_api_mixed_categories, source API | verified: sequence category khác nhau và cache key vẫn có category/page/page_size |
| AC-04 | Baseline.test_service_pagination_and_out_of_range, Baseline.test_api_page_and_size, Whitespace.test_service_padded_category_and_pagination, source service | verified trong catalog cố định và input được kiểm tra/source reasoning |
| AC-05 | Baseline.test_empty_category, Whitespace.test_service_spaces_mean_all, Whitespace.test_api_mixed_categories, Whitespace.test_ui_spaces_and_padded_category | verified: chuỗi rỗng/toàn dấu cách và category được bọc dấu cách trong scope |

Các tên Whitespace nằm trong file test mới đã link ở AC-01; các tên Baseline/Probe nằm trong file đã link tương ứng. Đối chiếu `snapshot=mock-06-fixed-v2` và `module` trong execution để xác nhận kết quả của bản mới.

## Giới hạn

Risk medium theo v1, phạm vi một process với catalog public giả lập, dễ revert. Input là string và page/page_size nguyên dương; không xét tab/newline/Unicode whitespace, invalid types, auth, TTL, concurrency, response mutation hoặc HTTP/browser thật. Data/API/UI được sao chép từ fixed-v1, chỉ service đổi lọc dấu cách. Mẫu v1 và toàn bộ evidence cũ giữ nguyên.

Đây là feasibility của luồng clarification → requirement version → thay đổi → kiểm chứng. Chưa đo effort/cost, hiệu quả reviewer hoặc ROI. Lựa chọn requirement của người dùng không thay thế approval/review kết quả. G1 còn chờ phản hồi về bản trình bày mới.
