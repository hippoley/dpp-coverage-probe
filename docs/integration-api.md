# Use DPP Coverage Probe as a service

This is an **experimental local integration API** backed by two real external validator implementations, not a simulated validator.

## Start

Follow [the dependency installation guide](validate-your-own-file.md) to install the pinned OpenDPP checkout, Node.js dependencies and `aas_test_engines==1.0.3`.

```bash
python3 api_server.py --host 127.0.0.1 --port 8765 --opendpp /tmp/opendpp
```

Submit a real AAS JSON serialization:

```bash
curl --fail-with-body -sS -X POST http://127.0.0.1:8765/v1/validate \
  -H 'Content-Type: application/json' \
  --data-binary @./my-aas.json
```

The response includes `overall`, `validators.opendpp`, `validators.aas_test_engines`, `input.sha256` and `comparison`. `OBSERVED` indicates that both external validators executed successfully; it does **not** assert full AAS or DPP compliance. Dependency failure returns HTTP 503.

## Batch CLI

```bash
python3 batch_validate.py ./my-aas-files --opendpp /tmp/opendpp --output ./batch-results
cat ./batch-results/batch-summary.json
```

Each file gets a separate machine-readable result, and `batch-summary.json` summarizes observed/failed executions.

## Deployment boundary

The HTTP server is deliberately bound to localhost by default. It has no authentication, request-rate limiting, TLS, sandboxing or multi-tenant isolation. **Do not expose it directly to the public internet.** Production deployment requires an authenticated reverse proxy, isolation of validator subprocesses, and resource limits. No third-party production adoption is claimed.
