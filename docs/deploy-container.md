# Run the real validator service in a container

The Docker image **installs both external implementations** at build time:
- OpenDPP `opendpp-interop` pinned to `20211ecc2b63eb7664c571a8d629aeeed364491e`
- Official IDTA `aas_test_engines==1.0.3`

## Build and launch

```bash
docker compose build validator
docker compose up -d validator
curl --fail http://127.0.0.1:8765/healthz
curl --fail-with-body -X POST http://127.0.0.1:8765/v1/validate \
  -H 'Content-Type: application/json' --data-binary @my-aas.json
```

The service is only published on the host's loopback interface. The container runs as a non-root user with a read-only root filesystem, bounded temporary filesystem, reduced Linux capabilities, and CPU/memory limits. The application still invokes third-party validator code and **has not been independently penetration-tested**. Do not expose directly to the public internet: authentication, rate limits and ingress policy must be provided by a trusted gateway.

## Integrate from another Python repository

Copy `dpp_client.py` or vendor it as a dependency, then:

```python
from dpp_client import DPPClient
result = DPPClient("http://127.0.0.1:8765").validate_file("my-aas.json")
assert result["overall"] == "OBSERVED"
```

## Verification status

Container configuration is committed, but no successful container build/run receipt has yet been obtained. `/healthz` currently checks HTTP process availability, not validator dependency readiness. Validate a real AAS file before treating the service as ready for use.
