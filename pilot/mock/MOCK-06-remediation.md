# MOCK-06 — Kiểm chứng sau sửa

Ngày 04/11/2026. Synthetic-only, walkthrough đã biết đáp án; người chuẩn bị là trợ lý, reviewer/domain owner thật unknown. Human decision pending. Commit nền `9bc27f6`; nhãn snapshot không phải Git SHA.

## Kết luận và phạm vi

Hai defect trong [hồ sơ gốc](MOCK-06-review.md) được sửa tại [snapshot mock-06-fixed-v1](../../examples/remediation/06-filter-pagination/fixed/). Kiểm tra lại cùng assertions trên head lỗi và bản sửa cho kết quả phân biệt đúng. Requirement whitespace vẫn chưa rõ: verification tổng thể **incomplete**, không có approval thật.

Hành động còn mở: Product/domain owner chốt nghĩa whitespace và developer thêm check sau khi requirement được xác nhận; Reviewer/TL đối chiếu evidence của fixed trước quyết định tiếp. Đây là vai trò đề xuất, người nhận thật unknown. Hai lỗi đã sửa không còn là hành động sửa code đang mở trong snapshot này.

Risk medium trong mô phỏng: UI state và API cache qua nhiều request, có thể hiển thị sai/rỗng; catalog public giả lập, phạm vi nhỏ, dễ revert. Giữ checks chuyển category từ page=3 và cache chung qua category. Không xét invalid inputs, TTL, concurrency, response mutation, auth hoặc triển khai thật.

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

Chưa đo effort/cost, usefulness, giảm defect hoặc lợi ích hơn review hiện tại. G1 với reviewer thật pending. Bước tiếp: người dùng rà khả năng truy claim và tính hữu ích của action trong hồ sơ, rồi giản lược core/template nếu có trường thừa; không xây automation để bù thiếu evidence.
