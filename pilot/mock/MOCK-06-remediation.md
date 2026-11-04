# MOCK-06 — Kiểm chứng sau sửa

Ngày 04/11/2026. Synthetic-only, walkthrough đã biết đáp án; người chuẩn bị là trợ lý, reviewer/domain owner thật unknown. Human decision pending. Commit nền `9bc27f6`; nhãn snapshot không phải Git SHA.

## Kết luận và phạm vi

Hai defect trong [hồ sơ gốc](MOCK-06-review.md) được sửa tại [snapshot mock-06-fixed-v1](../../examples/remediation/06-filter-pagination/fixed/). Kiểm tra lại cùng assertions trên head lỗi và bản sửa cho kết quả phân biệt đúng. Requirement whitespace vẫn chưa rõ: verification tổng thể **incomplete**, không có approval thật.

Hành động còn mở: Product/domain owner chốt nghĩa whitespace và developer thêm check sau khi requirement được xác nhận; Reviewer/TL đối chiếu evidence của fixed trước quyết định tiếp. Đây là vai trò đề xuất, người nhận thật unknown. Hai lỗi đã sửa không còn là hành động sửa code đang mở trong snapshot này.

Risk medium trong mô phỏng: UI state và API cache qua nhiều request, có thể hiển thị sai/rỗng; catalog public giả lập, phạm vi nhỏ, dễ revert. Giữ checks chuyển category từ page=3 và cache chung qua category. Không xét invalid inputs, TTL, concurrency, response mutation, auth hoặc triển khai thật.

## Đọc kết quả mà không cần đọc log test

Một test là một phép kiểm tra có kết quả mong đợi cụ thể. `pass` nghĩa kết quả khớp mong đợi ở những tình huống đã kiểm tra; không chứng minh mọi tình huống đều đúng. `fail` nghĩa một assertion không khớp. `error` nghĩa check không thực hiện bình thường, ví dụ lỗi import; `skipped` nghĩa check bị bỏ qua.

| Nhóm kiểm tra | Bản lỗi gốc | Bản sửa | Ý nghĩa |
|---|---|---|---|
| 6 kiểm tra cơ bản — baseline | Đều đạt | Đều đạt | Chức năng đã được kiểm tra trước đó vẫn hoạt động; nhóm này từng bỏ sót hai lỗi |
| 1 kiểm tra cũ — historical | Không đạt | Đạt | Đổi category từ trang 3 đã đưa màn hình về trang 1 |
| 2 kiểm tra bổ sung — probe | Đều không đạt | Đều đạt | Request dùng trang 1 sau đổi filter và cache không lẫn books/tools |

Historical và một probe cùng kiểm tra lỗi reset: ba test không đạt ở bản gốc chỉ tương ứng **hai lỗi**, không phải ba lỗi. Hai bản đều không có error hoặc skipped. Runner báo `MATCH`/exit 0 khi kết quả đúng thiết kế trên từng bản, kể cả failure cố ý ở bản gốc.

Để xem một chuỗi bằng chứng: đọc AC-03 trong [requirement](../../examples/mock/06-filter-pagination/requirements.md), rồi `Probe.test_cache_across_categories` trong [test bổ sung](../../examples/mock/06-filter-pagination/expected/test_probe.py). Trong [execution](../../examples/remediation/06-filter-pagination/execution.local.json), tìm `snapshot` là `mock-06-fixed-v1` và `module` là `test_probe`: `tests: 2`, `failures: []`, `errors: []`, `skipped: 0` nghĩa cả hai probe đã chạy và đạt. Đối chiếu với nhóm cùng tên ở `mock-06-head-v1` để thấy failure cũ. Hash ghi lại nội dung các file đã chạy, không phải approval.

## Thứ tự việc tiếp theo và điều kiện xong

| Thứ tự | Công việc / vai trò đề xuất | Điều kiện hoàn thành |
|---|---|---|
| 1 — làm ngay | Người dùng đọc phần giải thích trên, thử diễn giải kết quả và chỉ ra bước còn mở | Ghi phản hồi thực tế; nếu còn khó hiểu thì sửa cách trình bày. Chưa coi G1 đạt chỉ vì đã sửa tài liệu |
| 2 — trước khi sửa behavior whitespace | Người đặt yêu cầu chọn nghĩa cho `"   "` và `" books "` trong một version requirement synthetic mới | Mỗi input có expected behavior rõ, ghi quyết định là lựa chọn cho mock; không giả làm xác nhận của owner hệ thống thật |
| 3 — sau bước 2 | Developer tạo snapshot mới, bổ sung check rồi sửa code nếu requirement mới đòi hỏi | Check mới đạt, 9 check hiện có vẫn đạt, có execution/hash mới; snapshot/requirement/evidence cũ giữ nguyên |
| 4 — sau bước 3 | Reviewer đối chiếu từng yêu cầu với evidence mới và ghi quyết định | Không còn AC bắt buộc chưa kiểm chứng thì mới ghi verification complete trong scope; human decision vẫn cần ghi riêng |

Các vai trò trên chưa có người nhận thật. Hiện **bước 1 đang mở**; bước 2 chưa được quyết định, bước 3–4 chưa thực hiện. Không cần sửa thêm hai lỗi đã được kiểm chứng để hoàn thành bước 1.

## Evidence mới

Requirement [mock-req-06-v1](../../examples/mock/06-filter-pagination/requirements.md) giữ nguyên. [API sửa](../../examples/remediation/06-filter-pagination/fixed/api.py) dùng `(category, page, page_size)`; [UI sửa](../../examples/remediation/06-filter-pagination/fixed/ui.py) reset trước request. Data/service không thay đổi.

Lệnh đã chạy từ root repo trên Python 3.14.8:

```text
py -3 -X utf8 -B examples/remediation/06-filter-pagination/run.py
py -3 -X utf8 -B examples/mock/run.py
```

Cả hai exit 0. [Execution mới](../../examples/remediation/06-filter-pagination/execution.local.json) lưu SHA-256 input và kết quả thực chạy, không sử dụng CI input giả lập để xác nhận bản sửa.

| Snapshot | Baseline | Historical | Probe | Errors/skipped |
|---|---|---|---|---|
| mock-06-head-v1 | 6 pass | 1 fail | 2 fail | 0/0 |
| mock-06-fixed-v1 | 6 pass | 1 pass | 2 pass | 0/0 |

Hai assertion failures ở probe gốc xác nhận request reset vẫn page=3 và category tools nhận items books. Historical fail cũng thuộc cùng defect reset, không phải issue thứ ba. Trên bản sửa, probe reset xác nhận request `('tools', 1, 2)`; historical xác nhận view.page=1 và items T1/T2; probe cache xác nhận books B1/B2 rồi tools T1/T2, total=2 trên cùng instance.

Đường truy assertion (execution JSON phân biệt bằng `snapshot`, `module`):

- AC-02: [Historical.test_reset_from_third_page](../../examples/mock/06-filter-pagination/tests/test_historical.py) và [Probe.test_reset_with_recorded_api_call](../../examples/mock/06-filter-pagination/expected/test_probe.py).
- AC-03: [Probe.test_cache_across_categories](../../examples/mock/06-filter-pagination/expected/test_probe.py).
- AC-01/04 và phần chuỗi rỗng của AC-05: [Baseline](../../examples/mock/06-filter-pagination/tests/test_baseline.py), lần lượt `test_service_category_and_case`, `test_service_pagination_and_out_of_range`/`test_api_page_and_size`, `test_empty_category`. Phạm vi assertion vẫn giới hạn ở input được test.

## Trạng thái và hành động

| AC | Trước sửa | Sau sửa / nguồn | Hành động / vai trò |
|---|---|---|---|
| AC-01 | verified trong scope service | verified; baseline category/case, service giữ nguyên | Reviewer giữ evidence trong scope |
| AC-02 | failed, F-06-01 | verified trong mock; historical + recording probe trên fixed | Reviewer đối chiếu evidence mới |
| AC-03 | failed, F-06-02 | verified trong mock; category sequence probe + cache key mới | Reviewer đối chiếu evidence mới |
| AC-04 | verified trong scope category cố định | verified trong scope; baseline pagination/page/size | Không mở rộng claim ngoài assertions/source |
| AC-05 | unverified một phần | vẫn unverified tổng thể; chuỗi rỗng được baseline kiểm chứng | Product/domain owner chốt whitespace trước khi thêm requirement/test |

F-06-01/02: defect confirmed trong mock, đã sửa và targeted checks pass tại fixed; không gán verdict reviewer độc lập. Evidence cũ tại base/head lỗi không được dùng để verify fixed. Owner/người nhận thật chưa xác định.

## Giới hạn và bước tiếp

MOCK-01–05 vẫn khớp manifest, kể cả failure cố ý. Fixture MOCK-06 gốc và evidence đã commit được giữ nguyên. Đây là 18 lượt thực thi test trên hai snapshot, không phải 18 behavior độc lập hay phép đo recall.

Chưa đo effort/cost, usefulness, giảm defect hoặc lợi ích hơn review hiện tại. [Phản hồi qua câu hỏi có gợi ý](../../docs/REVIEWER-CHECK.md) cho thấy người dùng còn khó đọc kết quả test và cần thứ tự công việc/điều kiện hoàn thành. Phần hướng dẫn trên được bổ sung sau phản hồi, chưa được thử lại. G1 vẫn chưa xác nhận; không xây automation để bù thiếu evidence.
