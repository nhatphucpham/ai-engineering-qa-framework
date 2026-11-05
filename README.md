# ai-engineering-qa-framework
A practical framework for quality assurance in AI engineering systems, from evaluation and testing to safety and release readiness.

## Hướng phát triển hiện hành — 05/11/2026

**Thiết kế plugin QA cho agent thực hiện tự động, chưa pilot.** [Scope P0](docs/FRAMEWORK-SCOPE.md) tách core dùng chung, agent workflow và adapter; chưa chọn nền tảng/transport. [Plan P0–P6](docs/IMPLEMENTATION-PLAN.md): scope → contract → rules → kiến trúc đích → harness offline → kỹ thuật → đóng gói cho target được chọn. Scope đã ghi, bước tiếp là P1; chưa có plugin installable hoặc quyền publish. Walkthrough/feedback bên dưới là lịch sử tham khảo.

## Kiến trúc thực tế hiện tại

[Sơ đồ và khảo sát kiến trúc as-is](docs/CURRENT-ARCHITECTURE.md) phân biệt phương pháp thủ công, runner minh họa, evidence và phần mềm chưa được xây. Có audit subagent model cao. Các tài liệu đề xuất bên dưới chưa chứng minh repo sẵn sàng pilot vận hành.

## Kết quả hiện tại và đề xuất

[Tổng kết](pilot/results.md) tách fixture, phản hồi người dùng, giới hạn E1 và kết quả E2. [Proposal trước audit](docs/MANAGEMENT-PROPOSAL.md) là lịch sử đã bị thay bởi plan thiết kế trước, chưa pilot.

## Bản dùng thử E1

[Protocol E1](docs/EVALUATION-PROTOCOL.md) và [manifest](pilot/e1-freeze.json) giữ version frozen lịch sử. [Task register](pilot/task-register.md) và [results](pilot/results.md) ghi E1 kết thúc chưa đánh giá được mục tiêu, E2 có phản hồi chung; không có pilot task thật. Không đọc nhãn “chưa bắt đầu” trong artifact frozen như trạng thái hiện tại.

## Implementation plan

Xem [kế hoạch thiết kế và xây năng lực tối thiểu](docs/IMPLEMENTATION-PLAN.md). [Plan hai tuần cũ](docs/IMPLEMENTATION-PLAN-2026-11-03.md) chỉ để truy lịch sử.

Repo đang ở giai đoạn thiết kế framework, chỉ dùng synthetic. Chưa chốt stack sản phẩm; chọn sau contract/rules và kiến trúc đích. Chưa có runtime QA chung hoặc kết quả pilot thật.

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
