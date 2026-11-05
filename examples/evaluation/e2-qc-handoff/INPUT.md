# E2-01 — QC bàn giao tính năng xuất CSV cho Reviewer/TL

**Bạn đang ở đâu:** developer đã bàn giao, QC đã thực hiện một lượt kiểm thử trên candidate `export-r12`; QC đang gửi kết quả cho bạn, vai trò Reviewer/TL. **Bạn cần quyết định:** cho chuyển sang bước triển khai staging mô phỏng, hay cần thêm hành động trước đó; nếu cần, nêu ai xử lý và khi nào được coi là xong.

Tất cả bên dưới là **hồ sơ giả lập do tác giả soạn**. Không có developer/QC thật, test đã chạy thật, app hoặc môi trường staging thật. Case dùng để thử đọc hồ sơ bàn giao và quyết định; bạn không cần đọc code hoặc tự chạy test.

## 1. Feature, thay đổi và yêu cầu

Feature xuất danh sách đơn hàng ra CSV theo bộ lọc. Bản đang bàn giao: `export-r12`; bản trước: `export-r11`. R12 sửa lọc khoảng ngày và bố cục nút xuất, dựng lại cùng package ứng dụng. Các nhãn là revision giả lập.

| Yêu cầu | Điều phải đáp ứng |
|---|---|
| AC-01 | CSV đúng khoảng ngày và trạng thái đang chọn |
| AC-02 | Đủ cột mã đơn/ngày/trạng thái/tổng tiền, escape đúng dấu phẩy và xuống dòng |
| AC-03 | Quản lý được xuất, nhân viên bị từ chối tại API, không chỉ ẩn nút |
| AC-04 | Không có đơn hàng: file chỉ header và UI báo không có dữ liệu |

Quy tắc chuyển bước của **case này**: từng AC phải có evidence phù hợp trên r12, blocked không phải pass; không có bug high/critical mở. Bug low ngoài AC có thể hoãn nếu TL ghi lý do, vai trò xử lý và điều kiện theo dõi. [Requirement/quy trình đầy đủ](requirements.md).

## 2. Developer đã tự kiểm tra gì?

Record `DEV-12`, revision r12, môi trường `local-mock`, người thực hiện là vai trò developer giả lập:

| Check | Phạm vi self-test | Kết quả mô phỏng |
|---|---|---|
| D1 | Unit test lọc ngày và trạng thái — AC-01 | Pass |
| D2 | Unit test cột và escape CSV — AC-02 | Pass |
| D3 | Unit test role guard API — AC-03 | Pass |
| D4 | Unit test serializer khi không có dữ liệu — AC-04 | Pass |

Tổng 4 unit test pass theo record mô phỏng. Không có self-test end-to-end được cung cấp; không nói 4 unit test là toàn bộ kiểm chứng nghiệp vụ.

## 3. QC đã kiểm tra gì?

Record `QC-12`, revision r12, môi trường `qc-mock`, người thực hiện là vai trò QC giả lập:

| Check | Kịch bản QC | Kết quả mô phỏng |
|---|---|---|
| Q1 | Quản lý xuất file sau chọn khoảng ngày và trạng thái — AC-01 | Pass |
| Q2 | Mở file chứa nội dung có dấu phẩy/xuống dòng — AC-02 | Pass |
| Q3 | Xuất tập rỗng: header và thông báo UI — AC-04 | Pass |
| Q4 | Nhân viên gọi thẳng API xuất file — AC-03 | Blocked: chưa có tài khoản nhân viên, chỉ có tài khoản quản lý |

QC r12: **3 pass, 1 blocked**, không phải 4 pass. Không có execution exception được khai báo; record không cung cấp test runner nên không suy số error/skipped bằng 0.

QC còn đính kèm `QC-11-AUTH`: check Q0 về nhân viên bị API từ chối, quản lý được phép, pass ở **r11**. Không có kết quả rerun Q0 ở r12 trong gói bàn giao. D3 là unit test role guard, không chạy qua tài khoản/API tích hợp như Q4. [Record nguồn và provenance](evidence.mock.json).

## 4. Lỗi và phần còn mở

| ID | Tình trạng mô phỏng | Vai trò xử lý / hiện trạng |
|---|---|---|
| UI-17 | Low: nhãn nút xuất bị cắt ở độ rộng màn hình 360 px, vẫn bấm được; ngoài AC của case | Frontend đề xuất xử lý ở đợt sau; chưa có người nhận/thời hạn hoặc quyết định hoãn của TL |
| ENV-04 | Thiếu tài khoản nhân viên ở qc-mock khiến Q4 blocked | Người quản lý tài khoản test chưa được chỉ định; chưa có lịch rerun |

Không có bug high/critical được ghi trong gói; điều này không chứng minh không tồn tại bug khác. Chưa có quyết định triển khai hoặc approval. Không yêu cầu truy dữ liệu thật.

## 5. Phần bạn cần trả lời trước hồ sơ phân tích

Bạn sẽ quyết định gì với lần bàn giao này, dựa vào nguồn nào? Nếu còn việc cần làm, nêu vai trò xử lý và điều kiện để quyết định lại. Có thể nêu chưa đủ thông tin và điều cần bổ sung; không cần đoán ý tác giả hoặc tìm defect code mới.

Mình giữ ngân sách gần nhất bạn chọn: tổng 10 phút đọc trước/sau, không tính chờ trợ lý; nếu muốn đổi cho E2, hãy nói trước khi bắt đầu. Gợi ý tối đa 4 phút phần này, phần còn lại sau hồ sơ. Ghi phút thực đọc/nguồn đã mở hoặc chưa đo; không dùng thời gian chat để tính effort.
