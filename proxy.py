"""Forward the CitedBy app's paths to the app container (RES-661 production cutover).
Off unless APP_UPSTREAM is set (for example http://citedby-app:8080); unsetting it is the rollback.
Only the paths in ROUTES are forwarded; the client IP is sent as one X-Forwarded-For value."""
import json, os, re, time, urllib.error, urllib.request
import analytics
from urllib.parse import urlparse

UPSTREAM = os.environ.get("APP_UPSTREAM", "").rstrip("/")
ROUTES = {
    "GET": re.compile(r"/(instant|plans|dashboard|account|api/account/export|api/snapshot/(\d+|[A-Za-z0-9_-]{16,64})|login/[A-Za-z0-9_-]{20,64}|recount/[A-Za-z0-9_-]{20,64})"),
    "POST": re.compile(r"/(api/snapshot|api/account/(link|delete)|api/portal|api/checkout|login/[A-Za-z0-9_-]{20,64})"),
}
PASS = ("Content-Type", "Cache-Control", "Set-Cookie", "Location", "Referrer-Policy", "Content-Security-Policy")
_H = {"t": 0.0, "u": "", "v": None}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k): return None

_opener = urllib.request.build_opener(_NoRedirect)


def _call(req, timeout):
    try:
        r = _opener.open(req, timeout=timeout)
    except urllib.error.HTTPError as e:
        r = e
    return r.status if hasattr(r, "status") else r.code, r.headers, r.read()


def handle(h, method):
    """True if the request was an app path (and was answered here)."""
    u = urlparse(h.path)
    if not UPSTREAM or not ROUTES[method].fullmatch(u.path):
        return False
    body = None
    if method == "POST":
        try: n = int(h.headers.get("Content-Length") or 0)
        except ValueError: n = -1
        if n < 0 or n > 65536:
            _send(h, 413, {}, b'{"error":"too large"}'); return True
        body = h.rfile.read(n) if n else b""
    hdr = {"X-Forwarded-For": h.ip()}
    for k in ("Content-Type", "Cookie"):
        if h.headers.get(k): hdr[k] = h.headers[k]
    try:
        code, rh, rb = _call(urllib.request.Request(UPSTREAM + h.path, body, hdr, method=method), 20)
    except (urllib.error.URLError, OSError, ValueError):
        _send(h, 502, {}, b'{"error":"app unavailable"}'); return True
    _send(h, code, {k: rh[k] for k in PASS if rh.get(k)}, rb, rh.get_all("Set-Cookie"))
    return True


def _send(h, code, headers, body, cookies=None):
    if code == 200 and headers.get("Content-Type", "").startswith("text/html"):
        body = analytics.inject(body)  # RES-1071: cookieless analytics tag on the app pages too
    h.send_response(code)
    headers.setdefault("Content-Type", "application/json")
    headers.setdefault("Cache-Control", "no-store")
    headers.pop("Set-Cookie", None)
    for k, v in headers.items(): h.send_header(k, v)
    for c in cookies or []: h.send_header("Set-Cookie", c)
    h.send_header("X-Robots-Tag", "noindex")
    h.send_header("X-Content-Type-Options", "nosniff")
    h.send_header("Strict-Transport-Security", "max-age=31536000")
    h.send_header("Content-Length", str(len(body)))
    h.end_headers()
    if h.command != "HEAD": h.wfile.write(body)


def app_health():
    """None when the proxy is off, else {"status","deploy"} from the app's /health (cached 10 s, 2 s timeout)."""
    if not UPSTREAM: return None
    now = time.time()
    if _H["u"] == UPSTREAM and now - _H["t"] < 10: return _H["v"]
    try:
        code, _, b = _call(urllib.request.Request(UPSTREAM + "/health"), 2)
        j = json.loads(b)
        v = {"status": "ok" if code == 200 and j.get("ok") else "error", "deploy": j.get("deploy")}
    except (urllib.error.URLError, OSError, ValueError):
        v = {"status": "error", "deploy": None}
    _H.update(t=now, u=UPSTREAM, v=v)
    return v
