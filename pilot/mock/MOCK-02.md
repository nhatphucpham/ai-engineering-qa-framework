# Walkthrough MOCK-02 — Suite xanh, thiếu reset pagination

Loại dữ liệu: **synthetic/mock**, case thiết kế đã biết đáp án và probe có sẵn. Không phải blind evaluation, tự phát hiện lỗi mới hoặc human adjudication. Người chuẩn bị: trợ lý thực hiện walkthrough. Reviewer thật: unknown. Human decision: pending. Effort thực tế và cost: unknown.

Nguồn phiên bản: commit nền `063d25f0577d7bcbbba534073bc5b8dcc3cd8976`; head `mock-02-head` là nhãn toy. Requirement [mock-req-02-v1](../../examples/mock/02-missing-behavior/requirements.md). Liên hệ [pilot brief](../../docs/PILOT-BRIEF.md).

## Mục tiêu và risk

Áp filter phân biệt hoa thường, giữ row chứa query và reset page về 1 mỗi lần filter. Rows là list string, query không rỗng, page là số nguyên dương. [Diff](../../examples/mock/02-missing-behavior/change.diff) thêm filtering từ [before](../../examples/mock/02-missing-behavior/before.py) sang [after](../../examples/mock/02-missing-behavior/after.py) nhưng giữ page đầu vào.

Risk medium theo requirement mock vì thay đổi state có thể giữ sai trang khi đổi filter; phạm vi chỉ là dictionary của hàm toy, sửa/revert cục bộ dễ. Không kết luận về UI/router/backend thật. Check cần thiết: rows lọc đúng và state từ page khác 1 được reset.

## Trạng thái từ input ban đầu

Đây là tái dựng trạng thái trước probe khi đáp án đã được biết. [CI input giả lập](../../examples/mock/02-missing-behavior/evidence.mock.json) khai báo 2 test pass tại `mock-02-head`, mapping AC-02 rỗng. [Baseline](../../examples/mock/02-missing-behavior/test_baseline.py) chỉ assert rows và cả hai input dùng page=1; nó không kiểm chứng reset.

| AC | Expected behavior / nguồn | Evidence tại head | Trạng thái ban đầu | Gap / action / owner đề xuất |
|---|---|---|---|---|
| AC-01 | Requirement v1: chỉ row chứa query, phân biệt hoa thường | `test_matching_rows`, `test_no_matches` kiểm tra kết quả rows; source dùng `query in row`, case-sensitive | verified trong phạm vi toy bằng source và assertion; không có targeted test riêng cho hoa/thường | Không có gap được xác định trong scope này; có giới hạn test ví dụ |
| AC-02 | Requirement v1: mỗi lần filter page → 1 | Không có assertion page; source trả page không đổi là dấu hiệu kiểm tra tiếp | unverified khi chỉ xét baseline; suite pass không verify AC này | G-02 verification gap: chạy check từ page=3; người chuẩn bị hồ sơ/developer đề xuất |

Source đủ gợi ý vấn đề nhưng luồng này ghi G-02 ở bước evidence baseline rồi tái hiện bằng probe; không giả vờ chưa biết source hoặc đáp án.

## Sau probe và cách lặp lại

Từ root repo:

```sh
python3 -B examples/mock/run.py
```

Quan sát ngày 03/11/2026 trên file ở commit nền: baseline 2 tests pass, 0 failures/errors/skipped. [Probe](../../examples/mock/02-missing-behavior/expected/test_probe.py) `test_resets_page` gọi `apply_filter(['alpha', 'beta'], 'alpha', 3)` và assert page=1. Actual page=3; `AssertionError: 3 != 1`. Probe: 1 test, 1 failure, 0 errors, 0 skipped. Diff khớp snapshots; runner toàn bộ exit 0 vì kết quả này khớp manifest.

Có thể chạy riêng từ root:

```sh
(cd examples/mock/02-missing-behavior && python3 -B -m unittest -v expected.test_probe)
```

Lệnh riêng dự kiến exit 1 do assertion failure có chủ đích; kết quả quan sát ở đây lấy từ runner toàn bộ, không giả lập một lần chạy riêng.

| AC | Sau probe | Thay đổi / hành động |
|---|---|---|
| AC-01 | verified trong phạm vi toy | Không có behavior mới được probe này kiểm tra |
| AC-02 | failed | Đã có reproduction: expected 1, actual 3; đề xuất developer sửa reset state ở revision mới và thêm regression check |

## Finding và quyết định

G-02 là verification gap trước probe. F-02 là defect behavior sau reproduction, **confirmed trong mock**, severity medium vì vi phạm AC-02 về state. Nguồn: requirement v1 AC-02, `after.py` trả `"page": page`, và assertion trong probe. G-02/F-02 mô tả cùng behavior qua hai thời điểm, không đếm thành hai issue độc lập. Không có verdict human adjudication thật.

Đối chiếu [đáp án có sẵn](../../examples/mock/02-missing-behavior/expected/quality-record.md): phù hợp. Contribution cụ thể là targeted test có sẵn tái hiện lỗi; bảng hồ sơ thể hiện gap và next action. Chưa chứng minh framework/AI phát hiện lỗi mới, hơn review hiện tại hoặc giảm rework.

Verification sau probe: **failed trong scope toy**. Hành động đề xuất: developer sửa reset page và thêm regression check trên revision sửa riêng, reviewer xem evidence của revision đó. Owner thực tế: unknown, chưa được cam kết; human decision: pending. Trong S0 giữ nguyên bug, input, baseline và expected để bảo toàn fixture lỗi. Không có code fix hoặc approval đã thực hiện.

Giới hạn: chưa kiểm tra UI/router/backend, không có baseline review thật, không đo effort/usefulness hoặc khả năng khái quát. Không suy từ suite xanh sang approval hay từ một case synthetic sang tỷ lệ defect của tổ chức.
