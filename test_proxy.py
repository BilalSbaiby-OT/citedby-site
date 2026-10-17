"""App proxy rules (RES-661 prod cutover). Run: python3 test_proxy.py"""
import json, threading, unittest, urllib.request, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import proxy

SEEN = []
SIG = []

class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _do(self):
        n = int(self.headers.get("Content-Length") or 0)
        SEEN.append((self.command, self.path, self.headers.get("X-Forwarded-For"), self.headers.get("Cookie"), self.rfile.read(n)))
        SIG.append(self.headers.get("Stripe-Signature"))
        if self.path.startswith("/health"):
            b = b'{"status":"ok","deploy":"abc1234","db":"ok","ok":true}'
        else:
            b = b"app-page"
        self.send_response(302 if self.path == "/login/" + "x" * 24 else 200)
        self.send_header("Content-Type", "text/html"); self.send_header("Content-Length", str(len(b)))
        self.send_header("Set-Cookie", "ci_session=v; Path=/; HttpOnly"); self.send_header("Server", "leak")
        if self.path == "/login/" + "x" * 24: self.send_header("Location", "/dashboard")
        self.end_headers(); self.wfile.write(b)
    do_GET = do_POST = _do

class H(BaseHTTPRequestHandler):  # minimal host that uses proxy like server.py does
    def log_message(self, *a): pass
    def ip(self): return "203.0.113.9"
    def do_GET(self):
        if not proxy.handle(self, "GET"): self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()
    def do_POST(self):
        if not proxy.handle(self, "POST"): self.send_response(404); self.send_header("Content-Length", "0"); self.end_headers()

def serve(cls):
    s = ThreadingHTTPServer(("127.0.0.1", 0), cls); threading.Thread(target=s.serve_forever, daemon=True).start(); return s

class T(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = serve(Stub); cls.host = serve(H)
        cls.base = "http://127.0.0.1:%d" % cls.host.server_address[1]
    def setUp(self): SEEN.clear(); SIG.clear(); proxy.UPSTREAM = "http://127.0.0.1:%d" % self.app.server_address[1]
    def get(self, path, **kw):
        try:
            r = urllib.request.urlopen(urllib.request.Request(self.base + path, **kw)); return r.status, r.read(), r.headers
        except urllib.error.HTTPError as e: return e.code, e.read(), e.headers

    def test_off_by_default(self):
        proxy.UPSTREAM = ""
        self.assertEqual(self.get("/plans")[0], 404); self.assertEqual(SEEN, [])

    def test_allowlist_only(self):
        for p in ("/instant", "/plans?billing=year", "/dashboard", "/account", "/recount/" + "a" * 24, "/api/snapshot/7", "/api/snapshot/" + "Hn-hGKmWgDksJUToqNLfgw", "/thanks", "/report/" + "a" * 24):
            self.assertEqual(self.get(p)[1], b"app-page", p)
        for p in ("/", "/fr", "/health-x", "/api/order", "/thanksx", "/report/short", "/report/" + "a" * 65, "/api/snapshot/short", "/api/snapshot/" + "a" * 65, "/api/snapshot/abc/def", "/plansx", "/instantx", "/../plans"):
            self.assertEqual(self.get(p)[0], 404, p)

    def test_forwards_one_client_ip_and_cookie_not_spoofed_xff(self):
        self.get("/account", headers={"Cookie": "ci_session=abc", "X-Forwarded-For": "1.1.1.1, 2.2.2.2"})
        m, path, xff, ck, _ = SEEN[0]
        self.assertEqual(xff, "203.0.113.9"); self.assertEqual(ck, "ci_session=abc")

    def test_response_headers_are_filtered_and_robots_blocked(self):
        s, b, h = self.get("/plans")
        self.assertEqual(h["Set-Cookie"], "ci_session=v; Path=/; HttpOnly")
        self.assertEqual(h["X-Robots-Tag"], "noindex"); self.assertEqual(h["Cache-Control"], "no-store")
        self.assertNotIn("leak", (h.get("Server") or ""))

    def test_post_body_and_redirect_pass_through(self):
        req = urllib.request.Request(self.base + "/api/snapshot", b'{"a":1}', {"Content-Type": "application/json"})
        self.assertEqual(urllib.request.urlopen(req).read(), b"app-page"); self.assertEqual(SEEN[0][4], b'{"a":1}')
        class NoRedir(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        op = urllib.request.build_opener(NoRedir)
        with self.assertRaises(urllib.error.HTTPError) as c: op.open(self.base + "/login/" + "x" * 24)
        self.assertEqual(c.exception.code, 302); self.assertEqual(c.exception.headers["Location"], "/dashboard")

    def test_stripe_webhook_forwards_raw_body_and_signature(self):
        raw = b'{"id":"evt_1",  "type":"checkout.session.completed"}'
        req = urllib.request.Request(self.base + "/api/stripe/webhook", raw, {"Content-Type": "application/json", "Stripe-Signature": "t=1,v1=ab"})
        self.assertEqual(urllib.request.urlopen(req).read(), b"app-page"); self.assertEqual(SEEN[0][4], raw)
        self.assertEqual(SEEN[0][1], "/api/stripe/webhook"); self.assertEqual(SIG[-1], "t=1,v1=ab")

    def test_upstream_down_is_502_not_a_crash(self):
        proxy.UPSTREAM = "http://127.0.0.1:1"
        self.assertEqual(self.get("/plans")[0], 502)

    def test_app_health_summary(self):
        self.assertEqual(proxy.app_health(), {"status": "ok", "deploy": "abc1234"})
        proxy.UPSTREAM = ""; self.assertIsNone(proxy.app_health())
        proxy.UPSTREAM = "http://127.0.0.1:1"; proxy._H.update(t=0); self.assertEqual(proxy.app_health(), {"status": "error", "deploy": None})

if __name__ == "__main__": unittest.main()
