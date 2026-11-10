# Bắt đầu session mới — P4-A

**Bàn giao: DONE sau review vòng 2.** GPT-6 Astra high đã đóng NS-RV-01/02 và không tìm thấy finding mới trong brief/workflow. Đây là DONE của bản bàn giao, không phải P4-A đã được triển khai.

Bàn giao ngày 10/11/2026 từ session hoàn thành S1. Baseline implementation **d35ae6b337d1450f911d388adce2ee1bd0e3efd8** đã push `origin/master`; working tree sạch trước khi bổ sung hai tài liệu bàn giao này. Session mới phải đọc Git HEAD/status thực, không coi hash baseline là commit HEAD vĩnh viễn hoặc reset checkout để quay về baseline.

## Đọc theo thứ tự

1. `AGENTS.md` và `.agents/skills/qa-framework-development/SKILL.md`.
2. [IMPLEMENTATION-PLAN](IMPLEMENTATION-PLAN.md), phần mới nhất của [SESSION-HANDOFF](SESSION-HANDOFF.md), [CORE-FRAMEWORK](CORE-FRAMEWORK.md), [PRODUCT-DECISIONS](PRODUCT-DECISIONS.md).
3. [ADR-004](adr/004-core-baseline-after-s1.md), [TARGET-ARCHITECTURE](TARGET-ARCHITECTURE.md) nhất là report projection/constraint collision và component boundaries, ADR-001/002.
4. [OFFLINE-REPORT](OFFLINE-REPORT.md), [DATA-CONTRACT](DATA-CONTRACT.md), [VERIFICATION-RULES](VERIFICATION-RULES.md), schema/code/test liên quan P4-A.
5. [S1 results](S1-RESULTS.md), [S1 review](S1-REVIEW.md), [official evidence](s1-results/2026-11-10-r1.json) khi cần đối chiếu. Không chạy lại S1 mặc định chỉ để lấy lại số đo đã có.

## Đang ở đâu?

| Mốc | Đã có | Giới hạn còn lại |
|---|---|---|
| P0 | Scope/use case/actors đã chốt | Chưa đo giá trị sử dụng thực tế |
| P1 | Contract/schema/validator v2, 9 valid và 58 negative cases | Không auth/trust/atomic enforcement |
| P2 | Rules v2 đã sửa false integration coverage/conflict reason; v1 giữ replay | Assessment vẫn là supplied judgments |
| P3-A | Design/ports/boundaries đã review | Chưa runtime dịch vụ trong sơ đồ |
| P3-B/S1 | **DONE**, 356/356 structured cases + 28/28 CLI, ba trials/runtime, 26 unittest methods pass; S1-RV-01..09 đóng | S2–S6 chưa chạy; không đóng P3-B tổng thể |
| P4-A | Reference report/harness offline và quyết định pure-core baseline Python | **Việc làm tiếp ở session mới:** versioned runtime report/constraint integration và module core Python |
| P4-B–E | Có thiết kế control service, worker, adapters và Windows client | Chưa triển khai |
| P5/P6 | Có gate/plan | Chưa technical readiness toàn sản phẩm hoặc installer/package |

Node candidate của S1 nhanh hơn ở workload đã đo và dùng RSS cao hơn. Chọn Python cho **pure shared core/report** để tái sử dụng semantics/versioned artifacts và giữ một implementation production; không khẳng định Python nhanh nhất, không chọn runtime control/worker/DB/shell. TS/Node ở `spikes/s1` là conformance experiment, không engine production thứ hai. Source/package.json/package-lock.json/tsconfig của spike được track trong Git; chỉ installed node_modules, dist và portable runtime/cache dưới `.cache/s1/` được ignore. Không cài global.

## Mục tiêu P4-A kế tiếp

Trước khi sửa, xác định một slice kiểm được và ghi outputs/acceptance. Thiết kế rồi hiện thực contract report/constraint có version để bảo toàn **declared state** và **effective state**, input lineage, criterion/evidence mapping và human decision riêng. Tách pure core/application interface Python dùng chung, không để UI/plugin tự có rules khác hoặc core import provider/desktop/DB SDK.

Collision phải được kiểm rõ: **mandatory** constraint khai satisfied nhưng missing/stale/unaccepted current review → effective pending → verification incomplete khi các mandatory AC đã verified và không có criterion failed khác. Optional constraint pending đơn thuần không chặn complete; nếu có criterion failed, failed vẫn có precedence và các gap còn lại phải được hiển thị. Không sửa raw handoff, hạ AC thành unverified giả hoặc nâng P2 complete để hợp validator. V1/v2 và fixture/evidence cũ giữ nguyên; new schema/output có version rõ và golden/graph/lifecycle tests riêng.

Full runtime report integration cần schema/validator, identity/revision/provenance, report/run consistency và điều kiện report_ready/completed không mất semantics. Chỉ claim phần thực sự có implementation/evidence. Pure graph/predicate test không phải DB transaction/lease enforcement; chưa có server/persistence thì không tự gọi report đã persist. Legacy P1 exporter vẫn projection_unsupported đến khi đường tích hợp mới thật sự hỗ trợ và có kiểm chứng.

Không mở rộng slice đầu này sang server/auth/queue/container/model/GitHub/desktop để gọi sản phẩm đã hoàn tất. Các spike độc lập có thể tiến hành sau khi prerequisite riêng sẵn, theo plan. Agent host, distribution CLI/library/MCP và Windows shell chưa được chọn; không tự publish/pilot hoặc gọi account/key/project thật.

## Cách làm mỗi phase — giữ nguyên qua session

1. Kiểm Git và giữ thay đổi hiện có; đọc plan/decisions/handoff mới nhất. Chọn phase/slice, mục đích, file đầu ra và điều kiện xong trước implementation; đổi hướng phải ghi lý do trong decision log.
2. Luôn chỉ định ít nhất một reviewer độc lập **mô hình cao**. Agent chính làm, reviewer read-only kiểm accuracy/practicality và giải thích vì sao cần cải thiện. Gửi đúng file/snapshot, tests và known gaps, không chỉ tóm tắt chat.
3. Giữ stable finding IDs qua vòng sửa; thêm regression phân biệt behavior lỗi, chạy checks đúng vùng, gửi bản mới re-review cả lỗi cũ/tái xuất hiện/lỗi mới. Không tự dừng theo số vòng hoặc lấy suite xanh thay clean verdict. Thiếu domain decision thì hỏi cụ thể và tiếp tục phần độc lập; không hỏi duyệt lại routine đã được giao.
4. Chỉ mark **DONE trong scope** sau reviewer clean + checks pass. Lưu scope/snapshot/findings/fixes/actual commands/results/limits; phân biệt implementation readiness với approval và whole-product readiness. Xem [REVIEW-WORKFLOW](REVIEW-WORKFLOW.md).
5. Cập nhật plan, decision log và handoff. Giữ synthetic và fixture lỗi/frozen protocols; không đổi expected/evidence để làm xanh. Không tự cài toolchain toàn máy hoặc gọi môi trường thật.
6. Chỉ commit/push output đã review trong **phạm vi được giao và quyền Git người dùng đã cấp**; bản bàn giao này không cấp blanket authorization cho mọi phase tương lai. Trước push áp dụng review-rounds-before-push; thay đổi lớn cần hai vòng sạch liên tiếp, screenshots chỉ khi có UI và phải tự xem. Không suy quyền commit/push thành merge/approve/deploy/public publish.

## Kiểm tra và bàn giao

Lệnh regression hiện có từ repo root, trên interpreter đã xác nhận:

```text
py -3 -B -m unittest discover -s tools -p 'test_*.py' -v
```

26 methods là kết quả baseline đã thực chạy, không số bắt buộc của phase mới; thêm checks theo failure mode. Docs-only không cần rerun toàn suite. Exit/status của mock runner có failure cố ý, không đồng nghĩa app pass; tránh runners ghi đè execution gốc. Không rebenchmark S1 hoặc regenerate goldens cũ khi chưa có thay đổi cần kiểm.

Session mới làm tiếp P4-A ngay sau startup review, hoàn thiện slice và lặp review đến clean, cập nhật bàn giao bằng kết quả thực. Không khởi động lại việc đã DONE chỉ vì context mới, không tiếp tục đề xuất pilot cũ.
