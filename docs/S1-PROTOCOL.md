# S1 — Cross-runtime parity protocol

Baseline `c4149bd52a6b0658a78fe8988207f636a50c58b5`, ngày 10/11/2026. **Technical workload PASS; output DONE sau final clean review**. [Results](S1-RESULTS.md) và [ADR-004](adr/004-core-baseline-after-s1.md) ghi evidence/quyết định pure core; các stack boundaries khác chưa chọn. Scope: native TypeScript/Node candidate so với Python reference, synthetic only; không DB/container/UI/model/GitHub integration. Reviewer độc lập: GPT-6 Astra high, architecture_review; root thực hiện code và fixtures mới.

## Mục tiêu và outputs

`spikes/s1/` là package riêng, exact dependency lock và local runtime; `tools/run_s1.py` tạo inputs/reference outputs trong memory/temp, gọi candidate và đối chiếu kết quả; `docs/S1-RESULTS.md` cùng JSON kết quả ghi actual/gaps/metrics. Không thay Python reference/schema/corpus/fixture frozen để candidate pass. Candidate không gọi Python hoặc đọc expected answers; chỉ native validation/rules/projector được tính parity.

Điều kiện: P1 9 valid/58 negative so valid và tập error classes; P2 55 scenarios trên v1/v2 so toàn structured output hoặc tập lỗi; 20 lifecycle cases so errors; report v2 so output/bindings/actions/traces và validate tamper/cross-input; CLI 0/1/2 và check incomplete hợp lệ trả 0. Schema messages/path formats có thể khác nhưng không bỏ error classes để che divergence. Legacy P1 CLI permissive khác strict evaluator/report intake, phải ghi rõ boundary đang so.

Thêm discriminators source mislabeled integration v1/v2, mixed violation/conflict/plan, mandatory constraint missing/stale/current review, independent blockers và repeatability/no-mutation cả success/error. Raw vectors: duplicate decoded keys, Unicode supplementary/lone surrogate, safe/large integers, integer/float/exponent/signed zero; report digest Python serialization phải được đối chiếu riêng. Unsupported input không được âm thầm mất precision hoặc thành pass; ghi mismatch/blocked và giữ gate mở nếu còn gap bắt buộc.

## Runtime, protocol và số đo

Node LTS pin theo nguồn chính thức tại lúc chạy, không lấy installed Node làm product minimum; dependencies exact trong package-lock. Không cài toolchain toàn máy. Record versions/OS/arch, corpus sizes/counts, before/after input/source hashes, wall/CPU/memory theo units và process boundary. Tách cold startup/schema compile khỏi warm engine; không dùng số test làm hiệu năng, không SLA hoặc tuyên bố production readiness.

ADR-003 đặt timebox 60 phút **sau prerequisites sẵn sàng**; ghi start/end actual và phần chưa thực hiện. Nếu giới hạn runtime/dependency/numeric semantics chưa khép, ghi partial/unknown cùng recovery, không đổi ngưỡng hoặc gọi spike pass từ subset. S1 đóng không tự đóng P3-B vì queue/shell/executor/GitHub/secrets spikes còn riêng.

## Review loop

S1-RV IDs ổn định; reviewer kiểm accuracy/practicality và discriminating evidence, root sửa và gửi snapshot mới. Chỉ mark output DONE sau vòng sạch; gate S1 PASS cần đủ parity chứ không chỉ công việc ghi kết quả đã hoàn tất. Tách output DONE khỏi technical gate partial/failed nếu có limitation được chứng minh.
