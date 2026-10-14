#!/usr/bin/env python3
"""Operator queue for the email mini-audit. Confirmed requests wait here; at most DAILY_CAP are released per UTC day.
usage: tools/queue.py next --db /data/check.db [--cap 20] [--dry-run]   prints TSV: email, url, country, lang, niche, unsubscribe link
       tools/queue.py stats --db /data/check.db
The batch goes to bin/build_audit.py (CitedBy kit) one row at a time; the email is only for sending the finished audit."""
import argparse, base64, hashlib, hmac, os, sqlite3, time
ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["next", "stats"]); ap.add_argument("--db", required=True)
ap.add_argument("--cap", type=int, default=20); ap.add_argument("--dry-run", action="store_true"); a = ap.parse_args()
def unsub_link(rid):  # same signed token as server.make_token("u", rid): no expiry, one-click remove
    b = lambda x: base64.urlsafe_b64encode(x).rstrip(b"=").decode()
    p = f"u:{rid}:0".encode()
    return os.environ["BASE_URL"].rstrip("/") + "/api/unsubscribe?t=" + b(p) + "." + b(hmac.new(os.environ["OPTIN_SECRET"].encode(), p, hashlib.sha256).digest())
db = sqlite3.connect(a.db); today = time.strftime("%Y-%m-%d", time.gmtime())
if a.cmd == "stats":
    print("waiting:", db.execute("SELECT count(*) FROM request WHERE confirmed_ts IS NOT NULL AND released_day IS NULL").fetchone()[0],
          "released today:", db.execute("SELECT count(*) FROM request WHERE released_day=?", (today,)).fetchone()[0],
          "unconfirmed:", db.execute("SELECT count(*) FROM request WHERE confirmed_ts IS NULL").fetchone()[0])
else:
    left = a.cap - db.execute("SELECT count(*) FROM request WHERE released_day=?", (today,)).fetchone()[0]
    rows = db.execute("SELECT id,email,url,country,lang,niche FROM request WHERE confirmed_ts IS NOT NULL AND released_day IS NULL ORDER BY confirmed_ts LIMIT ?", (max(left, 0),)).fetchall()
    for r in rows:
        print("\t".join([str(x) for x in r[1:]] + [unsub_link(r[0])]))
        if not a.dry_run: db.execute("UPDATE request SET released_day=? WHERE id=?", (today, r[0]))
    db.commit()
