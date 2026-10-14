"""Tests for the CitedBy check. Run: OPTIN_SECRET=$(python3 -c 'print("x"*40)') BASE_URL=http://t DATA_DIR=/tmp/cbt python3 test_check.py"""
import json, os, threading, unittest, urllib.request, urllib.error, socket
from http.server import BaseHTTPRequestHandler, HTTPServer
os.environ.setdefault("OPTIN_SECRET", "x" * 40); os.environ.setdefault("BASE_URL", "http://t"); import tempfile; os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["MAIL_OUTBOX"] = "/tmp/cbt-outbox.jsonl"; os.environ["CHECK_PER_IP_HOUR"] = "1000"; os.environ["CHECK_PER_HOST_HOUR"] = "1000"
import safefetch, doorcheck, server


class Redir(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/shop":
            self.send_response(200); self.end_headers()
            self.wfile.write(b"<html><head><title>x</title></head><body>" + b"word " * 300 + b"</body></html>"); return
        target = {"/to-meta": "http://169.254.169.254/latest/meta-data/", "/to-loop": "http://127.0.0.1:%d/to-loop" % self.server.server_port,
                  "/to-file": "file:///etc/passwd", "/to-port": "http://example.com:22/"}.get(self.path, "/shop")
        self.send_response(302); self.send_header("Location", target); self.end_headers()
    def log_message(self, *a): pass


class SSRF(unittest.TestCase):
    def blocked(self, url, why=None):
        with self.assertRaises(safefetch.Blocked) as cm:
            safefetch.fetch(url)
        if why: self.assertEqual(str(cm.exception), why)

    def test_loopback(self): self.blocked("http://127.0.0.1/", "private_address")
    def test_metadata(self): self.blocked("http://169.254.169.254/latest/meta-data/", "private_address")
    def test_ipv6_loopback(self): self.blocked("http://[::1]/")
    def test_mapped_ipv6(self): self.blocked("http://[::ffff:127.0.0.1]/")
    def test_decimal_ip(self): self.blocked("http://2130706433/")
    def test_hex_ip(self): self.blocked("http://0x7f.1/")
    def test_private_ranges(self):
        for ip in ("10.0.0.1", "172.16.0.1", "192.168.1.1", "100.64.0.1", "0.0.0.0", "224.0.0.1"): self.blocked(f"http://{ip}/")
    def test_localhost_name(self): self.blocked("http://localhost/")
    def test_schemes(self):
        for u in ("file:///etc/passwd", "ftp://example.com/", "gopher://example.com/", "javascript:alert(1)"): self.blocked(u, "scheme")
    def test_ports(self): self.blocked("http://example.com:22/", "port"); self.blocked("http://example.com:8080/", "port")
    def test_userinfo(self): self.blocked("http://user:pw@example.com/", "userinfo")
    def test_mixed_dns_answer(self):
        orig = socket.getaddrinfo
        socket.getaddrinfo = lambda h, p, **k: [(2, 1, 6, "", ("93.184.216.34", p)), (2, 1, 6, "", ("10.0.0.5", p))]
        try: self.blocked("http://rebind.example.com/", "private_address")
        finally: socket.getaddrinfo = orig

    def test_redirect_to_private(self):
        srv = HTTPServer(("127.0.0.1", 0), Redir); threading.Thread(target=srv.serve_forever, daemon=True).start()
        port = srv.server_port
        orig = safefetch.addr_ok
        safefetch.addr_ok = lambda ip: ip == "127.0.0.1" or orig(ip)   # test only: let hop 0 reach our local server
        orig_parse = safefetch.parse
        safefetch.parse = lambda u: (safefetch.urlsplit(u), port) if u.startswith("http://127.0.0.1:%d" % port) else orig_parse(u)
        try:
            for path, why in (("/to-meta", "blocked:private_address"), ("/to-file", "blocked:scheme"), ("/to-port", "blocked:port")):
                r = safefetch.fetch(f"http://127.0.0.1:{port}{path}")
                self.assertEqual(r["error"], why, path); self.assertEqual(r["body"], "")
            r = safefetch.fetch(f"http://127.0.0.1:{port}/to-loop")  # loop of validated hops ends at the redirect cap
            self.assertIn(r["error"], ("too_many_redirects",))
            r = safefetch.fetch(f"http://127.0.0.1:{port}/ok"); self.assertEqual(r["status"], 200)   # control: a clean redirect works
        finally:
            safefetch.addr_ok, safefetch.parse = orig, orig_parse; srv.shutdown()

    def test_body_cap(self):
        srv = HTTPServer(("127.0.0.1", 0), type("B", (BaseHTTPRequestHandler,), {"do_GET": lambda s: (s.send_response(200), s.end_headers(), s.wfile.write(b"a" * 5_000_000)), "log_message": lambda *a: None}))
        threading.Thread(target=srv.serve_forever, daemon=True).start(); port = srv.server_port
        orig, orig_parse = safefetch.addr_ok, safefetch.parse
        safefetch.addr_ok = lambda ip: True
        safefetch.parse = lambda u: (safefetch.urlsplit(u), port)
        try: self.assertEqual(len(safefetch.fetch(f"http://127.0.0.1:{port}/", max_body=1000)["body"]), 1000)
        finally: safefetch.addr_ok, safefetch.parse = orig, orig_parse; srv.shutdown()


class Api(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.base = "http://127.0.0.1:%d" % cls.srv.server_port
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        open("/tmp/cbt-outbox.jsonl", "w").close()

    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()

    def post(self, path, d):
        req = urllib.request.Request(self.base + path, json.dumps(d).encode(), {"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req); return r.status, r.read()
        except urllib.error.HTTPError as e: return e.code, e.read()

    def test_api_blocks_ssrf(self):
        for u in ("127.0.0.1", "http://169.254.169.254/latest/meta-data/", "http://[::1]/", "file:///etc/passwd", "http://localhost:8080"):
            code, body = self.post("/api/check", {"url": u, "lang": "en"})
            self.assertIn(code, (400,)); self.assertNotIn(b"root:", body)
        code, body = self.post("/api/check", {"url": "localhost", "lang": "en"}); self.assertEqual(code, 400)

    def test_events_and_snapshot(self):
        self.assertEqual(server.snapshot("BE", "nl", "coffee")["top"][0]["name"], "OR Coffee Roasters")
        self.assertEqual(server.snapshot("BE", "en", "coffee")["other_language"], "fr")
        self.assertIsNone(server.snapshot("DE", "en", "coffee"))

    def test_optin_flow(self):
        d = {"email": "A@Example.com", "url": "example.com", "lang": "fr", "country": "BE", "niche": "coffee", "consent": True}
        self.assertEqual(self.post("/api/request", {**d, "consent": False})[0], 400)       # no consent
        self.assertEqual(self.post("/api/request", {**d, "email": "nope"})[0], 400)
        self.assertEqual(self.post("/api/request", {**d, "url": "http://127.0.0.1"})[0], 400)
        self.assertEqual(self.post("/api/request", {**d, "website": "spam.com"})[0], 200)   # honeypot: silent
        self.assertEqual(self.post("/api/request", d)[0], 200)
        self.assertEqual(self.post("/api/request", d)[0], 200)                              # duplicate within 10 min: no second mail
        mails = [json.loads(l) for l in open("/tmp/cbt-outbox.jsonl")]
        self.assertEqual(len(mails), 1); self.assertIn("a@example.com", mails[0]["to"])
        self.assertIn("Confirmez", mails[0]["subject"]); self.assertIn("List-Unsubscribe", mails[0]["headers"])
        import re
        link = re.search(r"(http://t/api/confirm\?t=\S+)", mails[0]["text"]).group(1).replace("http://t", self.base)
        self.assertEqual(urllib.request.urlopen(link).status, 200)
        row = server._db.execute("SELECT confirmed_ts FROM request WHERE email='a@example.com'").fetchone(); self.assertIsNotNone(row[0])
        self.assertEqual(self.get_status(self.base + "/api/confirm?t=bad.token"), 400)
        unsub = re.search(r"(http://t/api/unsubscribe\?t=\S+)", mails[0]["text"]).group(1).replace("http://t", self.base)
        self.assertEqual(urllib.request.urlopen(unsub).status, 200)                         # GET only shows the confirm form
        self.assertIsNotNone(server._db.execute("SELECT 1 FROM request WHERE email='a@example.com'").fetchone())
        self.assertEqual(urllib.request.urlopen(urllib.request.Request(unsub, b"", method="POST")).status, 200)
        self.assertIsNone(server._db.execute("SELECT 1 FROM request WHERE email='a@example.com'").fetchone())

    def get_status(self, url):
        try: return urllib.request.urlopen(url).status
        except urllib.error.HTTPError as e: return e.code

    def test_static_and_traversal(self):
        self.assertEqual(self.get_status(self.base + "/healthz"), 200)
        for p in ("/check", "/fr/check", "/nl/check", "/", "/style.css"): self.assertEqual(self.get_status(self.base + p), 200, p)
        for p in ("/../server.py", "/%2e%2e/server.py", "/..%2fserver.py", "/data/snapshots.json"):
            self.assertEqual(self.get_status(self.base + p), 404, p)

    def test_data_pages_routing(self):
        for p in ("/data", "/data/cafe-france", "/data/study-chatgpt-buyer-questions", "/data/cafe-france.csv", "/data/citedby-study-2026-10.pdf"):
            self.assertEqual(self.get_status(self.base + p), 200, p)
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, *a, **k): return None
        try: urllib.request.build_opener(NoRedirect).open(self.base + "/data/"); code = 200
        except urllib.error.HTTPError as e: code, loc = e.code, e.headers.get("Location")
        self.assertEqual((code, loc), (301, "/data"))
        with urllib.request.urlopen(self.base + "/data/cafe-france.csv") as r: self.assertTrue(r.headers["Content-Type"].startswith("text/csv"))
        for p in ("/data/../server.py", "/data/..%2fserver.py", "/data/%2e%2e/server", "/data/missing"):
            self.assertEqual(self.get_status(self.base + p), 404, p)

    def test_rate_limit(self):
        server.CHECK_PER_IP = 2; server._hits.clear()
        codes = [self.post("/api/check", {"url": "127.0.0.1"})[0] for _ in range(3)]
        server.CHECK_PER_IP = 1000
        self.assertEqual(codes, [400, 400, 429])


class Parsing(unittest.TestCase):
    def test_productgroup_variant(self):
        h = '<script type="application/ld+json">{"@type":"ProductGroup","hasVariant":[{"@type":"Product","gtin13":"1234567890123","offers":{"@type":"Offer","price":"9.5","availability":"InStock"}}]}</script>'
        self.assertEqual(doorcheck.product_facts(h), (True, True, True, True))
    def test_graph_org(self):
        h = '<script type="application/ld+json">{"@graph":[{"@type":["Thing","Store"]}]}</script>'
        self.assertIn("Store", doorcheck.types_of(doorcheck.jsonld_nodes(h)[1]))
    def test_robots(self):
        self.assertRaises(safefetch.Blocked, doorcheck.normalize, "ftp://x.com")
        self.assertEqual(doorcheck.normalize("Shop.Example.com/path?x=1"), "https://Shop.Example.com")


if __name__ == "__main__":
    unittest.main(verbosity=2)
