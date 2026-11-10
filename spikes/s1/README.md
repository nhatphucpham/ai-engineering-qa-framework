# S1 native TypeScript/Node parity spike

Private development package, không production core/server. Native implementation không gọi Python hoặc đọc expected results; parent harness chạy oracle riêng. [Protocol](../../docs/S1-PROTOCOL.md), [actual results](../../docs/S1-RESULTS.md), [decision](../../docs/adr/004-core-baseline-after-s1.md).

## Reproduce trên Windows x64

Reference đo với Python **3.14.8** và `jsonschema==4.26.0`; các Python khác có thể khác recursion/JSON behavior và chưa được S1 này xác nhận. Dùng môi trường Python project riêng nếu chưa có dependency, ví dụ venv dưới `.cache/s1/python/`, cài `tools/requirements-contracts.txt` vào venv đó; không cần cài global.

Node pin **26.13.0** (CLI từ chối khác patch). Có thể dùng executable tương ứng đã có, hoặc tải [official portable zip](https://nodejs.org/dist/v26.13.0/node-v26.13.0-win-x64.zip), xác minh với [SHASUMS256](https://nodejs.org/dist/v26.13.0/SHASUMS256.txt), rồi giải nén trong `.cache/s1/runtime/`. SHA-256 zip đo: `dcc60d59a0746999f99064a01c020445d54d84228c691cdbf25b49ac3b59150a`. Không thay Node toàn máy.

Chạy từ repo root sau khi portable runtime ở đúng path:

```powershell
$qaNode = (Resolve-Path '.cache/s1/runtime/node-v26.13.0-win-x64/node.exe').Path
& $qaNode '.cache/s1/runtime/node-v26.13.0-win-x64/node_modules/npm/bin/npm-cli.js' ci --prefix spikes/s1 --ignore-scripts --no-audit --no-fund --cache .cache/s1/npm
py -3 -B tools/run_s1.py --node $qaNode --out .cache/s1/my-new-run.json --trials 3
```

Nếu dùng venv, thay `py -3` bằng executable của venv. Harness compile TypeScript trước chạy, tự tạo và dọn temp inputs; output evidence phải là file chưa tồn tại (exclusive create). Exact dependencies và integrity nằm trong package-lock; lock chứa optional platform packages không có nghĩa tất cả được cài/chạy. Source, schema và corpus hashes được kiểm trước/sau.

## CLI thực

```powershell
& $qaNode spikes/s1/dist/cli.js evaluate examples/rules/v1/base-bundle.json examples/rules/v2/base-assessment.json
& $qaNode spikes/s1/dist/cli.js report examples/reports/v1/constraint-collision/bundle.json examples/reports/v1/constraint-collision/assessment.json --check examples/reports/v1/constraint-collision/report.json
```

Generate exit 0 complete / 1 incomplete-failed / 2 invalid input; check valid incomplete report exit 0. `contract <bundle>` kiểm P1 consistency. Typo/extra arguments reject. JSON diagnostics không echo raw input. Batch mode là internal experiment protocol, không API nhận từ model/UI; source parser/schema adapters là compatibility prototype, chưa production boundary. Measurements Windows-only, không claim performance các OS khác hoặc toàn sản phẩm.
