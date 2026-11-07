#!/usr/bin/env python3
"""Preview ./public locally the way Cloudflare serves it: /about -> about.html, _redirects, 404.html.
Usage: python3 tools/serve.py [port]   then open http://localhost:8080
"""
import http.server, os, sys

ROOT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public")
REDIRECTS = {}
for line in open(os.path.join(ROOT, "_redirects")):
    parts = line.split()
    if len(parts) >= 2 and not line.startswith("#"):
        REDIRECTS[parts[0]] = (parts[1], int(parts[2]) if len(parts) > 2 else 302)


class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=ROOT, **k)

    def log_message(self, *a):
        pass

    def do_GET(self):
        path = self.path.split("?")[0].split("#")[0]
        if path in REDIRECTS:
            to, code = REDIRECTS[path]
            self.send_response(code); self.send_header("Location", to); self.end_headers(); return
        if path.endswith(".html") and path != "/":
            self.send_response(307); self.send_header("Location", path[:-5] if path != "/index.html" else "/"); self.end_headers(); return
        fs = os.path.join(ROOT, path.lstrip("/"))
        if path == "/" or os.path.isfile(fs):
            return super().do_GET()
        if os.path.isfile(fs + ".html"):
            self.path = path + ".html"
            return super().do_GET()
        body = open(os.path.join(ROOT, "404.html"), "rb").read()
        self.send_response(404); self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    http.server.ThreadingHTTPServer(("127.0.0.1", port), H).serve_forever()
