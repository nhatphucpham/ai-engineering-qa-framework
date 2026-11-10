# ai-engineering-qa-framework
A practical framework for quality assurance in AI engineering systems, from evaluation and testing to safety and release readiness.

## Hướng phát triển hiện hành — 10/11/2026

**Mục đích: giúp Reviewer/Tech Lead biết requirement nào có evidence đúng revision, gap gì còn mở và ai xử lý tiếp.** Sản phẩm đích là plugin QA + desktop Windows + server/worker self-host nhiều người; chưa pilot. [Các lựa chọn đã chốt](docs/PRODUCT-DECISIONS.md) là nguồn yêu cầu: agent local hoặc OpenAI/Anthropic API, project data policy, container kiểm thử, GitHub polling/webhook, auth nội bộ và fixed roles. [Scope P0](docs/FRAMEWORK-SCOPE.md) và [plan P0–P6](docs/IMPLEMENTATION-PLAN.md) dùng một core chung; agent target và stack control/worker/desktop chưa chọn; pure core chọn baseline Python sau S1. Transport HTTPS JSON/SSE là thiết kế tại ADR-002, chưa có server. P1 contract v2, P2 rules v2 và reference report/harness đã có; P3-A design đã review. **S1 đã PASS 356 cases + 28 CLI; bước tiếp P4-A runtime report/constraint integration và module pure core Python** theo [ADR-004](docs/adr/004-core-baseline-after-s1.md). Chưa có phần mềm installable hoặc quyền publish. Walkthrough/feedback cũ là lịch sử.

## Kiến trúc thực tế hiện tại

P1 hiện có [contract v2](docs/DATA-CONTRACT.md), [JSON Schema v2](schemas/qa-contract-v2.schema.json) và [specimen valid/invalid](examples/contracts/v2/README.md), kèm công cụ kiểm schema/reference offline. Chưa có QA engine/server/worker/auth/container runtime; [P2 rules](docs/VERIFICATION-RULES.md) có strict schemas v1/v2 và reference evaluator: corpus 55 decision scenarios, 20 lifecycle cases cùng v2 regression. Công cụ tính trạng thái từ judgment được cung cấp, chưa tự xác thực trust/domain truth; [P3-A kiến trúc đích](docs/TARGET-ARCHITECTURE.md) có component/sequence/dataflow và ADRs; P3 tổng thể còn partial vì stack/spikes chưa kiểm chứng. Python reference được chọn làm baseline pure core/report sau S1; đây chưa là production server/worker. [Audit và bản sửa P1](docs/P1-REVIEW-FIXES.md) ghi lý do version hóa; P1 v1 giữ lịch sử và không còn được active validator chấp nhận.

[Sơ đồ và khảo sát kiến trúc as-is](docs/CURRENT-ARCHITECTURE.md) phân biệt phương pháp thủ công, runner minh họa, evidence và phần mềm chưa được xây. Có audit subagent model cao. Các tài liệu đề xuất bên dưới chưa chứng minh repo sẵn sàng pilot vận hành.

[Rules v2 sau audit](docs/P2-V2-REVIEW.md) sửa source reasoning tự gán integration coverage và mất conflict reason khi đồng thời có violation. V1 chỉ giữ replay lịch sử; [reference report offline](docs/OFFLINE-REPORT.md) dùng assessment v2, tạo output có version riêng, giữ declared/effective constraints và bindings về input. Đây là prerequisite P4-A/S1, không phải P1 report đã persist, execution project thật hoặc production runtime. Legacy P1 v2 projection gặp constraint collision vẫn cần fail-closed; chưa đóng full integration gate.

## Kết quả hiện tại và đề xuất

[Tổng kết](pilot/results.md) tách fixture, phản hồi người dùng, giới hạn E1 và kết quả E2. [Proposal trước audit](docs/MANAGEMENT-PROPOSAL.md) là lịch sử đã bị thay bởi plan thiết kế trước, chưa pilot.

## Bản dùng thử E1

[Protocol E1](docs/EVALUATION-PROTOCOL.md) và [manifest](pilot/e1-freeze.json) giữ version frozen lịch sử. [Task register](pilot/task-register.md) và [results](pilot/results.md) ghi E1 kết thúc chưa đánh giá được mục tiêu, E2 có phản hồi chung; không có pilot task thật. Không đọc nhãn “chưa bắt đầu” trong artifact frozen như trạng thái hiện tại.

## Implementation plan

Xem [kế hoạch thiết kế và xây năng lực tối thiểu](docs/IMPLEMENTATION-PLAN.md). [Plan hai tuần cũ](docs/IMPLEMENTATION-PLAN-2026-11-03.md) chỉ để truy lịch sử.

Repo đang ở giai đoạn thiết kế và kiểm chứng implementation, chỉ dùng synthetic. [S1 results](docs/S1-RESULTS.md) ghi actual parity/metrics và giới hạn; [native spike](spikes/s1/README.md) là công cụ conformance. Pure-core baseline đã chọn, các runtime boundaries khác còn cần spike. Chưa có runtime sản phẩm đầy đủ hoặc kết quả pilot thật.

## Mẫu thử offline

Xem [5 mẫu cơ bản và MOCK-06 nhiều file](examples/mock/README.md), kèm [mẫu hồ sơ kiểm chứng](templates/quality-record.md). Toàn bộ requirement, source, diff và CI evidence đều synthetic. Thử nghiệm thật chỉ thực hiện trong môi trường bảo mật riêng của người dùng.

Chạy từ root repo, chỉ cần Python 3.10+:

```sh
python3 -B examples/mock/run.py
```

Hai probe cố ý thất bại để tái hiện bug. Exit 0 của runner chỉ xác nhận bộ mẫu có kết quả đúng thiết kế, không phải approval hay đánh giá hiệu quả framework.

## Walkthrough lịch sử — Review một thay đổi nhiều file

Đọc [hồ sơ MOCK-06](pilot/mock/MOCK-06-review.md) để xem một thay đổi đi qua UI state, API giả lập, cache và service: baseline xanh, hai lỗi tái hiện được, evidence cũ và một yêu cầu chưa rõ. [Core framework v0](docs/CORE-FRAMEWORK.md) hướng dẫn cách đi từ yêu cầu đến hành động review. Đây là walkthrough đã biết đáp án, chưa đánh giá độc lập hoặc xác nhận usefulness với reviewer thật.

MOCK-06 có runner riêng, chạy từ root repo:

```sh
python3 -B examples/mock/06-filter-pagination/run.py
```

Runner này ghi execution local cùng hash input; xem [hướng dẫn case](examples/mock/06-filter-pagination/README.md). Runner phía trên vẫn chỉ chạy MOCK-01–05.

## Vòng sửa và kiểm chứng MOCK-06

[Snapshot sửa riêng](examples/remediation/06-filter-pagination/README.md) giữ nguyên fixture lỗi, chạy cùng baseline/historical/probe trên head gốc và bản sửa. [Hồ sơ sau sửa](pilot/mock/MOCK-06-remediation.md) ghi evidence mới và requirement còn chưa rõ; [decision log](docs/DECISION-LOG.md) nêu lý do chọn targeted checks thay vì automation tổng quát.

Đây là bước walkthrough lịch sử. [Phiếu thử review G1](docs/REVIEWER-CHECK.md) ghi việc truy claim/action, chưa chứng minh usability hoặc thay [bước phát triển hiện hành](docs/IMPLEMENTATION-PLAN.md).

## MOCK-06 v2 — Sau khi chốt cách xử lý dấu cách

Người dùng đã chọn toàn dấu cách là tất cả và bỏ dấu cách hai đầu khi tìm category. [Bản v2 riêng](examples/remediation/06-filter-pagination-v2/README.md) bổ sung 4 test bên cạnh 9 test cũ; [hồ sơ v2](pilot/mock/MOCK-06-v2.md) giải thích mong muốn, lý do, thay đổi và kết quả ngay tại chỗ. Các hồ sơ v1 vẫn giữ trạng thái tại thời điểm trước clarification.

## MOCK-07 — Dùng lại bố cục với bài toán giảm giá

[Case riêng](examples/mock/07-order-discount/README.md) có hai lỗi cố ý về ngưỡng giảm giá và phí giao hàng. [Hồ sơ MOCK-07](pilot/mock/MOCK-07-review.md) giải thích số tiền trước/sau ngay tại chỗ. Đây là ví dụ đã biết đáp án, runner riêng; không nằm trong manifest/runner MOCK-01–05.
