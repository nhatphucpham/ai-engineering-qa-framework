# Staged internal publication/replay v1

Ba package goldens synthetic tự chứa toàn frozen inputs và prepared report, manifest và graph candidate. Nguồn inputs giữ nguyên ở [runtime-v1](../runtime-v1/README.md); không regenerate goldens/evidence cũ.

| File | Verification | Processing candidate |
|---|---|---|
| complete.json | complete | completed + report_ready intent |
| constraint-collision.json | incomplete; mandatory declared satisfied/effective pending | completed + report_ready intent |
| failed-pending.json | failed + mandatory pending vẫn hiện | completed + report_ready intent |

Publication state staged, internal restricted replay; chưa persistence/transaction/event/auth hoặc outbound permission. Các trường execution/lease/time là supplied synthetic specimens, không actual execution/lease hiện hành. Không include artifact file bytes; raw metadata vẫn có thể rộng hơn target project/task. Chỉ check với expected input digests/IDs caller giữ độc lập. Xem [contract/cách chạy](../../../docs/P4-A-PUBLICATION.md) và [review](../../../docs/P4-A-PUBLICATION-REVIEW.md).
