# Phiếu thử review hồ sơ — G1

Ngày chuẩn bị: 04/11/2026. Synthetic-only. Trạng thái: **đã nhận phản hồi người dùng qua câu hỏi có gợi ý; chưa xác nhận G1**. Không nhập dữ liệu task thật vào phiếu này.

## Phản hồi thực nhận ngày 04/11/2026

Artifact được gửi cho người dùng ở commit `17e8e4f`; chưa xác nhận chính xác các file họ đã mở. Vai trò chuyên môn, thời gian đọc và mức quen case: unknown. Người dùng đã thấy kết luận và diễn giải của tác giả trong chat; câu hỏi có các đáp án gợi ý. Đây là phản hồi có hỗ trợ, không phải phép thử độc lập theo protocol bên dưới.

| Chủ đề hỏi trong chat | Đáp án người dùng chọn |
|---|---|
| Hiểu trạng thái hiện tại | “Hai lỗi đã sửa; còn yêu cầu whitespace chưa rõ nên hồ sơ chưa hoàn tất, chưa có approval” |
| Truy requirement/test/execution | “Tìm được một phần nhưng còn khó đối chiếu” |
| Hành động tiếp theo | “Chưa rõ hành động tiếp theo” |
| Nguyên nhân khó đối chiếu | “Chưa quen cách đọc kết quả test” |
| Thông tin cần làm rõ | “Thứ tự công việc và điều kiện hoàn thành” |

Chưa thu được câu trả lời tự diễn giải hoặc nguồn cụ thể do người dùng tìm. Q3 của protocol chưa được hỏi riêng; chưa có phản hồi về thông tin có thể bỏ hoặc giá trị tăng thêm so với review hiện tại. Các ô chưa thu thập bên dưới không được tự điền bằng suy đoán từ đáp án trắc nghiệm.

Hành động từ phản hồi: thêm phần đọc test bằng ngôn ngữ thường, chuỗi truy evidence cho AC-03 và bảng công việc theo thứ tự/điều kiện xong vào hồ sơ sau sửa. Chưa có phản hồi sau chỉnh sửa. Kết luận hiện tại: chưa đủ căn cứ xác nhận G1; tồn tại khó khăn người dùng tự báo cáo, không suy thành defect rate hoặc hiệu quả framework.

## Phản hồi tự diễn giải sau bản `dbf1582`

Người dùng nêu bản gốc có 9 test, 3 fail (historical và hai probe), nhưng hiểu ba test được sửa cùng bằng reset trang và không biết vì sao cần reset; muốn hiểu phải mở file khác. Đây là phản hồi tự diễn giải trong chat sau các gợi ý trước đó, chưa phải đánh giá độc lập. Tác giả sau đó giải thích hai lỗi và lý do reset; người dùng yêu cầu sửa hồ sơ theo cấu trúc mong muốn → lý do → thực tế → cách sửa → kết quả.

Thay đổi đáp ứng: thêm hai phần giải thích riêng ngay trong hồ sơ và quy tắc tương ứng ở template. Chưa có phản hồi về bản sửa mới; không đánh dấu Q2/Q3/Q4 hoàn thành hoặc G1 đạt từ việc tác giả đã giải thích.

## Cách dùng

Chọn [hồ sơ sau sửa MOCK-06](../pilot/mock/MOCK-06-remediation.md). Reviewer đọc hồ sơ và mở các nguồn cần thiết; không cần chạy code. Đây là thử khả năng đọc và sử dụng hồ sơ đã công khai đáp án, không phải blind bug-finding evaluation. Không dùng chính trợ lý tác giả để giả lập phản hồi người thật.

Trước phiên, ghi commit hồ sơ được đọc, vai trò người đọc, họ đã biết case/đáp án chưa và timebox do người tổ chức chọn. Người đọc trả lời trước khi nhận gợi ý; nếu tác giả giải thích, ghi câu hỏi nào cần hỗ trợ. Không cần công bố danh tính hoặc thông tin nhạy cảm.

## Nhiệm vụ cho người đọc

| Câu | Việc cần làm | Câu trả lời của reviewer / nguồn tìm được | Hỗ trợ cần dùng |
|---|---|---|---|
| Q1 | Nêu verification hiện tại và điều gì còn ngăn hồ sơ complete | Chưa thu thập | Chưa thu thập |
| Q2 | Chọn một lỗi đã sửa; tìm requirement, assertion, execution và snapshot kiểm chứng nó | Chưa thu thập | Chưa thu thập |
| Q3 | Giải thích kết quả test của head gốc và fixed khác nhau thế nào | Chưa thu thập | Chưa thu thập |
| Q4 | Nêu hành động tiếp theo và vai trò cần xử lý; phân biệt verification với approval | Chưa thu thập | Chưa thu thập |
| Q5 | Chỉ ra thông tin giúp quyết định, thông tin đã biết và chỗ khó hiểu hoặc có thể bỏ | Chưa thu thập | Chưa thu thập |

## Ghi nhận theo protocol — chưa thực hiện đầy đủ

- Commit/version được đọc: chưa ghi nhận.
- Vai trò reviewer / mức quen case: chưa ghi nhận.
- Timebox đã chọn / thời gian thực đo: unknown / unknown.
- Các claim truy được hoặc không truy được, kèm nguồn: chưa thu thập.
- Hành động hoặc lý do không cần thêm hành động do reviewer nêu: chưa thu thập.
- Điều mới so với cách review hiện tại của người đọc: chưa thu thập; nếu chỉ lặp lại, ghi đúng như vậy.
- Các gợi ý tác giả đã cung cấp: chưa thu thập.
- Đề xuất giữ/bỏ/sửa trường và lý do: chưa thu thập.
- Kết luận G1 / người ghi nhận / bước tiếp: pending / unknown / thu phản hồi.

Theo G1 trong [implementation plan](IMPLEMENTATION-PLAN.md), xem xét người đọc có truy được claim, hiểu status và nêu được hành động hoặc lý do không cần thêm, cùng nhu cầu/bottleneck cụ thể. Không tự đặt điểm số làm benchmark. Nếu cần tác giả hướng dẫn, ghi rõ giới hạn thay vì coi là sử dụng độc lập. Một phiên thử không chứng minh effectiveness hoặc ROI; feedback trên synthetic không phải pilot task thật.

## Tự rà của tác giả trước thử — không phải kết quả reviewer

| Quan sát từ artifact | Chỉnh sửa đề xuất đã thực hiện | Điều cần người đọc xác nhận |
|---|---|---|
| Template đặt kết luận/hành động ở cuối và lặp với bảng AC | Đưa tóm tắt lên đầu, giữ chi tiết tại bảng | Có tìm được status/action dễ hơn không? |
| Hồ sơ sau sửa nêu nhóm test nhưng thiếu link trực tiếp tới assertion | Thêm đường truy requirement → assertion → execution/snapshot | Người đọc có đối chiếu được mà không cần tác giả giải thích không? |
| Finding là trường mẫu bắt buộc về hình thức dù case có thể đủ evidence | Ghi rõ chỉ thêm finding khi có; đồng bộ process observation với core | Có tránh được nhập liệu không cần thiết không? |

Các chỉnh sửa D-02 là giả thuyết cải thiện bố cục. Phản hồi có gợi ý sau đó được ghi riêng ở đầu tài liệu; chưa có số đo hoặc phản hồi độc lập xác nhận lợi ích.
