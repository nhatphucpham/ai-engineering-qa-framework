# Hiện hành — commit/push S4-C/D/S5 và mở chat mới, 13/11/2026

User yêu cầu **“Commit push và mở sessiong mới làm tiếp”**. Quyền: commit/push toàn output S4-C/D/S5 + batch đã CLEAN, rồi tạo chat local mới trong cùng project để tiếp critical path. [Pre-push record](CDS5-PUSH-REVIEW-2026-11-13.md) ghi exact snapshot/checks/staging; Git intent chưa là proof push, actual hash/remote xác minh sau action và đưa vào prompt chat mới. Các entry “uncommitted/no Git action” bên dưới là lịch sử lúc nghiệm thu. Nền master32bd110, không reset/clean/stash/force hoặc đổi worktree. Pre-push EOF normalization trên3 new source files + S5 results không đổi behavior; latest actual S4-D R4 và S5v5 hashes được tạo lại, giữ R3/v4 lịch sử.

[Handoff chat mới](NEXT-SESSION-S4E.md): tiếp S4-E versioned trusted-local crash/orphan/helper-loss recovery và reconciliation, prerequisite cho worker thực. Giữ nguyên S4-C R2/S4-D R3/S5v4 evidence và fixtures; không biến metadata retirement/old cleanup bool thành proof tài nguyên sạch. Dùng high-model agent/reviewer theo preference user, tránh đọc/làm trùng vì credit hạn chế. Không mới cài toàn máy, dùng API/account/project/key thật, chọn production stack hoặc publish/pilot. Full product gates vẫn mở theo [batch](PARALLEL-REMAINING-2026-11-12.md).

# Hiện hành — agents mô hình cao: lifecycle + GitHub offline, 12/11/2026

User báo tuần còn20% credit và yêu cầu dùng agent mô hình cao xử lý nhanh phần còn lại. Đã chia hai nhánh độc lập cho2 GPT-6.1 Terra high +1 reviewer Terra high read-only từ đầu; root điều phối actual DB/WSL tuần tự, không chạy đè. Nền master32bd110 đã push; giữ nguyên toàn S4-C uncommitted DONE/CLEAN. [Hồ sơ tổng hợp](PARALLEL-REMAINING-2026-11-12.md) ghi evidence/review/gate còn mở, không suy credit còn lại hoặc % sản phẩm từ số tests.

[S4-D](S4-D-RESULTS.md) R3 actual4 groups PASS18.113s/42 input hashes match: active cancel/complete tranh chấp2 process, fence assignment/renew, cleanup trước terminal, timeout incident và late cleanup giữ failed history. Cleanup thực tế1.18–1.20s, unit/cgroup gone, DB STOPPED. S4D-RV-01/02/03 CLOSED, independent R3 CLEAN selected trusted-local scope. [S5](S5-RESULTS.md) v4 offline6 tests PASS/CLEAN, S5-RV-01 CLOSED; unknown event/revision giữ unresolved, hypothetical correlation seam không là GitHub integration. Fresh core45+S4preflight4+network4+S6B5+S2prereq6=64 checks PASS; cộng S5 là70 unit checks, tách khỏi4 DB/container groups.

Batch **DONE selected scopes — independent holistic CLEAN R2**, all findings CLOSED; required checks PASS. Full gates vẫn mở: crash/orphan/restart/partition/latest-authority restore; continuously supervised remote worker/TLS + durable public control/content API; broker/secret-use/taint/quarantine/sanitized export; proven GitHub occurrence↔revision + durable authenticated adapters; S3 Windows native comparison/desktop, P5 end-to-end và P6 packaging/target. Không app terminal/report_ready product claim từ local lifecycle fixture, không live API/project/account/new packages/stack selection. New output chưa commit/push; không tự sửa fixtures/source/evidence cũ.

# Hiện hành — S4-C live admission / observed cleanup, 12/11/2026

User yêu cầu commit/push + tiếp tục. S4-A/B đã commit **32bd110792c835f982b6f4226f7309425a17ff3c**, push origin/master thành công và ls-remote xác nhận cùng hash; working tree clean trước S4-C. [Pre-push review](S4-AB-PUSH-REVIEW.md) hai consecutive CLEAN, S4-PUSH-RV-01/02 CLOSED. Các Git intent/no-Git/uncommitted bên dưới là lịch sử theo snapshot.

[Protocol S4-C](S4-C-PROTOCOL.md) viết trước code/run; [source](../spikes/s4c/README.md), [results/review](S4-C-RESULTS.md). Actual R2 **C01–04 PASS12.799s /38 source hashes before=after/current match**: live worker DB authority → one-use committed consumption → actual3-process rootless container; duplicate launch denied; revoke-beforeconsume zero launches; revoke-afterlaunch explicit supervision observes denial, stop/removal before cleaned (~1.205s). Unknown-job/wrong-generation/replayed cleanup denied. Postconsume/pre-IO injected failure persists consumed/uncertain; metadata retire/new attempt and retry blocked until owned observation, injected channel outage never fabricates cleanup.

Core45/preflight4/network-parser4 PASS. Pinned existing DB/libs READY, marker-bound DB STOPPED after tests; task transient unit/cgroup absent.373 baseline paths byte-identical trước prepend5 current docs. No new packages/real project/account/API/provider or production-stack choice. S4-C **DONE selected scope — independent CLEAN R2**, S4C-RV-01 reviewer xác nhận CLOSED; required checks PASS.

Scope chỉ trusted local Windows authority + owned Linux helper pipe, không remote/TLS worker authentication. `cleaned` là resource observation, không app cancelled/completed/report_ready. Full gates mở: continuous supervision/durable cleanup incidents+timeouts, user active cancel/complete race, lease/retry, orphan/crash/restart/partition/latest-authority restore, broker/taint/sanitized export/OS keys/end-to-end. Next versioned active lifecycle/incident protocol trước production worker. New S4-C output chưa commit/push; Git quyền user đã có, không suy actual push từ review DONE.

# Hiện hành — commit/push S4-A/B và tiếp S4-C, 12/11/2026

User yêu cầu **“commit và push + tiếp tục”**: cho phép commit/push output S4-A/B đã CLEAN và tiếp bước kế hoạch. [Pre-push review](S4-AB-PUSH-REVIEW.md) ghi exact snapshot/checks/verdict. Git intent chưa là proof push: actual commit/remote hash xác minh sau Git action; current baseline master0d1c453. Các câu “uncommitted”, “No Git action” và baseline trong entry S4-A/B phía dưới là lịch sử lúc nghiệm thu, không hủy quyền Git mới.

S4-A private collector và S4-B selected actual engine controls DONE scoped CLEAN; full product gates vẫn mở. Bước tiếp theo S4-C: protocol có version cho live worker authority → one-use launch admission → actual cleanup; kiểm revoke/expiry trước admission và effect đã in-flight, không coi metadata retirement là proof cleanup. Giữ synthetic, không real API/project/credential, không chọn production stack. Reviewer độc lập từ đầu; chỉ DONE scope sau checks PASS + latest CLEAN.

# Hiện hành — S4-B actual rootless container controls, 12/11/2026

User mới yêu cầu **“cấp quyền hoặc tìm cách run thử”**, cho phép setup/grant cần actual experiment, thay no-system-change default trước trong scope này. Baseline master0d1c453 + uncommitted S4-A giữ nguyên. Đã setup Ubuntu Podman/crun/uidmap/slirp4netns/fuse-overlayfs + busybox-static (20 newly installed packages kể cả deps,0 upgrades), disable lại root Podman units mà package tự bật, không boot/linger/global cgroup permission change. Workload/engine chạy **rootless UID1000**, quyềnroot chỉ setup và transient delegated service.

[Protocol S4-B](S4-B-PROTOCOL.md), [source/README](../spikes/s4b/README.md), [results/review](S4-B-RESULTS.md): latest R2 **6 actual groups PASS17.524s/6 source hashes before=after/current match**. Local signed-package image pinned; readonly/nonroot/capabilities/network-none+cgroup CPU/PID/memory actual probes, OOM/PID/throttle events, actual descendant stop1.104s, private collector mounted-output roundtrip. All task containers removed and transient unit/cgroup absent, root package services inactive/disabled; marked engine caches/packages retained with provenance for reuse. Core45+S4preflight4+network-parser4 PASS.

**S4-B output DONE — independent CLEAN**, S4B-RV-01/02 reviewer xác nhận CLOSED, không finding mới trong scope; required checks PASS. S4-A historical BLOCKED/NOT RUN giữ nguyên đúng snapshot; generic S4-A discovery vẫn không là runnable executor allow gate. S4-B chỉ selected actual engine controls, chưa full S4, authenticated server/IAP-B/worker/cancel-revoke/broker/sanitized export/OS-key/end-to-end readiness.363 original paths/source/evidence byte-exact trước prepend5 current docs. No Git action/real accounts/API/project/production-stack decision. Next authenticated release/cancel/revoke/cleanup integration có version/failure protocol riêng, không dùng standalone harness làm production executor.

# Hiện hành — S4-A inventory/private collector, 12/11/2026

User yêu cầu tiếp S4 theo plan. Checkout master **0d1c4539cd65fdbf38b931dbcf2d39debb1756e7** đã commit/push IAP-A/B từ phiên trước; status sạch lúc mở phiên này. Giữ353 original paths/source/protocol/evidence/fixture byte-exact trước prepend current docs; không Git action trong phiên hiện tại.

[Protocol S4-A](S4-A-PROTOCOL.md), [source/preflight/collector](../spikes/s4/README.md) và [results/review](S4-A-RESULTS.md): actual Windows/WSL inventory chưa tìm runnable engine/runtime trong scope đã kiểm, current WSL cgroup không writable/delegation chưa chứng minh. Actual engine/network/resource/worker cleanup **NOT RUN**, launch gate BLOCKED; không global install hoặc host workload fallback. Linux private FD collector subset R2 **8 groups PASS0.782s/6 input hashes before=after/current match**; Windows preflight4 PASS và core45 PASS33.517s. **S4-A preparation/private collector subset DONE sau independent CLEAN R2 và required checks PASS**; S4-RV-01 CLOSED, không finding trong scope.

Collector pin root/leaf FDs, rejects symlink/FIFO/socket/hardlink/traversal/observed mutation, bounded private bytes/shared budgets; all raw QA content routes deny, no ordinary sanitized/export allow path. Cooperative deadline thôi, chưa hard syscall timeout/process cleanup; no authenticated IAP-B bridge/Vault encrypted quarantine/sanitizer. Source tests thật Linux filesystem không thay actual container/security/readiness proof. Full S4/S6/P3-B/P4-B/product gates còn mở.

Next để actual S4: approved runnable rootless engine + pinned image/disposable context, writable delegated resource/network controls rồi actual failure matrix/release/cleanup/collector integration. Discovery chỉ scope hiện tại, không khẳng định absence mọi nơi hoặc vĩnh viễn. Output mới chưa commit/push; giữ checkout và mọi evidence cũ, không reset/clean/stash/worktree change, real account/key/API/project/pilot/publish/production-stack decision.

# Yêu cầu commit/push IAP-A + IAP-B — 12/11/2026

User yêu cầu **“Commit and push”** cho toàn output IAP-A/IAP-B hiện có đã independent CLEAN trong đúng subset. Phạm vi: source/protocol/results/evidence/current docs trên master nền e8b47a1; không cache/dummy credentials/binaries hoặc implementation mới. [Pre-push review](IAP-AB-PUSH-REVIEW.md) ghi snapshot/checks trước action; đọc Git log/remote và outcome sau action để biết commit/push thực, không dùng intent này khẳng định đã push. Các câu “chưa commit/push/no Git action” trong entries/records trước là lịch sử, không phủ nhận quyền Git mới.

Giữ scope IAP-A queued commands và IAP-B authority metadata DONE/CLEAN; worker thực/cleanup/network/broker/full IAP24 và S4/S6/P3-B/P4-B/readiness còn mở. Không chạy S4 hoặc phát triển thêm trong lượt Git này. Next plan vẫn refresh actual S4 prerequisites và worker release/cleanup integration trước nối reservation authorizer vào executor; không mock PASS/host fallback/production-stack choice/real accounts/keys/API/pilot/publish.

# Hiện hành — IAP-B service/delegation/attempt authority, 12/11/2026

User yêu cầu tiếp tục theo plan. Baseline master **e8b47a18925dc1c64d817e1facd27dc83250f69c + toàn uncommitted IAP-A R5 DONE** được giữ nguyên. Đã thêm [IAP-B protocol](IAP-B-PROTOCOL.md), [source/harness](../spikes/iapb/README.md), [results/review](IAP-B-RESULTS.md): service identity tách user, run delegation live sau logout/access expiry, scheduler/worker audience/epoch/project scope, exact assignment/attempt/fence/deadline và final DB checkpoint. Đây là **authority metadata subset**, chưa actual worker execution/network enrollment/release/broker/cleanup.

Latest R3:8 groups PASS18.069s,41 input hashes before=after/current match; IAP-A regression8 groups PASS18.968s/36 inputs; core45 PASS33.613s + prerequisites5/6 PASS0.720/0.040s. DB đã stop;342 original nonignored paths byte-exact trước prepend current docs, source/protocol/evidence IAP-A và frozen artifacts không đổi. **IAP-B authority metadata subset DONE sau independent CLEAN R3 và required checks PASS**; IAPB-RV-01/02 CLOSED, không finding trong scope. Không commit/push.

IAP-B retire chỉ fence reservation metadata, không cleanup proof hoặc quyền retry actual workload. Background live role/project/grant/policy và credential reset fence old authority; không general membership epoch/restore anti-rollback provider. Full IAP24/S2/S4/S6/P3-B/P4-A/P4-B/readiness vẫn mở. Next sau CLEAN: refresh actual S4 prerequisites và worker release/cleanup integration protocol trước nối authorizer vào executor; thiếu engine không mock PASS/host fallback. Giữ mọi output chưa commit, không reset/clean/stash/chuyển worktree; không real account/key/API/project/pilot/publish/production-stack decision.

# Hiện hành sau push — IAP-A queued-command subset, 12/11/2026

**Commit/push đã hoàn tất**: master `e8b47a18925dc1c64d817e1facd27dc83250f69c`, HEAD/origin/master/actual remote đã kiểm cùng hash và checkout sạch ngay sau push.11 files gồm HS2 handoff/IAP contract/try-run docs/evidence; [pre-push record](IAP-PUSH-REVIEW.md) có2 independent CLEAN rounds, không cache/source/binaries. Các câu chưa commit/push trong phần lịch sử bên dưới không còn là trạng thái của commit này.

Theo user “Commit, push và tiếp tục”, đã triển khai [IAP-A protocol](IAP-A-PROTOCOL.md) và [source/harness mới](../spikes/iap/README.md): user identity/live policy/grant cùng transaction với queued start/cancel/receipt/idempotency; fresh schema, unchanged S6-B auth source, shared identity mutex. [Latest R5/results/review](IAP-A-RESULTS.md):8 selected groups PASS18.014s,36 inputs before=after/current match; core45 PASS33.631s và prerequisite5+6 PASS. Source/evidence cũ331 paths nguyên vẹn trước cập nhật docs; DB đã stop. **IAP-A subset DONE sau independent CLEAN R5 và required checks PASS**; Terra high xác nhận IAPA-RV-01/02/03 CLOSED, không finding chưa xử lý trong scope.

IAP-A chỉ selected interactive/queued DB subparts, không full24 IAP obligations: service/background dispatch, worker/lease/actual cleanup, external release/sink/broker, scoped content/OS keys chưa implemented/NOT RUN. Snapshot grant ceiling và current read authority kiểm lại cả replay; audit/commit failure rollback actual, raw/canonical snapshot selectors chưa trusted artifact resolver. Không production runtime/stack, account/key/API thật/pilot/publish. Full S4/S6/P3-B/P4-A/P4-B và readiness còn mở. Output phát triển sau push hiện **chưa commit/push**, giữ checkout/current+old outputs, không reset/clean/stash/chuyển worktree. Việc tiếp sau CLEAN là service/delegation/attempt authority slice có schema/acceptance/preflight riêng; không tự làm full runtime trong subset này.

# Yêu cầu Git và bước tiếp — 12/11/2026

User yêu cầu **“Commit, push và tiếp tục”** cho toàn output bàn giao HS2, IAP contract và lần chạy thử hiện có đã CLEAN. [Pre-push record](IAP-PUSH-REVIEW.md) kiểm exact snapshot trước Git action; kiểm Git log/remote và handoff mới nhất sau action để biết commit/push thực, không coi intent này là bằng chứng đã push. Những câu chưa commit/push/không có quyền Git trong phần dưới là lịch sử trước yêu cầu mới.

Sau push sẽ tiếp **IAP-A queued-command subset**: common transaction-aware user identity/live policy/start/cancel/idempotency trên fresh synthetic namespace, protocol/selected acceptance trước code. Không broker/service-worker/engine/production stack hoặc gọi account/key/API thật; không dùng subset DONE đóng full S4/S6/P3-B/P4-B. Giữ source/protocol/evidence/fixture cũ; output phát triển sau push để review riêng, chưa tự push tiếp.

# Cập nhật chạy thử — 12/11/2026

Theo yêu cầu “Hãy run thử”, đã chạy **implementation hiện có** với dữ liệu synthetic: S6-B identity/session/RBAC9 groups PASS14.939s và core/report45 tests PASS33.866s. Prerequisites local pins READY; fresh schema/new evidence,31 inputs before=after/current hashes match, DB đã stop/status exit3,328 original nonignored paths không đổi ngay sau run. [Kết quả/evidence/review](IAP-TRY-RUN-2026-11-12.md) **DONE cho hồ sơ chạy thử subset sau independent CLEAN TRY-R1 và required checks PASS**; reviewer Terra high xác nhận không finding trong scope.

Chưa có implementation để chạy24 IAP integration cases: tất cả vẫn NOT RUN integration; lượt chạy này không thêm HTTP/UI/worker/broker/runtime hoặc đóng full S4/S6/P3-B/P4-B. Không source/old protocol/evidence/fixture thay đổi; nội dung docs cũ giữ nguyên phía dưới. No real account/key/API, production stack, commit/push. Việc tiếp vẫn bounded integration harness theo IAP §10 sau scope/schema/selected acceptance mới, không tự triển khai trong lượt chạy thử.

# Session hiện hành — contract IAP-1.0.0, 12/11/2026

Yêu cầu mới từ session tiếp nhận thay trạng thái “chỉ chuẩn bị bàn giao” bên dưới: thực hiện identity→application/live-policy/broker **contract và acceptance/failure protocol**, chưa runtime integration. Baseline master `ef6d3c162ff68fab568d19c8eac9c50892d304c2`; bốn docs bàn giao sau push đã có, giữ toàn nội dung cũ bằng entry mới, không reset/clean/stash/chuyển worktree.

Outputs: [protocol](IDENTITY-APPLICATION-PROTOCOL.md) IAP-1.0.0 với port/source/trust/operation matrices và24 obligations; [review record](IDENTITY-APPLICATION-REVIEW.md); current NEXT/plan/handoff/implementation plan/decision D-32. **DONE docs slice sau independent CLEAN WT-IAP-R2/R2a và required docs checks PASS**; doneWhen docs-only đã đạt: source mapping chính xác, user/service và snapshot/live/private-Vault/broker tách rõ, acceptance có expected/observations/NOT RUN, links/fences/preservation/diff checks PASS và independent Terra high CLEAN trên latest snapshot, stable IAP-RV IDs. Không dùng DONE slice đóng full product gates.

Quyết định ghép: interactive access/family lifetime không là background worker credential. RunDelegation có nguồn/epoch/ceiling riêng; logout/access expiry dừng interactive, còn reset/change/disable/admin-change hoặc project/delegation revoke fence background. Snapshot promotion không mở rộng quyền cũ. Common atomic auth/mutation và external release/revoke ordering là yêu cầu thiết kế, chưa provider/dispatcher implementation. Broker chỉ sink-bound secret-use, không raw-secret/raw-log read/export/stream/attachment/source cho bất cứ role nào.

Checks phiên này chỉ docs/source preservation; không DB/core/runtime rerun, không tạo integration PASS. Reviewer độc lập model cao chỉ định trước sửa; gửi exact snapshot + source/evidence/checks, fix→recheck→re-review đến CLEAN. Kết quả và hashes tại review record. Giữ record HS2 nguyên vẹn, source/schema/protocol/evidence cũ và fixture có lỗi không đổi; thêm current entries để phân biệt lịch sử với tiến độ mới.

Tiếp sau output này: chọn bounded synthetic common-policy/RunCommand harness theo protocol §10, namespace mới + version/schema/selected obligations trước code; không tự bắt đầu ngoài scope phiên contract. S4 actual controls NOT RUN; full S6/P3-B/P4-B còn mở. No real accounts/keys/API/projects, production stack/runtime integration, commit/push/publish.

---

Phần dưới là kế hoạch/bàn giao lịch sử, giữ nguyên bytes; “dự kiến/chưa triển khai slice” áp dụng tại thời điểm bàn giao, không phủ nhận draft contract mới ở trên.

# Plan cho session tiếp — sau push ef6d3c1

12/11/2026. Baseline master **ef6d3c162ff68fab568d19c8eac9c50892d304c2 đã push/remote verified**, gồm57 files S2-C/S6-A/S6-B. [NEXT-SESSION](NEXT-SESSION.md) là entry point; bốn docs bàn giao mới sau push chưa commit, phải giữ/chuyển đủ. Những plan thực thi bên dưới là lịch sử, không là việc cần chạy lại. User hiện yêu cầu chuẩn bị bàn giao; chưa triển khai slice mới hoặc Git action mới.

## Mục tiêu dự kiến cho một phiên

Chốt **contract và acceptance/failure protocol cho identity→application/live-policy/broker** thuộc hướng P3-B/P4-B. Giải quyết chỗ ghép giữa S6-B user/session/snapshot grants, application/core report, S2 transaction/outbox và S6-A private Vault. Đây là protocol/design slice trước integration, không claim có API/worker/broker mới.

Outputs dự kiến (chưa có tại lúc bàn giao): một protocol versioned `docs/IDENTITY-APPLICATION-PROTOCOL.md` có trust/authority/operation matrix, mapping ports→source hiện có và failure matrix; một review record mới cho slice; cập nhật current plan/decision/handoff theo kết quả. Không đổi frozen protocols hoặc migrate các spike cũ để giả đã tích hợp. Nếu phiên sau mở rộng sang harness, ghi scope/acceptance mới trước code và chỉ claim actual behavior đã chạy; không dùng prose contract đóng integration gate.

## Trình tự và điều kiện xong

1. Kiểm Git/remote/status/cache thực; đọc AGENTS/skill/review workflow và current docs. Mang đủ bốn docs chưa commit nếu đổi checkout. Chỉ định high-model reviewer read-only từ đầu, giao scope/source/evidence cùng bản cụ thể.
2. Đọc S6-B `Identity.dispatch`/trusted `_Store`, S6-A Vault/raw-content denial, S2-C/S2-B transactions và `qa_core/application.py`/runtime/publication. Liệt kê port nào có implementation, port nào chỉ thiết kế; không tạo second rules engine hoặc tự chọn production runtime/DB/transport.
3. Chốt user actor vs service/worker identity, credential/session/role/project live state vs persisted snapshot grant, trusted policy provider và thao tác nào cần atomic recheck cùng mutation. Scope project/run/content/version/attempt không suy từ client role/authorized/cleanup flag hoặc ciphertext possession.
4. Mapping tối thiểu start/cancel/read-report/source/export/secret-use: preconditions, owner component, trust input, current policy/epoch fence, deny/error, audit/outbox/rollback/retry boundary. Chỉ rõ raw-secret/raw-log direct read/export/stream/attachment luôn deny mọi role; secret-use qua scoped broker là proposed contract, chưa actual injection. Không tự approve hoặc gửi whole-input replay package ra ordinary read/export.
5. Failure matrix phải phân biệt old/expired/reset/disabled session, refresh replay, cross-project ref, role promotion không mở rộng snapshot/downgrade/revoke, thay policy giữa authorize và write, stale worker/attempt/lease, broker misuse và secret-tainted output. Mỗi case có expected, observation/evidence cần thu và NOT RUN nếu chưa harness; synthetic bool không chứng minh authenticated worker cleanup.
6. Reviewer kiểm đúng latest output: tính chính xác/thực dụng/khả năng kiểm, lỗi cũ/tái xuất hiện/mới. Fix→checks→re-review đến CLEAN, stable IDs, không số vòng tối đa. Docs checks links/fences/diff/source-reference preservation phù hợp; không rerun suite/DB chỉ vì viết plan.
7. DONE chỉ protocol/output sau CLEAN+checks, full runtime integration vẫn open. Bàn giao ghi actual/unknown/next action; không commit/push docs hoặc implementation mới khi chưa được giao.

## Nhánh prerequisite

S4 actual engine controls vẫn NOT RUN từ discovery11/11. Khi công việc cần engine, inventory lại khả năng hiện tại trước khi gọi READY, không assume hôm nay y hệt; cần runnable rootless engine/pinned image và actual network/resource/collector/cleanup evidence. Không global install/host fallback/mock PASS. Protocol độc lập tiếp tục nếu engine thiếu. Local retained PostgreSQL cluster đã stop; chỉ start marker-bound synthetic cluster khi actual DB check được chọn, theo S2 README. Máy mới cần setup/preflight pins trước; cache không ở remote.

## Verification và semantics

Source/core/schema/corpus/goldens/old protocols/evidence giữ nguyên nếu chỉ làm contract. Runtime report/completion proposal và staged replay package chưa là durable completed/outbox hoặc ordinary scoped export. Declared/effective constraints, revision/provenance/input anchors/humanDecision phải bảo toàn; legacy projection unsupported giữ nguyên. No real accounts/keys/API/projects/pilot/publish hoặc production stack/platform choice.

## S2-C đã thực thi (lịch sử)

## S2-C đã thực thi và việc tiếp

User yêu cầu commit/push rồi tiếp: S2-A/B commit e61be7e và remote master verified, checkout sạch trước S2-C. [Protocol](S2-C-PROTOCOL.md) và `spikes/s2c/` model riêng; [R4](s2c-results/2026-11-11-r4.json) DB9 groups PASS38.708s,42 hashes before=after; full45 PASS34.619s/preflight6 PASS0.059s. [Review](S2-C-REVIEW.md) final CLEAN, S2-C subset DONE. S2-C output mới chưa commit/push; giữ old code/protocol/evidence/frozen artifacts.

Ưu tiên tiếp **S4/S6 prerequisite inventory và boundary protocol** cho actual executor/policy/identity, rồi runtime composition/P4-B/C. Kiểm công cụ/khả năng hiện tại, không dùng discovery cũ để assume READY. Chốt purpose/outputs/acceptance/fault matrix trước implementation, actual disposable engine/libs/dummy identities mới đóng integration gates; thiếu prerequisite tiếp phần độc lập và ghi NOT RUN/gap/restore step. Không dùng cleanup bool hoặc metadata restore làm proof container stop/auth/revoke/blob-key recovery. S2-C không tự quyết định production DB/control-worker hoặc chọn desktop/plugin platform; không rerun S1/S2 mặc định khi source không đổi.

## Ghi nhận S2-B trước S2-C (lịch sử)

## S2-B đã thực thi và việc tiếp

11/11/2026, user yêu cầu tiếp. [Protocol](S2-B-PROTOCOL.md) chốt trước sửa; `spikes/s2b/` model riêng và [results](S2-B-RESULTS.md) R4 DB10 groups PASS/32.140s,37 source/input hashes before=after; full regression45 PASS34.940s và preflight6 PASS0.051s. [Review](S2-B-REVIEW.md) final CLEAN, S2-B subset DONE. S2-A source/evidence/33 input paths không đổi, checkout d73dce3 + toàn uncommitted outputs được giữ.

Ưu tiên sau S2-B là S2-C đã được user yêu cầu/thực thi như entry đầu file. DB-only metadata restore không đóng external blob/key recovery. S4/S6 phải kiểm authenticated revoke và actual worker/container cleanup trước full lifecycle gate; giữ NOT RUN đúng boundary, không dùng DB subsets đóng full S2/P3-B/P4-A/P4-B.

## Plan S2-A đã thực thi (giữ acceptance lịch sử)

Ngày 11/11/2026. **Đã thực thi S2-A DB subset, DONE sau clean review trong subset**: [actual results](S2-A-RESULTS.md), [review](S2-A-REVIEW.md). Nội dung bên dưới giữ acceptance/nhánh READY–NOT READY đã dùng, không còn là bước chưa bắt đầu. Đọc [NEXT-SESSION](NEXT-SESSION.md), [ADR-003](adr/003-stack-and-spikes.md). Không coi spike này là production DB/runtime decision.

## Đích phiên và outputs

Tiến từ staged package đã DONE sang **S2-A subset** kiểm chứng concurrent claim + atomic report/completed/outbox trên đúng run/version/attempt, dùng DB riêng synthetic và crash/recovery evidence. Ưu tiên candidate PostgreSQL của ADR-003. Không triển khai toàn server/auth/worker/container/UI trong một lần. Spike language/driver không tự chọn runtime control/worker; Python core vẫn source of truth report semantics.

Outputs đã tạo: `docs/S2-A-PROTOCOL.md`, `spikes/s2/` (preflight/pinned harness/setup-stop), `docs/S2-A-RESULTS.md`, `docs/s2-results/2026-11-11-r1.json` đến `r5.json`, `docs/S2-A-REVIEW.md`, cập nhật plan/decisions/handoff. Versions/input-code hashes/commands/expected-actual/faults/limits nằm trong results và evidence. Không regenerate goldens cũ.

## Trình tự

| Bước | Làm gì | Điều kiện/đầu ra |
|---|---|---|
| 1. Baseline | Kiểm root/branch/HEAD/status thật, tracked + untracked changes; đọc brief/plan/review/decisions; confirm Python executable | Giữ đủ snapshot; không reset/clean/stash |
| 2. Prerequisites | Read-only discovery DB/driver/container tools/versions và khả năng tạo disposable instance; không dump env/secrets hoặc kết nối service thật | READY hoặc NOT READY từ actual observations; không dùng observation 05/11 làm trạng thái hôm nay |
| 3. Chốt slice | Nêu purpose/outputs/acceptance, invariant/fault matrix, scope DB experiment; chỉ định reviewer độc lập high-model trước sửa | Protocol versioned; S2-A subset/gaps rõ |
| 4. Hiện thực | READY: DB harness thật; NOT READY: protocol/preflight/harness độc lập, DB checks NOT RUN | Không dùng mocks để gọi DB gate pass |
| 5. Verify | Behavior/failure/regression theo vùng; before/after DB state và package hashes; đọc nguyên nhân trước retry | Actual evidence và safe diagnostics, không đổi expected để làm xanh |
| 6. Review loop | Gửi đúng latest snapshot + scope/tests/results/gaps/ledger; fix/check/re-review lỗi cũ/tái xuất hiện/mới | Stable IDs, high-model clean + required checks pass; không tự giới hạn số vòng |
| 7. Chốt phiên | Cập nhật plan/decisions/review/handoff/NEXT-SESSION; diff/status cuối | DONE đúng output/slice; completed/partial/not-run và việc tiếp; không tự commit/push |

## READY — actual DB experiment

Chỉ dùng instance/database riêng tạo cho spike với dummy identities/data. Không reuse DB/service công việc thật hoặc tự lấy connection string/secret từ môi trường. Toolchain nếu cần thì dùng project-local/portable/disposable trong quyền có sẵn, verify official version/support/integrity và pin trước chạy; không cài global/thay cấu hình hệ thống. Thiếu quyền/khả năng thì chuyển NOT READY.

1. Adapters/harness ở `spikes/s2/`, tách core. Document DB schema/CAS/uniqueness/claim/transaction semantics và cleanup scope. Payload dùng package v1 hiện tại; round-trip phải giữ canonical bytes/digests và caller-held anchors. Không chỉ đọc normalized JSON rồi giả raw representation/hash được giữ. Blob staging/integrity/durability thật kiểm riêng; thiếu thì không claim durable publication.
2. Seed **100 synthetic jobs**, dùng **2 processes/4 independent DB connections** tranh claim theo ADR-003. Kiểm row-lock/CAS/unique constraints thật, accepted attempts/tokens/versions và no duplicate claim/report/initial occurrence run. Không serialize mọi request trong một process rồi gọi concurrency proof.
3. Thử atomic unit **report metadata ref + completed transition + report_ready outbox row** trong một transaction; validate package và current DB preconditions trong đúng boundary. Concurrent completion/cancel-state transition chỉ một terminal winner. Rollback/commit failure không expose subset. Event chỉ readable/deliverable sau commit; delivery có thể trùng, không hứa exactly-once execution/delivery.
4. Kill/restart harness trước/sau commit, result acceptance và outbox delivery/ack; query từ connection/process khác sau restart. Ghi fault points inject/observe thật, pending points không gộp pass; kiểm accepted rows, sequence/ref, immutable package integrity và retry bounded.
5. Thử stale version/attempt/token, terminal repeat, duplicate IDs và unresolved-cleanup block trong **DB model của spike**. Synthetic permission/revoke/cleanup facts chỉ kiểm persistence predicates, không chứng minh authenticated live policy hoặc worker cleanup. Cancel/revoke/cleanup chưa kiểm đủ giữ gate partial. Thu latency/queue age và môi trường thực, không suy throughput SLA từ fixture.

ADR-003 đặt execution timebox 60 phút **sau khi prerequisites sẵn**: engineering protocol, không SLA user. Hết timebox giữ actual/unknown và bước tiếp, không đổi thresholds/bỏ failures để gọi pass. Review loop không bị cắt vì hết timebox spike; có thể hoàn tất reviewed partial results, không tự đóng S2.

## NOT READY — phần độc lập vẫn làm

Ghi tool/runtime/capability thiếu cùng safe discovery commands/results; không suy absence chỉ vì không có PATH. Hoàn thiện protocol/preflight fail-closed/harness/tests độc lập nếu có thể, review đúng scope. Results ghi DB race/crash/restart **NOT RUN/unknown**; không dựng benchmark hoặc JSON evidence pass. Nếu local disposable setup trong quyền đã có khả thi, tự hoàn thiện rồi chuyển READY; chỉ hỏi khi thiếu quyền/input bắt buộc và nêu quyết định nhỏ nhất.

Có thể DONE **preparation/protocol output** sau clean review/checks, nhưng S2-A DB experiment/S2/full P4-A vẫn PARTIAL/NOT RUN. Không dùng SQLite/mock thay PostgreSQL để đóng candidate gate; phương án so phải có label/scope/evidence riêng.

## Acceptance và bàn giao

- Outputs khớp scope chốt; nguồn/snapshot/version/execution truy được, raw/effective constraints/mapping/provenance/human decision của core giữ nguyên.
- READY: invariants đã chọn có actual DB evidence/checks pass, gaps ghi riêng. NOT READY: preparation được verify/review, DB tests không claim pass và có bước khôi phục.
- Full regression khi code/shared behavior đổi: `py -3 -B -m unittest discover -s tools -p 'test_*.py' -v`, thêm S2-specific tests; 45 methods hiện tại không chứng minh DB correctness. Không mặc định rerun S1 trials hoặc ghi đè fixtures/evidence/goldens.
- High-model reviewer clean trên latest output, stable IDs/reopen lỗi cũ nếu regression. Review record có commands/results/limits/verdict; không đếm rounds thay checks hoặc giữ DONE khi blocker mới xuất hiện.
- Bàn giao completed/partial/gaps/việc tiếp, diff/status và quyền còn thiếu. Không đóng P3-B/S2/P4-A/P4-B hoặc toàn sản phẩm từ một subset.

Sau phiên này tiến theo evidence: full S2 (queue/crash/cancel/revoke/cleanup/fairness/restore), runtime/storage ADR rồi P4-B transaction adapter; scoped read/export, S4/S6, S5 adapters và S3/desktop có prerequisites riêng. Không tự chọn platform/distribution, gọi account/API/project thật, pilot hoặc publish.

## Kết quả và bước tiếp sau S2-A

Actual disposable PostgreSQL18.6/psycopg3.3.8 đã READY qua portable project-local setup. Latest R5: DB14 groups PASS/22.872s, 6 preflight methods PASS, 45 regression methods PASS; output DONE sau final CLEAN trong review record. Working tree dựa d73dce3, chưa commit/push. Không dùng preparation DONE hoặc DB subset PASS đóng full S2/P4-A/P4-B.

Ưu tiên sau S2-A là **S2-B**, đã được user yêu cầu và thực thi như entry hiện hành đầu file. DB persistence subset không thay authenticated revoke hoặc worker cleanup proof; fairness/restore vẫn cần actual evidence riêng. Giữ acceptance/phân biệt READY–NOT READY bên trên như protocol session S2-A, không đọc là S2-B chưa bắt đầu.
