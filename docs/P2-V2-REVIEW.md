# P2 v2 — audit, correction và legacy replay

Ngày 10/11/2026, nền `9237018`. Review độc lập GPT-6 Astra high tìm hai lỗi; root replay được bằng copies trong memory, không sửa corpus/expected/evidence cũ. GPT-6.1 Terra high review riêng patch v2; không phải author implementation. Reference tooling, chưa production runtime.

| Finding | Trước sửa | V2 / regression |
|---|---|---|
| P1: source reasoning có thể tự gán integration level | source-proof-with-accepted-scope đổi requiredLevels/evidence.level sang integration vẫn verified/complete; P1 validation pass, không executionRef/observedAt | effective_level(source_reasoning)=source_review cho matches/checked; expected incomplete/open; source-only counterexample vẫn failed/open khi integration chưa chạy |
| P2: mixed violation/conflict mất reason | Có clear violation context A và conflict context B, output failed/open nhưng thiếu EVIDENCE_CONFLICT | Reason conflict độc lập status precedence; giữ cả CURRENT_BEHAVIOR_VIOLATION và EVIDENCE_CONFLICT |

`tools/evaluate_rules.py` chọn schema theo assessmentVersion; schema v2 có `assessmentVersion=2.0.0`, `rulesVersion=p2-rules-2.0.0`. V1 validator/semantics/output giữ nguyên để replay lịch sử; schema/corpus v1 không thay. Unknown/mismatched versions và malformed/null/list assessment bị từ chối. Không silent upgrade v1 trong evaluator hoặc report. Hình thức input ngoài version fields tương tự, nhưng migration không tự nâng judgment, authority, authenticity hoặc sufficiency.

`tools/test_rules_v2.py` có 5 methods: 55-case corpus replay trên v2 copies, positive source/integration false-green fix, negative source giữ violation/open, mixed conflict, malformed/version mismatches/no-mutation/repeatability. Corpus v1 nguyên gốc vẫn chạy qua test_rules.py; 20 lifecycle cases không đổi semantics.

Actual root run sau patch: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v` → 13 methods pass (3.809s) trước khi thêm report tests; full run với report → 20 methods pass (9.646s). [Record phiên](P4-A-REFERENCE-REVIEW.md) ghi lần kiểm cuối và review limits. Independent Terra đọc code xác nhận hai fix và explicit v1/v2 dispatch phù hợp scope; không thấy thêm issue trong patch đã rà, chưa chạy độc lập P2 suite ở lượt review đó.

V1 có known limitations, chỉ replay lịch sử; report corrected flow chỉ nhận v2. V2 vẫn dựa supplied accepted judgments, không xác minh domain truth, source content, permissions hoặc execution attestation. S1/runtime acceptance cần kiểm riêng, không lấy pass để cấp readiness/approval.
