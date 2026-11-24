# Bàn giao sau M50 — 24/11/2026

## Trạng thái đã xác nhận

Repo `E:/phucpn-workspace/git/ai-engineering-qa-framework`, nhánh `master`. HEAD và `origin/master` đã được đối chiếu cùng **019692b688737340790722474d36b1e264aa9937** sau một lượt push thành công. Workspace sạch trước khi viết bàn giao này. Năm commit đã push:

| Commit | Thay đổi |
|---|---|
| 4f8a5d6 | Chính sách Git giữ đúng byte nguồn/bằng chứng |
| a829fe7 | HC1 orchestration và evidence/native history |
| 0c6f97b | Bounded S4-F supervisor recovery |
| 7df73be | M50 control service và worker/acceptance |
| 019692b | Kết quả ba mốc và hồ sơ review/push |

**7/12 mốc ≈ 58,3%**. P4-A, P4-B, P4-C DONE/CLEAN trong synthetic reference scope; không cộng thêm tiến độ cho bàn giao, số tests hoặc một slice mới. P3-B/P4-D/P4-E/P5/P6 còn mở. Mục tiêu cũ “thêm 3 mốc” đã đạt, không tiếp tục coi nó là active goal hoặc tự đặt đích phần trăm mới.

[Final closure](m50-results/m50-20261124-final-closure.json), [final independent review](m50-results/m50-20261124-final-review.json), [M50 results](M50-RESULTS.md), [pre-push checks](m50-results/m50-push-20261124/checks.json), [two clean rounds](m50-results/m50-push-20261124/review.json). Pre-push record nói chưa push vì được ghi trước commit; kết quả push ở trên đã được xác minh sau thao tác. Các entry 4/12, 50%, “chưa Git/chưa server” bên dưới current prefixes là lịch sử theo snapshot.

Kiểm chứng gần nhất: core45 + HC1 15 + VF1 12 + candidate54 = **126 PASS**; browser A/B ×390/768/1280 ×light/dark = **12 PASS**, ảnh đã xem. Actual integration i9 có40 nhóm PASS; worker r1 có14/14 PASS; S4-F R6 có9 nhóm PASS; fresh normal QA có9 checks với6 pass,3 assertion fail cố ý,0 error/skip. Fresh native C được core chấp nhận; báo cáo gốc được đọc/khôi phục/restart và whole-package core replay, không QA/reason/submit lại. F1/F2/i8 ERROR lịch sử giữ nguyên. Human decision vẫn pending; native reasoning hiện còn session-mediated, không unattended connector.

## Khởi động session mới

1. Đọc `AGENTS.md`, `.agents/skills/qa-framework-development/SKILL.md`, `docs/REVIEW-WORKFLOW.md`; sau đó current prefixes của IMPLEMENTATION-PLAN, DECISION-LOG, SESSION-HANDOFF và tài liệu này. Đọc CORE-FRAMEWORK, PRODUCT-DECISIONS, FRAMEWORK-SCOPE, TARGET-ARCHITECTURE, TECHNOLOGY-DIRECTION và ADR-003 theo phần cần dùng.
2. Kiểm `git status`, branch, HEAD và remote trước sửa. Tài liệu này cùng hai prefix SESSION-HANDOFF/NEXT-SESSION là output local mới sau push, chưa commit/push; giữ nguyên, không coi là thay đổi lạ cần loại bỏ. Review record bàn giao được ghi tại `docs/POST-M50-HANDOFF-REVIEW-2026-11-24.json` sau CLEAN. Không reset/clean/stash, đổi nhánh hoặc tạo worktree tự động.
3. Đọc exact closure/results thay vì chạy lại toàn bộ actual campaigns. DB đã STOPPED sau worker r1; không có DB/container campaign đang chạy do session bàn giao này. Trước effect mới vẫn kiểm marker, DB status và tài nguyên chính xác; chỉ agent chính điều phối shared PostgreSQL/WSL tuần tự, các agent khác chỉ đọc/viết file được giao.
4. Chỉ định reviewer độc lập mô hình cao trước output mới; chuyển ledger liên quan, giữ finding IDs. Review → sửa → kiểm chứng → re-review đến CLEAN, không đặt số vòng tối đa. Nếu model/tool giới hạn, ghi thực trạng, tiếp tục việc độc lập và không tự tuyên bố đã review/invoke/execute.

## Thứ tự công việc kế tiếp được đề xuất

Đây là thứ tự kỹ thuật để tiếp tục trong ranh giới đã có, không là quyết định mới về production stack, provider SDK hoặc agent platform.

### 1. Mở P4-D bằng contract và conformance offline có version

Mục tiêu phiên đầu: nối adapter input tới cùng application API với provenance, scope, dedup và fail-closed được kiểm; không dựng một dashboard rời. Đọc `docs/S5-PROTOCOL.md`, `docs/S5-RESULTS.md`, `spikes/s5/normalizer.py`, `runtime_candidate/API.md`, cùng HC1/FRESH-FLOW trước thiết kế. S5 chỉ có hypothetical pairing seam, chưa chứng minh provider occurrence↔revision; không promote `bind_test_assertion` thành nguồn chứng thực.

- Kiểm capability matrix hiện hành và viết protocol/acceptance trước code. Tách rõ GitHub event ingress, local host connector, OpenAI adapter và Anthropic adapter; ports dùng chung lifecycle và policy, không chia đôi core.
- Với GitHub, xác minh semantics từ tài liệu chính thức hiện hành trước chốt strategy. Polling/webhook phải cùng canonical occurrence và exact event revision **khi có proof được chấp nhận**. Nếu không đủ proof, head đã đổi hoặc history có gap thì lưu unresolved, không fallback sang current HEAD, timestamp gần nhất hoặc tự ghép event.
- Thiết kế conformance synthetic cho duplicate cùng delivery, duplicate cross-ingress có proof, cùng SHA nhưng occurrence khác, delayed delivery/head advanced, missing history, conflict revision, project isolation, cursor/catch-up, restart/replay và revoke/data policy trước intake. Dữ liệu giả lập không tự chứng minh provider thực; không tạo run cho unresolved.
- Tiếp tục bằng một slice nhỏ trong thư mục/protocol version mới, không sửa S5/HC1 đã frozen. Có thể dùng trusted local fixture transport và registration riêng được gắn nhãn rõ để kiểm application boundary; không gọi đó là authenticated GitHub integration. Nếu cần DB/container thật cho slice thì đặt acceptance/evidence trước, giữ namespace/output mới và root chạy tuần tự.
- Local connector và hai provider có conformance riêng về context/digest, timeout/cancel, malformed response, error/budget và no silent retry. Không chọn host/SDK/API version chỉ vì công cụ đang cài sẵn; không gọi key/account/API thật. Session-mediated native evidence HC1/M50 không là connector nền tự chạy.

Điều kiện xong **slice**: protocol/code/evidence cùng version và snapshot, positives và negatives cần thiết đã chạy, tests liên quan đạt, reviewer đọc đúng bản mới không còn findings, ledger/handoff nêu rõ gaps. Full P4-D vẫn OPEN nếu chưa đáp ứng toàn bộ adapters và readiness được phép; count vẫn7/12. Không biến fixture correlation thành full gate PASS.

### 2. Tiếp P3-B/S3 rồi P4-E Windows client

Sau khi boundaries rõ, rà prerequisites và chuẩn bị so Tauri/Electron theo cùng workload/targets ADR-003; giữ lựa chọn mở, không tự cài native toolchain mới hoặc chọn shell/stack. Prerequisite thiếu thì ghi NOT RUN/unknown và tiếp phần độc lập. Native measurement phải có release build, mẫu cold start/RSS/interaction và điều kiện máy theo protocol, không dùng dev browser numbers làm kết luận native.

Windows client phải start/progress/cancel/report/source/export qua **cùng API**; reconnect/cursor/replay và app-close không làm mất worker job, không cấp executor quyền cho renderer. M50 đã chứng minh background driver sau UI fixture exit; điều đó chưa là native Windows client hoặc full P4-E. Browser HTML HC1 chỉ là standalone presentation evidence.

### 3. P5 rồi P6 sau prerequisites

P5 kiểm toàn luồng và failure boundaries/performance theo protocol có trước: isolation/revoke, queue/container/output/network/secrets, report consistency, native responsiveness. Chỉ đóng gate bằng actual evidence đúng scope; không suy ROI, product usability hoặc human approval từ synthetic tests.

P6 cần target/stack quyết định và gate trước đạt: installer/self-host deployment, install/upgrade/uninstall/migration/compatibility. Không tạo manifest/plugin distribution hoặc publish/pilot tự động khi target chưa được chọn.

## Bảo toàn và ranh giới

- Chỉ synthetic; không real task/code/log/project/account/API/key. Giữ MOCK-01–06 và lỗi cố ý, expected outcomes, native responses, manifests, source và các ERROR histories nguyên byte. Không sửa fixture để làm xanh.
- `core.autocrlf=true`; `.gitattributes` đã pin exact new artifacts và37 legacy raw-LF inputs. Windows checkout cuối khớp129/129 worker và38/38 S4-F source pins. Không normalize hàng loạt. Git baseline trước push có517 paths/512 Git blobs không đổi; workspace pre-M50 manifest có649 paths/644 raw files không đổi gồm132 HC1 lúc đó untracked. Hai baseline có doc-suffix offsets khác nhau; xem snapshot pre-push, đừng trộn counts.
- Pinned local Python/PostgreSQL/WSL/rootless runtime và dummy credentials/caches là experiment custody. Caches dưới `.cache/` bị ignore, không push/install/reset/migrate/prune toàn máy. Không dùng status report hoặc metadata retirement thay actual cleanup proof.
- Quyền commit/push trước đã hoàn tất cho năm commit nêu trên. Yêu cầu mới là bàn giao/tạo session; không tự coi đó là quyền push implementation tiếp theo. Không cần hỏi lại các việc đọc/sửa/test thuận nghịch trong phạm vi phát triển đã giao; chỉ nêu quyết định thiếu khi công việc thực sự phụ thuộc.
