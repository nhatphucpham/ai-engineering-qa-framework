# ADR-003 — Stack candidates và spike gate

Ngày 05/11/2026. Status: **proposed — chưa chốt stack**. P3-A design không đủ thay spike gate P3-B. Lựa chọn dưới đây là đề xuất kỹ thuật để kiểm chứng trong plan, không phải preference mới được gán cho người dùng. Không cài toolchain toàn máy hoặc chạy account/project thật trong phiên tài liệu này.

## Candidates và tiêu chí chọn

| Boundary | Candidate ưu tiên cho spike | Phương án so | Lý do dự án / điều chưa biết |
|---|---|---|---|
| Core/control/worker orchestration | TypeScript trên supported Node LTS, schema validator Draft 2020-12 | Python service reuse reference; .NET service nếu deployment fit | Typed client contracts và ports thuận tiện; chưa đo parity/JSON precision/CPU/cancel. Không chọn Node chỉ vì máy có sẵn |
| Metadata/queue | PostgreSQL + transactional outbox + queue table | SQLite single-node harness; broker ngoài nếu workload chứng minh cần | Multi-user/concurrent CAS/claim; cần test race/fairness/backup và ops cost |
| Evidence blobs | Server-local immutable files sau store port | Object storage adapter sau | Triển khai self-host đơn giản; cần quota/containment/atomic publish/backup, no shared worker write mount |
| Windows shell | Tauri + TypeScript UI | Electron cùng UI fixture | Thin client không bundle core server; phải đo startup/memory/installer/bridge/WebView/accessibility, không giả định nhẹ nhất là đủ |
| Worker executor | Linux + rootless OCI engine qua supervisor port | Dedicated engine host khác nếu controls/toolchain cần | Windows client không buộc Windows container; cần resource/network/cancel proof và OS supported matrix |
| API | HTTPS JSON + SSE | WebSocket nếu flow cần bidirectional stream | Chốt ở ADR-002; HTTP framework/validator/client codegen cụ thể chọn sau parity spike |
| Secret store | OS/operator key + encrypted envelope qua store port | External self-host secret service | Chưa chốt crypto library/backend; không tự viết crypto, restore/rotation/revoke trước enable |

Chọn supported version lúc tạo lockfile dựa docs/release/security hiện hành, pin và ghi compatibility matrix; không dùng installed Node version làm product minimum. [Node releases](https://nodejs.org/en/about/previous-releases) là nguồn kiểm khi pin. Không thêm framework agent hoặc SDK provider vào core chỉ vì chọn TypeScript.

Tauri có capability scopes nhưng custom application commands cần cấu hình giới hạn rõ, không suy có Rust là tự an toàn ([capabilities](https://v2.tauri.app/security/capabilities/)). Tauri dùng WebView OS nên runtime phụ thuộc máy ([webviews](https://v2.tauri.app/reference/webview-versions/)). Electron yêu cầu isolation/sandbox/IPC sender validation theo [security guidance](https://www.electronjs.org/docs/latest/tutorial/security). Đây là khả năng/ràng buộc từ docs; mọi đánh giá phù hợp/tối ưu trong bảng là suy luận cần đo, không benchmark vendor.

## Spike protocol — engineering targets, chưa SLA/ngân sách người dùng

Mỗi spike tối đa một phiên kỹ thuật timebox 60 phút **sau khi prerequisites sẵn sàng**, xuất committed notes/results hoặc unknown; không retry vô hạn. Trần benchmark dưới đây là target đề xuất của nhóm phát triển, không production default hoặc cam kết. Fail target cần tìm nguyên nhân/tradeoff, không đổi ngưỡng sau chạy để gọi pass.

| Spike | Workload và điều kiện hoàn thành | Target/đầu ra |
|---|---|---|
| S1 core parity | P1 9 valid/58 negative + P2 55 decisions/20 lifecycle; status/reasons/refs/error classes, no source mutation | Exact semantic parity; strict unknown fields/version rejection; P-05 satisfied-with-missing/stale-review collision phải fail projection rõ ràng, không đổi P2 hoặc raw handoff. Record fixture sizes/runtime/CPU/memory; perf unknown trước run |
| S2 queue/storage | DB riêng synthetic, 2 processes/4 independent connections tranh 100 jobs; kill/restart trước/sau commit/result/outbox; cancel/revoke races | Không duplicate accepted claim/report/initial event run; stale fenced; cleanup unresolved chặn execution mới. Record latency/queue age, no throughput SLA inferred |
| S3 desktop comparison | Same 1k-row synthetic history, paginated report, 1k progress events/10s; Windows release builds Tauri/Electron, same machine/power/state | UI interaction p95 <100ms under load, reconnect lossless sequence, cold start target <3s; idle RSS/package size measured, no preset winner |
| S4 executor/policy | Disposable synthetic container nonroot/read-only/input/output, denied outbound, resource caps, crash/cancel/orphan/revoke | No denied side effect; output symlink/FIFO/swap/oversize quarantined, denied-source/credential→allowed-log outbound blocked; cancel acknowledgement only after observed cleanup; target cleanup <10s on healthy local engine; timeout path failed/pending incident, not fake cancelled |
| S5 GitHub normalization | Auth-free recorded synthetic provider-shape fixtures + official API field review; duplicate delivery, same-SHA second ready, delayed webhook/head advanced, polling gap, same occurrence/two SHA and multi-project fan-out | Canonical common occurrence + exact event revision resolved or explicitly unresolved. No fallback current SHA or guessed timestamp correlation; unresolved does not pass integration gate |
| S6 secrets/identity | Selected maintained libs + disposable keys/accounts, rotation/recovery/revoke/export/log cases | Secret-tainted raw logs quarantined, direct QA read/export/stream/attachment denied for every role; only approved sanitized derivative/metadata. No raw secret in output; reset/refresh replay and cross-project access denied; recover test from documented backup, no actual credentials |

S3 measurements: at least 5 cold launch trials per candidate, fixed Windows/version/hardware/runtime, record samples/median/p95 method; RSS includes all app processes, installed/download size distinguish, no dev-mode numbers. Screenshots at 390/768/1280 with clipping/readability/accessibility checks; native keyboard/file picker/session close/reopen. This is a technical shell fixture, not a disconnected product dashboard or usability/pilot claim.

S2/S4 need actual DB/engine; mock tests alone cannot close them. S5 fixtures cannot prove authenticated provider integration, rate limits or history availability; P4 adapter conformance/P5 readiness retain those gaps. No live GitHub/model calls in this repo session. S1 pass only permits core/harness implementation, not the whole product release. Full report flow còn bị chặn bởi report/constraint contract collision tại TARGET-ARCHITECTURE §5; cần versioned extension/golden tests trước khi công bố full projection.

## Environment observation in P3-A

05/11/2026: command discovery found Node `v26.12.1`, npm `11.20.0`; `rustc`, `cargo`, `docker` not found in PATH. This does not prove absent software/services elsewhere. No Rust/native/container/DB spike executed, no dependencies installed, no benchmark claimed. Python P1/P2 tooling remains development reference.

## Decision after spikes

Publish actual commands, locked dependency/runtime versions, environment, output and limits; compare candidates on the same workload. Promote individual ADR decisions only when relevant checks meet criteria or documented tradeoff is accepted within engineering scope. Stack gate remains open while evidence absent; do not mark P3 complete from docs alone. Missing agent host choice blocks platform manifest/package P6, not shared core/API design. No installer/public release/pilot authorization follows automatically.
