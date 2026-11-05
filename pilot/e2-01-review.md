# E2-01 — Hồ sơ QC bàn giao xuất CSV cho Reviewer/TL

Ngày 05/11/2026. Synthetic-only. Người chuẩn bị: trợ lý; người đọc quyết định trong bài tập: người dùng. Requirement `e2-export-req-v1`, candidate `export-r12`, bản trước `export-r11`. Tất cả record developer/QC là do tác giả soạn, không có app hoặc test đã chạy thật. Template/core dùng đúng bản frozen tại `8c03ad5`.

## Đọc nhanh: đang ở đâu và còn thiếu gì?

**Đang ở QC → Reviewer/TL, chưa có quyết định chuyển sang staging.** Developer khai self-test 4 pass; QC khai 3 pass, 1 blocked trên r12. Verification **incomplete trong mô phỏng** vì AC-03 về quyền nhân viên chưa có bằng chứng tích hợp phù hợp tại r12. Không có bằng chứng đã thực thi để xác nhận behavior hệ thống thật.

Bạn đã đề xuất cấp tài khoản cho QC và sửa UI-17 trước bước tiếp. Hồ sơ này không thay quyết định đó: nó làm rõ phụ thuộc và điều kiện để xét lại. **Chưa có fix, tài khoản mới, rerun hoặc approval được thực hiện**; mọi hành động bên dưới còn pending, người nhận cụ thể unknown.

## 1. ENV-04 / Q4 — QC chưa kiểm tra được quyền nhân viên trên bản hiện tại

- **Mong muốn:** nhân viên gọi API xuất CSV bị từ chối; không chỉ ẩn nút UI. Điều kiện chuyển bước của case yêu cầu evidence phù hợp trên candidate hiện tại.
- **Lý do:** quản lý và nhân viên có quyền khác nhau; self-test của một hàm và kết quả của bản cũ chưa xác nhận luồng tài khoản/API trên bản mới.
- **Thực tế đang có:** D3 là unit test role guard pass trên r12; Q4 là kiểm tra tài khoản nhân viên gọi thẳng API, blocked vì thiếu tài khoản. Q0 pass ở r11, chưa rerun ở r12. **Chưa biết luồng đó pass hay fail ở r12**; không khẳng định có bug phân quyền.
- **Hành động đề xuất:** người quản lý tài khoản test cấp tài khoản đúng vai trò nhân viên ở môi trường QC. QC kiểm tra vai trò, chạy Q4 trên candidate cuối cùng cần xét và lưu kết quả/revision/môi trường. Cấp tài khoản mới chỉ gỡ blocker, chưa hoàn thành kiểm chứng.
- **Kết quả hiện tại / điều kiện xong:** chưa rerun, vẫn unverified. Đủ để xét lại khi có evidence hợp lệ cho luồng phân quyền trên candidate cuối; nếu fail, cần defect/fix/retest riêng thay vì đánh dấu complete.

## 2. UI-17 — Nhãn nút xuất bị cắt trên màn hình 360 px

- **Mong muốn:** theo yêu cầu xử lý của bạn trong lượt review, sửa nhãn bị cắt trước bước tiếp, thay vì hoãn như đề xuất Frontend trong input. Đây là lựa chọn xử lý issue của TL trong bài tập, không sửa hồi tố AC gốc.
- **Lý do:** bạn nhận xét đây là bug rõ, dễ nhận ra và muốn Frontend xử lý trước. Không tự nâng severity low trong record thành high chỉ vì chọn sửa ngay.
- **Thực tế theo record QC mô phỏng:** ở 360 px nhãn bị cắt, nút vẫn bấm được. Không có ảnh hoặc execution thật được cung cấp, nên hồ sơ không khẳng định đã tự tái hiện.
- **Hành động đề xuất:** Frontend sửa bố cục/nhãn, bàn giao candidate mới nếu code thay đổi. QC xác nhận nhãn đọc được ở 360 px và luồng bấm xuất vẫn hoạt động; ghi expected/actual và revision được kiểm tra.
- **Kết quả hiện tại / điều kiện xong:** issue còn mở, chưa có fix/retest. Không đủ chỉ ghi “Frontend đã sửa”; cần evidence QC tương ứng trước khi bạn xét lại.

## Thứ tự công việc và điều kiện xét lại

| Bước | Vai trò / công việc | Điều kiện hoàn thành |
|---|---|---|
| 1A | Quản lý tài khoản test cấp tài khoản nhân viên; QC xác nhận đúng role | Q4 có thể thực hiện, không chỉ có tài khoản quản lý |
| 1B — có thể song song 1A | Frontend sửa UI-17 và chỉ rõ candidate mới | Có bản sửa để QC retest; chưa coi issue đóng chỉ từ claim |
| 2 — sau 1A/1B | QC kiểm tra Q4 và UI-17 trên candidate cuối, xem lại các check bị ảnh hưởng | Kết quả/revision/môi trường rõ; failure được xử lý, evidence cũ không được gắn sang bản mới |
| 3 | Reviewer/TL đối chiếu các AC, blocker và issue, ghi quyết định | Có evidence phù hợp cho AC bắt buộc, UI-17 đạt điều kiện bạn yêu cầu hoặc có quyết định thay đổi rõ ràng; human decision ghi riêng |

Nếu Frontend tạo r13, gói r12 không tự verify r13. Chọn checks lại theo impact và ghi lý do; hồ sơ chưa tự đặt r13 đã tồn tại hoặc mọi test đã chạy lại. Không có nhiệm vụ nào đã được gửi cho người khác hoặc giao trên hệ thống thật.

## Đối chiếu requirement với nguồn

Nguồn gốc: [requirement/quy trình](../examples/evaluation/e2-qc-handoff/requirements.md), [gói bàn giao](../examples/evaluation/e2-qc-handoff/INPUT.md), [record mô phỏng](../examples/evaluation/e2-qc-handoff/evidence.mock.json). Trong JSON, tìm `records[].id`, `revision` và check ID dưới đây.

| AC | Expected behavior / nguồn | Evidence và revision | Trạng thái hiện tại trong mô phỏng | Gap / hành động |
|---|---|---|---|---|
| AC-01 | Đúng bộ lọc ngày/trạng thái | DEV-12/D1 và QC-12/Q1, r12, pass | verified theo record mô phỏng; không phải thực thi xác nhận | Không tạo finding giả; xét impact nếu candidate đổi |
| AC-02 | Cột và escape CSV đúng | DEV-12/D2 và QC-12/Q2, r12, pass | verified theo record mô phỏng trong scenario được nêu | Giới hạn assertion/coverage chưa có source thật |
| AC-03 | Nhân viên bị từ chối tại API | DEV-12/D3 unit pass ở r12; QC-12/Q4 blocked ở r12; QC-11-AUTH/Q0 pass ở r11 | unverified cho luồng tích hợp r12 | Gỡ ENV-04, QC rerun Q4; không coi D3 là Q4 hoặc r11 là r12 |
| AC-04 | File header và thông báo khi không có dữ liệu | DEV-12/D4 và QC-12/Q3, r12, pass | verified theo record mô phỏng | Xét impact nếu candidate đổi |

Ví dụ cách truy: AC-03 ở requirement → Q4 trong QC-12, `revision=export-r12`, `outcome=blocked` → lý do thiếu tài khoản. Q0 có outcome pass nhưng record là QC-11-AUTH, `revision=export-r11`. Đây là hai record khác revision, không thay thế nhau.

## Finding, quyết định và giới hạn

ENV-04 là verification gap/blocker môi trường được khai báo trong mock, không phải defect authorization đã chứng minh. UI-17 là defect low được báo trong input, chưa được người chuẩn bị tái hiện/adjudicate độc lập. Cả hai đã có trong gói trước khi bạn đọc; không claim framework tìm ra issue mới.

Quy tắc case cho phép TL hoãn bug low có điều kiện; bạn đã chọn sửa trước, là lựa chọn hợp lệ. Hồ sơ không tự đổi thành approval hoặc quyết định chấp nhận rủi ro. Chưa ghi nhận action thực hiện hay verdict sau hồ sơ.

Effort trước/sau và setup/triage: unknown. Không chạy thêm test hoặc bổ sung evidence giữa hai lượt; giá trị tăng thêm của cách tổng hợp còn phải hỏi người dùng. Không thể suy ROI, effectiveness, an toàn app thật hoặc giảm defect từ case này.
