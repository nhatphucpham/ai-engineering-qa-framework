# Vòng review bắt buộc cho mỗi output

Ngày 10/11/2026. Theo yêu cầu người dùng: luôn có ít nhất một agent review output, kiểm độ chính xác/tính thực dụng, giải thích cải thiện, sửa rồi lặp trên bản mới đến khi không còn lỗi được tìm trong scope; sau đó mark done. Áp dụng cho code, schema, report, plan và bàn giao của repo, kể cả output đã hoàn thành trước yêu cầu này khi đang được tiếp tục chỉnh sửa.

## 1. Chỉ định reviewer và đưa bản hiện tại vào review

Agent chính chịu trách nhiệm sửa. Ít nhất một reviewer độc lập được chỉ định từ lúc tạo output đến khi đóng review; dùng model cao theo yêu cầu hiện hành. Reviewer không tự sửa phần mình đang nghiệm thu; đề xuất fix được agent chính hiện thực và kiểm lại. Nếu reviewer thay người, chuyển toàn bộ findings/evidence và bản mới nhất cho người thay, không reset lịch sử.

Gói review gồm mục đích/người dùng, scope và non-goals, tiêu chí xong, file output/code/tests liên quan, baseline và bản hiện tại, checks đã chạy/chưa chạy, known gaps và findings các vòng trước. Dùng revision/hash hoặc tên snapshot rõ; review working tree phải đọc đúng file mới nhất, không chỉ đọc bản tóm tắt cũ. Đổi nội dung sau verdict phải re-review phần đổi và regression liên quan.

## 2. Reviewer kiểm gì?

| Góc nhìn | Câu hỏi kiểm chứng |
|---|---|
| Chính xác | Claim có đúng requirement/source/revision và actual execution? Input error, gap, defect, approval có bị trộn? Schema/code/report/docs có cùng semantics? |
| Thực dụng | Người nhận có chạy theo hướng dẫn được, hiểu giới hạn và biết việc tiếp theo/ai xử lý/doneWhen? Output có mất mapping hoặc thông tin cần quyết định? Có làm lại việc không cần thiết? |
| Regression | Lỗi đã sửa có thực sự hết trên bản mới? Test có phân biệt được behavior lỗi thay vì chỉ khớp implementation? Có side effect/lỗi mới từ fix? |
| Đề xuất cải thiện | Vì sao thay đổi này cần thiết, ảnh hưởng người dùng thế nào, fix nhỏ nhất có căn cứ là gì, kiểm lại bằng cách nào? Không tạo finding giả để đủ số vòng |

Mỗi finding có ID ổn định, mức độ, file/vị trí hoặc reproduction, expected/actual, lập luận về ảnh hưởng và fix/điều kiện đóng có thể kiểm. Phân biệt lỗi cần sửa với đề xuất ngoài scope; không chuyển một lỗi thuộc gate thành future work chỉ để đánh done.

## 3. Sửa, kiểm chứng và review lại

Agent chính xử lý từng finding, ghi thay đổi và kết quả thực chạy. Cùng nguyên nhân/behavior giữ một ID qua các vòng; nếu tái hiện lại thì reopen ID đó cùng evidence mới, không nhân bản hoặc giả là lỗi khác. Finding disputed cần reviewer và agent chính đối chiếu nguồn/repro; chỉ đóng khi có căn cứ, không chỉ vì agent chính nói đã sửa.

Gửi **bản mới** cùng diff/checks/finding ledger cho reviewer. Reviewer kiểm lại từng lỗi cũ, khả năng tái xuất hiện, tính nhất quán toàn output và lỗi mới; nêu lý do cải thiện còn cần thiết. Lặp cho đến khi có một vòng sạch trên bản mới nhất. Không tự dừng vì đã đủ số vòng, đã gần hết thời gian hoặc test xanh nếu reviewer vẫn tìm được lỗi trong scope.

Nếu thiếu môi trường/authority/input bắt buộc khiến không verify được, ghi rõ phần chưa xong và giữ output chưa done. Phần độc lập vẫn tiếp tục trong quyền đã có; không tự cài toàn máy, gọi API thật hoặc mở rộng scope/pilot để làm xanh gate.

## 4. Điều kiện mark DONE

Chỉ mark một output/slice DONE khi đồng thời:

- Bản hiện tại đáp ứng mục tiêu và tiêu chí đã ghi; reviewer đã đọc bản đó và không còn finding cần xử lý trong scope.
- Findings cũ đã được reviewer xác nhận đóng, không còn lỗi tái xuất hiện hoặc finding mới chưa xử lý; ledger lưu được reasoning/fix/verification qua các vòng.
- Checks cần thiết thực sự pass; các phần ngoài scope/gate chưa triển khai được ghi riêng, không tuyên bố đã kiểm.
- Review record ghi scope, bản/snapshot, reviewer, rounds/findings, actual checks, final verdict và trạng thái DONE. Bàn giao/plan dùng cùng trạng thái.

Thêm verdict/check evidence và chuyển trạng thái sau review là phần ghi nhận hành chính; không làm thay đổi nội dung đã nghiệm thu. Nếu sửa code/contract/hướng dẫn/claim sau đó, mở lại review cho bản mới. Không sửa manifest/hash để giả rằng bản đã đổi là bản đã review.

DONE có nghĩa hoàn tất **scope được ghi**, không bảo đảm tuyệt đối không có lỗi, không human approval, readiness toàn sản phẩm hoặc quyền commit/push/publish. Bản đầu của sản phẩm vẫn phải đi đủ gate trong IMPLEMENTATION-PLAN.
