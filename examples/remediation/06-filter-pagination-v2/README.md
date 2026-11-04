# MOCK-06 v2 — Làm rõ và kiểm chứng dấu cách

Synthetic-only. Người dùng đã chọn hai quy tắc cho ví dụ: chuỗi toàn dấu cách hiển thị tất cả; `" books "` tìm books sau khi bỏ dấu cách hai đầu. Xem [requirement v2](requirements.md) và [hồ sơ kết quả](../../../pilot/mock/MOCK-06-v2.md).

Từ root repo, Python 3.10+:

```sh
python3 -B examples/remediation/06-filter-pagination-v2/run.py
```

Windows: thay `python3 -B` bằng `py -3 -X utf8 -B`.

Runner dùng lại 9 assertions cũ và [4 test mới](tests/test_whitespace.py) trên hai snapshot: fixed-v1 và fixed-v2. V1 pass 9 test cũ, fail 4 test mới vì chưa xử lý dấu cách. V2 pass cả 13. Runner exit 0 khi kết quả đúng thiết kế trên cả hai bản; không phải approval.

Kết quả/hash input được ghi vào `execution.local.json` trong thư mục này; chạy lại thay timestamp và có thể thay đường dẫn traceback. Evidence v1 và fixture gốc không bị ghi đè. Không cần dependency ngoài standard library, mạng, model, browser hoặc hệ thống thật.
