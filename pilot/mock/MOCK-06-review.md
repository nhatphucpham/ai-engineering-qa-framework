# Review MOCK-06 — Đổi filter qua nhiều lớp code

Ngày 03/11/2026. **Synthetic-only; walkthrough đã biết đáp án**, cùng session tạo case và review. Không phải đánh giá mù, tự phát hiện defect chưa biết, human adjudication hoặc approval. Người chuẩn bị: trợ lý. Reviewer/owner thật, budget và human effort: unknown. Human decision: pending.

## Kết luận đọc nhanh

Suite hiện tại có **6 test xanh ở head**, nhưng hai hành vi sai được tái hiện: UI giữ trang 3 sau đổi filter, và API cache trả dữ liệu books cho request tools. Một yêu cầu whitespace chưa rõ nên cần owner chốt. Đề nghị sửa hai lỗi trên revision riêng, bổ sung regression checks và làm rõ requirement trước khi review tiếp. Fixture gốc giữ nguyên bug.

Giá trị minh họa so với MOCK-02: cần theo dõi state qua nhiều lớp và nhiều request, phân biệt evidence cũ với head, tách ambiguity khỏi defect, và giữ phần có evidence đủ. Chưa đo được giá trị tăng thêm với reviewer thật.

## Phạm vi, input và provenance

Requirement [mock-req-06-v1](../../examples/mock/06-filter-pagination/requirements.md). Snapshot `mock-06-base-v1` → `mock-06-head-v1` là nhãn local. Case được tạo mới trên checkout nền `063d25f`, sau đó được commit/push trong `5c65446`; Git SHA nền chưa chứa MOCK-06. [Execution local](../../examples/mock/06-filter-pagination/execution.local.json) ghi SHA-256 của code, requirement, diff, input evidence, tests và runner để xác định đúng nội dung đã chạy.

Đã đọc requirement, [diff](../../examples/mock/06-filter-pagination/change.diff), cả base/head của data/service/api/ui, [baseline](../../examples/mock/06-filter-pagination/tests/test_baseline.py), [historical test](../../examples/mock/06-filter-pagination/tests/test_historical.py), [CI input giả lập](../../examples/mock/06-filter-pagination/evidence.mock.json), [probe](../../examples/mock/06-filter-pagination/expected/test_probe.py), [đáp án thiết kế](../../examples/mock/06-filter-pagination/expected/quality-record.md) và runner. Không có nguồn ẩn/ngoài repo.

Luồng: `CatalogView.select_category` → `CatalogAPI.get_items` → cache hoặc `list_items` → catalog 8 item. Đây là lời gọi Python trong process, không có HTTP/browser/database thật. Risk medium: sai danh sách hoặc trang qua state/cache, phạm vi giả lập hẹp và revert dễ. Không đánh giá auth, TTL, concurrency, mutation response hoặc invalid inputs ngoài scope.

## A. Tái dựng trạng thái với input ban đầu và baseline

Đây là trình bày trước/sau có chủ đích, không phải nhận định mù đã đăng ký trước. CI-HEAD khai báo 6 pass tại head; CI-OLD-RESET khai báo reset pass **tại base**. Hai bản ghi JSON đều do tác giả soạn. Execution local sau đó xác nhận baseline head thực sự 6 pass; check reset cũ phải được chạy lại ở head.

| AC / nguồn requirement v1 | Evidence ban đầu và source head | Trạng thái trước kiểm tra bổ sung | Action |
|---|---|---|---|
| AC-01: service lọc chính xác | `Baseline.test_service_category_and_case` assert tools/T1,T2/total=2 và Tools/total=0; [service](../../examples/mock/06-filter-pagination/head/service.py) so khớp category chính xác | verified trong scope service bằng baseline local + source | Không tạo finding cho phần này |
| AC-02: UI reset về trang 1 | Baseline UI chỉ bắt đầu ở page=1; CI reset ở base. [UI head](../../examples/mock/06-filter-pagination/head/ui.py) bỏ reset trong diff | unverified theo evidence baseline; source gợi ý regression có thể tái hiện | Rerun historical check ở head, ghi request thực tới API |
| AC-03: cache phân biệt category/page/size | Baseline chỉ lặp cùng category hoặc đổi page/size; [API head](../../examples/mock/06-filter-pagination/head/api.py) key chỉ có page/size | unverified theo baseline; key thiếu category là candidate defect từ source | Chạy books rồi tools, cùng API instance/page/size |
| AC-04: pagination ổn định | `test_service_pagination_and_out_of_range`, `test_api_page_and_size`, service slice giữ thứ tự | verified cho catalog cố định và cùng category, bằng source + baseline | Không mở rộng claim sang cache mixed-category ở AC-03 |
| AC-05: category trống | `test_empty_category` xác nhận chuỗi rỗng cho total=8; requirement chưa chốt whitespace | unverified toàn AC; phần `""` verified | Hỏi owner; chưa tạo assertion cho whitespace theo ý người review |

Hai dòng unverified không có nghĩa source không đủ để nghi ngờ lỗi. Bảng này giới hạn trạng thái ban đầu theo baseline; reproduction bên dưới cung cấp expected/actual cụ thể. Comment “giữ state/all checks green” không thay thế requirement AC-02 hoặc evidence đúng revision.

## B. Kiểm tra đã chạy và kết quả

Từ root repo:

```sh
python3 -B examples/mock/06-filter-pagination/run.py
python3 -B examples/mock/run.py
```

Cả hai lệnh exit **0**. Lệnh đầu ghi [execution.local.json](../../examples/mock/06-filter-pagination/execution.local.json), gồm traceback, Python version và hash input; lệnh sau xác nhận MOCK-01–05 còn khớp thiết kế. Không có dependency ngoài standard library hoặc network/model call.

| Snapshot | Check | Tests | Failures | Errors / skipped | Ý nghĩa |
|---|---|---:|---:|---|---|
| base | baseline | 6 | 0 | 0 / 0 | Đối chứng scope kiểm tra cơ bản |
| base | historical | 1 | 0 | 0 / 0 | Reset từng đúng tại base |
| base | probe | 2 | 0 | 0 / 0 | Cùng check bổ sung pass trên base |
| head | baseline | 6 | 0 | 0 / 0 | Suite xanh nhưng bỏ sót hai sequence |
| head | historical | 1 | 1 | 0 / 0 | Reset hiện tại sai, evidence cũ không verify head |
| head | probe | 2 | 2 | 0 / 0 | Hai defect được tái hiện riêng biệt |

Runner so cả ID của test fail với thiết kế; import error/failure sai chỗ không được tính là match. Exit 0 xác nhận fixture có đúng behavior thiết kế, không phải approval hoặc tất cả assertion pass.

## C. Finding và trạng thái sau kiểm tra

**F-06-01 — Defect reset pagination, confirmed trong mock, severity medium.** Nguồn: AC-02, diff bỏ `self.page = 1`, [UI head](../../examples/mock/06-filter-pagination/head/ui.py), `Historical.test_reset_from_third_page` và `Probe.test_reset_with_recorded_api_call`. Khởi tạo view books/page=3 với API mới, chọn tools. Expected UI/page và API request page=1; actual UI page=3 và request `('tools', 3, 2)`. Danh sách tools tại trang đó rỗng thay vì T1/T2. Historical assertion và probe fail là hai bằng chứng của **cùng một defect**, không đếm hai finding.

**F-06-02 — Defect cache thiếu category, confirmed trong mock, severity medium.** Nguồn: AC-03, [API head](../../examples/mock/06-filter-pagination/head/api.py), `Probe.test_cache_across_categories`. Dùng cùng `CatalogAPI`, gọi books/page=1/size=2 rồi tools/page=1/size=2. Expected request thứ hai T1/T2 và total=2; actual items B1/B2 (response books từ cache, total=6). Check dừng ở assertion items đầu tiên; total=6 còn được xác định từ source/cached response, không mô tả là assertion total đã chạy pass/fail. Probe dùng API trực tiếp nên lỗi này độc lập với lỗi UI reset.

**A-06-01 — Requirement ambiguity, pending owner.** Nguồn: AC-05. Câu hỏi: chuỗi `"   "` có nghĩa tất cả, không khớp category nào hay input invalid? Có trim khoảng trắng hai đầu không? Requirement chưa xác nhận; không gán source hiện tại là defect whitespace. Sau khi owner chốt mới version requirement và thêm check.

**O-06-01 — Evidence cũ, observation trong mock.** CI-OLD-RESET dùng `mock-06-base-v1`; chạy lại test đó ở head fail. Cần evidence mới tại revision sửa. Không suy rằng reviewer thật đã bỏ sót, không cộng thành defect thứ ba.

| AC | Sau kiểm tra | Evidence / hành động |
|---|---|---|
| AC-01 | verified trong scope service | Baseline + source; giữ evidence có sẵn |
| AC-02 | failed | F-06-01; developer sửa reset trước gọi API, thêm regression ở head mới |
| AC-03 | failed | F-06-02; developer đưa category vào cache key, thêm sequence test |
| AC-04 | verified trong scope đã ghi | Baseline + source; cache mixed-category vẫn failed ở AC-03 |
| AC-05 | unverified; phần chuỗi rỗng verified | Owner chốt whitespace; không tự chọn expected behavior |

Verification tổng thể: **failed, đồng thời còn phần requirement chưa kiểm chứng**. Hai defect unique, một ambiguity; không quy thành finding validity/recall hay hiệu quả reviewer. Chưa có verdict từ người thật.

## D. Hành động và giới hạn

| Bước tiếp theo đề xuất | Vai trò xử lý | Trạng thái |
|---|---|---|
| Sửa reset UI và cache key ở snapshot riêng; giữ nguyên fixture lỗi | Developer | Chưa thực hiện; người nhận thật unknown |
| Giữ baseline, thêm hai regression sequence và rerun historical tại revision mới | Developer / người chuẩn bị evidence | Chưa có revision sửa |
| Chốt whitespace, cập nhật requirement/version và check tương ứng | Product/domain owner | pending; owner thật unknown |
| Đọc evidence mới, quyết định tiếp tục review theo quy trình | Reviewer/TL | Human decision pending |

Các failure chỉ chứng minh behavior của case được tạo sẵn. Chưa đo reviewer usefulness, effort/cost, false positives, khả năng tìm lỗi mới, hiệu quả hơn manual review hoặc hệ thống triển khai thực tế. Rủi ro thực tế của cache/tenant không nằm trong dataset này.

S1 có [core v0](../../docs/CORE-FRAMEWORK.md) và luồng đi từ input → check → action, chưa qua G1 với reviewer thật. Can thiệp nhỏ còn hợp lý: mapping AC/evidence + targeted sequence checks, chưa xây generic CLI/AI verifier. Bước review tài liệu có thể bắt đầu bằng câu hỏi: từng kết luận có nguồn đủ rõ và action có giúp người đọc quyết định tiếp không?
