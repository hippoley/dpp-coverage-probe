"""Real end-to-end product smoke: CLI, batch, and HTTP over pinned external engines.

Runs only after CI has installed the official AAS engine and pinned OpenDPP checkout.
No mocks: a real upstream AAS JSON sample is used throughout.
"""
import json
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from dpp_client import DPPClient

UPSTREAM = Path("/tmp/opendpp")
SAMPLE = UPSTREAM / "samples/battery-aas-environment.json"

def execute(*args):
    completed = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, timeout=180)
    if completed.returncode:
        raise RuntimeError("command failed: " + repr(args) + "\n" + completed.stdout + completed.stderr)
    return completed

def main():
    if not SAMPLE.is_file():
        raise RuntimeError("real OpenDPP sample missing: " + str(SAMPLE))
    with tempfile.TemporaryDirectory(prefix="dpp-e2e-") as temp:
        base = Path(temp)
        cli_dir = base / "cli"
        execute("validate_dpp.py", SAMPLE, "--opendpp", UPSTREAM, "--output", cli_dir)
        cli = json.loads((cli_dir / "validation-result.json").read_text())
        if cli["overall"] != "OBSERVED" or set(cli["validators"]) != {"opendpp", "aas_test_engines"}:
            raise RuntimeError("real CLI integration incomplete")

        folder = base / "inputs"
        folder.mkdir()
        (folder / "real-aas.json").write_bytes(SAMPLE.read_bytes())
        batch_dir = base / "batch"
        execute("batch_validate.py", folder, "--opendpp", UPSTREAM, "--output", batch_dir)
        batch = json.loads((batch_dir / "batch-summary.json").read_text())
        if batch["total"] != 1 or batch["observed"] != 1 or batch["failed"]:
            raise RuntimeError("real batch integration incomplete")

        server = subprocess.Popen([sys.executable, "api_server.py", "--host", "127.0.0.1",
                                   "--port", "18765", "--opendpp", str(UPSTREAM)],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        try:
            ready = False
            for _ in range(40):
                if server.poll() is not None:
                    raise RuntimeError("HTTP server exited before ready")
                try:
                    with urllib.request.urlopen("http://127.0.0.1:18765/healthz", timeout=1) as response:
                        ready = response.status == 200
                    if ready:
                        break
                except (urllib.error.URLError, TimeoutError):
                    time.sleep(0.25)
            if not ready:
                raise RuntimeError("HTTP service not ready")
            request = urllib.request.Request("http://127.0.0.1:18765/v1/validate",
                                             data=SAMPLE.read_bytes(),
                                             headers={"Content-Type": "application/json"},
                                             method="POST")
            with urllib.request.urlopen(request, timeout=160) as response:
                api = json.load(response)
            if api["overall"] != "OBSERVED" or set(api["validators"]) != {"opendpp", "aas_test_engines"}:
                raise RuntimeError("real HTTP integration incomplete")
            client = DPPClient("http://127.0.0.1:18765")
            sdk_result = client.validate_file(SAMPLE)
            if sdk_result["input"]["sha256"] != cli["input"]["sha256"]:
                raise RuntimeError("third-party Python client integration mismatch")
            if api["input"]["sha256"] != cli["input"]["sha256"] or api["comparison"] != cli["comparison"]:
                raise RuntimeError("API and CLI disagree for identical real input")
        finally:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        receipt = {"schema": "dpp-product-e2e-v1", "overall": "PASS",
                   "input_sha256": cli["input"]["sha256"], "cli": "OBSERVED",
                   "batch": "OBSERVED", "http": "OBSERVED", "python_client": "OBSERVED",
                   "comparison": cli["comparison"]}
        out = Path("gate-b-evidence")
        out.mkdir(exist_ok=True)
        (out / "product-e2e-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        print(json.dumps(receipt, indent=2))

if __name__ == "__main__":
    main()
