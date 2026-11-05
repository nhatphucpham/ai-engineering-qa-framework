# Đề xuất bước tiếp theo cho QA framework v0

Ngày 05/11/2026. **Bản đề xuất, chưa được phê duyệt.** Phạm vi evidence hiện tại: synthetic và phản hồi một người dùng có hỗ trợ trong chat. Không có task thật, số đo effort, adjudication độc lập hoặc ROI.

## Quyết định đề xuất

Giữ prototype thủ công và template hiện có. Có thể tiếp tục **một thử nghiệm giới hạn tại điểm QC → Reviewer/TL**, nếu có team tự nguyện, người đọc và ngân sách được xác nhận. Chưa có cơ sở đầu tư engine/AI verifier, dashboard hoặc rollout. Nếu chưa có điều kiện thử, dừng ở bộ artifact và báo cáo hiện tại; không tạo thêm mock vô hạn.

## Vấn đề và evidence

Người dùng cần biết vị trí bàn giao, developer/QC đã kiểm tra gì và điều kiện chuyển bước. E1 chỉ có feature/code/unit test nên chưa đánh giá được mục tiêu. Sau khi thêm bối cảnh QC → TL ở E2, người dùng đưa được hành động cấp tài khoản và sửa UI trước khi xem hồ sơ tổng hợp; sau hồ sơ phản hồi “đã ổn”.

Bố cục mong muốn → lý do → thực tế → cách sửa → kết quả được phản hồi tốt ở MOCK-06 v2. Fixtures cho thấy có thể nối requirement, targeted checks, sửa và evidence theo version. **Chưa biết hồ sơ có đổi quyết định hoặc giảm effort so với artifact hiện có.** Nguồn chi tiết tại [results](../pilot/results.md), [feedback v2](REVIEWER-CHECK.md) và [E2 trước/sau](../pilot/e2-01-observations.md).

## Can thiệp cần thử và tiêu chí

Một hồ sơ ngắn gắn với gói bàn giao hiện có: vị trí/quyết định, AC/evidence/revision, blocker/issue, action/owner/điều kiện xong. Tái dùng link và report sẵn có để hạn chế nhập lại. Targeted check bổ sung và clarification ghi effort/contribution riêng, không gán tất cả cho template.

So sánh nhận định trước khi xem hồ sơ bổ sung và sau khi xem trên cùng task; lưu điều mới, điều đã biết, action có đổi không và lý do. Ghi thời gian chuẩn bị/thu evidence/review/triage. Đây là so sánh bổ sung có bias thời gian/chú ý, không đủ kết luận causal hoặc giảm defect dài hạn.

## Phạm vi và nguồn lực đề xuất để thương lượng

| Hạng mục | Đề xuất, chưa phải cam kết |
|---|---|
| Team và task | Một team tự nguyện, một họ task bàn giao QC → TL; tối đa 3 task đủ điều kiện tiếp cận |
| Thời hạn | Tối đa 2 tuần, checkpoint sau task đầu hoặc cuối tuần 1, điều kiện nào đến trước |
| TL điều phối | Trần dự kiến 2 giờ setup/tổng hợp và 30 phút chuẩn bị/triage mỗi task; cần xác nhận trước thử |
| Reviewer | Tối đa 20 phút đọc trước/sau mỗi task, không quá 3 phiên; cần người nhận xác nhận |
| QC/developer | Cung cấp artifact đang có; check mới cần đồng ý effort riêng, không mặc định là nguồn lực sẵn có |
| Owner quyết định | Sponsor/TL, reviewer và domain adjudicator: chưa được chỉ định |
| Overhead chấp nhận được | Chưa chốt; các con số trên là trần thử đề xuất, không phải overhead đã được đo hoặc chấp nhận |

Vòng synthetic chỉ có lựa chọn timebox 10 phút và không có số đo thực tế. Các budget vòng sau vì vậy là **đề xuất vận hành để thương lượng**, chưa ước lượng từ năng suất đã quan sát; không suy thành chi phí thực tế hoặc tiết kiệm tiền. Nếu không đủ nguồn lực thì giảm số task hoặc không khởi động.

Task thật chỉ thực hiện trong môi trường bảo mật của người dùng; không đưa code/log/trace/task thật vào repo này. Không cần gửi kết quả nhạy cảm để tiếp tục lưu bộ synthetic. Nếu chỉ thử synthetic tiếp, không gọi đó là live pilot; chọn rõ một lượt có câu hỏi còn mở và điều kiện kết thúc.

## Điều kiện tiếp tục, đổi hoặc dừng

Trước task đầu, owner chốt loại improvement đáng giá và overhead tối đa. Tiếp tục giới hạn nếu có action hoặc thông tin hữu ích ngoài baseline, người dùng muốn dùng tiếp và effort nằm trong budget đã chọn. Một tín hiệu hữu ích chỉ hỗ trợ thử tiếp, chưa đủ rollout.

Nếu hồ sơ chủ yếu lặp report đã có hoặc tốn nhập liệu, giản lược/tái dùng report đó; nếu một vòng giản lược vẫn không đổi hành động hoặc quá budget, dừng can thiệp hiện tại. Nếu vấn đề là clarification/test environment/domain knowledge, chuyển effort sang đúng bottleneck. Không có người đọc/owner hoặc không có quyền tiếp cận thì không khởi động, ghi thiếu điều kiện thay vì tuyên bố framework thất bại.

Checkpoint chốt: tiếp tục có giới hạn / đổi can thiệp / dừng; kèm evidence, limitation và owner. Pilot tiến cứu hoặc rollout cần thiết kế và phê duyệt riêng. Đề xuất này không cấp quyền truy hệ thống thật, gửi thông báo, deploy hoặc tuyển người tham gia.
