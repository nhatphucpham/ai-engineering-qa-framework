# Kết quả chạy bộ mẫu synthetic

Chạy ngày 03/11/2026 bằng Python 3.12.14:

```sh
python3 -B examples/mock/run.py
```

| Mẫu | Baseline chạy local | Probe chạy local | Kết quả so với thiết kế |
|---|---|---|---|
| MOCK-01 | 2 pass, head | 1 pass, head | Khớp |
| MOCK-02 | 2 pass, head | 1 failure: page=3 thay vì 1 | Khớp bug cố ý |
| MOCK-03 | 2 pass, head | Không có oracle whitespace nên không đặt pass/fail | Khớp |
| MOCK-04 | 2 pass, **base** | 1 failure ở head: cho reserve quá stock | Khớp bug cố ý |
| MOCK-05 | 2 pass, head | 1 pass, head | Khớp; approval vẫn pending |

Tổng cộng 14 test methods, 12 pass, 2 failure được chủ đích thiết kế; không có error/skipped. Tất cả 5 diff khớp source snapshots. Runner exit 0 vì số lượng test và kết quả khớp manifest.

Đây là execution trên source synthetic trong repo, tách biệt với CI input được tác giả giả lập trong `evidence.mock.json`. Hồ sơ kết luận là đáp án viết sẵn, không phải output do framework/AI verifier sinh hoặc người dùng adjudicate. Chưa đo effort review, cost, hiệu quả hay độ an toàn của hệ thống thật.
