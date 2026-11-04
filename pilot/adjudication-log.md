# Adjudication log

Synthetic-only. Đây là sổ đối chiếu finding, không cấp approval. Người tạo fixture biết đáp án; self-check được tách khỏi verdict reviewer độc lập.

## Kết luận đã có từ walkthrough — không phải kết quả E1

| Finding / case | Nguồn | Kết luận có căn cứ hiện tại | Người đối chiếu / độc lập |
|---|---|---|---|
| F-06-01 — reset trang | [Hồ sơ gốc](mock/MOCK-06-review.md), [sửa](mock/MOCK-06-remediation.md) | Confirmed trong mock; historical và probe reset cùng một lỗi; targeted checks pass trên fixed | Trợ lý tạo case tự đối chiếu; chưa có verdict độc lập |
| F-06-02 — cache | Cùng hai hồ sơ trên | Confirmed trong mock; category sequence tái hiện lỗi; targeted check pass trên fixed | Self-check, chưa độc lập |
| A-06-01 — dấu cách | [v2](mock/MOCK-06-v2.md) | Ambiguity v1 được người dùng chốt cho mock tại v2; không relabel thành defect v1 | Quyết định requirement từ người dùng, execution do trợ lý; không phải approval |
| F-07-01 — đúng ngưỡng | [Hồ sơ 07](mock/MOCK-07-review.md) | Confirmed trong mock; probe ngưỡng fail ở head, pass ở fixed | Self-check, chưa độc lập |
| F-07-02 — phí giao hàng | Cùng hồ sơ 07 | Confirmed trong mock; probe phí fail ở head, pass ở fixed | Self-check, chưa độc lập |

Không tính các dòng này thành finding validity hoặc effectiveness của E1. Không giả lập verdict cho các case chưa được adjudicate.

## Finding E1 — chưa có lượt thực hiện

Khi có candidate, thêm một dòng gồm: run/case/finding ID; category; requirement + source/check + snapshot/execution; expected/actual; impact; nguồn phát hiện; người đối chiếu và mức độc lập; verdict/rationale; action/owner; duplicate-of nếu có.

Verdict: `pending`, `confirmed`, `rejected`, `duplicate`, `disputed`. Candidate chưa có người đối chiếu giữ pending. Duplicate không là issue mới; ambiguity và verification gap ghi riêng với defect. Rejected/disputed có lý do và nguồn. Nếu bổ sung evidence hoặc đổi verdict, thêm mốc/version thay vì xóa kết luận cũ. Không có adjudication thì không tính validity rate.

Xem [protocol](../docs/EVALUATION-PROTOCOL.md) và [task register](task-register.md).
