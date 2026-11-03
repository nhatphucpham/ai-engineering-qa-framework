# ai-engineering-qa-framework
A practical framework for quality assurance in AI engineering systems, from evaluation and testing to safety and release readiness.

## Implementation plan

Xem [kế hoạch phát triển framework và thử nghiệm trong hai tuần](docs/IMPLEMENTATION-PLAN.md): người dùng, quyết định cần hỗ trợ, artifact dùng thử sớm, lựa chọn prototype, stage gates và cách đo giá trị.

Repo đang ở giai đoạn lập kế hoạch và thử bằng dữ liệu synthetic. Công cụ và stack sản phẩm sẽ được chọn theo bottleneck quan sát được; chưa có framework tự động hoặc kết quả pilot thật.

## Mẫu thử offline

Xem [5 mẫu mock và hướng dẫn walkthrough](examples/mock/README.md), kèm [mẫu hồ sơ kiểm chứng](templates/quality-record.md). Toàn bộ requirement, source, diff và CI evidence đều synthetic. Thử nghiệm thật chỉ thực hiện trong môi trường bảo mật riêng của người dùng.

Chạy từ root repo, chỉ cần Python 3.10+:

```sh
python3 -B examples/mock/run.py
```

Hai probe cố ý thất bại để tái hiện bug. Exit 0 của runner chỉ xác nhận bộ mẫu có kết quả đúng thiết kế, không phải approval hay đánh giá hiệu quả framework.
