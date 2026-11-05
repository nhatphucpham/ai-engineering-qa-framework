# ADR-002 — Typed HTTPS clients, scoped identity và isolated execution

Ngày 05/11/2026. Status: **accepted design**, chưa implemented. [P3](../TARGET-ARCHITECTURE.md) chứa responsibility/flows/errors và giới hạn.

## Decision

Application API dùng HTTPS JSON, server-authoritative commands/queries; progress SSE có sequence replay/snapshot watermark. Desktop native bridge và host-neutral plugin adapter gọi cùng API, không embed check engine hoặc rules riêng. API/admin/worker/assessment envelopes cần spec version ở P4; P1 synthetic bundle không tự là OpenAPI.

Internal account/admin-managed, opaque sessions + rotating refresh, fixed project roles, worker/integration service identities riêng. Password hashing maintained Argon2id theo [OWASP](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html); concrete auth library/settings benchmark còn chờ. Credentials native OS storage, never renderer/localStorage; verify TLS/origin, no token URL. Server check quyền mỗi read/stream/command/side effect; snapshot intersect live policy.

Server secret broker phục vụ project credential references, không export raw secret; encrypted secret store/key backend phải qua spike/security spec. Assessment/domain decision authority không tự có từ quyền Runner. Admin cấp Owner/transfer/recovery có audit, Owner không tự cấp System Admin.

Tests chạy riêng container project/run qua enrolled supervisor và approved config/check IDs; no arbitrary shell API, no privileged flags/socket/mount từ input. Candidate Linux host/rootless engine chờ spike; unsupported network/resource control fail closed. Provider/local reasoning không chạy trong privileged supervisor context; outbound gateway áp cả API và local connector.

## Alternatives / consequences

WebSocket hai chiều chưa cần cho progress một chiều, có thể thêm khi có nhu cầu đo. SSE không tự bảo đảm auth/revoke/backpressure; native bridge phải quản subscription và headers. Native gRPC/MCP chưa chọn làm platform distribution; adapter target có thể map sang API sau khi người dùng chọn host.

Unrestricted host connector tiện nhưng không enforce outbound scope; không enable cho đến chứng minh controls. Rootless container giảm privilege, không là security proof ([Docker rootless](https://docs.docker.com/engine/security/rootless/)). No claim arbitrary hostile repo isolation trước P5. Desktop/user OS first không quyết định worker OS/toolchain support.

## Verification

P4/P5 phải kiểm login/refresh replay/revoke, Owner escalation, cross-project IDs/streams/exports, worker enrollment/revocation, lease/cancel races, prompt injection/raw authority claims, egress denied/redirect/source-summary lineage, container resource/cleanup failure, hostile output collection/no-follow/time-size caps và raw-log taint/denied-source exfiltration. Không có endpoint human auto-approval hoặc source/test edits. Chưa gọi account/API thật trong repo.
