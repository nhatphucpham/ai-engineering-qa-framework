# Hồ sơ kiểm chứng: <task ID>

Loại dữ liệu: synthetic/mock. Không dùng hồ sơ mẫu làm bằng chứng của task thật.
Snapshot code: <base/head hoặc snapshot ID>. Requirement: <nguồn/version>.
Người chuẩn bị: <vai trò>. Người quyết định: <vai trò hoặc pending>.

## Mục tiêu và risk

Behavior/constraint: <...>
Risk và lý do: <impact, blast radius, reversibility>.
Checks/review bắt buộc theo phạm vi này: <...>.

## Đối chiếu

| AC/constraint | Expected behavior và nguồn | Evidence / snapshot | Trạng thái | Gap / hành động / owner |
|---|---|---|---|---|
| AC-01 | ... | ... | verified / failed / unverified / not_applicable | ... |

Phân biệt trạng thái trước và sau khi bổ sung check. Evidence giả lập chỉ minh họa input; kết quả chạy local trên code synthetic chỉ chứng minh behavior của ví dụ đó.

## Finding và quyết định

- Finding: <ID, defect / ambiguity / verification gap, impact, evidence, cách tái hiện>.
- Trạng thái finding: <candidate / confirmed trong mock / disputed / rejected>.
- Giới hạn/context chưa kiểm tra: <...>.
- Hành động tiếp theo / owner: <...>.
- Verification: <complete / incomplete / failed trong phạm vi đã khai báo>.
- Human decision: <pending; không giả lập một approval thật>.
- Effort: <phút thực đo hoặc unknown; không tự đặt số giả làm số đo>.
