# Validate your own AAS JSON

The public Gate B demo uses a fixed pinned upstream sample. The `validate_dpp.py` command is the **real user-file entrypoint**: it invokes two independent external validator implementations on the file you provide.

## Install

Requires Python 3, Node.js 22+, Git and the pinned official IDTA Python engine.

```bash
python3 -m pip install aas_test_engines==1.0.3
git clone https://github.com/OpenDPP/opendpp-interop.git /tmp/opendpp
git -C /tmp/opendpp checkout --detach 20211ecc2b63eb7664c571a8d629aeeed364491e
npm ci --prefix /tmp/opendpp/validate
```

## Execute

```bash
python3 validate_dpp.py ./my-aas.json --opendpp /tmp/opendpp --output ./my-evidence
cat ./my-evidence/validation-result.json
```

The program executes the **actual OpenDPP Node CLI** and `aas_test_engines.file.check_json_data` against your JSON. The JSON report contains the source file SHA-256, pinned OpenDPP commit and entrypoint digest, IDTA engine version, validator verdicts, and captured OpenDPP output hashes and raw bytes. `AGREEMENT` and `COVERAGE_DIFFERENCE` describe observed scope results, **not** a universal AAS conformance certificate or a defect report.

If either external dependency is missing, a pin differs, or execution fails, the overall result is `NOT_COMPLETED` and the command exits nonzero.

## Current limitations

- Input is an AAS JSON serialization, not arbitrary DPP formats, JSON-LD or AASX.
- This is a local CLI, not yet a hosted API.
- It does not yet emit a cryptographically signed attestation.
- No independent-machine replay receipt exists for this new entrypoint yet.
