# Bộ mẫu thử synthetic, chạy offline

Toàn bộ requirement, code, revision ID, review và CI evidence ở đây được tạo mới để minh họa. Không chứa dữ liệu task thật, không cần tài khoản, model, network hay dependency ngoài Python 3.10+. Python chỉ dùng chạy fixtures; chưa chốt stack sản phẩm.

## Các mẫu

| Mẫu | Điều cần kiểm tra | Kết luận mong đợi |
|---|---|---|
| [01 — Đủ evidence](01-complete/expected/quality-record.md) | Hai AC cụ thể đều có targeted checks ở đúng snapshot | Verified trong phạm vi toy; không tạo finding giả |
| [02 — Test xanh, thiếu behavior](02-missing-behavior/expected/quality-record.md) | Baseline chỉ test filtering, bỏ reset pagination | Ban đầu unverified; probe tái hiện lỗi thì failed |
| [03 — Requirement mơ hồ](03-ambiguous/expected/quality-record.md) | “Không được để tên trống” chưa định nghĩa whitespace | Hỏi owner; chưa được gọi behavior whitespace là defect |
| [04 — Evidence cũ](04-stale-evidence/expected/quality-record.md) | Baseline pass ở snapshot trước, head đã có regression | Không verify head bằng evidence cũ; probe head thì failed |
| [05 — Thiếu human review](05-pending-review/expected/quality-record.md) | Toy authorization checks pass nhưng review bắt buộc còn pending | Behavior được kiểm chứng hẹp; verification tổng thể incomplete |
| [06 — UI state, API, cache và service](06-filter-pagination/README.md) | Review nhiều file: sequence checks, evidence cũ và requirement mơ hồ | Baseline xanh chưa đủ; xem hồ sơ riêng và kết quả execution local |

## Cách dùng

Các bước và runner ngay dưới áp dụng cho MOCK-01–05. MOCK-06 có hai thư mục snapshot, test suite và runner riêng; xem [hướng dẫn MOCK-06](06-filter-pagination/README.md) và [hồ sơ review](../../pilot/mock/MOCK-06-review.md).

1. Chọn một folder, chỉ đọc `requirements.md`, `before.py`, `after.py`, `change.diff`, `test_baseline.py`, `evidence.mock.json` trước.
2. Điền [hồ sơ kiểm chứng](../../templates/quality-record.md): claim nào có evidence, cần thêm check gì, hành động của ai? `evidence.mock.json` là CI input được giả lập, chưa phải execution log thật.
3. Sau khi chốt nhận định ban đầu, mở `expected/quality-record.md` và `expected/test_probe.py` nếu có. Đây là đáp án và probe thiết kế sẵn; không đưa chúng cho một verifier đang được đánh giá.
4. Chạy lại code toy và các probe bằng lệnh dưới. Kết quả baseline/probe quan sát được trên máy tách biệt với input CI giả lập.

Từ root repo:

```sh
python3 -B examples/mock/run.py
```

Runner kiểm tra diff khớp snapshots, chạy baseline/probe cục bộ và so số test/failure/error/skipped với manifest. Case 02 và 04 **cố ý có một assertion failure ở probe**. Exit 0 nghĩa fixtures có đúng behavior thiết kế, không có nghĩa tất cả task đạt quality. Một error hoặc failure ngoài dự kiến làm runner exit 1. Runner không đọc/đánh giá hồ sơ Markdown và không tự tìm bug.

Xem [kết quả chạy local đã ghi nhận](RESULTS.md).

Để chạy riêng probe ở case 02:

```sh
cd examples/mock/02-missing-behavior
python3 -B -m unittest -v expected.test_probe
```

Lệnh riêng này cố ý exit 1 do reset pagination sai. Không sửa bug trong fixture chỉ để làm test xanh; cần giữ case lỗi để kiểm tra verifier tương lai.

Các snapshot ID `mock-...` là nhãn local do tác giả đặt, không phải Git SHA hay bằng chứng provenance đáng tin của hệ thống thật. Case 04 cố ý không khớp head. Mapping AC/test trong mock có thể đối chiếu assertion trong source; không giả định mapping tự khai báo là đủ evidence trong sản phẩm thật.

## Phạm vi kết luận

- Đây là walkthrough/fixture đã biết đáp án; chưa phải blind evaluation, human adjudication hay pilot thực tế.
- Có thể kiểm tra semantics trạng thái và cơ chế toy. Chưa đo được hiệu quả reviewer, khả năng phát hiện lỗi mới, bảo mật của hệ thống thật, false-positive rate hay ROI.
- Không có human approval thật, cost/review-time thật hoặc provider AI. Những trường chưa đo là unknown.
- Thử nghiệm với task thật chỉ diễn ra trong môi trường bảo mật do người dùng quản lý. Không đưa code/log/trace/task thật vào repo này. Kết quả thật chỉ chia sẻ nếu người dùng chủ động chọn thông tin được phép công bố; bộ mẫu không phụ thuộc việc chia sẻ đó.
