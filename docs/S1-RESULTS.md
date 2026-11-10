# S1 — Kết quả cross-runtime parity

Ngày 10/11/2026, design baseline `c4149bd52a6b0658a78fe8988207f636a50c58b5`. **Technical gate: PASS trên workload được liệt kê. Output: DONE** sau final clean verdict, không còn finding mở trong scope. [Evidence gốc](s1-results/2026-11-10-r1.json) được tạo bằng harness, không viết tay hoặc ghi đè; [protocol](S1-PROTOCOL.md), [review ledger](S1-REVIEW.md).

## Đã thực chạy

Python 3.14.8/jsonschema 4.26.0 đối chiếu native TypeScript 7.0.2/Node **26.13.0 LTS Lithium**, Ajv 8.20.0, @types/node 26.6.6. Windows x64 build 19045. Node portable chỉ trong cache repo, kiểm SHA-256 từ [official archive/checksums](https://nodejs.org/dist/v26.13.0/SHASUMS256.txt); zip SHA `dcc60d59a0746999f99064a01c020445d54d84228c691cdbf25b49ac3b59150a`. Không đổi Node toàn máy, không cài package global hoặc chạy dependency install scripts.

```text
py -3 -B tools/run_s1.py --out docs/s1-results/2026-11-10-r1.json --trials 3
py -3 -B -m unittest discover -s tools -p 'test_*.py' -v
```

Lệnh đầu là provenance của evidence đã có; rerun phải dùng đường dẫn mới. Worker Node tự validate/evaluate/project/check, không gọi Python hoặc đọc expected answers. Parent chỉ gửi inputs; expected invariants được kiểm riêng ở harness, không đưa cho candidate. Reference/candidate chạy lại cả success/error và kiểm input mutation; report output có detachment check.

| Nhóm | Khớp / tổng | Ghi chú |
|---|---:|---|
| P1 valid + negative + legacy version | 68/68 | 9 valid, 58 negatives, 1 explicit legacy rejection; so unique error classes |
| P2 v1 và v2 | 110/110 | 55 mỗi version; mỗi bộ có 10 expected input errors |
| Report generate / validate | 100/100 | 55 generation (10 expected errors), 45 valid checks; full output/reason/ref/action/binding/digest parity |
| Lifecycle + prototype-name edges | 29/29 | 20 frozen cases + 9 adversarial state names |
| Tamper / detachment / v2 regressions | 11/11 | Cross-bundle, status, numeric representation, mapping/version; returned objects detached |
| Numeric / Unicode / malformed document | 13/13 | Unsafe + 310-digit integers, exact-version mismatch, int/float, final LF regex, Unicode, invalid assessment |
| Raw JSON/digest | 25/25 | Duplicate decoded keys, signed zero, exponent, lone/paired surrogate, Unicode key ordering, overflow, deep array |
| **Tổng structured cases** | **356/356** | **0 mismatch, 0 skipped**; invalid inputs đúng class vẫn là parity pass, không app pass |
| **CLI** | **28/28** | Normal 0/1/2, typed errors, invalid UTF-8/BOM/duplicates, typo/extra args; incomplete report check exit 0 |

Source/fixture hashes trước/sau khớp toàn bộ 58 file được harness ghi nhận. Reviewer độc lập đã rehash cả 58 file và chạy 26 unittest methods pass (20.603s). Không chạy fixture runners ghi execution, API/model, DB/container/native desktop.

## Ba lần đo trên cùng workload

331 engine requests, 2,302,348 UTF-8 bytes; bỏ 25 raw-intake cases khỏi benchmark vì reference raw-intake có temp-file IO. Mỗi request chạy hai lần với clone/serialization/no-mutation guards; không phải latency một lần QA hoặc service throughput. Mỗi trial có `outcomesMatchInitial=true`.

| Chỉ số — median (min–max) | Python reference | TypeScript/Node candidate |
|---|---:|---:|
| Parent-observed process wall, ms | 4219.43 (4189.97–4413.39) | 919.27 (911.37–948.39) |
| Import/schema compile, ms | 540.03 (532.90–548.57) | 241.94 (230.53–242.80) |
| Warm guarded batch, ms | 3484.44 (3444.65–3655.13) | 504.66 (499.85–515.55) |
| Warm user CPU, ms | 3406.25 (3250.00–3484.38) | 656.00 (656.00–657.00) |
| Warm system CPU, ms | 15.63 (0–15.63) | 16.00 (15.00–32.00) |
| Peak process RSS, bytes | 38,162,432 (38,031,360–38,281,216) | 103,899,136 (103,870,464–103,952,384) |

Đây là fresh process launches trên cùng máy, không OS cold boot/file-cache flush. Import metric không bao gồm toàn bộ engine startup; parent wall có cả process startup/input/output. Peak RSS gồm imports/schema compile/payload/results, không chỉ pure function working set. Windows Python đo PeakWorkingSetSize, Node maxRSS KiB đổi bytes; user/system CPU đơn vị gốc µs, độ phân giải OS có thể thô. Optional packages của OS khác có trong lock metadata, không có nghĩa đã chạy trên các OS đó.

Node nhanh hơn trong workload đo được và dùng RSS cao hơn. Không suy thành SLA, benefit/ROI hoặc hiệu năng server/concurrency chưa đo. Kết quả first discovery có compile timing khác chiều do caches; bảng chỉ dùng ba official trials này, không chọn một sample thuận lợi.

## Các khác biệt đã xử lý và giới hạn

- BigInt giữ exact value cho comparisons/fencing/output/digest. Chỉ Ajv validation projection dùng finite numeric view với guard: bounds trong safe-number range, không multipleOf, uniqueItems chỉ string domains. Source schema frozen không bị chỉnh; unsupported future schema profile fail setup thay vì âm thầm đổi nghĩa.
- Candidate compiler bảo toàn Python terminal `$` cho final LF trên schema hiện có; parser reject duplicate decoded keys. Lossless numeric wrapper giữ `1`/`1.0`, signed zero và float formatting cho vectors đã kiểm, Unicode key sort theo code points.
- Node depth guard 4096; đã kiểm raw depth 1200. Không tuyên bố parity trên mọi độ sâu, mọi binary64 spelling hoặc schema tương lai. Cần payload limits/compatibility contract rõ trước endpoint production; candidate là spike, không production parser/validator/security boundary.
- Legacy P1 CLI dùng parser permissive lịch sử; S1 so P1 validation API/classes và normal CLI statuses. Strict malformed-byte intake target là corrected evaluator/report; không claim hai parser lịch sử có cùng semantics.

Trần timebox được tính bảo thủ từ clock quan sát 11:30:15 UTC (khi chốt local toolchain) đến official evidence 12:17:00 UTC: khoảng **46m45s**, gồm cả phần chuẩn bị còn lại; nằm trong 60 phút. Official invocation riêng 12:16:07–12:17:00 UTC. Sau đó chỉ review/tài liệu/kiểm regression, không kéo dài benchmark để chọn số đẹp.

## Quyết định và việc tiếp theo

[ADR-004](adr/004-core-baseline-after-s1.md) chọn **Python làm baseline implementation cho pure shared QA core/report ở P4-A**, giữ TS/Node là conformance spike. Đây là suy luận kỹ thuật từ evidence và chi phí duy trì semantics hiện có, không kết luận Python nhanh nhất. S1 semantic parity đã đạt trên workload; P3-B tổng thể còn S2–S6. Tiếp versioned runtime report/constraint integration và đóng module core Python; server/worker/DB/shell vẫn cần quyết định riêng.
