# P3-A — Traceability và kiểm tra thiết kế

Ngày 05/11/2026, nền `337ab82`. [Target architecture](TARGET-ARCHITECTURE.md) và [ADRs](adr/001-boundaries-and-persistence.md) là thiết kế; P3-B spike/stack gate chưa đạt. Review độc lập được ghi sau khi subagent đọc bản nháp; không ghi trước verdict.

## Requirement → owner → kiểm tra dự kiến

| Yêu cầu / contract | Nơi nhận và enforce | Check trước readiness |
|---|---|---|
| Hai intake chung pipeline, stable task/candidate | Intake + scoped artifact store + pure P1 validator | Task/revision conflict, archive/path/symlink/oversize, no hooks |
| Một ruleset UI/plugin | Pure core + typed application API + report projector | P1/P2 cross-runtime parity và client result parity |
| Local agent hoặc OpenAI/Anthropic | Connector/provider ports + gateway + acceptance | Missing connector, refusal, timeout, no uncontrolled egress/fallback |
| QA read/check/report-only | Check registry/executor, no edit/shell API | Input immutable, approved scratch output, no model command escalation |
| Self-host multi-user, desktop đóng vẫn chạy | Control service + DB queue + worker độc lập | Close/reconnect/restart, concurrent users/claims |
| Internal auth/fixed roles/Runner cancel own | Identity/project API, server principal, CAS | Role escalation, own/other cancel, revoke/read/stream |
| Project secret/data scope config | Secret broker + live policy intersection + gateway | Deny before send, derived context lineage, rotate/revoke/redaction |
| Container per project/run | Worker supervisor + isolated runtime | Nonroot/mount/network/resource limits, crash/orphan/cleanup |
| GitHub polling + webhook | Durable receipts + reconciliation normalizer | Same occurrence one run, repeated-ready distinct, exact revision or unresolved |
| Requirement conflict/independent checks | Acceptance + P2, clarification authority | Conflict unverified; independent AC continues; material change new snapshot |
| Freshness/provenance/coverage | Artifact proof resolver + acceptance + P2 | No stale/mock-to-execution upgrade; unsupported judgment pending |
| Finding/action lifecycle và P-05 | Domain authority/basis resolver + P2 predicates + audit | No client authorized bool; no action done without proof; constraint review bound |
| completed khác verification/approval | Partial report projector + terminal transaction | P1/P2 collision → projection_unsupported, no report/completed; versioned contract prerequisite; humanDecision pending |
| Version/storage/recovery | Immutable inputs, DB transactions/outbox/blob registry | Crash boundaries, backup/restore, no silent rules/config migration |
| Windows first, plugin host chưa chọn | Thin desktop bridge + host-neutral client API | Shell spike then installer tests; no host-specific package claim |

## Review / actual checks

Reviewer: subagent GPT-6 Astra, high reasoning, đọc độc lập product decisions/P1/P2/target/ADRs, không edit. Đây là design review, không security certification hoặc implementation acceptance.

| Finding | Severity | Sửa trong bản thiết kế | Gate còn mở |
|---|---|---|---|
| P1 declared constraint vs P2 effective constraint không luôn project được | P1 / blocker bản nháp P3-A | TARGET §5: partial projector, projection_unsupported, no report/completed; S1 golden collision | P4-A phải version contract/validator trước full projection |
| Supervisor thu output thù địch có thể follow link/FIFO hoặc swap | P1 | TARGET §9: quiesced/no-follow/rooted open/regular files/caps, quarantine nếu không enforce | S4/P5 actual engine/output collector tests |
| Denied source/secret có thể được copy vào allowed test_output | P1 | TARGET §9: raw-output taint theo toàn read scope/secret; secret-tainted raw ở restricted quarantine, chặn mọi QA read/export/stream/attachment, chỉ approved sanitized derivative/metadata | S4/S6/P5 denied-source→log, credential→stderr và direct read/export/stream/attachment |
| Full event key có revision nên cùng occurrence/two SHA có thể tạo hai run | P2 | TARGET §10: internal occurrence unique→immutable revision, conflict quarantine; receipt scope/fan-out/backlog | S5 + P4/P5 concurrency/reconciliation |

Actual checks trong phiên:

- Python `3.14.8`; Node `v26.12.1` và npm `11.20.0` từ môi trường máy, không là product pins. rustc/cargo/docker không tìm thấy qua PATH, không kết luận máy hoàn toàn không có chúng.
- Relative links trong target/review/3 ADRs được kiểm tồn tại; diff whitespace check pass.
- Replay read-only bằng `tools.test_rules.scenario_inputs` cho `satisfied-claim-without-review`: P2 verification incomplete. Đưa cùng handoff/evidence và AC verified vào bản sao P1 valid-handoff report: incomplete chỉ lỗi E_REPORT_SUMMARY; đổi complete thì P1 validation pass nhưng trái P2. Replay dùng copy trong memory, không sửa specimen hoặc tạo execution evidence.
- `git diff --exit-code 337ab82 -- tools schemas examples templates pilot` pass: không đổi runtime/reference tooling, schemas, fixture/evidence/protocol cũ. Không cần chạy lại toàn suite cho thay đổi chỉ design docs; collision replay trực tiếp dùng P1/P2 code hiện hành.
- Chưa chạy DB/container/provider/native-shell benchmark hoặc model API trên project; chưa có screenshots app vì chưa có app UI trong step này.

Final independent re-review verdict: **có thể đóng P3-A ở mức thiết kế** sau sửa bốn nhóm finding. Reviewer đã đối chiếu bản cuối với P1/P2 và replay collision độc lập; không thấy blocker P3-A còn lại trong scope đã rà. Đây không là bảo đảm không có sai sót. P3 overall vẫn partial vì ADR-003/P3-B, GitHub history correlation và report-contract integration còn mở; RBAC/lease/secret/DB/container/desktop chưa runtime-verified.
