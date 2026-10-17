"""Tests for the CitedBy check. Run: OPTIN_SECRET=$(python3 -c 'print("x"*40)') BASE_URL=http://t DATA_DIR=/tmp/cbt python3 test_check.py"""
import json, os, threading, unittest, urllib.request, urllib.error, socket
from http.server import BaseHTTPRequestHandler, HTTPServer
os.environ.setdefault("OPTIN_SECRET", "x" * 40); os.environ.setdefault("BASE_URL", "http://t"); import tempfile; os.environ["DATA_DIR"] = tempfile.mkdtemp()
os.environ["MAIL_OUTBOX"] = "/tmp/cbt-outbox.jsonl"; os.environ["CHECK_PER_IP_HOUR"] = "1000"; os.environ["CHECK_PER_HOST_HOUR"] = "1000"; os.environ["REQ_PER_IP_HOUR"] = "1000"
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

    def test_embedded_ipv4_blocked(self):                                                    # S4
        for ip in ("64:ff9b::7f00:1", "::7f00:1", "2002:7f00:1::", "64:ff9b::a9fe:a9fe"): self.assertFalse(safefetch.addr_ok(ip), ip)

    def test_trickle_deadline(self):                                                         # H5: 1 byte/s server must not pin a slot
        import time
        def trickle(s):
            s.send_response(200); s.send_header("Content-Length", "100000"); s.end_headers()
            try:
                for _ in range(60): s.wfile.write(b"a"); s.wfile.flush(); time.sleep(1)
            except OSError: pass
        srv = HTTPServer(("127.0.0.1", 0), type("T", (BaseHTTPRequestHandler,), {"do_GET": trickle, "log_message": lambda *a: None}))
        threading.Thread(target=srv.serve_forever, daemon=True).start(); port = srv.server_port
        orig, orig_parse = safefetch.addr_ok, safefetch.parse
        safefetch.addr_ok = lambda ip: True
        safefetch.parse = lambda u: (safefetch.urlsplit(u), port)
        try:
            t0 = time.time(); r = safefetch.fetch(f"http://127.0.0.1:{port}/", deadline=time.monotonic() + 3)
            self.assertLess(time.time() - t0, 6); self.assertEqual(r["error"], "timeout")
        finally: safefetch.addr_ok, safefetch.parse = orig, orig_parse

    def _raw_trickle(self, payload):
        """Server that sends `payload` one byte per 0.5 s, never finishing the status line or headers."""
        import time
        ls = socket.socket(); ls.bind(("127.0.0.1", 0)); ls.listen(5); port = ls.getsockname()[1]
        def serve():
            while True:
                try: c, _ = ls.accept()
                except OSError: return
                def drip(c=c):
                    try:
                        c.recv(4096)
                        for b in payload: c.send(bytes([b])); time.sleep(0.5)
                    except OSError: pass
                threading.Thread(target=drip, daemon=True).start()
        threading.Thread(target=serve, daemon=True).start()
        return ls, port

    def _timed_fetch(self, payload):
        import time
        ls, port = self._raw_trickle(payload)
        orig, orig_parse = safefetch.addr_ok, safefetch.parse
        safefetch.addr_ok = lambda ip: True
        safefetch.parse = lambda u: (safefetch.urlsplit(u), port)
        try:
            t0 = time.time(); r = safefetch.fetch(f"http://127.0.0.1:{port}/", deadline=time.monotonic() + 3)
            return time.time() - t0, r
        finally: safefetch.addr_ok, safefetch.parse = orig, orig_parse; ls.close()

    def test_trickle_status_line(self):                                                     # R1: deadline holds before the headers arrive
        dt, r = self._timed_fetch(b"HTTP/1.1 200 OK" + b"x" * 500)
        self.assertLess(dt, 4); self.assertEqual(r["error"], "timeout")

    def test_trickle_headers(self):                                                         # R1
        dt, r = self._timed_fetch(b"HTTP/1.1 200 OK\r\n" + b"X-A: b\r\n" * 200)
        self.assertLess(dt, 4); self.assertEqual(r["error"], "timeout")

    def test_inbox_key(self):                                                               # R2
        k = server.inbox_key
        self.assertEqual({k("victim@gmail.com"), k("Victim+1@gmail.com"), k("v.ictim@googlemail.com")}, {"victim@gmail.com"})
        self.assertNotEqual(k("a+x@example.com"), k("b@example.com")); self.assertEqual(k("a+x@example.com"), "a@example.com")
        self.assertNotEqual(k("a.b@example.com"), k("ab@example.com"))                       # dots count outside Gmail

    def test_tls_context_matches_http_client(self):                                         # prod OpenSSL 3.5 + Shopify: bare ClientHello gets 429
        self.assertTrue(safefetch.CTX.post_handshake_auth)

    def test_https_connection_close(self):                                                  # regression: live checks all failed as "unreachable" over HTTPS
        import ssl, subprocess, tempfile
        d = tempfile.mkdtemp(); crt, key = d + "/c.pem", d + "/k.pem"
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-keyout", key, "-out", crt, "-days", "1", "-subj", "/CN=localhost"], check=True, capture_output=True)
        h = type("S", (BaseHTTPRequestHandler,), {"protocol_version": "HTTP/1.1", "log_message": lambda *a: None,
            "do_GET": lambda s: (s.send_response(200), s.send_header("Connection", "close"), s.end_headers(), s.wfile.write(b"hello https"))})
        srv = HTTPServer(("127.0.0.1", 0), h); sc = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER); sc.load_cert_chain(crt, key)
        srv.socket = sc.wrap_socket(srv.socket, server_side=True)
        threading.Thread(target=srv.serve_forever, daemon=True).start(); port = srv.server_port
        cc = ssl.create_default_context(); cc.check_hostname = False; cc.load_verify_locations(crt)
        orig, orig_parse, orig_ctx = safefetch.addr_ok, safefetch.parse, safefetch.CTX
        safefetch.addr_ok = lambda ip: True; safefetch.CTX = cc
        safefetch.parse = lambda u: (safefetch.urlsplit(u), port)
        try:
            r = safefetch.fetch(f"https://127.0.0.1:{port}/")
            self.assertEqual((r["status"], r["body"], r["error"]), (200, "hello https", ""))
        finally: safefetch.addr_ok, safefetch.parse, safefetch.CTX = orig, orig_parse, orig_ctx; srv.shutdown()

    def test_connect_deadline_race(self):                                                   # RES-464: timer fires while connect() is still in flight
        import time
        ls = socket.socket(); ls.bind(("127.0.0.1", 0)); ls.listen(5); port = ls.getsockname()[1]  # accepts in the kernel, never answers
        orig, orig_parse, orig_cc = safefetch.addr_ok, safefetch.parse, socket.create_connection
        def slow(addr, timeout=None, *a, **k):
            time.sleep(0.5); return orig_cc(addr, timeout, *a, **k)
        safefetch.addr_ok = lambda ip: True; safefetch.parse = lambda u: (safefetch.urlsplit(u), port); socket.create_connection = slow
        try:
            r = safefetch.fetch(f"http://127.0.0.1:{port}/", deadline=time.monotonic() + 0.3)
            self.assertEqual(r["error"], "timeout")
            conn, _ = ls.accept(); conn.settimeout(0.5)                                      # without the fix the request is sent on the late socket
            try: got = conn.recv(100)
            except socket.timeout: got = b""
            conn.close(); self.assertNotIn(b"GET", got)
        finally: safefetch.addr_ok, safefetch.parse, socket.create_connection = orig, orig_parse, orig_cc; ls.close()

    def test_stalled_resolver_counts_in_deadline(self):                                      # RES-733: slow DNS must not overshoot the fetch deadline
        import time
        orig = socket.getaddrinfo
        socket.getaddrinfo = lambda *a, **k: time.sleep(3) or []
        try:
            t0 = time.monotonic(); r = safefetch.fetch("http://slow-ns.example.com/", deadline=time.monotonic() + 1)
            self.assertLess(time.monotonic() - t0, 1.5); self.assertEqual(r["error"], "timeout")
        finally: socket.getaddrinfo = orig

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
        mails = [m for m in (json.loads(l) for l in open("/tmp/cbt-outbox.jsonl")) if "a@example.com" in m["to"]]
        self.assertEqual(len(mails), 1); self.assertIn("a@example.com", mails[0]["to"])
        self.assertIn("Confirmez", mails[0]["subject"]); self.assertIn("List-Unsubscribe", mails[0]["headers"])
        import re
        link = re.search(r"(http://t/api/confirm\?t=\S+)", mails[0]["text"]).group(1).replace("http://t", self.base)
        r = urllib.request.urlopen(link); self.assertEqual(r.status, 200)
        self.assertEqual(r.headers["Cache-Control"], "no-store")                              # H3: /api never cached
        self.assertIsNone(server._db.execute("SELECT confirmed_ts FROM request WHERE email='a@example.com'").fetchone()[0])  # GET (mail scanner) does not confirm
        self.assertIn(b"<form", r.read())
        self.assertEqual(urllib.request.urlopen(urllib.request.Request(link, b"", method="POST")).status, 200)
        row = server._db.execute("SELECT confirmed_ts FROM request WHERE email='a@example.com'").fetchone(); self.assertIsNotNone(row[0])
        self.assertEqual(self.get_status(self.base + "/api/confirm?t=bad.token"), 400)
        unsub = re.search(r"(http://t/api/unsubscribe\?t=\S+)", mails[0]["text"]).group(1).replace("http://t", self.base)
        self.assertEqual(urllib.request.urlopen(unsub).status, 200)                         # GET only shows the confirm form
        self.assertIsNotNone(server._db.execute("SELECT 1 FROM request WHERE email='a@example.com'").fetchone())
        self.assertEqual(urllib.request.urlopen(urllib.request.Request(unsub, b"", method="POST")).status, 200)
        self.assertIsNone(server._db.execute("SELECT 1 FROM request WHERE email='a@example.com'").fetchone())

    def test_mail_cap_per_address(self):                                                     # H4: 2 mails per address per 24 h across URLs
        for host in ("example.com", "example.org", "example.net", "iana.org"):
            self.assertEqual(self.post("/api/request", {"email": "cap@example.com", "url": host, "lang": "en", "consent": True})[0], 200)
        self.assertEqual(len([l for l in open("/tmp/cbt-outbox.jsonl") if "cap@example.com" in l]), server.MAILS_PER_ADDR_DAY)  # outbox is shared across tests; filtered by recipient

    def test_mail_cap_same_inbox(self):                                                      # R2: +tag and Gmail dots share one cap
        for addr in ("victim@gmail.com", "victim+1@gmail.com", "v.ictim@gmail.com", "vi.ctim+z@gmail.com"):
            self.assertEqual(self.post("/api/request", {"email": addr, "url": "example.com", "lang": "en", "consent": True})[0], 200)
        sent = [l for l in open("/tmp/cbt-outbox.jsonl") if "ictim" in l]
        self.assertEqual(len(sent), server.MAILS_PER_ADDR_DAY)

    def test_trailing_dot_email_rejected(self):                                             # RES-464: victim@gmail.com. must not get its own cap bucket
        for addr in ("zdot@gmail.com.", "zdot@gmail..com", "zdot@.gmail.com"):
            self.assertEqual(self.post("/api/request", {"email": addr, "url": "example.com", "lang": "en", "consent": True})[0], 400, addr)
        self.assertFalse([l for l in open("/tmp/cbt-outbox.jsonl") if "zdot" in l])

    def test_clean_url_fallback(self):                                                       # S3: nginx try_files parity
        os.makedirs(os.path.join(server.SITE_DIR, "zz-test"), exist_ok=True)
        open(os.path.join(server.SITE_DIR, "zz-test.html"), "w").write("x"); open(os.path.join(server.SITE_DIR, "zz-test", "index.html"), "w").write("y")
        try:
            self.assertEqual(self.get_status(self.base + "/zz-test"), 200)
        finally:
            os.remove(os.path.join(server.SITE_DIR, "zz-test.html")); os.remove(os.path.join(server.SITE_DIR, "zz-test", "index.html")); os.rmdir(os.path.join(server.SITE_DIR, "zz-test"))

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


class Health(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.ThreadingHTTPServer(("127.0.0.1", 0), server.H); cls.base = "http://127.0.0.1:%d" % cls.srv.server_port
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls): cls.srv.shutdown()

    def get(self, path):
        try:
            r = urllib.request.urlopen(self.base + path); return r.status, r.headers, json.loads(r.read())
        except urllib.error.HTTPError as e: return e.code, e.headers, json.loads(e.read())

    def test_health_ok(self):
        code, h, d = self.get("/health")
        self.assertEqual(code, 200); self.assertEqual(d["status"], "ok"); self.assertEqual(d["db"], "ok"); self.assertIn("time", d)
        self.assertTrue(h["Content-Type"].startswith("application/json")); self.assertEqual(h["Cache-Control"], "no-store")

    def test_health_503_when_db_unreadable(self):
        import shutil, tempfile
        d = tempfile.mkdtemp(); bad = os.path.join(d, "copy.db"); shutil.copy(os.path.join(server.DATA_DIR, "check.db"), bad)
        orig = server.DB_PATH
        try:
            open(bad, "wb").write(b"not a database" * 100)   # unreadable as SQLite
            server.DB_PATH = bad
            code, _, body = self.get("/health"); self.assertEqual((code, body["status"], body["db"]), (503, "error", "error"))
            server.DB_PATH = os.path.join(d, "missing.db")   # file gone: must not be created by the probe
            code, _, body = self.get("/health"); self.assertEqual(code, 503); self.assertFalse(os.path.exists(server.DB_PATH))
        finally: server.DB_PATH = orig
        self.assertEqual(self.get("/health")[0], 200)

    def test_deploy_id_comes_from_the_build(self):
        orig = server.DEPLOY_ID
        try:
            for v in ("abc1234", "def5678"):
                server.DEPLOY_ID = v; code, _, d = self.get("/deploy-id"); self.assertEqual((code, d["deploy_id"]), (200, v))
        finally: server.DEPLOY_ID = orig


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

    def test_empty_200_is_unknown_not_fail(self):  # RES-1182: terresdecafe.com sent an empty 200 to our old Accept header
        def fake(url, **kw):
            body = "    \r\n" if url.endswith("/") and "robots" not in url and "llms" not in url else ""
            return {"status": 200 if body else 404, "url": url, "body": body, "error": ""}
        orig = safefetch.fetch; safefetch.fetch = fake
        try: out = doorcheck.run("https://www.terresdecafe.com")
        finally: safefetch.fetch = orig
        st = {c["id"]: c["status"] for c in out["checks"]}
        self.assertEqual((st["raw_text"], st["org_schema"]), ("unknown", "unknown"))
    def test_accept_header_has_no_json(self):  # RES-1182
        import inspect; src = inspect.getsource(safefetch.fetch)
        self.assertNotIn("application/json", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
