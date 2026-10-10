"""Minimal third-party Python client for the real DPP validation HTTP service.

No dependency on the server repository or non-stdlib packages is required.
"""
import argparse
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class DPPValidationError(RuntimeError):
    pass


class DPPClient:
    def __init__(self, endpoint="http://127.0.0.1:8765", timeout=180):
        self.endpoint = endpoint.rstrip("/")
        self.timeout = timeout

    def validate_bytes(self, payload: bytes):
        if not isinstance(payload, bytes):
            raise TypeError("payload must be bytes")
        request = Request(self.endpoint + "/v1/validate", data=payload,
                          headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urlopen(request, timeout=self.timeout) as response:
                result = json.load(response)
        except HTTPError as exc:
            try:
                details = json.loads(exc.read())
            except (ValueError, UnicodeDecodeError):
                details = {"error": "unparseable server error"}
            raise DPPValidationError("HTTP %s: %s" % (exc.code, details.get("error", details))) from exc
        except URLError as exc:
            raise DPPValidationError("validator service unavailable: " + str(exc)) from exc
        if result.get("overall") != "OBSERVED":
            raise DPPValidationError("validation incomplete: " + str(result.get("error", "unknown")))
        return result

    def validate_file(self, path):
        return self.validate_bytes(Path(path).read_bytes())


def main():
    p = argparse.ArgumentParser(description="Call a real external DPP validator service")
    p.add_argument("file", type=Path)
    p.add_argument("--endpoint", default="http://127.0.0.1:8765")
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = DPPClient(args.endpoint).validate_file(args.file)
    except (DPPValidationError, OSError) as exc:
        p.exit(2, str(exc) + "\n")
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered)
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
