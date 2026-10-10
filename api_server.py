"""HTTP integration for real OpenDPP + IDTA validation; stdlib only.

POST /v1/validate with Content-Type: application/json and a raw AAS JSON body.
GET /healthz for readiness. No uploads are persisted; evidence is returned inline.
Run behind a trusted reverse proxy if exposed outside localhost.
"""
import argparse
import json
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from validate_dpp import MAX_BYTES, run

class Handler(BaseHTTPRequestHandler):
    upstream = Path("/tmp/opendpp")

    def reply(self, status, data):
        body = json.dumps(data, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            return self.reply(200, {"status": "ready", "service": "dpp-coverage-probe"})
        return self.reply(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/v1/validate":
            return self.reply(404, {"error": "not found"})
        if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
            return self.reply(415, {"error": "expected application/json"})
        try:
            size = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            return self.reply(400, {"error": "invalid content length"})
        if size <= 0 or size > MAX_BYTES:
            return self.reply(413, {"error": "payload size outside supported range"})
        body = self.rfile.read(size)
        if len(body) != size:
            return self.reply(400, {"error": "incomplete request body"})
        try:
            json.loads(body)
        except (ValueError, UnicodeDecodeError):
            return self.reply(400, {"error": "invalid JSON"})
        with tempfile.TemporaryDirectory(prefix="dpp-validation-") as temp:
            base = Path(temp)
            source = base / "request.json"
            source.write_bytes(body)
            result = run(source, base / "evidence", self.upstream)
        return self.reply(200 if result["overall"] == "OBSERVED" else 503, result)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--opendpp", type=Path, default=Path("/tmp/opendpp"))
    args = p.parse_args()
    Handler.upstream = args.opendpp
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print("DPP validator API listening on %s:%s" % (args.host, args.port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == "__main__":
    main()
