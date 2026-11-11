# Internal runtime report proposals v1 — synthetic only

Ba snapshots mới cho [P4-A slice](../../../docs/P4-A-RUNTIME-REPORT.md), không thay goldens offline v1. Mỗi thư mục có frozen `bundle.json` (P1 v2), `assessment.json` (P2 v2), `prepared.json` (internal runtime report + completion proposal v1).

| Snapshot | Verification | Constraint | Processing proposal |
|---|---|---|---|
| complete | complete | Không constraint | completed + report_ready intent |
| constraint-collision | incomplete | Mandatory declared satisfied, review missing → effective pending; AC vẫn verified | completed + report_ready intent |
| failed-pending | failed | Counterexample + mandatory pending cùng hiện | completed + report_ready intent |

Run/lease/timestamps/execution labels là specimens do tác giả soạn; không là worker execution/current lease thật. Publication proposed, event chưa emitted, report chưa persisted, human decision pending. Validator không chứng minh auth/trust/transaction. Inputs/expected mới tạo riêng cho slice; không regenerate evidence/corpus/goldens cũ. Tests compare snapshots và thêm semantic assertions.
