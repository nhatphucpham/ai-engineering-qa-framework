# ADR-004 — Pure core Python sau S1

Ngày 10/11/2026. **Accepted engineering direction, trong phạm vi pure core/report cho bước P4-A kế tiếp**; output S1 đã final clean review và DONE trong scope synthetic. Không chốt web framework, server/worker topology/runtime, DB, container engine, desktop shell hoặc agent host.

## Evidence và quyết định

[S1](../S1-RESULTS.md) có native TypeScript/Node parity 356/356 + 28/28 CLI, ba trials, no mutation. Node candidate nhanh hơn ở cả warm batch và import trong official trials, nhưng peak RSS khoảng 104 MB so với 38 MB Python. Không có service latency/concurrency SLA hoặc workload production để coi một runtime thắng toàn diện.

Chọn **Python baseline cho một pure shared core/report**, tái sử dụng semantics/schema/evaluator đã version và được kiểm. Runtime đo là Python 3.14.8; line 3.14 còn supported theo [Python version status](https://devguide.python.org/versions/). Packaging pin/compatibility deployment cần chốt tiếp khi dựng production module, không lấy hướng dẫn fixture Python 3.10+ thành product support matrix.

Đây là **suy luận thiết kế**, không phải benchmark proof: Python hiện không cần lossless numeric/schema compatibility layer bổ sung chỉ để giữ Python-json digest, trong khi TS candidate cần layer đó và bản port rules/report riêng. Chưa có yêu cầu đo được buộc migration. Giữ một source of truth triển khai ở pure core; không đưa TS spike vào production path hoặc hai rules engines cho UI/plugin. Công cụ spike tiếp tục kiểm conformance, không là server đã sẵn sàng.

TS/Node vẫn là implementation khả thi và optimization option có evidence, không bị loại khỏi control/worker/client. API HTTPS JSON/SSE và domain schemas giữ language-neutral. Chưa tự tạo process bridge giữa Node control và Python core; khi chọn control deployment phải xét khả năng dùng core trong cùng service hoặc mở lại ADR, không ngầm thêm topology/IPC mới.

## Điều kiện mở lại

- Có workload/service target đại diện mà baseline không đạt và đo cho thấy bottleneck ở pure core.
- S2/P4 control/worker deployment chứng minh yêu cầu khác về runtime/process composition.
- Versioned wire/canonicalization contract mới giảm gánh compatibility và có conformance evidence tương đương.
- Source/domain rules thay đổi hoặc runtime/library support/security cần nâng phiên bản; chạy lại parity trước promote.

## Bước tiếp

P4-A formalize versioned runtime report/constraint schema + validator/graph/lifecycle tests, raw-input lineage, rồi đóng module core/application interface. Offline report envelope hiện tại không tự thành P1 persisted report/report_ready/completed. S2/S4/S6 và các spike khác thực hiện khi prerequisites riêng sẵn; P5/P6/pilot/public publish không được cấp quyền bởi ADR này.
