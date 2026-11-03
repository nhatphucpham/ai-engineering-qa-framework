# MOCK-06 — Một thay đổi đi qua UI state, API và cache

Đây là case synthetic nhiều file, chạy hoàn toàn trong process bằng Python standard library. `api.py` mô phỏng API bằng lời gọi hàm; `ui.py` mô phỏng state, không có HTTP server hoặc browser thật. Case tạo mới trong session S1; người viết walkthrough đã biết đáp án.

## Bắt đầu từ đâu?

Đọc [hồ sơ review dễ theo dõi](../../../pilot/mock/MOCK-06-review.md) để xem kết luận và hành động. Để xem quy trình tổng quát, đọc [core framework](../../../docs/CORE-FRAMEWORK.md).

Luồng ứng dụng: người dùng chọn category → `CatalogView` cập nhật state → `CatalogAPI` lấy cache hoặc gọi `list_items` → trả items/total/page. Dữ liệu chỉ là 8 item giả trong `data.py`.

| Input để review | Nội dung |
|---|---|
| [requirements.md](requirements.md) | 5 AC, scope và phần owner chưa chốt |
| [base/](base/api.py) và [head/](head/api.py) | Mỗi snapshot có `data.py`, `service.py`, `api.py`, `ui.py` |
| [change.diff](change.diff) | Diff thực giữa hai snapshot |
| [test_baseline.py](tests/test_baseline.py) | Suite hiện tại |
| [test_historical.py](tests/test_historical.py) | Check cũ có thể chạy lại, cần đối chiếu revision |
| [evidence.mock.json](evidence.mock.json) | CI/review input do tác giả soạn, không phải execution log thật |

Nếu tổ chức lượt review riêng, chỉ cấp requirements, base/head, diff, tests và evidence mock. Chưa cấp `expected/`, `run.py`, `execution.local.json` hoặc hồ sơ walkthrough vì chúng tiết lộ đáp án. Session hiện tại đã biết đáp án; tách file chỉ hỗ trợ lượt review sau, không làm session này trở thành đánh giá mù.

## Chạy suite ban đầu mà chưa mở đáp án

Từ thư mục case:

```sh
cd examples/mock/06-filter-pagination
PYTHONPATH=head python3 -B -m unittest discover -s tests -p test_baseline.py -v
```

Thay `-p test_baseline.py` bằng `-p test_historical.py` để chạy lại check cũ tại head; thay `PYTHONPATH=head` bằng `PYTHONPATH=base` để đối chiếu base. Các lệnh unittest trả exit 1 khi assertion sai, không chuyển failure thành pass.

## Kiểm tra toàn bộ fixture và xem đáp án

Từ root repo, chỉ cần Python 3.10+:

```sh
python3 -B examples/mock/06-filter-pagination/run.py
```

Runner riêng của MOCK-06 kiểm tra diff và các test tại cả base/head trong process tách biệt. Nó so cả test ID bị fail, số tests, errors và skipped với kết quả thiết kế, rồi ghi [execution.local.json](execution.local.json): thời điểm UTC, Python version, SHA-256 của input/code/test/runner và traceback thực tế. Chạy lại sẽ cập nhật file này. Hash giúp phát hiện thay đổi file local, không phải chữ ký hay provenance của CI thật.

Runner exit 0 nghĩa fixture khớp thiết kế, có cả failure cố ý. Một lỗi/reset UI được tái hiện bởi hai checks không được đếm thành hai defect. Xem [đáp án](expected/quality-record.md) và [probe](expected/test_probe.py) sau bước review ban đầu. Không sửa head để làm hết failure trong fixture; nhánh sửa cần snapshot và evidence mới.

Runner cũ `python3 -B examples/mock/run.py` vẫn chạy MOCK-01–05, chưa bao gồm MOCK-06. Hai lệnh cùng nhau kiểm tra cả bộ hiện tại; chưa có CLI hoặc verifier chung.
