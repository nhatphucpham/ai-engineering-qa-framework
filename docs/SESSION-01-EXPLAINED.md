# Đọc nhanh: session S0 đã làm gì?

Tài liệu này giúp bạn đọc kết quả session mà không cần hiểu trước các thuật ngữ trong kế hoạch. Tất cả ví dụ đều là dữ liệu giả lập (synthetic), chạy cục bộ.

## 1. Mục tiêu của công việc

Khi nhận một thay đổi code để review, người review cần trả lời: **Yêu cầu nào đã được kiểm tra, yêu cầu nào còn thiếu bằng chứng, và cần làm gì tiếp?**

Session này bắt đầu **S0**, tức bước chuẩn bị phạm vi thử nghiệm và xem các case mẫu trong [kế hoạch](IMPLEMENTATION-PLAN.md). Để bạn có thứ cụ thể để review, session còn tạo hai hồ sơ đi từng bước qua ví dụ. Chúng minh họa cách đối chiếu yêu cầu với code và test.

## 2. Những việc đã thực hiện

Đã lấy code từ nhánh chính `master` đến commit `063d25f`, đọc kế hoạch và bộ mẫu có sẵn, rồi tạo ba tài liệu:

| Tài liệu | Nó trả lời câu hỏi gì? |
|---|---|
| [PILOT-BRIEF](PILOT-BRIEF.md) | Thử cho ai, hỗ trợ quyết định nào, dùng dữ liệu gì, đang nghi ngờ điểm nghẽn nào và còn chưa biết gì? |
| [Hồ sơ MOCK-01](../pilot/mock/MOCK-01.md) | Khi yêu cầu đã có bằng chứng phù hợp, kết luận và hành động nên là gì? |
| [Hồ sơ MOCK-02](../pilot/mock/MOCK-02.md) | Khi test đang xanh nhưng bỏ sót một yêu cầu, cần kiểm tra thêm và đổi kết luận ra sao? |

Code mẫu, test, bug cố ý và đáp án đã có trước session. Session giữ nguyên chúng và chạy lại bộ kiểm tra. Ba tài liệu trên là phần bổ sung để giải thích, truy nguồn và ghi hành động tiếp theo. File bạn đang đọc là bản hướng dẫn bổ sung sau đó.

## 3. MOCK-01: bằng chứng đã đủ trong ví dụ

Ví dụ là một hàm tính phí giao hàng: tổng dưới 100 thì phí 5; từ 100 trở lên thì miễn phí. Code mẫu đã sửa điều kiện từ `> 100` thành `>= 100` để xử lý đúng mốc 100.

Test ban đầu kiểm tra tổng 20 và 100; cả hai đều đúng. Một test bổ sung kiểm tra 101 cũng đúng. Khi đối chiếu thêm code, hai yêu cầu đều có bằng chứng phù hợp trong phạm vi hàm mẫu.

**Kết quả:** ghi nhận đã kiểm chứng trong phạm vi ví dụ, không tạo thêm lỗi giả. Hành động đề xuất là tiếp tục review thông thường. Việc kiểm chứng này chưa phải quyết định phê duyệt của reviewer.

## 4. MOCK-02: test xanh vẫn có thể thiếu một yêu cầu

Ví dụ là thao tác lọc danh sách. Yêu cầu có hai phần: lọc ra các dòng phù hợp và đưa số trang về 1 sau mỗi lần lọc.

Test ban đầu chỉ kiểm tra danh sách sau lọc. Nó luôn truyền trang 1 và không kiểm tra số trang trả về. Vì vậy, dù hai test đều xanh, chúng chưa chứng minh được yêu cầu reset trang.

| Thời điểm | Điều quan sát được | Kết luận cho yêu cầu reset trang |
|---|---|---|
| Chỉ có test ban đầu | Các dòng được lọc đúng; chưa có test kiểm tra reset | `unverified`: chưa đủ bằng chứng từ baseline |
| Chạy test bổ sung từ trang 3 | Mong đợi trang 1, thực tế vẫn là trang 3 | `failed`: đã tái hiện hành vi sai |

**Kết quả:** đề xuất developer sửa reset trang và thêm test chống tái diễn trên một phiên bản sửa riêng. Bug trong bộ mẫu vẫn được giữ để tiếp tục minh họa case lỗi.

Điều ví dụ này giúp thấy là: **cần xem test kiểm tra yêu cầu nào, ngoài việc xem test có xanh hay không.** Test bổ sung và đáp án đã có sẵn; session không tự phát hiện một lỗi mới chưa biết trước.

## 5. Đọc kết quả chạy test như thế nào?

Đã chạy lệnh sau từ thư mục gốc repo:

```sh
python3 -B examples/mock/run.py
```

Cả 5 case trong bộ mẫu khớp kết quả thiết kế, nên runner kết thúc với mã `0`. Riêng test bổ sung ở MOCK-02 và MOCK-04 cố ý thất bại để tái hiện bug. Runner coi những failure dự kiến đó là đúng thiết kế của bộ mẫu. Vì vậy, mã `0` ở đây có nghĩa **bộ mẫu hoạt động đúng như đã mô tả**; MOCK-02 vẫn có lỗi hành vi.

Runner chạy code/test và kiểm tra diff, số test cùng kết quả dự kiến. Phần diễn giải và kết luận trong hồ sơ Markdown được viết thủ công.

## 6. Một số từ thường gặp

| Từ trong hồ sơ | Cách hiểu khi đọc |
|---|---|
| AC — acceptance criterion | Một yêu cầu cụ thể cần kiểm chứng, như “lọc xong phải về trang 1” |
| Evidence | Bằng chứng hỗ trợ kết luận: assertion trong test, kết quả chạy và code liên quan |
| Baseline | Các test có sẵn trước bước kiểm tra bổ sung; ở đây chưa có baseline review của người thật |
| Probe | Test bổ sung tập trung vào một hành vi cụ thể |
| Snapshot / revision | Phiên bản code mà bằng chứng áp dụng; test của phiên bản cũ chưa đủ chứng minh phiên bản mới |
| `verified` / `unverified` / `failed` | Đã có bằng chứng phù hợp / chưa đủ bằng chứng / có bằng chứng hành vi sai |
| `unknown` / `pending` | Chưa biết hoặc chưa đo / đang chờ quyết định hay xác nhận |
| G0 | Điểm kiểm tra cuối S0: đã có case truy nguồn và người đánh giá để thử ở đâu chưa? |

## 7. Hiện đang ở đâu và nên đọc tiếp gì?

S0 đã có phạm vi thử nghiệm, hai hồ sơ truy được nguồn và kết quả chạy offline. Phần kỹ thuật có thể tiếp tục bằng synthetic. Reviewer thật, độ hữu ích với người dùng, ngân sách và thời gian bỏ ra vẫn chưa được xác nhận; chưa thể công bố G0 với người dùng thật đã đạt hoặc framework giúp giảm lỗi/tiết kiệm thời gian.

Bạn có thể đọc [MOCK-02](../pilot/mock/MOCK-02.md) trước để thấy rõ vấn đề, rồi đọc [MOCK-01](../pilot/mock/MOCK-01.md) để so với case đủ evidence. Sau đó đọc [PILOT-BRIEF](PILOT-BRIEF.md) để xem phạm vi và lý do chọn hướng tiếp theo.

Bước tiếp theo được đề xuất là S1: làm rõ hướng dẫn cốt lõi và thử cách đối chiếu từng yêu cầu với bằng chứng bằng hồ sơ thủ công. Chưa cần xây công cụ tự động. Các thay đổi của session chưa được commit/push.

## 8. Cập nhật: S1 đã có ví dụ nhiều file

Sau S0, session đã tạo [MOCK-06 và hồ sơ review](../pilot/mock/MOCK-06-review.md) cùng [core framework v0](CORE-FRAMEWORK.md). Case mới đi qua UI state, API giả lập, cache và service. Sáu test baseline tại head xanh, nhưng sequence checks tái hiện hai lỗi: giữ sai trang khi đổi category và cache trả nhầm category. Một kết quả test ở base không chứng minh được head; phần yêu cầu whitespace vẫn cần owner chốt.

Bạn nên đọc phần “Kết luận đọc nhanh” của hồ sơ MOCK-06 trước, rồi xem bảng trước/sau và hành động. Đây là bước làm ví dụ phức tạp hơn để kiểm tra cách suy luận; chưa có reviewer độc lập, số đo effort hoặc bằng chứng framework hiệu quả hơn quy trình hiện tại. Các ví dụ vẫn synthetic và không có hệ thống thật được truy cập.
