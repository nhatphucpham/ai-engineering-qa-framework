# MOCK-06 — Snapshot sửa riêng

Synthetic-only, đã biết đáp án. Không thay đổi [fixture gốc](../../mock/06-filter-pagination/README.md). Snapshot mới `mock-06-fixed-v1` dùng nguyên [requirement v1](../../mock/06-filter-pagination/requirements.md).

Hai thay đổi so với head gốc: thêm category vào cache key; reset page=1 trước khi UI gọi API. Data/service giữ nguyên. Whitespace chưa được owner xác nhận và không được thay đổi.

Từ root repo, Python 3.10+ và standard library:

```sh
python3 -B examples/remediation/06-filter-pagination/run.py
```

Windows có thể dùng `py -3 -X utf8 -B` thay `python3 -B`.

Runner chạy baseline (6), historical (1), probe (2) của fixture gốc trên hai snapshot, trong process riêng cho mỗi suite. Head gốc: baseline pass, historical 1 fail, probe 2 fail. Fixed: cả 9 pass. Exit 0 nghĩa kết quả khớp thiết kế, không phải approval.

Runner ghi đè `execution.local.json` chỉ trong thư mục remediation này. File chứa thời điểm UTC, Python version, hashes của code/requirement/assertions/runner và execution thực tế gồm traceback. Không ghi đè evidence gốc. Chạy lại sẽ đổi timestamp và có thể đổi đường dẫn trong traceback; xem diff trước khi lưu.

Xem [hồ sơ sau sửa](../../../pilot/mock/MOCK-06-remediation.md). Không có browser/HTTP/model call, CI thật, blind evaluation hoặc đo usefulness.
