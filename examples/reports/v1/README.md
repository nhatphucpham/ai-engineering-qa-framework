# Report goldens v1 — synthetic reference outputs

Ngày 10/11/2026. Hai snapshot mới tạo bằng `tools/project_report.py` từ copies của P2 scenarios; authored execution-shaped records/judgments không phải execution hoặc QA thật. V1 report format dùng assessment/rules v2, không P1 report persistence. Original P1/P2 fixtures và execution evidence giữ nguyên.

| Snapshot | Nguồn synthetic | Expected |
|---|---|---|
| [complete](complete/report.json) | scoped-integration-coverage, versioned assessment copy | complete, scoped assessment, humanDecision pending, P1 export unsupported |
| [constraint-collision](constraint-collision/report.json) | satisfied-claim-without-review, versioned assessment copy | declared satisfied + missing review → effective pending/incomplete, proposed review action, P1 collision diagnostic |

Mỗi folder có bundle.json, assessment.json và report.json được tạo mới, không sao chép report cũ làm evidence chạy mới. Digests ràng buộc parsed input metadata/judgments; không chứng nhận source content, integrity hoặc actor thật. Hai goldens là reference examples có kiểm consistency, không oracle độc lập của domain truth.

```text
py -3 -B tools/project_report.py examples/reports/v1/complete/bundle.json examples/reports/v1/complete/assessment.json --check examples/reports/v1/complete/report.json
py -3 -B tools/project_report.py examples/reports/v1/constraint-collision/bundle.json examples/reports/v1/constraint-collision/assessment.json --check examples/reports/v1/constraint-collision/report.json
```

Đọc [contract/CLI/digest/limits](../../../docs/OFFLINE-REPORT.md) và [tests](../../../tools/test_reports.py). Không overwrite snapshot cũ khi rerun; muốn update golden phải có thay đổi version/semantics được giải thích và review.
