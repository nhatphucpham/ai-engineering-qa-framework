# Hướng dẫn phát triển repo

Khi tiếp tục phát triển, lập kế hoạch phiên, sửa walkthrough hoặc prototype của repo này, đọc và áp dụng [.agents/skills/qa-framework-development/SKILL.md](.agents/skills/qa-framework-development/SKILL.md).

Kế hoạch sản phẩm nằm trong `docs/IMPLEMENTATION-PLAN.md`; semantics verification nằm trong `docs/CORE-FRAMEWORK.md`. Giữ dữ liệu synthetic và các fixture có lỗi cố ý. Yêu cầu hiện tại của người dùng được ưu tiên; ghi rõ lý do nếu thay đổi hướng đã chọn.

## Review bắt buộc cho mọi output

Luôn chỉ định ít nhất một agent review độc lập, dùng mô hình cao, cho output hiện tại. Gửi đúng bản đang làm cùng mục tiêu/phạm vi và evidence; reviewer kiểm độ chính xác, tính thực dụng và giải thích vấn đề/điểm cần cải thiện. Sửa findings rồi gửi lại bản mới để kiểm cả lỗi cũ, lỗi tái xuất hiện và lỗi mới. Giữ stable finding IDs, không ghi cùng lỗi thành finding mới qua từng vòng.

Lặp review → sửa → kiểm chứng → re-review đến khi reviewer xác nhận bản mới không còn finding chưa xử lý trong scope và các checks yêu cầu đã pass. Khi đó mới mark output **DONE** trong review record/bàn giao; không dùng DONE của một slice để đóng gate sản phẩm chưa đạt. Không tự đặt số vòng tối đa rồi bỏ qua finding. Nếu còn blocker hoặc chưa kiểm chứng được thì giữ trạng thái chưa done và nêu rõ.

Chi tiết quy trình và điều kiện DONE: [docs/REVIEW-WORKFLOW.md](docs/REVIEW-WORKFLOW.md). Review không thay tests, human approval hoặc quyền commit/push/publish.
