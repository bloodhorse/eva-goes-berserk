"""Local server for the dream-stream front: serves this folder and forwards eva's data.

The browser only ever talks to this server. /api/* and /stream/plate/* are fetched from
eva.x server-side and handed back as if they were ours — so there is no cross-site block,
and the plates count as same-origin, which the glass look needs (it reads their pixels;
a cross-origin picture taints the canvas and the look silently shows nothing).

eva.x is signed by the mini's own Caddy CA; eva-root.crt (public, pulled from the mini)
lets us verify it properly instead of switching TLS checks off.

run (from dreamshit/, stdlib only):
  uv run --python 3.12 front/serve.py        →  http://127.0.0.1:8766/
stdlib only, no packages.
"""
import http.server
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVA = 'https://eva.x'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
FORWARD = ('/api/', '/stream/plate/')
TLS = ssl.create_default_context(cafile=str(HERE / 'eva-root.crt'))


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=str(HERE), **kw)

    def do_GET(self):
        if self.path.startswith(FORWARD):
            return self.forward()
        return super().do_GET()

    def forward(self):
        try:
            with urllib.request.urlopen(EVA + self.path, context=TLS, timeout=20) as r:
                body = r.read()
                self.send_response(r.status)
                self.send_header('Content-Type', r.headers.get('Content-Type', 'application/octet-stream'))
                # the stream must never be served stale; plates carry ?v= and may be cached
                self.send_header('Cache-Control', 'no-store' if self.path.startswith('/api/') else 'max-age=86400')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
        except urllib.error.HTTPError as e:
            self.send_error(e.code, 'eva said ' + str(e.code))
        except (urllib.error.URLError, TimeoutError) as e:
            # eva unreachable (mini down, tailscale off): say so plainly, the page shows it
            self.send_error(502, 'eva unreachable: ' + str(getattr(e, 'reason', e)))

    def log_message(self, fmt, *args):
        # quiet: only forwarding failures are worth a line
        if args and str(args[1])[:1] in '45':
            super().log_message(fmt, *args)


if __name__ == '__main__':
    srv = http.server.ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print(f'dream front on http://127.0.0.1:{PORT}/  (forwarding {", ".join(FORWARD)} to {EVA})')
    srv.serve_forever()
