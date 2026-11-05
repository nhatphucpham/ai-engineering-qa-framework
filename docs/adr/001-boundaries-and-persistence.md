# ADR-001 — Shared core, control plane và transactional persistence

Ngày 05/11/2026. Status: **accepted design**, chưa implemented; stack backend chờ [ADR-003](003-stack-and-spikes.md). Scope theo [P3](../TARGET-ARCHITECTURE.md).

## Context

Desktop Windows và plugin phải dùng cùng rules; multi-user self-host vẫn chạy khi desktop đóng. P1 yêu cầu atomic identity/run/lease/version và P2 cần trusted assessment facts. Không thể coi reference Python hoặc Markdown skill là sản phẩm đã có.

## Decision

- Pure core gồm validation, bounded P2 rules và P1 report projection; không có provider/DB/desktop imports.
- Một modular control service chứa auth/project/intake/orchestration/assessment acceptance/queries. Worker execution là process/host boundary riêng. Không triển khai microservice cho mỗi module ở bản đầu.
- Một transactional metadata store cho auth/config/jobs/receipts/progress/outbox/audit references. Immutable blob store port cho evidence/assessment/report; publish metadata sau bytes integrity/containment checks. Secret store tách dữ liệu QA.
- Mỗi mutation kiểm principal/scope/live revoke, CAS stateVersion và append audit/outbox khi cần. Immutable snapshots, no mutate completed run; retry attempts khác manual rerun.
- Queue metadata trong cùng transaction authority với run trước; chưa thêm Redis/broker để rồi phải xử lý dual write. Adapter boundary cho queue sau, không hứa vô hạn scale.
- Assessment acceptance là trusted application module tạo P2 sidecar từ candidate inference + resolved proof/policy. Không nhận accepted bool làm authority từ model/client.

## Alternatives / consequences

Embedded desktop worker đơn giản hơn nhưng trái yêu cầu background/multi-user. Microservices/broker riêng thêm deployment/consistency cost chưa có nhu cầu đo. DB-only blob dễ tăng tải metadata; external blobs cần orphan recovery và backup phối hợp. SQLite có thể dùng harness nhưng không được dùng test harness để chứng minh server concurrency.

PostgreSQL candidate có row locking và SKIP LOCKED phục vụ queue-like consumers theo [official SELECT docs](https://www.postgresql.org/docs/current/sql-select.html). Khả năng này không tự bảo đảm fairness/fencing/cleanup; cần multi-connection integration spike. Runtime/db versions và driver chưa chốt, không lấy URL current làm version pin.

## Verification / rollback

P4 invariants: duplicate start/occurrence unique; claim CAS/fencing; report+completed+outbox atomic; DB/blob failure recovery; project isolation; input/rules version replay. Giữ ports để đổi backend trước persistence rollout. Sau có data, đổi DB/schema phải có explicit migration/backup/restore, không silent fallback.
