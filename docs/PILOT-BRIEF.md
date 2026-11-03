# Pilot brief — S0 bằng mock

Ngày: 03/11/2026. Phân loại: **synthetic-only**. Trạng thái: S0 có artifact để review; chưa có pilot thật hoặc xác nhận của reviewer thật.

Cơ sở: [kế hoạch triển khai](IMPLEMENTATION-PLAN.md), [template](../templates/quality-record.md), [hướng dẫn mock](../examples/mock/README.md) và nội dung SESSION-01-HANDOFF do người dùng cung cấp trong chat. File `docs/SESSION-01-HANDOFF.md` chưa có tại commit nền `063d25f0577d7bcbbba534073bc5b8dcc3cd8976`; không suy ra yêu cầu bổ sung ngoài nội dung đã cung cấp.

## Người dùng và quyết định

Người dùng mục tiêu là Reviewer/Tech Lead nhận bàn giao task có AI hỗ trợ tại một revision cụ thể, trước quyết định review tiếp theo. Developer chuẩn bị evidence và xử lý gap. Tình trạng AI hỗ trợ của task thật: unknown; các case ở đây hoàn toàn do tác giả tạo.

Quyết định cần hỗ trợ: evidence đã kiểm chứng được AC nào, cần bổ sung check hoặc sửa code ở đâu, và ai xử lý tiếp? Verification tách khỏi quyền review/merge/release. Human decision luôn pending khi chưa có người có thẩm quyền quyết định.

Reviewer thật, domain owner, team thử nghiệm, budget TL/reviewer, overhead chấp nhận được, human effort thực tế và model cost: **unknown**. Vai trò ghi trong walkthrough chỉ là người xử lý đề xuất, chưa phải nguồn lực đã cam kết. Chưa đủ dữ liệu kết luận effort chấp nhận được.

## Phạm vi và inventory

Họ task mock: thay đổi behavior của hàm Python toy với AC rõ, diff nhỏ và test chạy offline. Đây là phạm vi thiết kế chung; chưa chứng minh dùng được xuyên domain. Không có UI/backend/checkout thật, task/code/log/trace thật, API/model call hoặc dependency ngoài Python 3.10+ cho bộ mẫu. Không triển khai CLI/platform/verifier ở S0.

| Case thiết kế | Requirement / code | Evidence ban đầu | Probe và đầu ra walkthrough |
|---|---|---|---|
| MOCK-01 — đối chứng đủ evidence | [requirements](../examples/mock/01-complete/requirements.md) `mock-req-01-v1`; [before](../examples/mock/01-complete/before.py), [after](../examples/mock/01-complete/after.py), [diff](../examples/mock/01-complete/change.diff); head `mock-01-head` | [baseline](../examples/mock/01-complete/test_baseline.py), [CI input giả lập](../examples/mock/01-complete/evidence.mock.json) đúng nhãn head | [probe có sẵn](../examples/mock/01-complete/expected/test_probe.py); [hồ sơ MOCK-01](../pilot/mock/MOCK-01.md) |
| MOCK-02 — gap behavior | [requirements](../examples/mock/02-missing-behavior/requirements.md) `mock-req-02-v1`; [before](../examples/mock/02-missing-behavior/before.py), [after](../examples/mock/02-missing-behavior/after.py), [diff](../examples/mock/02-missing-behavior/change.diff); head `mock-02-head` | [baseline](../examples/mock/02-missing-behavior/test_baseline.py), [CI input giả lập](../examples/mock/02-missing-behavior/evidence.mock.json) đúng nhãn head; mapping AC-02 rỗng | [probe có sẵn](../examples/mock/02-missing-behavior/expected/test_probe.py); [hồ sơ MOCK-02](../pilot/mock/MOCK-02.md) |

[Manifest](../examples/mock/manifest.json) mô tả kết quả fixture dự kiến; [runner](../examples/mock/run.py) chạy code và kiểm tra diff/counts. Nhãn `mock-*-head` là snapshot ID synthetic, không phải Git SHA. Commit nền ở trên xác định phiên bản file được chạy. `evidence.mock.json` là input tác giả soạn, không phải log CI thật.

Chọn MOCK-01 để kiểm tra hồ sơ có tránh tạo defect giả khi evidence đã đủ; chọn MOCK-02 để minh họa suite xanh không verify AC bị bỏ sót. Cả hai là case thiết kế **đã biết đáp án**, kể cả [đáp án 01](../examples/mock/01-complete/expected/quality-record.md) và [đáp án 02](../examples/mock/02-missing-behavior/expected/quality-record.md). Không dùng chúng làm holdout, blind evaluation hoặc bằng chứng tự phát hiện lỗi mới. MOCK-03–05 ngoài walkthrough S0; runner vẫn kiểm tra cả bộ, và đáp án cả bộ đã công khai.

## Bottleneck giả lập và giả thuyết cạnh tranh

| Giả thuyết | Quan sát trong mock | Giới hạn / cách phân biệt tiếp |
|---|---|---|
| H2 — thiếu check behavior cụ thể | MOCK-02 baseline chỉ assert rows; probe page=3 tái hiện lỗi reset | Có căn cứ cho fixture này; chưa biết tần suất ở task thật hoặc review hiện tại đã biết lỗi chưa |
| H3 — khó đối chiếu AC với evidence | Bảng AC làm rõ AC-02 chưa được baseline kiểm tra | Mapping rỗng đã có sẵn trong input; chưa chứng minh hồ sơ bổ sung thông tin hoặc giảm effort reviewer |
| H1 — requirement chưa rõ | AC-02 ở MOCK-02 đã nói rõ mỗi lần filter phải reset page=1 | Không giải thích được gap trong fixture này; không loại trừ H1 ở task khác |
| H4 — review bỏ sót dù đủ context | Source giữ nguyên page và requirement rõ | Không có review thật trước treatment; chưa thể nói reviewer bỏ sót hoặc AI review tốt hơn |
| H5 — verification không hợp risk | Thay đổi state được mock gán medium; baseline không kiểm tra reset | Có thể cùng đóng góp với H2; chưa có chính sách team/risk thực tế để xác nhận |

Bottleneck làm việc cho bước sau: **H2 trong MOCK-02**, chưa phải nguyên nhân gốc ở tổ chức. MOCK-01 là đối chứng tránh mặc định mọi task đều cần thêm check/layer QA.

## Protocol và ghi nhận

1. Đối chiếu requirement, diff/source, assertion, snapshot và input CI giả lập. Ghi trạng thái ở thời điểm chỉ có input baseline; đây là tái dựng từ fixture đã biết đáp án, không phải nhận định mù được đăng ký trước.
2. Chạy probe có sẵn, tách kết quả execution local khỏi CI input. Thiếu evidence là `unverified`; assertion tái hiện behavior sai mới chuyển `failed` trong luồng walkthrough này.
3. Ghi action/owner đề xuất, giới hạn, verification và human decision riêng. Không đếm verification gap và defect cùng behavior thành hai issue độc lập.
4. Ghi count quan sát được; effort/reviewer usefulness/approval chưa có thì unknown/pending. Không suy benefit, false-positive rate, ROI hoặc giảm defect từ fixture.

Kiểm tra ngày 03/11/2026 từ root repo:

```sh
python3 -B examples/mock/run.py
```

Exit **0**, cả 5 case khớp manifest và diff khớp snapshots. MOCK-01: baseline 2 test pass, probe 1 pass. MOCK-02: baseline 2 pass; probe 1 failure (`3 != 1`), 0 error, 0 skipped. MOCK-04 cũng có một probe failure đúng thiết kế. Exit 0 xác nhận fixture đúng thiết kế, không phải tất cả task đạt quality; runner không đánh giá hồ sơ Markdown.

## Tổng kết G0 và bước sau

Phần kỹ thuật làm được bằng synthetic: có hai case truy được requirement/source/test/snapshot, hồ sơ tách input với sau probe, và runner offline xác nhận behavior đã thiết kế. MOCK-01 complete trong phạm vi toy, không có finding; MOCK-02 chuyển AC-02 từ unverified sang failed và cần sửa reset state ở một revision mới nếu làm nhánh sửa minh họa.

**G0 dùng mock có artifact kỹ thuật; G0 có người đánh giá thật chưa được xác nhận.** Reviewer/usefulness, thay đổi hành động so với review hiện tại, budget và overhead đều unknown. Không có human adjudication hay approval thật. Không yêu cầu dữ liệu thật để tiếp tục mock.

Can thiệp nhỏ đề xuất cho S1: giữ hồ sơ thủ công, đối chiếu từng AC với assertion tại head và dùng targeted check cho behavior thiếu. Với MOCK-01, tiếp tục review thông thường; với MOCK-02, đề xuất developer sửa reset page và giữ regression check trong nhánh sửa riêng. Không sửa fixture gốc hoặc đáp án. Chưa đầu tư automation; H3 cần được phân biệt với giá trị trực tiếp từ test. Bước review artifact tiếp theo và owner thật: pending; không tuyên bố G1/usability/effectiveness đã đạt.
