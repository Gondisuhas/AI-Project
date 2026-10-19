"""BugPilot AI frontend server.

Serves frontend/index.html and exposes /api/analyze so the dashboard
can actually run the debugging agent against a local repository.

Run:
    python frontend/server.py
    then open http://localhost:8090/
"""

import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = FRONTEND_DIR.parent

sys.path.insert(0, str(PROJECT_ROOT))

from agent.engine import run_agent  # noqa: E402

PORT = 8090


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, fmt, *args):
        sys.stderr.write("[frontend] " + fmt % args + "\n")

    def _send_json(self, payload, status=200):
        body = json.dumps(payload, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != "/api/analyze":
            self._send_json({"error": "Unknown endpoint"}, 404)
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            payload = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as exc:
            self._send_json({"error": f"Bad JSON: {exc}"}, 400)
            return

        repo = (payload.get("repo") or "").strip()
        language = (payload.get("language") or "auto").strip().lower()
        try:
            attempts = int(payload.get("attempts", 3))
        except (TypeError, ValueError):
            attempts = 3

        if language in ("auto", ""):
            language = None

        if not repo:
            self._send_json({"error": "Repository path is required."}, 400)
            return

        root = Path(repo).expanduser()
        if not root.is_dir():
            self._send_json(
                {"error": f"Folder does not exist: {root}"}, 400
            )
            return

        try:
            result = run_agent(
                root,
                max_attempts=max(1, min(attempts, 5)),
                use_ollama=bool(payload.get("use_ollama", False)),
                language=language,
            )
        except Exception as exc:  # surfaced to the UI, not swallowed
            self._send_json({"error": f"{type(exc).__name__}: {exc}"}, 500)
            return

        self._send_json({"result": result})


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"BugPilot AI frontend: http://localhost:{PORT}/")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()
