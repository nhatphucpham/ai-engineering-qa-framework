# Review — P4-A internal report/core slice

Ngày 10/11/2026. Baseline `d8bf1757228f31a8fd0e00f49baeda96741857aa`, master sạch khi bắt đầu. Scope/acceptance: [P4-A-RUNTIME-REPORT](P4-A-RUNTIME-REPORT.md). Delegation session mới yêu cầu tiếp tục P4-A; không suy quyền commit/push.

**Status: DONE trong scope internal report/core + pure completion**, sau clean review WT-P4A-R2 và required checks pass. Full P4-A vẫn partial. Reviewer độc lập GPT-6 Astra, reasoning high, agent `/root/p4a_review`, read-only. Output gồm code/schema/goldens/tests/docs trong diff; snapshot `WT-P4A-R1`. Reviewer đọc files mới nhất, baseline/working tree, actual checks và known gaps.

## Checks trước vòng 1

- `py -3 --version`: Python 3.14.8.
- Sau extraction: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: 26 methods pass, 14.358s.
- Checks mới: `py -3 -B -m unittest discover -s tools -p 'test_runtime_reports.py' -v`: 7 methods pass, 7.650s. Corpus dùng subtests; không gọi 7 methods là chỉ 7 scenarios.
- Full regression cùng lệnh discover: 33 methods pass, 23.194s. Sau thêm subcases candidate/disputed constraint review, targeted 7 methods pass lại, 7.259s.
- AST comparison với `git show HEAD:tools/{validate_contracts,evaluate_rules,project_report}.py`: mọi non-CLI function/class giữ nguyên AST sau extraction.
- `git diff --name-only -- examples schemas pilot spikes`: rỗng với tracked files; chỉ có fixtures/schema mới untracked, không sửa artifacts cũ.
- Local Markdown relative links ở tất cả docs mới/đổi pass; `git diff --check` pass. Không UI/screenshot trong slice.

## Finding ledger / rounds

Vòng 1 `WT-P4A-R1`: CHANGES REQUIRED; reviewer độc lập chạy full 33 methods pass (23.373s) nhưng tìm sáu findings. Các fix dưới đây đã hiện thực ở `WT-P4A-R2`; **reviewer đã xác nhận CLOSED cả sáu IDs trên R2**; không còn finding trong scope.

| ID | Mức | Expected/actual và ảnh hưởng | Fix và regression |
|---|---|---|---|
| P4A-RV-01 | high | P1 snapshot hợp lệ có reports/report_ready cho cùng run nhưng run.reportId null vẫn sinh proposal mới; có thể duplicate publication intent | Reject existing report hoặc report_ready của exact run; test report-only/ready/nonnull ref/completed và foreign run không bị chặn |
| P4A-RV-02 | high | Integral float `9007199254740992.0 + 1` không tăng version/sequence; `10**4300-1` tạo successor không encode được, CLI có thể traceback | Int trước arithmetic, giữ raw digest; kiểm prepared JSON encode trước return, fail safe khi vượt limit. Test exact successor same/other run, both integer bounds và CLI safe error |
| P4A-RV-03 | medium | Unused absolute json_input import làm `from tools.validate_contracts import validate` và module CLI vỡ từ root | Bỏ unused import, subprocess kiểm import/module CLI từ root ngoài unittest sys.path |
| P4A-RV-04 | medium | S1 source guard chỉ hash wrappers sau extraction, bỏ implementation/provenance thật | Thêm qa_core vào source inventory, test file presence/hash; không rerun S1 hoặc đổi evidence |
| P4A-RV-05 | minor | README và plan §4 còn nói extraction là bước chưa bắt đầu, lệch current slice | Update hai entry hiện hành, link slice và liệt kê publication/export/storage/full lifecycle còn mở; giữ audit lịch sử |
| P4A-RV-06 | medium | Regex `$` cho phép new report ID có final LF, kể cả 96 valid chars + LF | Strict new report ID/ref schema với alphabet guard/maxLength; test LF/CRLF/97 length, max valid length và legacy run final-LF compatibility |

R2 targeted: `py -3 -B -m unittest discover -s tools -p 'test_runtime_reports.py' -v`: 11 methods pass, 8.999s. Full `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: **38 methods pass, 26.018s**. AST extraction, frozen tracked artifacts, Markdown links (gồm README mới đổi) và `git diff --check` pass lại. Không regenerate goldens mới hoặc cũ sau fixes; cả ba snapshots vẫn khớp. R2 thêm `tools/run_s1.py`, `tools/test_s1_harness.py`, README vào output scope. Re-review R2 đã clean như verdict bên dưới.

## Giới hạn gate

Internal report + proposal slice, không full P4-A: chưa publication/export manifest, production storage/lifecycle integration, persistence/transaction/outbox, runtime auth/lease hoặc trusted acceptance. Legacy P1 v2 exporter unsupported. S1 không rerun, S2–S6/P4-B–E/P5/P6 chưa đóng; không approval/pilot/publication. DONE chỉ sau clean verdict và required checks pass.

## Final verdict — WT-P4A-R2

GPT-6 Astra high đọc đúng code/schemas/goldens/tests/docs mới nhất và xác nhận **CLEAN**, đóng P4A-RV-01..06, không có finding mới/tái xuất hiện. Reviewer tái hiện thêm successor `1e308`, LF/CRLF/97/U+2028/U+0085 IDs và rehash core inventory; tất cả đúng semantics mới. Independent full regression: **38 methods pass, 24.986s**, `git diff --check` pass. Slice **DONE**; không dùng DONE này đóng P4-A hoặc gate sản phẩm.

Reviewer ghi manifest R2 trước administrative status updates: 33 changed/untracked files, `cb709e5240d6e3c1ed14f9dddd9cf15a49323eff216303f934db678ff773b4a5`; 25 implementation/schema/test/golden paths dưới qa_core/, tools/, schemas/, examples/: `d214ac3b5a0b56d697b5d2a4bc241ac5261d0c040e0d23509d94be6b7ca346de`.

Algorithm: sorted union `git diff --name-only` và `git ls-files --others --exclude-standard`; mỗi dòng là path + ASCII space + SHA256(file bytes), join LF không trailing LF, SHA256 UTF-8 toàn chuỗi. Sau verdict chỉ ghi ledger/verdict và đổi trạng thái hành chính DONE trong README/plan/decision log/handoff, không sửa implementation/contract/goldens hoặc nội dung nghiệm thu. Final check xác nhận manifest implementation 25 paths khớp, Markdown links/diff whitespace pass, frozen tracked artifacts không đổi; full-doc manifest lịch sử không sửa để giả là hash bản hậu verdict. Chưa commit/push.

## Tái xác nhận ngày 11/11/2026

Theo yêu cầu review lại của người dùng, reviewer mới GPT-6 Astra high `/root/p4a_rereview` kiểm cả runtime/core trong [WT-PUB-R2](P4-A-PUBLICATION-REVIEW.md). Verdict CLEAN, P4A-RV-01..06 giữ CLOSED, không thấy regression hoặc finding mới. Full suite hiện tại 45 methods PASS (root 37.113s; reviewer 36.320s); runtime slice DONE trong scope tiếp tục được xác nhận. Không sửa implementation/schema/tests/goldens trong vòng này; manifest lịch sử R2 ở trên giữ nguyên. Full P4-A vẫn partial.
