# E2 — QC bàn giao cho Reviewer/TL

Ngày 05/11/2026. Synthetic-only. Người dùng đã chọn điểm bàn giao QC → Reviewer/TL. E1 giữ nguyên và kết thúc chưa đánh giá được mục tiêu; không nối kết quả E2 vào một baseline E1 giả định.

## Quyết định cần hỗ trợ

Reviewer/TL nhận một thay đổi đã qua self-test và một lượt QC, để quyết định có cho chuyển sang bước triển khai mô phỏng hay cần thêm hành động. Quy trình và điều kiện triển khai được đặt riêng cho case, không phải quy định của mọi team. Kết quả thực sự cần thu là quyết định, nguồn và điều kiện hoàn thành; không yêu cầu người dùng tìm lỗi từ Python.

Can thiệp vẫn là core/template frozen tại `8c03ad55f41811c2539c44cbcb049322530501a2`, định danh bằng [manifest E1](../pilot/e1-freeze.json). Protocol E2 là file này tại commit đưa E2 vào repo, phải ghi commit đó khi lưu phản hồi. Giữ tài liệu nguồn input nguyên bản khi bắt đầu thu nhận định; chỉnh sau feedback cần version/lượt mới hoặc ghi hỗ trợ rõ.

## Dữ liệu và provenance

Case E2-01 mới là hồ sơ bàn giao tính năng xuất danh sách đơn hàng. Đây là bài tập đọc artifact; không có app xuất CSV được dựng/chạy trong vòng này. Self-test và QC được **tác giả soạn thành evidence mô phỏng**, có vai trò, revision, môi trường giả lập và kết quả. Chúng không phải execution local, CI hoặc kiểm thử bởi developer/QC thật. Không chuyển các record mô phỏng thành kết luận behavior đã được thực thi kiểm chứng.

Mục tiêu H3: người đọc hiểu điểm bàn giao, đối chiếu evidence/revision và chọn hành động. Tác giả biết thiết kế; đây là walkthrough có hỗ trợ và so sánh bổ sung cùng case, không phải blind evaluation hay phép đo lợi ích nhân quả. Không xây thêm app/test runner để che thiếu bối cảnh.

## Tiến hành một lượt

1. Gửi [input E2](../examples/evaluation/e2-qc-handoff/INPUT.md), gồm vị trí hiện tại, requirement/điều kiện chuyển bước, self-test/QC, issue và giới hạn. Chưa gửi hồ sơ phân tích do core/template tạo.
2. Thu nhận định trước: quyết định hiện tại, nguồn cụ thể, hành động/owner/điều kiện xong; hỏi thêm nguồn đã mở và phút thực đọc. Nếu chưa đủ bối cảnh, lưu nguyên phản hồi; không biến nó thành 0 finding hoặc ép đoán lỗi.
3. Sau khi lưu phản hồi trước, chuẩn bị hồ sơ bổ sung bằng bản frozen, giải thích mong muốn/lý do/evidence/trạng thái/action ngay tại chỗ. Không tạo thêm evidence làm thay đổi case giữa hai lượt; nếu phải thêm thì ghi contribution mới, không gán benefit chỉ cho bố cục.
4. Thu nhận định sau, điều thay đổi hoặc đã biết, phần cần hỗ trợ, nguồn tự truy và thời gian. Verdict của người dùng là quyết định trong bài tập, không approval deploy thật. Self-check từ tác giả không là adjudication độc lập.
5. Cập nhật register/results với limitation; hoàn thành proposal dù chưa đủ evidence. Một lượt/case, không tạo thêm case liên tục để tránh tổng kết.

## Thời gian và tiêu chí

Dùng ngân sách 10 phút tổng đọc trước/sau như lựa chọn gần nhất của người dùng, nêu rõ khi gửi input để họ điều chỉnh nếu cần. Gợi ý tối đa 4 phút trước, phần còn lại sau; không tính chờ trợ lý. Phút thực tế tự báo, thiếu là unknown; hết thời gian ghi incomplete, không reset timer sau hỗ trợ.

Quan sát: người đọc nêu đúng vị trí, biết ai đã test/cái gì/ở revision nào, chọn quyết định có căn cứ và action có owner/điều kiện xong. Không chấm bằng số lỗi tìm được, số test pass, hoặc đáp án chọn sẵn. Không xem một câu dễ hiểu là G1 đầy đủ; không suy effectiveness thực tế từ evidence mô phỏng.
