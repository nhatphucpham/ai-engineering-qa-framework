# MOCK-07 — Giảm giá đúng ngưỡng và phí giao hàng

Synthetic-only, ví dụ đã biết đáp án để thử lại cách trình bày hồ sơ trên domain khác; không phải holdout/blind evaluation. [Requirement](requirements.md) do tác giả đặt cho bài tập. [Hồ sơ đọc nhanh](../../../pilot/mock/MOCK-07-review.md) giải thích hai lỗi ngay tại chỗ.

Từ root repo, Python 3.10+:

```sh
python3 -B examples/mock/07-order-discount/run.py
```

Windows có thể dùng `py -3 -X utf8 -B` thay `python3 -B`.

Runner riêng chạy cùng 2 baseline và 2 probe trên head/fixed. Head: baseline 2 pass, probe 2 fail; fixed: cả 4 pass. Exit 0 nghĩa outcome khớp thiết kế, không phải tất cả test pass hoặc approval. Errors/skipped hoặc failure ID ngoài dự kiến làm runner exit 1.

Chạy lại ghi đè `execution.local.json` trong case này, gồm hashes input, timestamp, Python version và traceback. Không dùng CI input giả lập. Không cần network, model, thư viện ngoài hoặc thanh toán thật. Runner/mock manifest cũ không thay đổi và không tự chạy case 07.
