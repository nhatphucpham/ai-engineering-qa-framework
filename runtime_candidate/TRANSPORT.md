# Synthetic loopback HTTPS transport

The operator supplies an application factory and temporary PEM certificate/key. The server binds a numeric IPv4/IPv6 loopback address. The caller starts serving, calls shutdown from another thread, then closes the server. Each valid request creates and closes one application. The recording application in these tests exercises the wire contract. Issuing sessions, checking project roles and grants, storing outbox rows, and serializing release against real revocation belong to application integration acceptance.

```python
server = serve(factory, certificate_path, key_path, host="127.0.0.1")
client = CandidateClient("127.0.0.1", server.server_address[1], certificate_path)
```

The client opens a fresh HTTPS connection per operation. It verifies the IP SAN and trusts only the explicitly supplied certificate file. Both endpoints require TLS 1.2 or newer. Client code supplies the API version and exact fields in every POST body. The application validates them against the [operation matrix](API.md). A successful command that returns accepted=true uses HTTP 202 for run_start, run_cancel and worker_admit. Other operations use HTTP 200. The client returns the application object as a Python dictionary. Application failures carry a fixed safe error code.

## Requests and release

- POST /v1/<operation> requires a known operation, one application/json Content-Type (optional charset=utf-8), one explicit Content-Length up to 1 MiB, and a finite UTF-8 JSON object with unique field names.
- GET /v1/events?project=pA&run=runA&after=0 dispatches events with the adapter-supplied API version, project, run_id and after. The /v1/ route selects the version for GET. The application returns an events list of id/event/data objects. Its query must retrieve only committed records visible for this project/run and detect a cursor beyond the current watermark. The server emits a single SSE page of at most 64 consecutive records, with the sequence starting at after + 1. The client reconnects with the last fully received sequence. A Last-Event-ID header can supply after. If both appear they must match. A cursor gap or a cursor ahead of the watermark requires resynchronization via run_read. A successful empty page means no new events in this read.
- All operations except session_login and session_refresh require one explicit Authorization header with a Bearer token. Requests use HTTP/1.1 with the bound numeric host and explicit port. The transport rejects duplicate headers, transfer/content encoding, browser cookies, browser Origin, upgrades and ambiguous query fields. Each response closes the connection. The server omits request logs and uses fixed diagnostics for malformed requests and unexpected exceptions.
- For session_read, project_list, project_read, run_list, run_read, events, report_read, source_read and report_export, the full encoded response is limited to 64 KiB. For other JSON operations the limit is 1 MiB. Before sending the header, and separately around each body write of at most 4,096 bytes, the transport enters app.release_unit(operation, token, body, result). The app must acquire its authority mutex, recheck current access and hold the mutex through the actual write. Each SSE record also starts a separate release unit. A unit admitted before revocation may send its bounded bytes first. Revocation committed first blocks that unit. Before headers, denial returns a fixed error; after headers, denial closes the connection short of its advertised length. Receivers must discard incomplete JSON and reconcile a possibly committed mutation using its application receipt. CandidateClient never retries a mutation. It returns an SSE page only after receiving the complete body.
- All listeners, application selection, certificate files and process lifetimes are operator-controlled. No system trust setup, deployment or external service is involved in this test.

## Local conformance check

From the repo root in PowerShell, use the provisioned Python 3.14 and the existing pinned test-only cryptography dependency. The test class creates disposable keys/certs in a temporary directory and closes all servers and client connections.

```powershell
$env:PYTHONPATH = (Resolve-Path '.cache/s6/deps').Path
py -3 -B -m unittest -v runtime_candidate.test_transport
```

The tests use real independent TLS connections to a recording application, including a denied release between two body writes and between two SSE records. Actual database authorization ordering, persisted run-scoped outbox replay after restart, and independent worker processes require separate acceptance evidence. These checks make no milestone closure claim.
