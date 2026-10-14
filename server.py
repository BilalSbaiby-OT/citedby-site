"""CitedBy: static site plus the free check. Standard library only.

Routes: GET static pages (clean URLs), POST /api/check, POST /api/request, GET|POST /api/confirm, GET|POST /api/unsubscribe,
POST /api/event, GET /healthz. Data: one SQLite file under DATA_DIR. No cookies. Events are anonymous counters.
"""
import base64, hashlib, hmac, html, json, mimetypes, os, re, sqlite3, threading, time, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

import doorcheck, safefetch

HERE = os.path.dirname(os.path.abspath(__file__))
CONSENT_VERSION = "2026-10-15.v1"
SECRET = os.environ["OPTIN_SECRET"].encode()  # crash if missing (fail-secure)
if len(SECRET) < 32:
    raise SystemExit("OPTIN_SECRET must be at least 32 bytes")
BASE_URL = os.environ["BASE_URL"].rstrip("/")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
SITE_DIR = os.environ.get("SITE_DIR", os.path.join(HERE, "public"))
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
MAIL_FROM = os.environ.get("MAIL_FROM", "CitedBy <hello@citedby.eu>")
MAIL_OUTBOX = os.environ.get("MAIL_OUTBOX", "")  # test only: append mails to this file instead of sending
CHECK_PER_IP = int(os.environ.get("CHECK_PER_IP_HOUR", "10"))
CHECK_PER_HOST = int(os.environ.get("CHECK_PER_HOST_HOUR", "4"))
REQ_PER_IP = int(os.environ.get("REQ_PER_IP_HOUR", "5"))
DAILY_CAP = int(os.environ.get("DAILY_CAP", "20"))
MAILS_PER_ADDR_DAY = 2
INTERNAL_IPS = {x for x in os.environ.get("INTERNAL_IPS", "").split(",") if x}
LANGS = ("en", "fr", "nl")
COUNTRIES = ("BE", "FR", "NL", "IE", "DE", "ES", "GB", "OTHER")
NICHES = ("coffee", "tea", "beauty", "mattress", "supplements", "other")
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}\.[^@\s]{2,}$")
SNAPSHOTS = json.load(open(os.path.join(HERE, "data", "snapshots.json")))
EVENTS = ("check_start", "check_complete", "email_submitted", "fixpack_click")

os.makedirs(DATA_DIR, exist_ok=True)
_db = sqlite3.connect(os.path.join(DATA_DIR, "check.db"), check_same_thread=False)
_db.execute("PRAGMA journal_mode=WAL")
_db.execute("""CREATE TABLE IF NOT EXISTS request(
  id INTEGER PRIMARY KEY, email TEXT NOT NULL, url TEXT NOT NULL, country TEXT, lang TEXT, niche TEXT, summary TEXT,
  ts INTEGER, consent_text_version TEXT, last_mail_ts INTEGER DEFAULT 0, confirmed_ts INTEGER, confirmed_day TEXT, released_day TEXT)""")
_db.execute("CREATE TABLE IF NOT EXISTS mail_log(email TEXT NOT NULL, ts INTEGER NOT NULL)")
_db.execute("""CREATE TABLE IF NOT EXISTS event_count(
  day TEXT NOT NULL, lang TEXT NOT NULL, type TEXT NOT NULL, n INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(day,lang,type))""")
_db.commit()
_lock = threading.Lock()
_slots = threading.BoundedSemaphore(4)  # concurrent outbound checks
UNCONFIRMED_TTL, MAX_AGE = 7 * 86400, 365 * 86400
_hits = {}

TXT = {
 "en": dict(subj="Confirm your email to get your ChatGPT mini-audit (CitedBy)",
  body="Hello,\n\nYou asked for the CitedBy mini-audit of {site}.\nTo confirm this address, open this link (valid 7 days):\n{c}\n\nAfter you confirm, we ask ChatGPT the questions your buyers ask in your market and email you the result within 2 working days.\n\nIf this wasn't you, ignore this message: without confirmation we send nothing more and delete the address.\n\nSender: CitedBy, operated by Resale IQ. We use your address only for this audit and one follow-up about it. Unsubscribe and delete the address: {u}\n",
  ok_q="Address confirmed. Your mini-audit is queued; you will get it by email within 2 working days.", confirm_q="Confirm this address and start the mini-audit?", confirm_btn="Confirm",
  bad="Invalid or expired link.", unsub_q="Remove this address and cancel the mini-audit?", unsub_btn="Remove", unsub_ok="Address removed."),
 "fr": dict(subj="Confirmez votre e-mail pour recevoir votre mini-audit ChatGPT (CitedBy)",
  body="Bonjour,\n\nVous avez demandé le mini-audit CitedBy de {site}.\nPour confirmer cette adresse, ouvrez ce lien (valable 7 jours) :\n{c}\n\nUne fois confirmé, nous posons à ChatGPT les questions de vos acheteurs sur votre marché et vous envoyons le résultat par e-mail sous 2 jours ouvrés.\n\nSi ce n'est pas vous, ignorez ce message : sans confirmation, nous n'écrivons plus et supprimons l'adresse.\n\nExpéditeur : CitedBy, exploité par Resale IQ. Nous utilisons votre adresse uniquement pour cet audit et un message de suivi. Se désinscrire et supprimer l'adresse : {u}\n",
  ok_q="Adresse confirmée. Votre mini-audit est en file ; vous le recevrez par e-mail sous 2 jours ouvrés.", confirm_q="Confirmer cette adresse et lancer le mini-audit ?", confirm_btn="Confirmer",
  bad="Lien invalide ou expiré.", unsub_q="Supprimer cette adresse et annuler le mini-audit ?", unsub_btn="Supprimer", unsub_ok="Adresse supprimée."),
 "nl": dict(subj="Bevestig je e-mailadres voor je ChatGPT-miniaudit (CitedBy)",
  body="Hallo,\n\nJe vroeg de CitedBy-miniaudit van {site} aan.\nOm dit adres te bevestigen, open je deze link (7 dagen geldig):\n{c}\n\nNa je bevestiging stellen we ChatGPT de vragen die jouw kopers in jouw markt stellen en mailen we je het resultaat binnen 2 werkdagen.\n\nWas jij dit niet? Negeer dan dit bericht: zonder bevestiging sturen we niets meer en wissen we het adres.\n\nAfzender: CitedBy, uitgebaat door Resale IQ. We gebruiken je adres alleen voor deze audit en één opvolgbericht. Uitschrijven en adres wissen: {u}\n",
  ok_q="Adres bevestigd. Je miniaudit staat in de wachtrij; je krijgt hem binnen 2 werkdagen per e-mail.", confirm_q="Dit adres bevestigen en de miniaudit starten?", confirm_btn="Bevestigen",
  bad="Ongeldige of verlopen link.", unsub_q="Dit adres wissen en de miniaudit annuleren?", unsub_btn="Wissen", unsub_ok="Adres gewist."),
}


def b64(b): return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def unb64(s): return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def make_token(kind, rid, ttl=None):
    exp = int(time.time()) + ttl if ttl else 0
    p = f"{kind}:{rid}:{exp}".encode()
    return b64(p) + "." + b64(hmac.new(SECRET, p, hashlib.sha256).digest())


def read_token(tok, kind):
    try:
        pb, sb = tok.split(".")
        p = unb64(pb)
        if not hmac.compare_digest(unb64(sb), hmac.new(SECRET, p, hashlib.sha256).digest()):
            return None
        k, rid, exp = p.decode().split(":")
        if k != kind or (int(exp) and int(exp) < time.time()):
            return None
        return int(rid)
    except Exception:
        return None


def send_mail(to, subject, text, headers=None):
    msg = {"from": MAIL_FROM, "to": [to], "subject": subject, "text": text, "headers": headers or {}}
    if MAIL_OUTBOX:
        with open(MAIL_OUTBOX, "a") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return True
    if not RESEND_API_KEY:
        print("mail skipped: no RESEND_API_KEY", flush=True)
        return False
    req = urllib.request.Request("https://api.resend.com/emails", json.dumps(msg).encode(), {
        "Authorization": "Bearer " + RESEND_API_KEY, "Content-Type": "application/json", "User-Agent": "citedby-check/1"})
    try:
        urllib.request.urlopen(req, timeout=10).read()
        return True
    except Exception as e:
        print("mail failed:", type(e).__name__, flush=True)  # never log the address
        return False


def purge_expired(now=None):
    now = int(now or time.time())
    with _lock:
        cur = _db.execute("DELETE FROM request WHERE (confirmed_ts IS NULL AND ts < ?) OR ts < ?", (now - UNCONFIRMED_TTL, now - MAX_AGE))
        _db.execute("DELETE FROM mail_log WHERE ts < ?", (now - 86400,))
        _db.commit()
    print("retention: deleted", cur.rowcount, "rows", flush=True)


def retention_loop():
    while True:
        try:
            purge_expired()
        except Exception as e:
            print("retention failed:", type(e).__name__, flush=True)
        time.sleep(86400)


def count_event(etype, lang, ip=""):
    if etype not in EVENTS or lang not in LANGS or ip in INTERNAL_IPS:
        return
    day = time.strftime("%Y-%m-%d", time.gmtime())
    with _lock:
        _db.execute("INSERT INTO event_count(day,lang,type,n) VALUES(?,?,?,1) ON CONFLICT(day,lang,type) DO UPDATE SET n=n+1", (day, lang, etype))
        _db.commit()


def limited(key, limit):
    """True if key has used up its hourly allowance (and records the hit otherwise)."""
    now = time.time()
    with _lock:
        h = [t for t in _hits.get(key, []) if now - t < 3600]
        if len(h) >= limit:
            _hits[key] = h
            return True
        h.append(now)
        _hits[key] = h
        if len(_hits) > 5000:
            for k in [k for k, v in _hits.items() if not v or now - v[-1] > 3600]:
                del _hits[k]
    return False


def inbox_key(email):
    """Same inbox, same key: lowercase, drop +tag, and for Gmail drop dots and unify the domain."""
    local, _, domain = email.lower().partition("@")
    local = local.split("+", 1)[0]
    if domain in ("gmail.com", "googlemail.com"):
        local, domain = local.replace(".", ""), "gmail.com"
    return f"{local}@{domain}"


def snapshot(country, lang, niche):
    s = SNAPSHOTS.get(f"{country}|{lang}|{niche}")
    other = False
    if not s:
        for k, v in SNAPSHOTS.items():
            c, _, n = k.split("|")
            if c == country and n == niche:
                s, other = v, k.split("|")[1]
                break
    if not s or not s["top"]:
        return None
    return {**s, "country": country, "niche": niche, "other_language": other}


def handle_check(data, ip):
    """Returns (http_status, body_dict)."""
    lang = data.get("lang") if data.get("lang") in LANGS else "en"
    country = data.get("country") if data.get("country") in COUNTRIES else "OTHER"
    niche = data.get("niche") if data.get("niche") in NICHES else "other"
    try:
        root = doorcheck.normalize(str(data.get("url", "")))
    except safefetch.Blocked:
        return 400, {"ok": False, "error": "bad_url"}
    if limited("ip:" + ip, CHECK_PER_IP) or limited("host:" + root, CHECK_PER_HOST):
        return 429, {"ok": False, "error": "rate_limited"}
    if not _slots.acquire(timeout=5):
        return 503, {"ok": False, "error": "busy"}
    try:
        count_event("check_start", lang, ip)
        try:
            res = doorcheck.run(root, lang)
        except safefetch.Blocked:
            return 400, {"ok": False, "error": "bad_url"}
    finally:
        _slots.release()
    if res.get("reachable"):
        count_event("check_complete", lang, ip)
    res["ok"] = True
    res["snapshot"] = snapshot(country, lang, niche)
    return 200, res


def handle_request(data, ip):
    """Always True for well-formed input, so responses never reveal who requested what."""
    if data.get("website"):  # honeypot
        return True
    email = str(data.get("email", "")).strip().lower()
    lang = data.get("lang") if data.get("lang") in LANGS else "en"
    if not EMAIL_RE.match(email) or len(email) > 320 or data.get("consent") is not True:
        return False
    try:
        root = doorcheck.normalize(str(data.get("url", "")))
        u, port = safefetch.parse(root)
        safefetch.resolve_public(u.hostname, port)  # the operator pipeline fetches this URL later: refuse private targets now
    except safefetch.Blocked:
        return False
    country = data.get("country") if data.get("country") in COUNTRIES else "OTHER"
    niche = data.get("niche") if data.get("niche") in NICHES else "other"
    if limited("req:" + ip, REQ_PER_IP):
        return True
    summary = json.dumps(data.get("summary")) if isinstance(data.get("summary"), dict) and len(json.dumps(data["summary"])) < 300 else ""
    now = int(time.time())
    with _lock:
        row = _db.execute("SELECT id,last_mail_ts,confirmed_ts FROM request WHERE email=? AND url=?", (email, root)).fetchone()
        if row is None:
            cur = _db.execute("INSERT INTO request(email,url,country,lang,niche,summary,ts,consent_text_version) VALUES(?,?,?,?,?,?,?,?)",
                              (email, root, country, lang, niche, summary, now, CONSENT_VERSION))
            rid, last, conf = cur.lastrowid, 0, None
        else:
            rid, last, conf = row
        _db.commit()
        if conf or now - last < 600:
            return True
        if _db.execute("SELECT count(*) FROM mail_log WHERE email=? AND ts>?", (inbox_key(email), now - 86400)).fetchone()[0] >= MAILS_PER_ADDR_DAY:
            return True  # nobody can flood a stranger's inbox through this form
        _db.execute("INSERT INTO mail_log(email,ts) VALUES(?,?)", (inbox_key(email), now))
        _db.execute("UPDATE request SET last_mail_ts=? WHERE id=?", (now, rid))
        _db.commit()
    count_event("email_submitted", lang, ip)
    t = TXT[lang]
    unsub = f"{BASE_URL}/api/unsubscribe?t={make_token('u', rid)}"
    send_mail(email, t["subj"], t["body"].format(site=root, c=f"{BASE_URL}/api/confirm?t={make_token('c', rid, 7 * 86400)}", u=unsub),
              {"List-Unsubscribe": f"<{unsub}>"})
    return True


def confirm(rid):
    """Returns lang or None. Confirmed requests wait in the queue; tools/queue.py releases DAILY_CAP a day."""
    today = time.strftime("%Y-%m-%d", time.gmtime())
    with _lock:
        row = _db.execute("SELECT lang,confirmed_ts FROM request WHERE id=?", (rid,)).fetchone()
        if not row:
            return None
        if row[1] is None:
            _db.execute("UPDATE request SET confirmed_ts=?, confirmed_day=? WHERE id=?", (int(time.time()), today, rid))
            _db.commit()
    return row[0]


def page(msg, lang="en", form=None):
    return (f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="robots" content="noindex"><title>CitedBy</title><link rel="stylesheet" href="/style.css"><link rel="stylesheet" href="/check.css">'
            f'<body><main class="doc"><p>{html.escape(msg)}</p>{form or ""}<p><a href="/">CitedBy</a></p></main>').encode()


ROUTES = {"/": "index.html", "/check": "check.html", "/fr/check": "fr/check.html", "/nl/check": "nl/check.html",
          "/legal": "legal.html", "/privacy": "privacy.html"}
CSP = ("default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; script-src 'self'; connect-src 'self'; "
       "base-uri 'self'; form-action 'self' https://buy.stripe.com mailto:; frame-ancestors 'none'")


class H(BaseHTTPRequestHandler):
    timeout = 15  # idle or half-sent connections must not hold a thread
    server_version = "citedby"
    sys_version = ""

    def log_message(self, fmt, *a):  # no query strings (tokens) or IPs in logs
        print(self.command, urlparse(self.path).path, a[1] if len(a) > 1 else "", flush=True)

    def ip(self):
        xf = self.headers.get("X-Forwarded-For", "")
        return xf.split(",")[-1].strip() if xf else self.client_address[0]

    def out(self, code, body, ctype="text/html; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        cache = "no-store"
        if code == 200 and not self.path.startswith("/api/"):
            cache = "public, max-age=604800" if self.path.split("?")[0].endswith((".css", ".js", ".svg", ".png", ".ico", ".woff2")) else "public, max-age=300"
        self.send_header("Cache-Control", cache)
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Content-Security-Policy", CSP)
        self.send_header("Strict-Transport-Security", "max-age=31536000")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def static(self, path):
        rel = ROUTES.get(path) or path.lstrip("/")
        base = os.path.realpath(SITE_DIR)
        full = os.path.realpath(os.path.join(base, rel))
        for cand in (full, full + ".html", os.path.join(full, "index.html")):  # same clean URLs as the old nginx try_files
            if cand.startswith(base + os.sep) and os.path.isfile(cand):
                full = cand
                break
        if not full.startswith(base + os.sep) or not os.path.isfile(full):
            return self.out(404, page("Not found"))
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/xml", "application/javascript"):
            ctype += "; charset=utf-8"
        with open(full, "rb") as f:
            self.out(200, f.read(), ctype)

    def do_HEAD(self): self.do_GET()

    def do_GET(self):
        u = urlparse(self.path)
        tok = (parse_qs(u.query).get("t") or [""])[0]
        if u.path == "/healthz":
            return self.out(200, b'{"ok":true}', "application/json")
        if u.path == "/api/confirm":
            rid = read_token(tok, "c")  # GET only shows a button: mail scanners fetch links, a person presses the button
            row = _db.execute("SELECT lang FROM request WHERE id=?", (rid,)).fetchone() if rid is not None else None
            if not row:
                return self.out(400, page(TXT["en"]["bad"] + " / " + TXT["fr"]["bad"]))
            form = f'<form method="post" action="/api/confirm?t={html.escape(tok)}"><button class="btn p">{html.escape(TXT[row[0]]["confirm_btn"])}</button></form>'
            return self.out(200, page(TXT[row[0]]["confirm_q"], row[0], form))
        if u.path == "/api/unsubscribe":
            rid = read_token(tok, "u")
            if rid is None:
                return self.out(400, page(TXT["en"]["bad"] + " / " + TXT["fr"]["bad"]))
            row = _db.execute("SELECT lang FROM request WHERE id=?", (rid,)).fetchone()
            lang = row[0] if row else "en"
            form = (f'<form method="post" action="/api/unsubscribe?t={html.escape(tok)}"><button class="btn g">{html.escape(TXT[lang]["unsub_btn"])}</button></form>')
            return self.out(200, page(TXT[lang]["unsub_q"], lang, form))
        if u.path.startswith("/api/"):
            return self.out(404, b'{"ok":false}', "application/json")
        self.static(u.path)

    def do_POST(self):
        u = urlparse(self.path)
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = 0
        if n > 4096:
            return self.out(413, b'{"ok":false}', "application/json")
        raw = self.rfile.read(n) if n else b""
        try:
            data = json.loads(raw or b"{}")
            if not isinstance(data, dict):
                raise ValueError
        except ValueError:
            data = None
        send = lambda code, d: self.out(code, json.dumps(d).encode(), "application/json")
        if u.path == "/api/confirm":
            rid = read_token((parse_qs(u.query).get("t") or [""])[0], "c")
            r = confirm(rid) if rid is not None else None
            if r is None:
                return self.out(400, page(TXT["en"]["bad"]))
            return self.out(200, page(TXT[r]["ok_q"], r))
        if u.path == "/api/unsubscribe":
            rid = read_token((parse_qs(u.query).get("t") or [""])[0], "u")
            if rid is None:
                return self.out(400, page(TXT["en"]["bad"]))
            with _lock:
                row = _db.execute("SELECT lang FROM request WHERE id=?", (rid,)).fetchone()
                _db.execute("DELETE FROM request WHERE id=?", (rid,))
                _db.commit()
            lang = row[0] if row else "en"
            return self.out(200, page(TXT[lang]["unsub_ok"], lang))
        if data is None:
            return send(400, {"ok": False})
        if u.path == "/api/check":
            code, body = handle_check(data, self.ip())
            return send(code, body)
        if u.path == "/api/request":
            ok = handle_request(data, self.ip())
            return send(200 if ok else 400, {"ok": ok})
        if u.path == "/api/event":
            if data.get("type") == "fixpack_click":  # the only event the browser reports; the rest are counted server-side
                count_event("fixpack_click", data.get("lang"), self.ip())
            return self.out(204, b"", "application/json")
        self.out(404, b'{"ok":false}', "application/json")


if __name__ == "__main__":
    threading.Thread(target=retention_loop, daemon=True).start()
    ThreadingHTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8080"))), H).serve_forever()
