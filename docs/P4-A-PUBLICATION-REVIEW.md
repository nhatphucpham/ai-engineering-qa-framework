# Review — P4-A publication/replay package slice

**Re-review WT-PUB-R2 ngày 11/11/2026: CLEAN — DONE trong hai scope core/runtime và staged internal publication/replay.** Reviewer mới GPT-6 Astra high, read-only `/root/p4a_rereview`, đọc lại output từ đầu và xác nhận P4A-RV-01..06 giữ CLOSED, không có finding PUB-RV mới hoặc lỗi tái xuất hiện. Không sửa implementation/schema/tests/goldens trong vòng kiểm lại; verdict R1 bên dưới giữ như lịch sử. Full P4-A vẫn partial.

Checks root trên R2: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v` chạy mới: **45 methods pass, 37.113s**. Rehash 33 implementation paths vẫn khớp `325c39c933a448434c842c297917e27232c5714f3176b83fd2f96980755fa478`; legacy non-CLI AST, Markdown links, frozen tracked artifacts và `git diff --check` pass. Không dùng kết quả này thay independent verdict.

Ngày 10/11/2026. Git baseline `d8bf175`, cộng WT-P4A-R2 trước đó đã DONE/38 methods pass và chưa commit. User yêu cầu tiếp các bước tiếp theo. Scope/acceptance tại [P4-A-PUBLICATION](P4-A-PUBLICATION.md). **DONE trong scope staged internal publication/replay**, clean verdict xác nhận ngày 11/11/2026. Full P4-A còn partial.

Reviewer độc lập GPT-6 Astra high, read-only `/root/p4a_review`. Snapshot `WT-PUB-R1`: new publication module/schema/harness/tests/goldens/docs, additive application interface và current README/plan/decision/handoff. Stable finding IDs mới PUB-RV-01..., kiểm cả regression P4A-RV-01..06 của slice trước.

## Checks và ledger

- `py -3 --version`: Python 3.14.8.
- Initial `py -3 -B -m unittest discover -s tools -p 'test_publication.py' -v`: 7 methods pass, 10.831s. Sau đó thay assertion tự so chính nó bằng assertion source declaration/evidence thực; full regression sẽ ghi trước review.
- Full `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`: **45 methods pass, 33.469s** trên assertion đã sửa; gồm 7 publication methods và 38 regression trước. Corpus dùng subtests, không coi count methods là số decision inputs.
- AST functions/classes non-CLI của original P1/P2/offline so HEAD vẫn khớp; tracked examples/schemas/pilot/spikes không đổi. Không regenerate runtime-v1/offline-v1 goldens hoặc S1 evidence.
- Relative Markdown links mọi docs mới/đổi và `git diff --check`: pass. Không UI/screenshot.
- WT-PUB-R1 CLEAN: không có finding PUB-RV cần mở; P4A-RV-01..06 của slice trước giữ CLOSED. Không tạo finding giả để đủ vòng.

Không DB/source artifact bytes/worker/model/network/publish/external account. Tests là pure derivation/graph/replay, không transaction/durability hoặc authorization proof. P4-A tổng thể partial; legacy P1 exporter unsupported. Chưa commit/push.

## Final verdict — WT-PUB-R1, xác nhận 11/11/2026

Reviewer GPT-6 Astra high đọc đúng code/schema/harness/tests/goldens/docs mới nhất và xác nhận **CLEAN**, không tìm thấy lỗi mới/tái xuất hiện trong scope. Lượt review trước bị usage limit trước khi trả verdict; khi resume đã nhận completion của independent full suite **45 methods PASS, 33.562s** khởi chạy trước giới hạn. Đây không là full-suite rerun ngày 11/11. Hôm nay reviewer thực chạy probes độc lập: round-trip integral floats/1e308/501-digit integer; encoder boundaries stateVersion/sequence; legacy final-LF run và new report max96; **235 leaf mutations** trong prepared/graph/target/handling/scopes đều bị reject. 38 regression trước pass; AST legacy non-CLI, Markdown links và diff-check pass.

Reviewer rehash snapshot trước administrative updates: **33 implementation paths** dưới qa_core/, tools/, schemas/, examples/ có manifest `325c39c933a448434c842c297917e27232c5714f3176b83fd2f96980755fa478`; **43 total changed/untracked paths** có manifest `6dbdee4015857b6f189a8c6ea92d61a956e952d25e4b9e8361ff22d125fa29f9`. Algorithm như review trước: sorted union git diff --name-only và git ls-files --others --exclude-standard; mỗi dòng path + ASCII space + SHA256(file bytes), join LF không trailing LF; SHA256 UTF-8 toàn chuỗi.

Slice **DONE**: manifest/replay/graph candidate đáp ứng scope/acceptance, no open finding, required checks pass. Sau verdict chỉ cập nhật trạng thái/verdict hành chính; không đổi code/schema/goldens hoặc giả rằng full-doc manifest cũ là hash hậu verdict. Full P4-A/storage/transaction/live policy và scoped read/export còn mở. Chưa commit/push.

## Independent re-review verdict — WT-PUB-R2

Theo yêu cầu kiểm lại DONE, reviewer mới không dựa vào clean verdict cũ. Đã đọc acceptance, core/runtime/publication schemas/code/tests/goldens, kiến trúc và current docs/handoff. **CLEAN**, không cần sửa implementation hoặc mở finding mới. P4A-RV-01..06 giữ CLOSED; không có finding PUB-RV cần xử lý.

Independent run mới: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v` — **45 methods PASS, 36.320s**, Python 3.14.8. Reviewer chạy **638 structural deletion probes** trên package, tất cả reject; numeric integer→integral-float substitutions tại graph/manifest/raw payload bị reject; malformed roots trả safe diagnostics. Legacy non-CLI AST so HEAD, frozen tracked fixtures/schema/evidence và `git diff --check` pass. Root bổ sung 15 parsed-deep-JSON extra-field probes ở runtime/prepared/publication (depth 100/800/970/980/990): tất cả reject, không exception.

Reviewer và root rehash độc lập **33 implementation paths** khớp `325c39c933a448434c842c297917e27232c5714f3176b83fd2f96980755fa478`. Giữ nguyên manifest/code/schema/goldens, không rerun S1 hoặc regenerate evidence. Sau verdict chỉ ghi administrative R2 status/checks/handoff và reference xác nhận lại runtime slice.

**DONE được tái xác nhận cho hai slice** core/runtime và staged internal publication/replay; publication có **2 vòng clean** (R1, R2), runtime có vòng R1 findings → R2 clean trước đó và được kiểm lại trong WT-PUB-R2. Không chuyển slice DONE thành full P4-A DONE: persistence/transaction/outbox, live authorization/lease/trust enforcement, scoped read/export và full lifecycle integration còn mở. Chưa commit/push/publish.
