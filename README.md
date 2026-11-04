# ai-engineering-qa-framework
A practical framework for quality assurance in AI engineering systems, from evaluation and testing to safety and release readiness.

## Bản dùng thử E1

[Protocol đánh giá](docs/EVALUATION-PROTOCOL.md) chốt core/template theo commit cùng [manifest](pilot/e1-freeze.json). [Task register](pilot/task-register.md) và [adjudication log](pilot/adjudication-log.md) ghi rõ phần đã có từ walkthrough và phần đánh giá mới chưa bắt đầu. Chưa có kết quả E1 hoặc pilot task thật.

## Implementation plan

Xem [kế hoạch phát triển framework và thử nghiệm trong hai tuần](docs/IMPLEMENTATION-PLAN.md): người dùng, quyết định cần hỗ trợ, artifact dùng thử sớm, lựa chọn prototype, stage gates và cách đo giá trị.

Repo đang ở giai đoạn lập kế hoạch và thử bằng dữ liệu synthetic. Công cụ và stack sản phẩm sẽ được chọn theo bottleneck quan sát được; chưa có framework tự động hoặc kết quả pilot thật.

## Mẫu thử offline

Xem [5 mẫu cơ bản và MOCK-06 nhiều file](examples/mock/README.md), kèm [mẫu hồ sơ kiểm chứng](templates/quality-record.md). Toàn bộ requirement, source, diff và CI evidence đều synthetic. Thử nghiệm thật chỉ thực hiện trong môi trường bảo mật riêng của người dùng.

Chạy từ root repo, chỉ cần Python 3.10+:

```sh
python3 -B examples/mock/run.py
```

Hai probe cố ý thất bại để tái hiện bug. Exit 0 của runner chỉ xác nhận bộ mẫu có kết quả đúng thiết kế, không phải approval hay đánh giá hiệu quả framework.

## S1 — Review một thay đổi nhiều file

Đọc [hồ sơ MOCK-06](pilot/mock/MOCK-06-review.md) để xem một thay đổi đi qua UI state, API giả lập, cache và service: baseline xanh, hai lỗi tái hiện được, evidence cũ và một yêu cầu chưa rõ. [Core framework v0](docs/CORE-FRAMEWORK.md) hướng dẫn cách đi từ yêu cầu đến hành động review. Đây là walkthrough đã biết đáp án, chưa đánh giá độc lập hoặc xác nhận usefulness với reviewer thật.

MOCK-06 có runner riêng, chạy từ root repo:

```sh
python3 -B examples/mock/06-filter-pagination/run.py
```

Runner này ghi execution local cùng hash input; xem [hướng dẫn case](examples/mock/06-filter-pagination/README.md). Runner phía trên vẫn chỉ chạy MOCK-01–05.

## Vòng sửa và kiểm chứng MOCK-06

[Snapshot sửa riêng](examples/remediation/06-filter-pagination/README.md) giữ nguyên fixture lỗi, chạy cùng baseline/historical/probe trên head gốc và bản sửa. [Hồ sơ sau sửa](pilot/mock/MOCK-06-remediation.md) ghi evidence mới và requirement còn chưa rõ; [decision log](docs/DECISION-LOG.md) nêu lý do chọn targeted checks thay vì automation tổng quát.

Bước tiếp theo: dùng [phiếu thử review G1](docs/REVIEWER-CHECK.md) để kiểm tra người đọc có truy được claim và chọn hành động hay không. Phiếu đang chờ phản hồi thật, chưa phải kết quả usability.

## MOCK-06 v2 — Sau khi chốt cách xử lý dấu cách

Người dùng đã chọn toàn dấu cách là tất cả và bỏ dấu cách hai đầu khi tìm category. [Bản v2 riêng](examples/remediation/06-filter-pagination-v2/README.md) bổ sung 4 test bên cạnh 9 test cũ; [hồ sơ v2](pilot/mock/MOCK-06-v2.md) giải thích mong muốn, lý do, thay đổi và kết quả ngay tại chỗ. Các hồ sơ v1 vẫn giữ trạng thái tại thời điểm trước clarification.

## MOCK-07 — Dùng lại bố cục với bài toán giảm giá

[Case riêng](examples/mock/07-order-discount/README.md) có hai lỗi cố ý về ngưỡng giảm giá và phí giao hàng. [Hồ sơ MOCK-07](pilot/mock/MOCK-07-review.md) giải thích số tiền trước/sau ngay tại chỗ. Đây là ví dụ đã biết đáp án, runner riêng; không nằm trong manifest/runner MOCK-01–05.
