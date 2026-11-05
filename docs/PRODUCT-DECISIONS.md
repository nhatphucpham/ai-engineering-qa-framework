# Các lựa chọn sản phẩm đã được người dùng xác nhận

Ngày 05/11/2026. Nền `303b85a`. Tài liệu ghi yêu cầu sản phẩm qua câu hỏi trong chat, không cấp quyền chạy QA trên project thật, gọi API, đọc bí mật hoặc publish ở phiên này. Chưa pilot/E3; scope/contract/architecture đang thiết kế.

## Đã chốt

| Chủ đề | Lựa chọn người dùng | Hệ quả thiết kế |
|---|---|---|
| Đầu vào | Cả repo/task và gói bàn giao Dev/QC | Hai intake adapter chuẩn hóa về cùng pipeline/contract, không tạo hai bộ rules |
| Model/agent runtime | Cả agent có sẵn trên máy và API mô hình, chọn theo project | Agent connector và model-provider adapter tách core; desktop không bắt buộc một chế độ duy nhất |
| Can thiệp code bản đầu | Đọc, chạy kiểm tra, báo cáo, đề xuất sửa | Không tự tạo/sửa test hoặc code sản phẩm; check output ở khu vực run đã cấu hình, phải kiểm tác dụng phụ |
| Phạm vi QA | Requirement/nghiệp vụ, code review, kết quả unit/integration test | Chưa có UI/e2e, security hoặc performance audit chuyên sâu như năng lực sản phẩm bản đầu |
| Kích hoạt | Chủ động và theo sự kiện | Cùng run lifecycle, scope và permission policy |
| Sự kiện bản đầu | Bàn giao Dev/QC hoặc PR chuyển sang chờ review | Không mặc định chạy mỗi lần save file/commit; thiết kế event ID, snapshot/dedup và trạng thái mới |
| Dữ liệu gửi API | Cấu hình phạm vi cho phép một lần theo project, tự chạy trong phạm vi đó | Data policy có version và scope; thiếu/vượt scope phải chặn phần outbound tương ứng, không hỏi lại mọi bước đã được ủy quyền |
| Desktop và triển khai | Desktop Windows; worker/server self-host do người dùng/team vận hành, tiếp tục chạy khi desktop đóng | Mở rộng lựa chọn local-first: nhiều người dùng, tài khoản/vai trò/quyền project ngay bản đầu; không phải cloud do sản phẩm vận hành |
| Nguồn PR | GitHub đầu tiên | GitHub event/repo/PR adapter, không hứa GitLab/ADO ở bản đầu |
| Requirement/AC | Cả file/gói bàn giao và issue/ticket/PR; khi mâu thuẫn ghi rõ, chưa kết luận AC đó, hỏi owner và tiếp tục phần độc lập | Không tự ưu tiên một nguồn để che conflict; lưu source/version, conflict và clarification state |
| Desktop OS | Windows trước, giữ mở rộng macOS/Linux | Package/test Windows đầu; không cam kết đủ mọi OS |
| Agent platform/plugin | Chưa chọn, kiến trúc dùng chung trước | Không chốt Codex/Claude, SDK/transport hoặc package manifest trước quyết định |

## Bổ sung runtime và triển khai

- OpenAI và Anthropic qua **hai model API adapter riêng**; chưa chốt API/SDK version hoặc gọi account thật.
- Sự kiện khi desktop đóng do **worker/server riêng** xử lý; desktop theo dõi. Người dùng đã chọn self-host trên máy/server của mình/team, không phải dịch vụ cloud do sản phẩm vận hành. Lựa chọn này mở rộng định hướng local-first trước đó; không giữ giả định mọi run phụ thuộc desktop process.
- Quyền repo, phạm vi dữ liệu và secret store được cấu hình theo project **trên server**, desktop không cần luôn mở. Cách bảo vệ/mã hóa/vòng đời secret còn thuộc thiết kế, không tự thu key thật.
- Quyết định mới thay local-first trước đó bằng server nhiều người dùng có quyền project; không suy thành dịch vụ cloud do sản phẩm vận hành hoặc federation nhiều tổ chức.

## Server và thực thi đã chốt thêm

- Server self-host phục vụ **nhiều người**, cần tài khoản, vai trò và quyền project ngay bản đầu. Đăng nhập bằng tài khoản nội bộ do admin quản lý, thiết kế thêm SSO sau; fixed roles: System Admin, Project Owner, Runner, Viewer. Chi tiết permission matrix/chống tự nâng quyền thuộc P1/P3, chưa hỗ trợ custom roles ở bản đầu.
- Unit/integration tests chạy trong **container riêng theo project/run**, môi trường do project cấu hình. Không dùng workspace host dùng chung hoặc desktop renderer để chạy tests. Container không tự bảo đảm an toàn nếu cấu hình đặc quyền/mount sai; P1/P3 phải định nghĩa trust/quyền/network/resource/cleanup.
- GitHub hỗ trợ **polling và webhook ngay bản đầu**. Cả hai tạo cùng event/run contract; cần dedup/idempotency để không chạy hai lần cùng sự kiện và cơ chế catch-up khi offline. Chưa có endpoint public/GitHub account thật được cấp trong phiên này.

## Chi tiết cần thiết kế/chốt tiếp ở P1/P3

- Chi tiết permission matrix, user/credential lifecycle và SSO extension interface; event delivery/sync/dedup, queue/claim/lease/retry và phục hồi khi worker/container không sẵn sàng thuộc P1/P3.
- Project checks/config tin cậy, budget runtime/model/concurrency và cách hủy; chi tiết P1/P3, chưa tự chọn trần chi phí thay người dùng.
- Stack/runtime/shell/transport và secrets storage: cần contract/ADR, không coi nghiên cứu Tauri/Electron là quyết định.

Không đồng nhất lựa chọn nhà cung cấp API với quyền sử dụng account/key thật trong repo này. Bản đầu có thể test contract bằng provider giả lập; network calls thực cần quyền/cấu hình của môi trường chạy sản phẩm.

## Phạm vi P1 cần bổ sung

Project config: intake/source adapters, requirement precedence, runtime mode và agent/model connection, outbound data policy, GitHub/event subscriptions, run budget/check permissions. Contract chung: task/candidate/AC/evidence/report, events/idempotency, run state/commands, artifact references và lỗi/partial/waiting.

Đầu vào đa nguồn không có nghĩa tin mọi claim; mode API không biến inference thành execution; automatic trigger không tự cấp permission hoặc bỏ qua policy project. Luồng plugin/desktop dùng cùng application interface và core.
